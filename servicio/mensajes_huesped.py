"""Mensajes preformateados al huésped (#452) y datos que faltan para contratar (#454).

La plataforma arma el texto de cada plantilla con los datos de la reserva y deja tres salidas:
copiar, abrir WhatsApp (`wa.me`) y enviar por el buzón de correo de la plataforma. No envía solo:
cada envío lo decide una persona de recepción y queda registrado sin el cuerpo del mensaje.
"""
from __future__ import annotations

import re
import uuid
from datetime import date
from urllib.parse import quote

import psycopg

from . import canal_publico, operacion, seguridad

MARCA = "Hotel Herencia"
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

# id → (nombre en pantalla, asunto, texto). Variables entre llaves; las que faltan quedan vacías.
PLANTILLAS: dict[str, tuple[str, str, str]] = {
    "confirmacion": (
        "Confirmación de reserva",
        "Tu reserva {reserva} en " + MARCA,
        "Hola {nombre}, tu reserva {reserva} en " + MARCA + " está confirmada.\n"
        "Llegada: {llegada}. Salida: {salida} ({noches} noche(s)). Habitación: {tipo}.\n"
        "Total: {total}.\n{cancelacion}\n"
        "Si necesitas cambiar algo, responde este mensaje.",
    ),
    "recordatorio": (
        "Recordatorio antes de la Llegada",
        "Te esperamos el {llegada} en " + MARCA,
        "Hola {nombre}, te recordamos que tu Llegada a " + MARCA + " es el {llegada} (reserva {reserva}).\n"
        "Para agilizar el ingreso, ten a mano el documento de todas las personas que se alojan.",
    ),
    "solicitar_datos": (
        "Pedir datos que faltan",
        "Datos para tu reserva {reserva}",
        "Hola {nombre}, para completar tu reserva {reserva} en " + MARCA + " necesitamos: {faltantes}.\n"
        "Puedes responder este mensaje con esos datos.",
    ),
    "cancelacion": (
        "Cancelación de reserva",
        "Cancelación de tu reserva {reserva}",
        "Hola {nombre}, registramos la cancelación de tu reserva {reserva} ({llegada} al {salida}).\n"
        "{cancelacion}",
    ),
    "gracias": (
        "Gracias por tu estadía",
        "Gracias por alojarte en " + MARCA,
        "Hola {nombre}, gracias por alojarte en " + MARCA + ". Esperamos verte pronto.",
    ),
}


class PlantillaDesconocida(operacion.OperacionInvalida):
    """409: la plantilla no existe."""


class SinDestino(operacion.OperacionInvalida):
    """409: la reserva no tiene correo para ese envío."""


class CanalNoConfigurado(operacion.OperacionInvalida):
    """409: no hay buzón de envío activo."""


def _fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")


def _clp(monto: int | None) -> str:
    return "$" + f"{int(monto or 0):,}".replace(",", ".")


def enmascarar(destino: str) -> str:
    if "@" in destino:
        usuario, dominio = destino.split("@", 1)
        return usuario[:1] + "***@" + dominio
    return destino[:3] + "***" + destino[-2:] if len(destino) > 5 else "***"


def contacto_de_reserva(conexion: psycopg.Connection, reserva_id: str) -> dict:
    """Correo y teléfono del titular; si faltan, los de la solicitud de la que nació la reserva."""
    fila = conexion.execute(
        "SELECT h.correo, h.telefono FROM reserva_huespedes rh JOIN huespedes h ON h.id = rh.huesped_id "
        "WHERE rh.reserva_id = %s AND rh.rol = 'titular'", (reserva_id,),
    ).fetchone()
    correo, telefono = (fila or (None, None))
    if not correo or not telefono:
        sol = conexion.execute(
            "SELECT huesped_correo, huesped_telefono FROM solicitudes WHERE reserva_id = %s", (reserva_id,),
        ).fetchone()
        if sol:
            correo = correo or sol[0]
            telefono = telefono or sol[1]
    return {"correo": correo or None, "telefono": canal_publico.telefono_e164(telefono) if telefono else None}


def datos_faltantes(conexion: psycopg.Connection, reserva_id: str) -> list[str]:
    """Qué falta para poder contratar y recibir al huésped (#454); lista vacía = completo."""
    r = conexion.execute(
        "SELECT huesped_nombre, huesped_documento, huesped_documento_tipo FROM reservas WHERE id = %s",
        (reserva_id,),
    ).fetchone()
    if r is None:
        return []
    contacto = contacto_de_reserva(conexion, reserva_id)
    faltan = []
    if not contacto["correo"] and not contacto["telefono"]:
        faltan.append("un correo o un teléfono de contacto")
    elif not contacto["correo"]:
        faltan.append("el correo electrónico")
    elif not contacto["telefono"]:
        faltan.append("el teléfono")
    if not r[1] or not r[2]:
        faltan.append("el documento del titular (RUT o pasaporte)")
    return faltan


def _variables(conexion: psycopg.Connection, empresa_id: str, reserva_id: str) -> dict:
    r = conexion.execute(
        "SELECT r.huesped_nombre, r.inicio, r.fin, r.total_aceptado_clp, h.tipo, r.politica_snapshot "
        "FROM reservas r JOIN habitaciones h ON h.id = r.habitacion_id "
        "WHERE r.id = %s AND r.empresa_id = %s", (reserva_id, empresa_id),
    ).fetchone()
    if r is None:
        return {}
    nombre, inicio, fin, total, tipo, snapshot = r
    cancelacion = (snapshot or {}).get("texto_cancelacion") or ""
    return {
        "nombre": (nombre or "").split(" ")[0] if nombre else "",
        "reserva": reserva_id, "llegada": _fecha(inicio), "salida": _fecha(fin),
        "noches": (fin - inicio).days, "tipo": tipo or "", "total": _clp(total),
        "cancelacion": cancelacion, "faltantes": ", ".join(datos_faltantes(conexion, reserva_id)) or "ninguno",
    }


class _Seguro(dict):
    def __missing__(self, clave):
        return ""


def armar(conexion: psycopg.Connection, empresa_id: str, reserva_id: str) -> dict | None:
    variables = _variables(conexion, empresa_id, reserva_id)
    if not variables:
        return None
    contacto = contacto_de_reserva(conexion, reserva_id)
    faltan = datos_faltantes(conexion, reserva_id)
    mensajes = []
    for pid, (nombre, asunto, texto) in PLANTILLAS.items():
        cuerpo = texto.format_map(_Seguro(variables))
        mensajes.append({
            "plantilla": pid, "nombre": nombre,
            "asunto": asunto.format_map(_Seguro(variables)), "texto": cuerpo,
            "whatsapp": (f"https://wa.me/{contacto['telefono'].lstrip('+')}?text={quote(cuerpo)}"
                         if contacto["telefono"] else None),
            "puede_correo": bool(contacto["correo"]),
        })
    return {
        "reserva_id": reserva_id,
        "contacto": {"correo": contacto["correo"], "telefono": contacto["telefono"]},
        "datos_faltantes": faltan,
        "alerta": None if (contacto["correo"] or contacto["telefono"])
        else "Sin forma de contactar al huésped: falta correo y teléfono.",
        "mensajes": mensajes,
    }


def _registrar(conexion, empresa_id, reserva_id, plantilla, canal, destino, estado, actor, detalle=None):
    conexion.execute(
        "INSERT INTO mensajes_huesped_envios (id, empresa_id, reserva_id, plantilla, canal, "
        "destino_enmascarado, estado, detalle, actor) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (f"MSG-{uuid.uuid4().hex[:12]}", empresa_id, reserva_id, plantilla, canal,
         enmascarar(destino), estado, detalle, actor),
    )
    seguridad.auditar(conexion, actor, "mensaje_huesped", reserva_id, f"{plantilla}:{canal}:{estado}")


def registrar_whatsapp_abierto(conexion, empresa_id, reserva_id, plantilla, actor) -> dict:
    if plantilla not in PLANTILLAS:
        raise PlantillaDesconocida(plantilla)
    contacto = contacto_de_reserva(conexion, reserva_id)
    if not contacto["telefono"]:
        raise SinDestino("la reserva no tiene teléfono")
    _registrar(conexion, empresa_id, reserva_id, plantilla, "whatsapp_manual", contacto["telefono"], "abierto", actor)
    return {"reserva_id": reserva_id, "plantilla": plantilla, "canal": "whatsapp_manual", "estado": "abierto"}


def enviar_por_correo(conexion, empresa_id, reserva_id, plantilla, actor, buzon=None) -> dict:
    if plantilla not in PLANTILLAS:
        raise PlantillaDesconocida(plantilla)
    contacto = contacto_de_reserva(conexion, reserva_id)
    if not contacto["correo"] or not PATRON_CORREO.match(contacto["correo"]):
        raise SinDestino("la reserva no tiene un correo válido")
    if buzon is None:
        from . import correo
        buzon = correo.buzon_envio_activo(conexion, empresa_id)
    if buzon is None:
        raise CanalNoConfigurado("no hay buzón de envío de correo activo (Configuración → Correo)")
    variables = _variables(conexion, empresa_id, reserva_id)
    _, asunto, texto = PLANTILLAS[plantilla]
    try:
        buzon.enviar(asunto.format_map(_Seguro(variables)), texto.format_map(_Seguro(variables)),
                     destinos=[contacto["correo"]])
    except Exception as error:  # noqa: BLE001 — el motivo queda registrado sin datos personales
        _registrar(conexion, empresa_id, reserva_id, plantilla, "correo", contacto["correo"],
                   "fallido", actor, type(error).__name__)
        return {"reserva_id": reserva_id, "plantilla": plantilla, "canal": "correo", "estado": "fallido"}
    _registrar(conexion, empresa_id, reserva_id, plantilla, "correo", contacto["correo"], "enviado", actor)
    return {"reserva_id": reserva_id, "plantilla": plantilla, "canal": "correo", "estado": "enviado"}


def historial(conexion: psycopg.Connection, empresa_id: str, reserva_id: str) -> list[dict]:
    return [
        {"plantilla": f[0], "canal": f[1], "destino": f[2], "estado": f[3], "actor": f[4], "creado_en": f[5].isoformat()}
        for f in conexion.execute(
            "SELECT plantilla, canal, destino_enmascarado, estado, actor, creado_en FROM mensajes_huesped_envios "
            "WHERE empresa_id = %s AND reserva_id = %s ORDER BY creado_en DESC LIMIT 20",
            (empresa_id, reserva_id)).fetchall()
    ]
