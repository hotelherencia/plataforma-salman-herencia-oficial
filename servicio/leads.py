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
import os
import re
import secrets
import uuid
from datetime import date, timedelta

import psycopg

from . import roles
from . import avisos, entrada_publica, seguridad

MAX_NOMBRE = 200
MAX_CORREO = 320
MAX_TELEFONO = 40
MAX_MENSAJE = 2000
MAX_PERSONAS = 30
MAX_NOCHES = 30
ESTADOS = ("nuevo", "contactado", "cerrado")
ROLES_GESTION = roles.con_admin_hotel("recepcion")
_RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RE_REFERENCIA = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
_TRANSICIONES = {"nuevo": frozenset({"contactado", "cerrado"}), "contactado": frozenset({"cerrado"})}
# SOC-016: la referencia para continuar la reserva caduca (por defecto 72 h,
# configurable con LEAD_REFERENCIA_HORAS, entre 1 h y 30 días) y se revoca
# al cerrar el lead.
REFERENCIA_HORAS_DEFECTO = 72
REFERENCIA_HORAS_MAX = 24 * 30
# #354 (2026-11-18): «nuevo» = sin gestión y creado dentro de la ventana
# (LEADS_VENTANA_NUEVO_DIAS, por defecto 30, propuesta del issue; entre 1 y
# 365). Fuera de la ventana, el lead sin gestión es «sin gestionar (antiguo)».
VENTANA_NUEVO_DEFECTO = 30


def ventana_nuevo_dias() -> int:
    try:
        dias = int(os.environ.get("LEADS_VENTANA_NUEVO_DIAS") or VENTANA_NUEVO_DEFECTO)
    except ValueError:
        return VENTANA_NUEVO_DEFECTO
    return min(max(dias, 1), 365)


def normalizar_telefono(telefono: str | None) -> str | None:
    """Aproximación a E.164 para comparar: solo dígitos con +; un móvil
    chileno de 9 dígitos (9XXXXXXXX) recibe el prefijo 56."""
    digitos = re.sub(r"\D", "", telefono or "")
    if not digitos:
        return None
    if len(digitos) == 9 and digitos.startswith("9"):
        digitos = "56" + digitos
    return "+" + digitos


def _contacto_para(conexion: psycopg.Connection, empresa_id: str, nombre: str, correo: str, telefono: str) -> str:
    """#354: ficha única por correo (o, si no, por teléfono normalizado)."""
    tel = normalizar_telefono(telefono)
    fila = conexion.execute(
        "SELECT id FROM contactos WHERE empresa_id = %s AND (correo = %s OR (%s::text IS NOT NULL AND telefono_normalizado = %s)) "
        "ORDER BY (correo = %s) DESC, creado_en LIMIT 1 FOR UPDATE",
        (empresa_id, correo, tel, tel, correo),
    ).fetchone()
    if fila:
        conexion.execute(
            "UPDATE contactos SET nombre = %s, telefono_normalizado = COALESCE(telefono_normalizado, %s), "
            "correo = COALESCE(correo, %s), actualizado_en = now() WHERE id = %s",
            (nombre, tel, correo, fila[0]),
        )
        return fila[0]
    contacto_id = f"CTO-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO contactos (id, empresa_id, nombre, correo, telefono_normalizado) VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (empresa_id, correo) WHERE correo IS NOT NULL DO NOTHING",
        (contacto_id, empresa_id, nombre, correo, tel),
    )
    (contacto_id,) = conexion.execute(
        "SELECT id FROM contactos WHERE empresa_id = %s AND correo = %s", (empresa_id, correo)
    ).fetchone()
    return contacto_id


def horas_referencia() -> int:
    try:
        horas = int(os.environ.get("LEAD_REFERENCIA_HORAS") or REFERENCIA_HORAS_DEFECTO)
    except ValueError:
        return REFERENCIA_HORAS_DEFECTO
    return min(max(horas, 1), REFERENCIA_HORAS_MAX)


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


def _validar(nombre, correo, telefono, huespedes, check_in, check_out, mensaje, exigir_futuro: bool = True) -> None:
    if not nombre or len(nombre) > MAX_NOMBRE:
        raise LeadInvalido(f"nombre es obligatorio (máx. {MAX_NOMBRE})")
    if not correo or len(correo) > MAX_CORREO or not _RE_CORREO.match(correo):
        raise LeadInvalido("correo es obligatorio y debe tener formato de correo")
    if not telefono or len(telefono) > MAX_TELEFONO:
        raise LeadInvalido(f"telefono es obligatorio (máx. {MAX_TELEFONO})")
    if not entrada_publica.telefono_con_formato(telefono):
        raise LeadInvalido("telefono solo admite dígitos, espacios, +, (, ), . y -")
    digitos = re.sub(r"\D", "", telefono)
    if len(digitos) < 8 or len(digitos) > 15:
        raise LeadInvalido("telefono debe incluir entre 8 y 15 dígitos")
    if huespedes is not None and (huespedes < 1 or huespedes > MAX_PERSONAS):
        raise LeadInvalido(f"huespedes debe estar entre 1 y {MAX_PERSONAS}")
    if (check_in is None) != (check_out is None):
        raise LeadInvalido("check_in y check_out vienen juntos o ninguno")
    if check_in is not None and check_out <= check_in:
        raise LeadInvalido("check_out debe ser mayor que check_in")
    from . import contabilidad

    if exigir_futuro and check_in is not None and check_in < contabilidad.hoy_chile():
        raise LeadInvalido("check_in debe ser hoy o una fecha futura")
    if check_in is not None and (check_out - check_in).days > MAX_NOCHES:
        raise LeadInvalido(f"el rango supera las {MAX_NOCHES} noches")
    if mensaje is not None and len(mensaje) > MAX_MENSAJE:
        raise LeadInvalido(f"mensaje supera los {MAX_MENSAJE} caracteres")


def _hash_cuerpo(cuerpo: dict) -> str:
    canonico = json.dumps(cuerpo, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def clave_registrada(conexion: psycopg.Connection, empresa_id: str, clave: str) -> bool:
    """True si ya hay un lead con esa Idempotency-Key en la empresa: el envío
    es un reintento (del proxy de la landing o del navegador tras un corte)."""
    return conexion.execute(
        "SELECT 1 FROM leads WHERE empresa_id = %s AND idempotency_key = %s",
        (empresa_id, clave),
    ).fetchone() is not None


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
    nombre = entrada_publica.limpiar_texto(nombre)
    correo = entrada_publica.limpiar_texto(correo).lower()
    telefono = entrada_publica.limpiar_texto(telefono)
    mensaje = entrada_publica.limpiar_texto(mensaje, multilinea=True) or None
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
        "SELECT id, cuerpo_hash, token_consulta, (token_expira IS NOT NULL AND token_expira > now()) "
        "FROM leads WHERE empresa_id = %s AND idempotency_key = %s",
        (empresa_id, clave),
    ).fetchone()
    if existente is not None:
        if existente[1] != cuerpo_hash:
            raise ClaveEnConflicto("esa clave ya se usó con otros datos")
        vigente = existente[2] if existente[2] and existente[3] else None
        token = vigente or _nueva_referencia(conexion, existente[0])
        return {"lead": _resumen(conexion, existente[0]), "referencia": token, "reintento": True}

    lead_id = f"LEAD-{uuid.uuid4().hex[:12]}"
    token = secrets.token_urlsafe(32)
    contacto_id = _contacto_para(conexion, empresa_id, nombre, correo, telefono)
    conexion.execute(
        "INSERT INTO leads (id, empresa_id, nombre, correo, telefono, huespedes, check_in, "
        "check_out, mensaje, estado, origen, idempotency_key, cuerpo_hash, token_consulta, "
        "token_expira, contacto_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'nuevo', 'landing', %s, %s, %s, "
        "now() + make_interval(hours => %s), %s)",
        (lead_id, empresa_id, nombre, correo, telefono, huespedes, check_in, check_out,
         mensaje, clave, cuerpo_hash, token, horas_referencia(), contacto_id),
    )
    seguridad.auditar(conexion, f"publico:{lead_id}", "lead_recibido", lead_id, "nuevo")
    # Aviso a la administración en la misma transacción (sin datos de contacto).
    avisos.registrar_evento(conexion, "consulta_recibida", lead_id, {
        "inicio": check_in.isoformat() if check_in else None, "fin": check_out.isoformat() if check_out else None,
        "personas": huespedes, "con_mensaje": bool(mensaje)}, empresa_id)
    return {"lead": _resumen(conexion, lead_id), "referencia": token, "reintento": False}


def _nueva_referencia(conexion: psycopg.Connection, lead_id: str) -> str:
    """Emite una referencia nueva (la anterior, si existía, queda inválida).
    Un lead cerrado no recibe referencia: no hay reserva que continuar."""
    token = secrets.token_urlsafe(32)
    fila = conexion.execute(
        "UPDATE leads SET token_consulta = %s, token_expira = now() + make_interval(hours => %s) "
        "WHERE id = %s AND estado <> 'cerrado' RETURNING token_consulta",
        (token, horas_referencia(), lead_id),
    ).fetchone()
    return fila[0] if fila else None


def por_referencia(conexion: psycopg.Connection, token: str) -> dict | None:
    """SOC-016: con una referencia vigente devuelve solo lo necesario para
    precargar /reservar (nombre, correo y, si se indicaron, llegada/salida/personas;
    nunca el teléfono, el mensaje ni el token). Caducada, revocada o de un lead
    cerrado → None (404)."""
    if not token or not _RE_REFERENCIA.fullmatch(token):
        raise LeadInvalido("referencia inválida")
    fila = conexion.execute(
        "SELECT nombre, correo, check_in, check_out, huespedes FROM leads WHERE token_consulta = %s "
        "AND token_expira IS NOT NULL AND token_expira > now() AND estado <> 'cerrado'",
        (token,),
    ).fetchone()
    if fila is None:
        return None
    salida = {"nombre": fila[0], "correo": fila[1]}
    if fila[2] is not None and fila[3] is not None:
        salida["llegada"] = fila[2].isoformat()
        salida["salida"] = fila[3].isoformat()
    if fila[4] is not None:
        salida["personas"] = fila[4]
    return salida


def consumir_referencia(conexion: psycopg.Connection, empresa_id: str, token: str | None) -> None:
    """Revoca la referencia opaca una vez que el visitante completó su solicitud en /reservar,
    evitando que datos de una consulta anterior reaparezcan en envíos posteriores."""
    if not token or not _RE_REFERENCIA.fullmatch(token):
        return
    conexion.execute(
        "UPDATE leads SET token_consulta = NULL, token_expira = NULL "
        "WHERE empresa_id = %s AND token_consulta = %s",
        (empresa_id, token),
    )


def revocar_referencia(conexion: psycopg.Connection, lead_id: str) -> None:
    conexion.execute(
        "UPDATE leads SET token_consulta = NULL, token_expira = NULL WHERE id = %s", (lead_id,)
    )


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
        "estado, origen, nota, gestion_por, gestion_en, creado_en, contacto_id, "
        "(SELECT count(*) FROM leads x WHERE x.contacto_id = leads.contacto_id), "
        "creado_en >= now() - make_interval(days => %s) "
        "FROM leads WHERE id = %s",
        (ventana_nuevo_dias(), lead_id),
    ).fetchone()
    if fila is None:
        raise LeadAjenoOInexistente("acceso denegado")
    if fila[8] != "nuevo":
        situacion = fila[8]
    else:
        situacion = "nuevo" if fila[16] else "sin_gestionar_antiguo"
    return {
        "id": fila[0],
        "contacto_id": fila[14],
        "leads_del_contacto": fila[15] if fila[14] else 1,
        "situacion": situacion,
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


def bandeja(conexion: psycopg.Connection, empresa_id: str, estado: str | None,
            desde: date | None = None, hasta: date | None = None, contacto_id: str | None = None,
            todos: bool = False, hoy: date | None = None) -> dict:
    """#354: por defecto solo la ventana vigente (últimos N días), con el
    corte visible; `todos` quita el corte; `desde`/`hasta` lo fijan."""
    if estado is not None and estado not in ESTADOS:
        raise LeadInvalido(f"estado debe ser uno de: {', '.join(ESTADOS)}")
    hoy = hoy or date.today()
    ventana = ventana_nuevo_dias()
    if desde is None and not todos and contacto_id is None:
        desde = hoy - timedelta(days=ventana)
    filtros, parametros = ["empresa_id = %s"], [empresa_id]
    if estado is not None:
        filtros.append("estado = %s")
        parametros.append(estado)
    if desde is not None:
        filtros.append("creado_en >= %s::date")
        parametros.append(desde)
    if hasta is not None:
        filtros.append("creado_en < %s::date + 1")
        parametros.append(hasta)
    if contacto_id is not None:
        filtros.append("contacto_id = %s")
        parametros.append(contacto_id)
    filas = conexion.execute(
        f"SELECT id FROM leads WHERE {' AND '.join(filtros)} ORDER BY creado_en DESC, id DESC", parametros
    ).fetchall()
    (antiguos,) = conexion.execute(
        "SELECT count(*) FROM leads WHERE empresa_id = %s AND estado = 'nuevo' "
        "AND creado_en < now() - make_interval(days => %s)",
        (empresa_id, ventana),
    ).fetchone()
    return {
        "leads": [_fila_bandeja(conexion, fila[0]) for fila in filas],
        "corte": {"desde": desde.isoformat() if desde else None, "hasta": hasta.isoformat() if hasta else None,
                  "ventana_nuevo_dias": ventana},
        "sin_gestionar_antiguos": antiguos,
    }


def contactos(conexion: psycopg.Connection, empresa_id: str, desde: date | None = None,
              hasta: date | None = None) -> dict:
    """#354: lista para fidelización, deduplicada por contacto (un envío por
    persona, nunca por lead). Fase 1 contable (2026-11-19): `desde`/`hasta`
    acotan la exportación a los contactos con algún lead en ese rango (fecha
    de Chile, ambos extremos incluidos)."""
    if desde is not None and hasta is not None and desde > hasta:
        raise LeadInvalido("la fecha «desde» debe ser anterior o igual a «hasta»")
    filtros, parametros = ["c.empresa_id = %s"], [empresa_id]
    if desde is not None:
        filtros.append("(l.creado_en AT TIME ZONE 'America/Santiago')::date >= %s")
        parametros.append(desde)
    if hasta is not None:
        filtros.append("(l.creado_en AT TIME ZONE 'America/Santiago')::date <= %s")
        parametros.append(hasta)
    filas = conexion.execute(
        "SELECT c.id, c.nombre, c.correo, c.telefono_normalizado, count(l.id), max(l.creado_en), "
        "bool_or(l.estado = 'cerrado') FROM contactos c JOIN leads l ON l.contacto_id = c.id "
        f"WHERE {' AND '.join(filtros)} GROUP BY c.id ORDER BY max(l.creado_en) DESC",
        parametros,
    ).fetchall()
    return {"contactos": [
        {"contacto_id": f[0], "nombre": f[1], "correo": f[2], "telefono": f[3], "leads": f[4],
         "ultimo_lead_en": f[5].isoformat(), "algun_cerrado": f[6]}
        for f in filas
    ]}


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
    # #355: el «contactado» automático (revisión de correo) se puede deshacer.
    deshacer_auto = actual == "contactado" and estado == "nuevo" and conexion.execute(
        "SELECT gestion_por = 'auto:correo' FROM leads WHERE id = %s", (lead_id,)).fetchone()[0]
    if deshacer_auto:
        conexion.execute("UPDATE leads SET estado = 'nuevo', nota = %s, gestion_por = NULL, gestion_en = NULL "
                         "WHERE id = %s", (nota or f"deshecho el contacto automático por {actor}", lead_id))
        seguridad.auditar(conexion, actor, "lead_gestion", lead_id, "contactado:nuevo (deshace auto)")
        return _fila_bandeja(conexion, lead_id)
    if estado not in _TRANSICIONES.get(actual, frozenset()):
        raise TransicionInvalida(f"no se puede pasar de {actual} a {estado}")
    conexion.execute(
        "UPDATE leads SET estado = %s, nota = %s, gestion_por = %s, gestion_en = now() "
        "WHERE id = %s",
        (estado, nota, actor, lead_id),
    )
    if estado == "cerrado":
        revocar_referencia(conexion, lead_id)  # SOC-016
    seguridad.auditar(conexion, actor, "lead_gestion", lead_id, f"{actual}:{estado}")
    return _fila_bandeja(conexion, lead_id)


def editar(
    conexion: psycopg.Connection,
    empresa_id: str,
    lead_id: str,
    nombre: str,
    correo: str,
    telefono: str,
    huespedes: int | None,
    check_in: date | None,
    check_out: date | None,
    mensaje: str | None,
    nota: str | None,
    actor: str,
) -> dict:
    """Corrige los datos de un lead en cualquier estado (también cerrado). No cambia el estado ni la
    gestión, y no borra nada. La llegada ya pasada solo se rechaza si la edición toca las fechas: un
    lead antiguo se corrige sin reescribirlas. Si cambian correo o teléfono, el lead pasa a la ficha de
    contacto que corresponda (#354); la ficha anterior conserva sus otros leads. La auditoría guarda
    los nombres de los campos cambiados, nunca sus valores."""
    nombre = entrada_publica.limpiar_texto(nombre)
    correo = entrada_publica.limpiar_texto(correo).lower()
    telefono = entrada_publica.limpiar_texto(telefono)
    mensaje = entrada_publica.limpiar_texto(mensaje, multilinea=True) or None
    nota = entrada_publica.limpiar_texto(nota, multilinea=True) or None
    actual = conexion.execute(
        "SELECT nombre, correo, telefono, huespedes, check_in, check_out, mensaje, nota, contacto_id "
        "FROM leads WHERE id = %s AND empresa_id = %s FOR UPDATE",
        (lead_id, empresa_id),
    ).fetchone()
    if actual is None:
        raise LeadAjenoOInexistente("acceso denegado")
    _validar(nombre, correo, telefono, huespedes, check_in, check_out, mensaje,
             exigir_futuro=(check_in, check_out) != (actual[4], actual[5]))
    nuevo = (nombre, correo, telefono, huespedes, check_in, check_out, mensaje, nota)
    campos = ("nombre", "correo", "telefono", "huespedes", "check_in", "check_out", "mensaje", "nota")
    cambiados = [c for c, a, n in zip(campos, actual, nuevo) if a != n]
    if not cambiados:
        return _fila_bandeja(conexion, lead_id)
    contacto_id = actual[8]
    if {"nombre", "correo", "telefono"} & set(cambiados):
        contacto_id = _contacto_para(conexion, empresa_id, nombre, correo, telefono)
        if contacto_id == actual[8] and "telefono" in cambiados:
            otros = conexion.execute(
                "SELECT count(*) FROM leads WHERE contacto_id = %s AND id <> %s", (contacto_id, lead_id)
            ).fetchone()[0]
            if otros == 0:  # ficha de un solo lead: el teléfono corregido es el de la ficha
                conexion.execute("UPDATE contactos SET telefono_normalizado = %s WHERE id = %s",
                                 (normalizar_telefono(telefono), contacto_id))
    conexion.execute(
        "UPDATE leads SET nombre = %s, correo = %s, telefono = %s, huespedes = %s, check_in = %s, "
        "check_out = %s, mensaje = %s, nota = %s, contacto_id = %s WHERE id = %s",
        (*nuevo, contacto_id, lead_id),
    )
    seguridad.auditar(conexion, actor, "lead_edicion", lead_id, ",".join(cambiados))
    return _fila_bandeja(conexion, lead_id)
