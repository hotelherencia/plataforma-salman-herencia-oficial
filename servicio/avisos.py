"""Avisos activos al administrador (#353, 2026-11-18).

- `registrar_evento` deja el evento en la bandeja de salida dentro de la
  transacción de negocio (idempotente por tipo + referencia).
- `Despachador.despachar` envía cada evento reciente por cada canal
  configurado (correo SMTP y plantilla de WhatsApp Cloud API). Cada canal
  se enciende solo si su configuración está completa; sin canales no hace
  nada. Un envío fallido queda registrado y se reintenta hasta 5 veces.
- El contenido es mínimo: tipo, fechas, personas y el enlace a la bandeja;
  nunca el nombre ni el contacto del huésped.
"""
from __future__ import annotations

import json
import logging
import smtplib
import threading
import urllib.request
import uuid
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Callable

import psycopg

_log = logging.getLogger(__name__)
MAX_INTENTOS = 5
VENTANA_HORAS = 48


def registrar_evento(conexion: psycopg.Connection, tipo: str, referencia: str, datos: dict) -> None:
    conexion.execute(
        "INSERT INTO avisos_eventos (id, tipo, referencia, datos) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (tipo, referencia) DO NOTHING",
        (f"AVI-{uuid.uuid4().hex[:12]}", tipo, referencia, json.dumps(datos)),
    )


def solicitudes_recibidas(conexion: psycopg.Connection, empresa_id: str) -> int:
    (n,) = conexion.execute(
        "SELECT count(*) FROM solicitudes WHERE empresa_id = %s AND estado = 'recibida'", (empresa_id,)
    ).fetchone()
    return n


def _texto(evento: dict, front_url: str) -> tuple[str, str, str]:
    d = evento["datos"]
    enlace = f"{front_url.rstrip('/')}/hotel/solicitudes"
    asunto = f"Nueva solicitud de reserva: {d.get('tipo', '')} {d.get('inicio', '')} → {d.get('fin', '')}"
    cuerpo = (
        "Llegó una solicitud de reserva.\n\n"
        f"Tipo: {d.get('tipo', '')}\nLlegada: {d.get('inicio', '')}\nSalida: {d.get('fin', '')}\n"
        f"Personas: {d.get('personas', '')}\nOrigen: {d.get('origen', 'web')}\n\n"
        f"Revísala en {enlace}\n"
    )
    return asunto, cuerpo, enlace


@dataclass
class CanalCorreo:
    host: str
    puerto: int
    usuario: str | None
    clave: str | None
    remitente: str
    destino: str
    front_url: str
    nombre: str = "correo"
    enviar_smtp: Callable[[EmailMessage], None] | None = None

    def enviar(self, evento: dict) -> None:
        asunto, cuerpo, _ = _texto(evento, self.front_url)
        mensaje = EmailMessage()
        mensaje["Subject"] = asunto
        mensaje["From"] = self.remitente
        mensaje["To"] = self.destino
        mensaje.set_content(cuerpo)
        if self.enviar_smtp:
            self.enviar_smtp(mensaje)
            return
        with smtplib.SMTP(self.host, self.puerto, timeout=15) as smtp:
            smtp.starttls()
            if self.usuario:
                smtp.login(self.usuario, self.clave or "")
            smtp.send_message(mensaje)


@dataclass
class CanalWhatsapp:
    phone_number_id: str
    token: str
    destino: str
    plantilla: str
    idioma: str
    front_url: str
    nombre: str = "whatsapp"
    publicar: Callable[[str, dict, dict], None] | None = None

    def enviar(self, evento: dict) -> None:
        d = evento["datos"]
        _, _, enlace = _texto(evento, self.front_url)
        parametros = [str(d.get("tipo", "")), str(d.get("inicio", "")), str(d.get("fin", "")),
                      str(d.get("personas", "")), enlace]
        url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages"
        cuerpo = {
            "messaging_product": "whatsapp",
            "to": self.destino,
            "type": "template",
            "template": {
                "name": self.plantilla,
                "language": {"code": self.idioma},
                "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in parametros]}],
            },
        }
        cabeceras = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        if self.publicar:
            self.publicar(url, cuerpo, cabeceras)
            return
        peticion = urllib.request.Request(url, data=json.dumps(cuerpo).encode(), headers=cabeceras, method="POST")
        with urllib.request.urlopen(peticion, timeout=15) as respuesta:  # noqa: S310 (URL fija de Meta)
            respuesta.read()


def canales_desde_config(config) -> list:
    if config is None:
        return []
    canales: list = []
    if config.aviso_correo_destino and config.smtp_host and config.smtp_remitente:
        canales.append(CanalCorreo(config.smtp_host, config.smtp_puerto, config.smtp_usuario, config.smtp_clave,
                                   config.smtp_remitente, config.aviso_correo_destino, config.front_url))
    if (config.aviso_whatsapp_destino and config.whatsapp_access_token and config.whatsapp_phone_number_id
            and config.aviso_whatsapp_plantilla):
        canales.append(CanalWhatsapp(config.whatsapp_phone_number_id, config.whatsapp_access_token,
                                     config.aviso_whatsapp_destino, config.aviso_whatsapp_plantilla,
                                     config.aviso_whatsapp_idioma, config.front_url))
    return canales


class Despachador:
    def __init__(self, canales: list, database_url: str | None):
        self.canales = canales
        self.database_url = database_url
        self._parar = threading.Event()

    @property
    def activo(self) -> bool:
        return bool(self.canales and self.database_url)

    def despachar(self, limite: int = 20) -> dict:
        """Envía lo pendiente. Seguro con varios procesos (SKIP LOCKED)."""
        resultado = {"enviados": 0, "fallidos": 0}
        if not self.activo:
            return resultado
        with psycopg.connect(self.database_url) as conexion:
            for canal in self.canales:
                filas = conexion.execute(
                    "SELECT e.id, e.tipo, e.referencia, e.datos FROM avisos_eventos e "
                    "LEFT JOIN avisos_envios v ON v.evento_id = e.id AND v.canal = %s "
                    "WHERE e.creado_en > now() - make_interval(hours => %s) "
                    "AND (v.evento_id IS NULL OR (v.estado = 'fallido' AND v.intentos < %s)) "
                    "ORDER BY e.creado_en LIMIT %s FOR UPDATE OF e SKIP LOCKED",
                    (canal.nombre, VENTANA_HORAS, MAX_INTENTOS, limite),
                ).fetchall()
                for f in filas:
                    evento = {"id": f[0], "tipo": f[1], "referencia": f[2], "datos": f[3]}
                    try:
                        canal.enviar(evento)
                        estado, error = "enviado", None
                        resultado["enviados"] += 1
                    except Exception as exc:  # noqa: BLE001 (cualquier fallo de red o proveedor)
                        estado, error = "fallido", f"{type(exc).__name__}: {exc}"[:300]
                        resultado["fallidos"] += 1
                        _log.warning("aviso_fallido canal=%s evento=%s error=%s", canal.nombre, f[0], error)
                    conexion.execute(
                        "INSERT INTO avisos_envios (evento_id, canal, estado, intentos, ultimo_error) "
                        "VALUES (%s, %s, %s, 1, %s) ON CONFLICT (evento_id, canal) DO UPDATE SET "
                        "estado = EXCLUDED.estado, intentos = avisos_envios.intentos + 1, "
                        "ultimo_error = EXCLUDED.ultimo_error, actualizado_en = now()",
                        (f[0], canal.nombre, estado, error),
                    )
                conexion.commit()
        return resultado

    def despachar_seguro(self) -> None:
        try:
            self.despachar()
        except Exception:  # noqa: BLE001
            _log.exception("despachador_avisos_error")

    def iniciar(self, intervalo_segundos: int) -> None:
        """Reintentos periódicos (y avisos que no pasan por la ruta pública)."""
        if not self.activo or intervalo_segundos <= 0:
            return

        def ciclo():
            while not self._parar.wait(intervalo_segundos):
                self.despachar_seguro()

        threading.Thread(target=ciclo, name="despachador-avisos", daemon=True).start()

    def detener(self) -> None:
        self._parar.set()
