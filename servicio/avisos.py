"""Avisos activos al administrador (#353, 2026-11-18; correo completo 2026-11-19).

- `registrar_evento` deja el evento en la bandeja de salida dentro de la
  transacción de negocio (idempotente por tipo + referencia). Eventos:
  solicitud de reserva, consulta de la landing, reserva confirmada, pago
  registrado y el resumen diario de las 08:00 (hora de Chile).
- `Despachador.despachar` envía cada evento reciente por cada canal
  configurado (correo por el buzón de envío de la plataforma o por SMTP de
  variables, y plantilla de WhatsApp Cloud API solo para solicitudes). Cada
  canal se enciende solo si su configuración está completa; sin canales no
  hace nada. Un envío fallido queda registrado y se reintenta hasta 5 veces.
- Qué eventos avisan y a quién lo decide la administración del hotel
  (`avisos_preferencias`, pestaña Configuración → Avisos). Sin preferencia
  guardada: destino del buzón de envío, AVISO_CORREO_DESTINO o ADMIN_EMAIL.
- El contenido es mínimo: tipo, fechas, personas, monto si corresponde y el
  enlace directo a la pantalla; nunca el nombre ni el contacto del huésped.
"""
from __future__ import annotations

import html as html_mod
import json
import logging
import re
import smtplib
import threading
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Callable

import psycopg

_log = logging.getLogger(__name__)
MAX_INTENTOS = 5
VENTANA_HORAS = 48
MARCA = "Hotel Herencia"
PREFIJO_ASUNTO = f"[{MARCA}]"
MAX_DESTINATARIOS = 10
# Resumen diario: desde las 08:00 de Chile; si el servicio estuvo caído, se
# manda hasta el mediodía y después ya no (un resumen tardío confunde).
HORA_RESUMEN = 8
HORA_LIMITE_RESUMEN = 12

# Tipos de evento configurables: id → (nombre en pantalla, descripción).
TIPOS: dict[str, tuple[str, str]] = {
    "solicitud_recibida": ("Nueva solicitud de reserva", "Cuando un huésped pide reservar desde la web."),
    "consulta_recibida": ("Nueva consulta de la web", "Cuando llega una consulta desde el formulario de la landing."),
    "reserva_confirmada": ("Reserva confirmada", "Cuando se confirma una reserva (en recepción o al convertir una solicitud)."),
    "pago_registrado": ("Pago registrado", "Cuando se registra un pago confirmado en Caja."),
    "observacion_dueno": ("Observación del dueño", "Cuando el dueño deja una observación para la administración."),
    "resumen_diario": ("Resumen del día (08:00)", "Llegadas y Salidas de hoy y solicitudes pendientes, cada mañana."),
}
TIPO_PRUEBA = "prueba"

try:  # pragma: no cover - depende de la imagen
    from zoneinfo import ZoneInfo

    ZONA_HOTEL = ZoneInfo("America/Santiago")
except Exception:  # noqa: BLE001 (sin base de zonas: Chile continental, UTC-3)
    ZONA_HOTEL = timezone(timedelta(hours=-3))

_RE_CORREO = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$")


class SinDestinatarios(Exception):
    """No hay a quién enviar: queda «omitido», no se reintenta."""


class PreferenciaInvalida(Exception):
    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


def ahora_hotel() -> datetime:
    return datetime.now(ZONA_HOTEL)


def registrar_evento(conexion: psycopg.Connection, tipo: str, referencia: str, datos: dict,
                     empresa_id: str | None = None) -> None:
    conexion.execute(
        "INSERT INTO avisos_eventos (id, tipo, referencia, datos, empresa_id) VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (tipo, referencia) DO NOTHING",
        (f"AVI-{uuid.uuid4().hex[:12]}", tipo, referencia, json.dumps(datos), empresa_id),
    )


def solicitudes_recibidas(conexion: psycopg.Connection, empresa_id: str) -> int:
    (n,) = conexion.execute(
        "SELECT count(*) FROM solicitudes WHERE empresa_id = %s AND estado = 'recibida'", (empresa_id,)
    ).fetchone()
    return n


# --- preferencias (qué avisa y a quién) ------------------------------------

def _lista_correos(valor) -> list[str]:
    if valor is None:
        return []
    if isinstance(valor, str):
        valor = re.split(r"[,;\s]+", valor)
    if not isinstance(valor, list):
        raise PreferenciaInvalida("los destinatarios deben ser una lista de correos")
    limpios: list[str] = []
    for v in valor:
        if not isinstance(v, str):
            raise PreferenciaInvalida("los destinatarios deben ser correos")
        c = v.strip().lower()
        if not c:
            continue
        if len(c) > 254 or not _RE_CORREO.fullmatch(c):
            raise PreferenciaInvalida(f"«{v.strip()[:60]}» no es un correo válido")
        if c not in limpios:
            limpios.append(c)
    if len(limpios) > MAX_DESTINATARIOS:
        raise PreferenciaInvalida(f"máximo {MAX_DESTINATARIOS} destinatarios por aviso")
    return limpios


def correos_desde_texto(texto: str | None) -> list[str]:
    """«a@x.cl, b@x.cl» (variables de entorno) → lista; ignora lo inválido."""
    return [c for c in (s.strip().lower() for s in re.split(r"[,;\s]+", texto or "")) if _RE_CORREO.fullmatch(c)]


def preferencias(conexion: psycopg.Connection, empresa_id: str | None) -> dict[str, dict]:
    filas = {}
    if empresa_id:
        filas = {f[0]: f for f in conexion.execute(
            "SELECT tipo, activo, destinatarios, actualizado_por, actualizado_en FROM avisos_preferencias "
            "WHERE empresa_id = %s", (empresa_id,)).fetchall()}
    resultado = {}
    for tipo, (nombre, descripcion) in TIPOS.items():
        f = filas.get(tipo)
        resultado[tipo] = {
            "tipo": tipo, "nombre": nombre, "descripcion": descripcion,
            "activo": f[1] if f else True,
            "destinatarios": list(f[2]) if f else [],
            "actualizado_por": f[3] if f else None,
            "actualizado_en": f[4].isoformat() if f else None,
        }
    return resultado


def guardar_preferencias(conexion: psycopg.Connection, empresa_id: str, cuerpo: dict, actor: str) -> dict:
    """Cuerpo: {"preferencias": [{"tipo", "activo", "destinatarios"}]}. Todo o nada."""
    lista = cuerpo.get("preferencias") if isinstance(cuerpo, dict) else None
    if not isinstance(lista, list) or not lista:
        raise PreferenciaInvalida("faltan las preferencias")
    limpias = {}
    for p in lista:
        if not isinstance(p, dict) or p.get("tipo") not in TIPOS:
            raise PreferenciaInvalida("tipo de aviso desconocido")
        if not isinstance(p.get("activo", True), bool):
            raise PreferenciaInvalida("«activo» debe ser verdadero o falso")
        try:
            destinos = _lista_correos(p.get("destinatarios"))
        except PreferenciaInvalida as error:
            raise PreferenciaInvalida(f"{TIPOS[p['tipo']][0]}: {error.detalle}")
        limpias[p["tipo"]] = (p.get("activo", True), destinos)
    for tipo, (activo, destinos) in limpias.items():
        conexion.execute(
            "INSERT INTO avisos_preferencias (empresa_id, tipo, activo, destinatarios, actualizado_por) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (empresa_id, tipo) DO UPDATE SET "
            "activo = EXCLUDED.activo, destinatarios = EXCLUDED.destinatarios, "
            "actualizado_por = EXCLUDED.actualizado_por, actualizado_en = now()",
            (empresa_id, tipo, activo, json.dumps(destinos), actor),
        )
    from . import seguridad

    seguridad.auditar(conexion, actor, "avisos_preferencias", empresa_id,
                      ", ".join(f"{t}:{'on' if a else 'off'}:{len(d)}" for t, (a, d) in sorted(limpias.items())))
    return {"preferencias": list(preferencias(conexion, empresa_id).values())}


def ultimos_envios(conexion: psycopg.Connection, empresa_id: str, limite: int = 20) -> list[dict]:
    filas = conexion.execute(
        "SELECT e.id, e.tipo, e.referencia, e.creado_en, v.canal, v.estado, v.intentos, v.ultimo_error, "
        "v.actualizado_en, v.destinatarios FROM avisos_envios v JOIN avisos_eventos e ON e.id = v.evento_id "
        "WHERE e.empresa_id = %s OR e.empresa_id IS NULL ORDER BY v.actualizado_en DESC LIMIT %s",
        (empresa_id, limite),
    ).fetchall()
    resultado = []
    for f in filas:
        estado = f[5]
        if estado == "fallido" and f[6] < MAX_INTENTOS and f[3] > datetime.now(timezone.utc) - timedelta(hours=VENTANA_HORAS):
            estado = "reintentando"
        resultado.append({
            "evento_id": f[0], "tipo": f[1], "nombre": TIPOS.get(f[1], ("Correo de prueba",))[0],
            "referencia": f[2], "creado_en": f[3].astimezone(ZONA_HOTEL).replace(tzinfo=None).isoformat(timespec="minutes"),
            "canal": f[4], "estado": estado, "intentos": f[6], "detalle": detalle_legible(f[7]),
            "actualizado_en": f[8].astimezone(ZONA_HOTEL).replace(tzinfo=None).isoformat(timespec="minutes"),
            "destinatarios": [d for d in (f[9] or "").split(",") if d],
        })
    return resultado


def detalle_legible(error: str | None) -> str | None:
    """El error técnico se traduce a algo que la administración entienda."""
    if not error:
        return None
    e = error.lower()
    if e.startswith("omitido:"):
        return error.split(":", 1)[1].strip()
    if "authentication" in e or "smtpauthenticationerror" in e or "535" in e or "invalid_grant" in e:
        return "El servidor de correo rechazó el usuario o la clave del buzón de envío."
    if "timeout" in e or "timed out" in e:
        return "El servidor de correo no respondió a tiempo."
    if "gaierror" in e or "name or service" in e or "connectionrefused" in e or "connection refused" in e:
        return "No se pudo conectar con el servidor de correo (revisa servidor y puerto)."
    if "recipient" in e or "smtprecipientsrefused" in e:
        return "El servidor de correo rechazó a uno de los destinatarios."
    return "No se pudo enviar; se reintenta automáticamente."


# --- contenido de los correos ----------------------------------------------

@dataclass
class Mensaje:
    asunto: str
    texto: str
    html: str
    enlace: str


def _fecha(iso) -> str:
    try:
        return date.fromisoformat(str(iso)[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return str(iso or "")


def _noches(inicio, fin) -> int | None:
    try:
        return (date.fromisoformat(str(fin)[:10]) - date.fromisoformat(str(inicio)[:10])).days
    except ValueError:
        return None


def _clp(monto) -> str:
    try:
        n = int(monto)
    except (TypeError, ValueError):
        return ""
    return ("-" if n < 0 else "") + "$" + f"{abs(n):,}".replace(",", ".")


def _plural(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"


def _tipo_hab(tipo) -> str:
    t = str(tipo or "").replace("_", " ").strip()
    return t[:1].upper() + t[1:] if t else ""


def _html(titulo: str, filas: list[tuple[str, str]], enlace: str, boton: str,
          secciones: list[tuple[str, list[str]]] = (), nota: str = "") -> str:
    e = html_mod.escape
    tabla = "".join(
        f'<tr><td style="padding:6px 12px 6px 0;color:#5b6b63;white-space:nowrap;vertical-align:top">{e(k)}</td>'
        f'<td style="padding:6px 0;color:#1f2a24;font-weight:600">{e(v)}</td></tr>' for k, v in filas)
    bloques = "".join(
        f'<h2 style="font-size:16px;margin:20px 0 6px;color:#1f2a24">{e(t)}</h2>'
        + ('<ul style="margin:0;padding-left:20px">' + "".join(f'<li style="margin:2px 0">{e(i)}</li>' for i in items) + "</ul>"
           if items else '<p style="margin:0;color:#5b6b63">Ninguna.</p>')
        for t, items in secciones)
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        '<body style="margin:0;padding:0;background:#f4f1ea">'
        '<div style="max-width:560px;margin:0 auto;padding:16px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.45">'
        f'<p style="margin:0 0 12px;color:#2f5d46;font-weight:700;letter-spacing:.02em">{e(MARCA)}</p>'
        '<div style="background:#ffffff;border-radius:10px;padding:20px;border:1px solid #e3ddd0">'
        f'<h1 style="font-size:19px;margin:0 0 12px;color:#1f2a24">{e(titulo)}</h1>'
        f'<table role="presentation" style="border-collapse:collapse;width:100%">{tabla}</table>{bloques}'
        f'<p style="margin:20px 0 4px"><a href="{e(enlace)}" style="display:inline-block;background:#2f5d46;color:#ffffff;'
        f'text-decoration:none;padding:12px 18px;border-radius:8px;font-weight:700">{e(boton)}</a></p>'
        f'<p style="margin:8px 0 0;font-size:12px;color:#5b6b63;word-break:break-all">{e(enlace)}</p>'
        '</div>'
        + (f'<p style="font-size:12px;color:#5b6b63;margin:12px 4px">{e(nota)}</p>' if nota else "")
        + f'<p style="font-size:12px;color:#5b6b63;margin:12px 4px">Aviso automático de la plataforma de {e(MARCA)}. '
        'Qué avisos llegan y a quién se cambia en Configuración → Avisos.</p>'
        '</div></body></html>'
    )


def _texto_plano(titulo: str, filas: list[tuple[str, str]], enlace: str, boton: str,
                 secciones: list[tuple[str, list[str]]] = (), nota: str = "") -> str:
    lineas = [titulo, ""] + [f"{k}: {v}" for k, v in filas]
    for t, items in secciones:
        lineas += ["", f"{t}:"] + ([f"- {i}" for i in items] if items else ["- Ninguna."])
    lineas += ["", f"{boton}: {enlace}"]
    if nota:
        lineas += ["", nota]
    lineas += ["", "--", f"Aviso automático de la plataforma de {MARCA}.",
               "Qué avisos llegan y a quién se cambia en Configuración → Avisos."]
    return "\n".join(lineas) + "\n"


def componer(evento: dict, front_url: str) -> Mensaje:
    """Asunto, texto, HTML y enlace directo del aviso, sin datos del huésped."""
    d = evento.get("datos") or {}
    tipo, ref = evento.get("tipo"), evento.get("referencia", "")
    base = (front_url or "").rstrip("/")
    secciones: list[tuple[str, list[str]]] = []
    nota = ""
    if tipo == "solicitud_recibida":
        noches = _noches(d.get("inicio"), d.get("fin"))
        titulo = "Llegó una solicitud de reserva"
        asunto = f"Nueva solicitud de reserva: {_tipo_hab(d.get('tipo'))} · Llegada {_fecha(d.get('inicio'))}"
        filas = [("Tipo de habitación", _tipo_hab(d.get("tipo"))), ("Llegada", _fecha(d.get("inicio"))),
                 ("Salida", _fecha(d.get("fin")))]
        if noches is not None:
            filas.append(("Noches", str(noches)))
        filas += [("Personas", str(d.get("personas", ""))), ("Origen", str(d.get("origen") or "web"))]
        enlace, boton = f"{base}/hotel/solicitudes?id={ref}", "Revisar la solicitud"
    elif tipo == "consulta_recibida":
        titulo = "Llegó una consulta desde la web"
        asunto = "Nueva consulta desde la web" + (f" · Llegada {_fecha(d.get('inicio'))}" if d.get("inicio") else "")
        filas = []
        if d.get("inicio"):
            filas.append(("Llegada", _fecha(d.get("inicio"))))
        if d.get("fin"):
            filas.append(("Salida", _fecha(d.get("fin"))))
        if d.get("personas"):
            filas.append(("Personas", str(d.get("personas"))))
        filas.append(("Trae mensaje", "Sí" if d.get("con_mensaje") else "No"))
        filas.append(("Origen", "Formulario de contacto de la landing"))
        enlace, boton = f"{base}/hotel/leads?id={ref}", "Ver la consulta"
        nota = "Los datos de contacto están en la plataforma, no en este correo."
    elif tipo == "reserva_confirmada":
        noches = _noches(d.get("inicio"), d.get("fin"))
        titulo = "Se confirmó una reserva"
        asunto = f"Reserva confirmada: {d.get('habitacion_id', '')} · Llegada {_fecha(d.get('inicio'))}"
        filas = [("Reserva", ref), ("Habitación", str(d.get("habitacion_id", ""))),
                 ("Llegada", _fecha(d.get("inicio"))), ("Salida", _fecha(d.get("fin")))]
        if noches is not None:
            filas.append(("Noches", str(noches)))
        if d.get("personas"):
            filas.append(("Personas", str(d.get("personas"))))
        if d.get("total_clp") is not None:
            filas.append(("Total (IVA incluido)", _clp(d.get("total_clp"))))
        enlace, boton = f"{base}/hotel/reservas/{ref}", "Ver la reserva"
    elif tipo == "pago_registrado":
        reserva = d.get("reserva_id", "")
        titulo = "Se registró un pago"
        tipo_pago = {"total": "Pago total (cuenta saldada)", "parcial": "Pago parcial",
                     "exceso": "Pago mayor al saldo"}.get(d.get("tipo_pago"), "Pago")
        asunto = f"Pago registrado: {_clp(d.get('monto_clp'))} · reserva {reserva}"
        filas = [("Monto", _clp(d.get("monto_clp"))), ("Tipo", tipo_pago), ("Reserva", reserva)]
        if d.get("habitacion_id"):
            filas.append(("Habitación", str(d.get("habitacion_id"))))
        if d.get("saldo_despues_clp") is not None:
            filas.append(("Saldo pendiente", _clp(max(int(d.get("saldo_despues_clp")), 0))))
        enlace, boton = f"{base}/hotel/reservas/{reserva}", "Ver la reserva"
    elif tipo == "resumen_diario":
        llegadas, salidas = d.get("llegadas") or [], d.get("salidas") or []
        pendientes = int(d.get("solicitudes_pendientes") or 0)
        titulo = f"Resumen del {_fecha(d.get('fecha'))}"
        asunto = (f"Resumen del {_fecha(d.get('fecha'))}: {_plural(len(llegadas), 'Llegada')}, "
                  f"{_plural(len(salidas), 'Salida')}, {_plural(pendientes, 'solicitud pendiente', 'solicitudes pendientes')}")
        filas = [("Llegadas de hoy", str(len(llegadas))), ("Salidas de hoy", str(len(salidas))),
                 ("Solicitudes por responder", str(pendientes))]

        def item(r: dict) -> str:
            partes = [str(r.get("habitacion_id", ""))]
            if r.get("noches") is not None:
                partes.append(_plural(int(r["noches"]), "noche"))
            if r.get("personas"):
                partes.append(_plural(int(r["personas"]), "persona"))
            return " · ".join(p for p in partes if p)

        secciones = [("Llegadas", [item(r) for r in llegadas]), ("Salidas", [item(r) for r in salidas])]
        enlace, boton = f"{base}/hotel/panel", "Abrir el panel de hoy"
    elif tipo == TIPO_PRUEBA:
        titulo = "Correo de prueba de avisos"
        asunto = "Correo de prueba de avisos"
        filas = [("Enviado", ahora_hotel().strftime("%d/%m/%Y %H:%M")), ("Resultado", "Si lees esto, los avisos llegan bien.")]
        enlace, boton = f"{base}/hotel/configuracion?seccion=avisos", "Ver la configuración de avisos"
    else:
        titulo = "Aviso de la plataforma"
        asunto = "Aviso de la plataforma"
        filas = [("Tipo", str(tipo)), ("Referencia", str(ref))]
        enlace, boton = f"{base}/hotel/panel", "Abrir la plataforma"
    return Mensaje(f"{PREFIJO_ASUNTO} {asunto}", _texto_plano(titulo, filas, enlace, boton, secciones, nota),
                   _html(titulo, filas, enlace, boton, secciones, nota), enlace)


def _texto(evento: dict, front_url: str) -> tuple[str, str, str]:
    """Compatibilidad: (asunto, cuerpo en texto, enlace)."""
    m = componer(evento, front_url)
    return m.asunto, m.texto, m.enlace


def mensaje_correo(m: Mensaje, remitente: str, destinos: list[str]) -> EmailMessage:
    mensaje = EmailMessage()
    mensaje["Subject"] = m.asunto
    mensaje["From"] = remitente
    mensaje["To"] = ", ".join(destinos)
    mensaje.set_content(m.texto)
    mensaje.add_alternative(m.html, subtype="html")
    return mensaje


def _destinos(evento: dict, propio: str | None) -> list[str]:
    """Preferencia guardada → destino propio del canal → defecto del proceso."""
    destinos = list(evento.get("destinos") or []) or correos_desde_texto(propio) or list(evento.get("destinos_defecto") or [])
    if not destinos:
        raise SinDestinatarios("omitido: no hay destinatarios configurados")
    return destinos


# --- canales -----------------------------------------------------------------

@dataclass
class CanalCorreo:
    host: str
    puerto: int
    usuario: str | None
    clave: str | None
    remitente: str
    destino: str | None
    front_url: str
    nombre: str = "correo"
    enviar_smtp: Callable[[EmailMessage], None] | None = None

    def enviar(self, evento: dict) -> list[str]:
        destinos = _destinos(evento, self.destino)
        mensaje = mensaje_correo(componer(evento, self.front_url), self.remitente, destinos)
        if self.enviar_smtp:
            self.enviar_smtp(mensaje)
            return destinos
        with smtplib.SMTP(self.host, self.puerto, timeout=15) as smtp:
            smtp.starttls()
            if self.usuario:
                smtp.login(self.usuario, self.clave or "")
            smtp.send_message(mensaje)
        return destinos


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
    # La plantilla aprobada por Meta es la de solicitudes de reserva.
    tipos: tuple = ("solicitud_recibida",)

    def enviar(self, evento: dict) -> None:
        d = evento["datos"]
        enlace = componer(evento, self.front_url).enlace
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
    # El destino puede venir de las preferencias guardadas; basta servidor y remitente.
    if config.smtp_host and config.smtp_remitente:
        canales.append(CanalCorreo(config.smtp_host, config.smtp_puerto, config.smtp_usuario, config.smtp_clave,
                                   config.smtp_remitente, config.aviso_correo_destino, config.front_url))
    if (config.aviso_whatsapp_destino and config.whatsapp_access_token and config.whatsapp_phone_number_id
            and config.aviso_whatsapp_plantilla):
        canales.append(CanalWhatsapp(config.whatsapp_phone_number_id, config.whatsapp_access_token,
                                     config.aviso_whatsapp_destino, config.aviso_whatsapp_plantilla,
                                     config.aviso_whatsapp_idioma, config.front_url))
    return canales


def destinos_defecto_desde_config(config) -> list[str]:
    if config is None:
        return []
    return correos_desde_texto(config.aviso_correo_destino) or correos_desde_texto(config.admin_email)


@dataclass
class CanalBuzon:
    """#355: correo de avisos por el buzón de envío configurado en la
    plataforma (SMTP, API de Gmail o Microsoft Graph)."""
    buzon: object
    front_url: str
    nombre: str = "correo"

    def enviar(self, evento: dict) -> list[str]:
        destinos = _destinos(evento, (getattr(self.buzon, "parametros", None) or {}).get("destino"))
        m = componer(evento, self.front_url)
        self.buzon.enviar(m.asunto, m.texto, destinos=destinos, html=m.html)
        return destinos


# --- resumen diario ------------------------------------------------------------

def datos_resumen(conexion: psycopg.Connection, empresa_id: str, hoy: date) -> dict:
    def reservas(condicion: str) -> list[dict]:
        return [
            {"habitacion_id": f[0], "noches": (f[2] - f[1]).days, "personas": f[3]}
            for f in conexion.execute(
                "SELECT habitacion_id, inicio, fin, personas FROM reservas "
                f"WHERE empresa_id = %s AND {condicion} = %s ORDER BY habitacion_id, id",
                (empresa_id, hoy),
            ).fetchall()
        ]

    return {
        "fecha": hoy.isoformat(),
        "llegadas": reservas("estado = 'confirmada' AND inicio"),
        "salidas": reservas("estado = 'en_estadia' AND fin"),
        "solicitudes_pendientes": solicitudes_recibidas(conexion, empresa_id),
    }


def programar_resumen(conexion: psycopg.Connection, empresa_id: str, ahora: datetime | None = None) -> bool:
    """Registra el resumen del día una sola vez por fecha (UNIQUE tipo +
    referencia), entre las 08:00 y el mediodía de Chile, si está encendido."""
    ahora = (ahora or ahora_hotel()).astimezone(ZONA_HOTEL)
    if not (HORA_RESUMEN <= ahora.hour < HORA_LIMITE_RESUMEN):
        return False
    if not preferencias(conexion, empresa_id)["resumen_diario"]["activo"]:
        return False
    hoy = ahora.date()
    referencia = f"{empresa_id}:{hoy.isoformat()}"
    if conexion.execute("SELECT 1 FROM avisos_eventos WHERE tipo = 'resumen_diario' AND referencia = %s",
                        (referencia,)).fetchone():
        return False
    registrar_evento(conexion, "resumen_diario", referencia, datos_resumen(conexion, empresa_id, hoy), empresa_id)
    return True


# --- despacho ------------------------------------------------------------------

class Despachador:
    def __init__(self, canales: list, database_url: str | None, front_url: str = "", usar_buzones: bool = True,
                 empresa_id: str | None = None, destinos_defecto: list[str] | None = None,
                 resumen_diario: bool = False):
        self.canales = canales
        self.database_url = database_url
        self.front_url = front_url
        self.usar_buzones = usar_buzones
        self.empresa_id = empresa_id
        self.destinos_defecto = list(destinos_defecto or [])
        self.resumen_diario = resumen_diario
        self._parar = threading.Event()

    @property
    def activo(self) -> bool:
        return bool(self.database_url and (self.canales or self.usar_buzones))

    def canales_vigentes(self, conexion: psycopg.Connection) -> list:
        """Los de variables de entorno; el buzón de envío activo de la
        plataforma (#355) reemplaza al correo por SMTP de entorno."""
        canales = list(self.canales)
        if self.usar_buzones:
            from . import correo

            buzon = correo.buzon_envio_activo(conexion)
            if buzon is not None:
                canales = [c for c in canales if c.nombre != "correo"] + [CanalBuzon(buzon, self.front_url)]
        return canales

    def canal_correo(self, conexion: psycopg.Connection):
        return next((c for c in self.canales_vigentes(conexion) if c.nombre == "correo"), None)

    def _preparar(self, conexion, evento: dict, cache: dict) -> str | None:
        """Agrega destinatarios al evento. Devuelve el motivo si se omite."""
        empresa = evento.get("empresa_id") or self.empresa_id
        if empresa not in cache:
            cache[empresa] = preferencias(conexion, empresa)
        evento["destinos_defecto"] = self.destinos_defecto
        if evento["tipo"] == TIPO_PRUEBA:
            evento["destinos"] = (evento.get("datos") or {}).get("destinos") or []
            return None
        pref = cache[empresa].get(evento["tipo"])
        if pref is None:
            evento["destinos"] = []
            return None
        if not pref["activo"]:
            return "omitido: aviso apagado en Configuración → Avisos"
        if evento["tipo"] == "resumen_diario":
            fecha = (evento.get("datos") or {}).get("fecha")
            if fecha and fecha != ahora_hotel().date().isoformat():
                return "omitido: el resumen era de otro día"
        evento["destinos"] = pref["destinatarios"]
        return None

    def enviar_evento(self, conexion: psycopg.Connection, canal, evento: dict, cache: dict | None = None) -> str:
        """Envía un evento por un canal y deja el resultado en avisos_envios."""
        cache = {} if cache is None else cache
        motivo = self._preparar(conexion, evento, cache)
        destinos = None
        if motivo:
            estado, error = "omitido", motivo
        else:
            try:
                destinos = canal.enviar(evento)
                estado, error = "enviado", None
            except SinDestinatarios as exc:
                estado, error = "omitido", str(exc)
            except Exception as exc:  # noqa: BLE001 (cualquier fallo de red o proveedor)
                estado, error = "fallido", f"{type(exc).__name__}: {exc}"[:300]
                _log.warning("aviso_fallido canal=%s evento=%s error=%s", canal.nombre, evento["id"], type(exc).__name__)
        # Una prueba fallida no se reintenta sola: la persona vuelve a apretar el botón.
        intentos_fallo = MAX_INTENTOS if evento["tipo"] == TIPO_PRUEBA and estado == "fallido" else 1
        conexion.execute(
            "INSERT INTO avisos_envios (evento_id, canal, estado, intentos, ultimo_error, destinatarios) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (evento_id, canal) DO UPDATE SET "
            "estado = EXCLUDED.estado, intentos = avisos_envios.intentos + 1, "
            "ultimo_error = EXCLUDED.ultimo_error, destinatarios = EXCLUDED.destinatarios, actualizado_en = now()",
            (evento["id"], canal.nombre, estado, intentos_fallo, error,
             ",".join(destinos) if isinstance(destinos, list) else None),
        )
        return estado

    def despachar(self, limite: int = 20) -> dict:
        """Envía lo pendiente. Seguro con varios procesos (SKIP LOCKED)."""
        resultado = {"enviados": 0, "fallidos": 0}
        if not self.activo:
            return resultado
        with psycopg.connect(self.database_url) as conexion:
            cache: dict = {}
            for canal in self.canales_vigentes(conexion):
                tipos = list(getattr(canal, "tipos", None) or [])
                filas = conexion.execute(
                    "SELECT e.id, e.tipo, e.referencia, e.datos, e.empresa_id FROM avisos_eventos e "
                    "LEFT JOIN avisos_envios v ON v.evento_id = e.id AND v.canal = %s "
                    "WHERE e.creado_en > now() - make_interval(hours => %s) "
                    "AND (v.evento_id IS NULL OR (v.estado = 'fallido' AND v.intentos < %s)) "
                    "AND (cardinality(%s::text[]) = 0 OR e.tipo = ANY(%s::text[])) "
                    "AND (e.tipo <> %s OR %s = 'correo') "
                    "ORDER BY e.creado_en LIMIT %s FOR UPDATE OF e SKIP LOCKED",
                    (canal.nombre, VENTANA_HORAS, MAX_INTENTOS, tipos, tipos, TIPO_PRUEBA, canal.nombre, limite),
                ).fetchall()
                for f in filas:
                    evento = {"id": f[0], "tipo": f[1], "referencia": f[2], "datos": f[3], "empresa_id": f[4]}
                    estado = self.enviar_evento(conexion, canal, evento, cache)
                    if estado == "enviado":
                        resultado["enviados"] += 1
                    elif estado == "fallido":
                        resultado["fallidos"] += 1
                conexion.commit()
        return resultado

    def enviar_prueba(self, empresa_id: str, destinos: list[str]) -> dict:
        """«Enviar correo de prueba»: sale ahora por el canal de correo vigente
        y queda en «últimos envíos»."""
        if not self.database_url:
            return {"ok": False, "detalle": "El servicio no tiene base de datos configurada."}
        with psycopg.connect(self.database_url) as conexion:
            canal = self.canal_correo(conexion)
            if canal is None:
                return {"ok": False, "detalle": "Aún no hay desde dónde enviar: configura el buzón de envío de avisos "
                                                "en la pestaña Correo."}
            evento_id = f"AVI-{uuid.uuid4().hex[:12]}"
            datos = {"destinos": destinos}
            conexion.execute(
                "INSERT INTO avisos_eventos (id, tipo, referencia, datos, empresa_id) VALUES (%s, %s, %s, %s, %s)",
                (evento_id, TIPO_PRUEBA, evento_id, json.dumps(datos), empresa_id),
            )
            evento = {"id": evento_id, "tipo": TIPO_PRUEBA, "referencia": evento_id, "datos": datos,
                      "empresa_id": empresa_id}
            estado = self.enviar_evento(conexion, canal, evento)
            fila = conexion.execute(
                "SELECT ultimo_error, destinatarios FROM avisos_envios WHERE evento_id = %s", (evento_id,)).fetchone()
            conexion.commit()
        if estado == "enviado":
            lista = [d for d in (fila[1] or "").split(",") if d]
            return {"ok": True, "destinatarios": lista,
                    "detalle": f"Correo de prueba enviado a {', '.join(lista)}. Revisa la bandeja de entrada (y spam)."}
        return {"ok": False, "detalle": detalle_legible(fila[0]) or "No se pudo enviar."}

    def ciclo(self) -> None:
        """Una vuelta del hilo: resumen diario (si corresponde) y despacho."""
        if self.resumen_diario and self.empresa_id and self.database_url:
            try:
                with psycopg.connect(self.database_url) as conexion:
                    if self.canales_vigentes(conexion):
                        programar_resumen(conexion, self.empresa_id)
                    conexion.commit()
            except Exception:  # noqa: BLE001
                _log.exception("resumen_diario_error")
        self.despachar_seguro()

    def despachar_seguro(self) -> None:
        try:
            self.despachar()
        except Exception:  # noqa: BLE001
            _log.exception("despachador_avisos_error")

    def iniciar(self, intervalo_segundos: int) -> None:
        """Reintentos periódicos, eventos que no pasan por la ruta pública y
        el resumen de la mañana."""
        if not self.activo or intervalo_segundos <= 0:
            return

        def bucle():
            while not self._parar.wait(intervalo_segundos):
                self.ciclo()

        threading.Thread(target=bucle, name="despachador-avisos", daemon=True).start()

    def detener(self) -> None:
        self._parar.set()
