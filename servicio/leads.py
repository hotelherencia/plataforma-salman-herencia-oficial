"""Leads / contacto de la landing (spec-api-v1 «Contacto y leads de la
landing», V1-ISSUE-20 punto 8 resuelto: formulario propio, Formspree
retirado).

Prospección: la consulta general del visitante queda en la plataforma como
agenda de seguimiento de recepción. La creación es pública (sin sesión) con
idempotencia propia — el espacio de claves es propio y la clave del visitante
nunca toca `claves_idempotencia`. La gestión (contactado/cerrado con nota y
auditoría) la hace recepción o administrador. Los datos de contacto se guardan
tal cual: son el objeto de la gestión comercial (igual que
`solicitudes.huesped_contacto`); la redacción NFR-A03 solo aplica si el texto
sale a un modelo externo, que este canal no hace. La gestión nunca borra.
"""
import hashlib
import json
import re
import secrets
import uuid
from datetime import date

import psycopg

from . import seguridad

MAX_NOMBRE = 200
MAX_CORREO = 320
MAX_TELEFONO = 40
MAX_MENSAJE = 2000
MAX_PERSONAS = 30
MAX_NOCHES = 30
ESTADOS = ("nuevo", "contactado", "cerrado")
ROLES_GESTION = frozenset({"recepcion", "administrador"})
_RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RE_REFERENCIA = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
_TRANSICIONES = {"nuevo": frozenset({"contactado", "cerrado"}), "contactado": frozenset({"cerrado"})}


class LeadInvalido(Exception):
    """422: validación de nombre, correo, teléfono o fechas del lead."""

    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


class ClaveEnConflicto(Exception):
    """409: misma clave de idempotencia con otro cuerpo."""


class LeadAjenoOInexistente(Exception):
    """403 sin revelar cuál es el caso (igual que las solicitudes internas)."""


class TransicionInvalida(Exception):
    """409: el lead no admite la operación en su estado actual."""


def _validar(nombre, correo, telefono, huespedes, check_in, check_out, mensaje) -> None:
    if not nombre or len(nombre) > MAX_NOMBRE:
        raise LeadInvalido(f"nombre es obligatorio (máx. {MAX_NOMBRE})")
    if not correo or len(correo) > MAX_CORREO or not _RE_CORREO.match(correo):
        raise LeadInvalido("correo es obligatorio y debe tener formato de correo")
    if not telefono or len(telefono) > MAX_TELEFONO:
        raise LeadInvalido(f"telefono es obligatorio (máx. {MAX_TELEFONO})")
    digitos = re.sub(r"\D", "", telefono)
    if len(digitos) < 8 or len(digitos) > 15:
        raise LeadInvalido("telefono debe incluir entre 8 y 15 dígitos")
    if huespedes is not None and (huespedes < 1 or huespedes > MAX_PERSONAS):
        raise LeadInvalido(f"huespedes debe estar entre 1 y {MAX_PERSONAS}")
    if (check_in is None) != (check_out is None):
        raise LeadInvalido("check_in y check_out vienen juntos o ninguno")
    if check_in is not None and check_out <= check_in:
        raise LeadInvalido("check_out debe ser mayor que check_in")
    if check_in is not None and check_in < date.today():
        raise LeadInvalido("check_in debe ser hoy o una fecha futura")
    if check_in is not None and (check_out - check_in).days > MAX_NOCHES:
        raise LeadInvalido(f"el rango supera las {MAX_NOCHES} noches")
    if mensaje is not None and len(mensaje) > MAX_MENSAJE:
        raise LeadInvalido(f"mensaje supera los {MAX_MENSAJE} caracteres")


def _hash_cuerpo(cuerpo: dict) -> str:
    canonico = json.dumps(cuerpo, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def crear_lead(
    conexion: psycopg.Connection,
    empresa_id: str,
    nombre: str,
    correo: str,
    telefono: str,
    huespedes: int | None,
    check_in: date | None,
    check_out: date | None,
    mensaje: str | None,
    clave: str,
) -> dict:
    """Persiste el lead `nuevo` con idempotencia propia. Reintento (misma
    clave y cuerpo) devuelve el lead original con reintento=true; misma clave
    y otro cuerpo → ClaveEnConflicto (409)."""
    nombre = (nombre or "").strip()
    correo = (correo or "").strip()
    telefono = (telefono or "").strip()
    mensaje = (mensaje or "").strip() or None
    _validar(nombre, correo, telefono, huespedes, check_in, check_out, mensaje)

    cuerpo = {
        "nombre": nombre, "correo": correo, "telefono": telefono,
        "huespedes": huespedes,
        "check_in": check_in.isoformat() if check_in is not None else None,
        "check_out": check_out.isoformat() if check_out is not None else None,
        "mensaje": mensaje,
    }
    cuerpo_hash = _hash_cuerpo(cuerpo)
    existente = conexion.execute(
        "SELECT id, cuerpo_hash, token_consulta FROM leads WHERE empresa_id = %s AND idempotency_key = %s",
        (empresa_id, clave),
    ).fetchone()
    if existente is not None:
        if existente[1] != cuerpo_hash:
            raise ClaveEnConflicto("esa clave ya se usó con otros datos")
        token = existente[2] or _nueva_referencia(conexion, existente[0])
        return {"lead": _resumen(conexion, existente[0]), "referencia": token, "reintento": True}

    lead_id = f"LEAD-{uuid.uuid4().hex[:12]}"
    token = secrets.token_urlsafe(32)
    conexion.execute(
        "INSERT INTO leads (id, empresa_id, nombre, correo, telefono, huespedes, check_in, "
        "check_out, mensaje, estado, origen, idempotency_key, cuerpo_hash, token_consulta) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'nuevo', 'landing', %s, %s, %s)",
        (lead_id, empresa_id, nombre, correo, telefono, huespedes, check_in, check_out,
         mensaje, clave, cuerpo_hash, token),
    )
    seguridad.auditar(conexion, f"publico:{lead_id}", "lead_recibido", lead_id, "nuevo")
    return {"lead": _resumen(conexion, lead_id), "referencia": token, "reintento": False}


def _nueva_referencia(conexion: psycopg.Connection, lead_id: str) -> str:
    token = secrets.token_urlsafe(32)
    conexion.execute(
        "UPDATE leads SET token_consulta = %s WHERE id = %s AND token_consulta IS NULL",
        (token, lead_id),
    )
    fila = conexion.execute("SELECT token_consulta FROM leads WHERE id = %s", (lead_id,)).fetchone()
    return fila[0]


def por_referencia(conexion: psycopg.Connection, token: str) -> dict | None:
    """Devuelve solo nombre, correo y teléfono de esa referencia. El token
    no se escribe en el resultado."""
    if not token or not _RE_REFERENCIA.fullmatch(token):
        raise LeadInvalido("referencia inválida")
    fila = conexion.execute(
        "SELECT nombre, correo, telefono FROM leads WHERE token_consulta = %s",
        (token,),
    ).fetchone()
    if fila is None:
        return None
    return {"nombre": fila[0], "correo": fila[1], "telefono": fila[2]}


def _resumen(conexion: psycopg.Connection, lead_id: str) -> dict:
    fila = conexion.execute(
        "SELECT id, estado, creado_en FROM leads WHERE id = %s", (lead_id,)
    ).fetchone()
    if fila is None:
        raise LeadAjenoOInexistente("acceso denegado")
    return {"id": fila[0], "estado": fila[1], "creado_en": fila[2].isoformat()}


def _fila_bandeja(conexion: psycopg.Connection, lead_id: str) -> dict:
    fila = conexion.execute(
        "SELECT id, nombre, correo, telefono, huespedes, check_in, check_out, mensaje, "
        "estado, origen, nota, gestion_por, gestion_en, creado_en "
        "FROM leads WHERE id = %s",
        (lead_id,),
    ).fetchone()
    if fila is None:
        raise LeadAjenoOInexistente("acceso denegado")
    return {
        "id": fila[0],
        "nombre": fila[1],
        "correo": fila[2],
        "telefono": fila[3],
        "huespedes": fila[4],
        "check_in": fila[5].isoformat() if fila[5] is not None else None,
        "check_out": fila[6].isoformat() if fila[6] is not None else None,
        "mensaje": fila[7],
        "estado": fila[8],
        "origen": fila[9],
        "nota": fila[10],
        "gestion_por": fila[11],
        "gestion_en": fila[12].isoformat() if fila[12] is not None else None,
        "creado_en": fila[13].isoformat(),
    }


def bandeja(conexion: psycopg.Connection, empresa_id: str, estado: str | None) -> dict:
    if estado is not None and estado not in ESTADOS:
        raise LeadInvalido(f"estado debe ser uno de: {', '.join(ESTADOS)}")
    if estado is None:
        filas = conexion.execute(
            "SELECT id FROM leads WHERE empresa_id = %s ORDER BY creado_en DESC, id DESC",
            (empresa_id,),
        ).fetchall()
    else:
        filas = conexion.execute(
            "SELECT id FROM leads WHERE empresa_id = %s AND estado = %s "
            "ORDER BY creado_en DESC, id DESC",
            (empresa_id, estado),
        ).fetchall()
    return {"leads": [_fila_bandeja(conexion, fila[0]) for fila in filas]}


def gestionar(
    conexion: psycopg.Connection,
    empresa_id: str,
    lead_id: str,
    estado: str,
    nota: str | None,
    actor: str,
) -> dict:
    """Avanza el lead (contactado/cerrado) con nota, gestion_en/por y
    auditoría. La gestión nunca borra: el lead queda en su estado final."""
    fila = conexion.execute(
        "SELECT estado FROM leads WHERE id = %s AND empresa_id = %s", (lead_id, empresa_id)
    ).fetchone()
    if fila is None:
        raise LeadAjenoOInexistente("acceso denegado")
    actual = fila[0]
    if estado not in _TRANSICIONES.get(actual, frozenset()):
        raise TransicionInvalida(f"no se puede pasar de {actual} a {estado}")
    conexion.execute(
        "UPDATE leads SET estado = %s, nota = %s, gestion_por = %s, gestion_en = now() "
        "WHERE id = %s",
        (estado, nota, actor, lead_id),
    )
    seguridad.auditar(conexion, actor, "lead_gestion", lead_id, f"{actual}:{estado}")
    return _fila_bandeja(conexion, lead_id)
