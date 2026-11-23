"""Incidencias operativas con evidencia móvil y bloqueo automático de disponibilidad (#415).

Permite registrar desperfectos, reclamos o reparaciones en una habitación o área
común, adjuntar evidencia fotográfica ligera desde móvil (JPG/PNG/WebP, máx. 5 MB)
y bloquear automáticamente la disponibilidad de la habitación cuando
`bloquea_disponibilidad = true` (vía `hotel_sql.fijar_mantenimiento`).

Toda mutación queda en `auditoria` sin copiar PII ni descripciones extensas.
"""
from __future__ import annotations

import base64
import binascii
import uuid
from datetime import date

import psycopg

from . import hotel_sql, roles, seguridad

ROLES_REPORTE = roles.con_admin_hotel("recepcion", "aseo")
ROLES_GESTION = roles.con_admin_hotel("recepcion")

GRAVEDADES = ("baja", "media", "alta", "critica")
ESTADOS = ("abierta", "en_progreso", "resuelta", "cerrada")
ESTADOS_ABIERTOS = ("abierta", "en_progreso")
AREAS_VALIDAS = (
    "habitacion",
    "pasillo",
    "comedor",
    "recepcion",
    "banos_comunes",
    "lavanderia",
    "estacionamiento",
    "cocina",
    "otro",
)
MAX_EVIDENCIA_BYTES = 5 * 1024 * 1024


class IncidenciaInvalida(Exception):
    """422: datos de incidencia o evidencia inválidos."""


class IncidenciaNoEncontrada(Exception):
    """403/404: incidencia inexistente o de otra empresa."""


class TransicionIncidenciaInvalida(Exception):
    """409: la operación no aplica en el estado actual."""


def detectar_mime_imagen(datos: bytes) -> str:
    """Valida firma mágica real de imagen (JPG, PNG o WebP); jamás confía en Content-Type."""
    if not datos:
        raise IncidenciaInvalida("la evidencia fotográfica está vacía")
    if len(datos) > MAX_EVIDENCIA_BYTES:
        raise IncidenciaInvalida("la evidencia supera el límite de 5 MB")
    if datos.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if datos.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(datos) >= 12 and datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "image/webp"
    raise IncidenciaInvalida("la evidencia debe ser una imagen JPG, PNG o WebP válida")


def decodificar_evidencia_base64(texto: str) -> tuple[bytes, str]:
    crudo = (texto or "").strip()
    if crudo.startswith("data:") and "," in crudo:
        crudo = crudo.split(",", 1)[1].strip()
    try:
        datos = base64.b64decode(crudo, validate=True)
    except (binascii.Error, ValueError) as error:
        raise IncidenciaInvalida("evidencia base64 inválida") from error
    mime = detectar_mime_imagen(datos)
    return datos, mime


def _verificar_habitacion(conexion: psycopg.Connection, habitacion_id: str) -> None:
    fila = conexion.execute("SELECT 1 FROM habitaciones WHERE id = %s", (habitacion_id,)).fetchone()
    if fila is None:
        raise IncidenciaInvalida(f"la habitación {habitacion_id} no existe")


def _sincronizar_bloqueo_habitacion(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    habitacion_id: str | None,
    plazo: date | None = None,
) -> None:
    """Sincroniza `habitaciones.mantenimiento` según las incidencias abiertas bloqueantes."""
    if not habitacion_id:
        return
    bloqueantes = conexion.execute(
        "SELECT plazo FROM incidencias "
        "WHERE empresa_id = %s AND habitacion_id = %s "
        "AND estado IN ('abierta', 'en_progreso') AND bloquea_disponibilidad = true",
        (empresa_id, habitacion_id),
    ).fetchall()
    if bloqueantes:
        plazos = [r[0] for r in bloqueantes if r[0] is not None]
        hasta = max(plazos) if plazos else plazo
        desde = date.today()
        if hasta is not None and hasta <= desde:
            hasta = None
        hotel_sql.fijar_mantenimiento(conexion, hotel, empresa_id, habitacion_id, True, desde=desde, hasta=hasta)
    else:
        hotel_sql.fijar_mantenimiento(conexion, hotel, empresa_id, habitacion_id, False)


def _a_dict(f) -> dict:
    return {
        "incidencia_id": f[0],
        "habitacion_id": f[1],
        "area": f[2],
        "titulo": f[3],
        "descripcion": f[4],
        "gravedad": f[5],
        "estado": f[6],
        "responsable": f[7],
        "plazo": f[8].isoformat() if f[8] else None,
        "costo_clp": f[9],
        "bloquea_disponibilidad": bool(f[10]),
        "tiene_evidencia": bool(f[11]),
        "evidencia_nombre": f[12],
        "evidencia_mime": f[13],
        "resolucion": f[14],
        "reportada_por": f[15],
        "creada_en": f[16].isoformat() if f[16] else None,
        "actualizada_en": f[17].isoformat() if f[17] else None,
        "cerrada_en": f[18].isoformat() if f[18] else None,
        "cerrada_por": f[19],
    }


_COLS = (
    "id, habitacion_id, area, titulo, descripcion, gravedad, estado, responsable, plazo, "
    "costo_clp, bloquea_disponibilidad, (evidencia_datos IS NOT NULL), evidencia_nombre, "
    "evidencia_mime, resolucion, reportada_por, creada_en, actualizada_en, cerrada_en, cerrada_por"
)


def crear(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    actor: str,
    *,
    titulo: str,
    descripcion: str,
    habitacion_id: str | None = None,
    area: str = "habitacion",
    gravedad: str = "media",
    responsable: str | None = None,
    plazo: date | None = None,
    costo_clp: int | None = None,
    bloquea_disponibilidad: bool = False,
    evidencia_base64: str | None = None,
    evidencia_nombre: str | None = None,
) -> dict:
    titulo = " ".join((titulo or "").split())
    descripcion = (descripcion or "").strip()
    area = (area or ("habitacion" if habitacion_id else "otro")).strip().lower()
    if len(titulo) < 3 or len(titulo) > 160:
        raise IncidenciaInvalida("el título debe tener entre 3 y 160 caracteres")
    if len(descripcion) < 3 or len(descripcion) > 2000:
        raise IncidenciaInvalida("la descripción debe tener entre 3 y 2000 caracteres")
    if gravedad not in GRAVEDADES:
        raise IncidenciaInvalida("gravedad inválida")
    if area not in AREAS_VALIDAS:
        raise IncidenciaInvalida("área inválida")
    if habitacion_id:
        habitacion_id = habitacion_id.strip()
        _verificar_habitacion(conexion, habitacion_id)
        area = "habitacion"
    elif bloquea_disponibilidad:
        raise IncidenciaInvalida("solo una incidencia con habitación asignada puede bloquear disponibilidad")
    if costo_clp is not None and costo_clp < 0:
        raise IncidenciaInvalida("el costo no puede ser negativo")

    ev_datos: bytes | None = None
    ev_mime: str | None = None
    ev_nombre: str | None = None
    if evidencia_base64:
        ev_datos, ev_mime = decodificar_evidencia_base64(evidencia_base64)
        ev_nombre = (evidencia_nombre or f"evidencia.{ev_mime.split('/')[-1]}")[:120]

    incidencia_id = f"INC-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO incidencias (id, empresa_id, habitacion_id, area, titulo, descripcion, gravedad, "
        "estado, responsable, plazo, costo_clp, bloquea_disponibilidad, evidencia_nombre, evidencia_mime, "
        "evidencia_datos, reportada_por) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, 'abierta', %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            incidencia_id,
            empresa_id,
            habitacion_id,
            area,
            titulo,
            descripcion,
            gravedad,
            (responsable or "").strip()[:100] or None,
            plazo,
            costo_clp,
            bool(bloquea_disponibilidad),
            ev_nombre,
            ev_mime,
            ev_datos,
            actor,
        ),
    )
    if bloquea_disponibilidad and habitacion_id:
        _sincronizar_bloqueo_habitacion(conexion, hotel, empresa_id, habitacion_id, plazo=plazo)
    destino = habitacion_id or area
    seguridad.auditar(
        conexion,
        actor,
        "incidencia_creada",
        incidencia_id,
        f"{gravedad}:{destino}:bloquea={int(bool(bloquea_disponibilidad))}",
    )
    return obtener(conexion, empresa_id, incidencia_id)


def obtener(conexion: psycopg.Connection, empresa_id: str, incidencia_id: str) -> dict:
    fila = conexion.execute(
        f"SELECT {_COLS} FROM incidencias WHERE id = %s AND empresa_id = %s",
        (incidencia_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise IncidenciaNoEncontrada("acceso denegado")
    return _a_dict(fila)


def listar(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    estado: str | None = None,
    gravedad: str | None = None,
    habitacion_id: str | None = None,
    area: str | None = None,
    bloquea_disponibilidad: bool | None = None,
    solo_abiertas: bool = False,
) -> list[dict]:
    filtros = ["empresa_id = %s"]
    params: list = [empresa_id]
    if solo_abiertas:
        filtros.append("estado IN ('abierta', 'en_progreso')")
    elif estado:
        if estado not in ESTADOS:
            raise IncidenciaInvalida("estado inválido")
        filtros.append("estado = %s")
        params.append(estado)
    if gravedad:
        if gravedad not in GRAVEDADES:
            raise IncidenciaInvalida("gravedad inválida")
        filtros.append("gravedad = %s")
        params.append(gravedad)
    if habitacion_id:
        filtros.append("habitacion_id = %s")
        params.append(habitacion_id)
    if area:
        filtros.append("area = %s")
        params.append(area)
    if bloquea_disponibilidad is not None:
        filtros.append("bloquea_disponibilidad = %s")
        params.append(bool(bloquea_disponibilidad))

    orden = (
        "CASE WHEN estado IN ('abierta', 'en_progreso') THEN 0 ELSE 1 END, "
        "bloquea_disponibilidad DESC, "
        "CASE gravedad WHEN 'critica' THEN 0 WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END, "
        "creada_en DESC, id DESC"
    )
    filas = conexion.execute(
        f"SELECT {_COLS} FROM incidencias WHERE {' AND '.join(filtros)} ORDER BY {orden}",
        params,
    ).fetchall()
    return [_a_dict(f) for f in filas]


def actualizar(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    incidencia_id: str,
    actor: str,
    cambios: dict,
) -> dict:
    actual = conexion.execute(
        "SELECT habitacion_id, estado, bloquea_disponibilidad, plazo FROM incidencias "
        "WHERE id = %s AND empresa_id = %s FOR UPDATE",
        (incidencia_id, empresa_id),
    ).fetchone()
    if actual is None:
        raise IncidenciaNoEncontrada("acceso denegado")
    hab_actual, estado_actual, bloquea_actual, plazo_actual = actual

    sets: list[str] = []
    params: list = []
    campos_audit: list[str] = []

    if "titulo" in cambios and cambios["titulo"] is not None:
        t = " ".join(str(cambios["titulo"]).split())
        if len(t) < 3 or len(t) > 160:
            raise IncidenciaInvalida("el título debe tener entre 3 y 160 caracteres")
        sets.append("titulo = %s")
        params.append(t)
        campos_audit.append("titulo")
    if "descripcion" in cambios and cambios["descripcion"] is not None:
        d = str(cambios["descripcion"]).strip()
        if len(d) < 3 or len(d) > 2000:
            raise IncidenciaInvalida("la descripción debe tener entre 3 y 2000 caracteres")
        sets.append("descripcion = %s")
        params.append(d)
        campos_audit.append("descripcion")
    if "gravedad" in cambios and cambios["gravedad"] is not None:
        if cambios["gravedad"] not in GRAVEDADES:
            raise IncidenciaInvalida("gravedad inválida")
        sets.append("gravedad = %s")
        params.append(cambios["gravedad"])
        campos_audit.append("gravedad")
    nuevo_estado = estado_actual
    if "estado" in cambios and cambios["estado"] is not None:
        if cambios["estado"] not in ESTADOS:
            raise IncidenciaInvalida("estado inválido")
        nuevo_estado = cambios["estado"]
        sets.append("estado = %s")
        params.append(nuevo_estado)
        campos_audit.append("estado")
        if nuevo_estado in ("resuelta", "cerrada") and estado_actual in ESTADOS_ABIERTOS:
            sets.append("cerrada_en = now()")
            sets.append("cerrada_por = %s")
            params.append(actor)
        elif nuevo_estado in ESTADOS_ABIERTOS and estado_actual not in ESTADOS_ABIERTOS:
            sets.append("cerrada_en = NULL")
            sets.append("cerrada_por = NULL")
    if "responsable" in cambios:
        resp = (cambios["responsable"] or "").strip()[:100] or None
        sets.append("responsable = %s")
        params.append(resp)
        campos_audit.append("responsable")
    nuevo_plazo = plazo_actual
    if "plazo" in cambios:
        nuevo_plazo = cambios["plazo"]
        sets.append("plazo = %s")
        params.append(nuevo_plazo)
        campos_audit.append("plazo")
    if "costo_clp" in cambios:
        costo = cambios["costo_clp"]
        if costo is not None and costo < 0:
            raise IncidenciaInvalida("el costo no puede ser negativo")
        sets.append("costo_clp = %s")
        params.append(costo)
        campos_audit.append("costo_clp")
    if "resolucion" in cambios:
        res = (cambios["resolucion"] or "").strip()[:1000] or None
        sets.append("resolucion = %s")
        params.append(res)
        campos_audit.append("resolucion")
    nuevo_bloquea = bloquea_actual
    if "bloquea_disponibilidad" in cambios and cambios["bloquea_disponibilidad"] is not None:
        nuevo_bloquea = bool(cambios["bloquea_disponibilidad"])
        if nuevo_bloquea and not hab_actual:
            raise IncidenciaInvalida("solo una incidencia con habitación asignada puede bloquear disponibilidad")
        sets.append("bloquea_disponibilidad = %s")
        params.append(nuevo_bloquea)
        campos_audit.append("bloquea_disponibilidad")

    if sets:
        sets.append("actualizada_en = now()")
        params.extend([incidencia_id, empresa_id])
        conexion.execute(
            f"UPDATE incidencias SET {', '.join(sets)} WHERE id = %s AND empresa_id = %s",
            params,
        )
        if hab_actual and (
            nuevo_bloquea != bloquea_actual or nuevo_estado != estado_actual or nuevo_plazo != plazo_actual
        ):
            _sincronizar_bloqueo_habitacion(conexion, hotel, empresa_id, hab_actual, plazo=nuevo_plazo)
        seguridad.auditar(conexion, actor, "incidencia_actualizada", incidencia_id, ",".join(campos_audit))
    return obtener(conexion, empresa_id, incidencia_id)


def cerrar(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    incidencia_id: str,
    actor: str,
    *,
    resolucion: str | None = None,
    costo_clp: int | None = None,
    estado_final: str = "cerrada",
) -> dict:
    if estado_final not in ("resuelta", "cerrada"):
        raise IncidenciaInvalida("estado_final debe ser resuelta o cerrada")
    actual = conexion.execute(
        "SELECT habitacion_id, estado, bloquea_disponibilidad FROM incidencias "
        "WHERE id = %s AND empresa_id = %s FOR UPDATE",
        (incidencia_id, empresa_id),
    ).fetchone()
    if actual is None:
        raise IncidenciaNoEncontrada("acceso denegado")
    hab_id, estado_actual, bloqueaba = actual
    if estado_actual == "cerrada":
        raise TransicionIncidenciaInvalida("la incidencia ya está cerrada")
    if costo_clp is not None and costo_clp < 0:
        raise IncidenciaInvalida("el costo no puede ser negativo")
    res_texto = (resolucion or "").strip()[:1000] or None
    conexion.execute(
        "UPDATE incidencias SET estado = %s, resolucion = COALESCE(%s, resolucion), "
        "costo_clp = COALESCE(%s, costo_clp), cerrada_en = now(), cerrada_por = %s, actualizada_en = now() "
        "WHERE id = %s AND empresa_id = %s",
        (estado_final, res_texto, costo_clp, actor, incidencia_id, empresa_id),
    )
    if hab_id and bloqueaba:
        _sincronizar_bloqueo_habitacion(conexion, hotel, empresa_id, hab_id)
    seguridad.auditar(conexion, actor, "incidencia_cerrada", incidencia_id, estado_final)
    return obtener(conexion, empresa_id, incidencia_id)


def guardar_evidencia(
    conexion: psycopg.Connection,
    empresa_id: str,
    incidencia_id: str,
    actor: str,
    datos: bytes,
    nombre: str | None = None,
) -> dict:
    actual = conexion.execute(
        "SELECT 1 FROM incidencias WHERE id = %s AND empresa_id = %s FOR UPDATE",
        (incidencia_id, empresa_id),
    ).fetchone()
    if actual is None:
        raise IncidenciaNoEncontrada("acceso denegado")
    mime = detectar_mime_imagen(datos)
    ev_nombre = (nombre or f"evidencia.{mime.split('/')[-1]}")[:120]
    conexion.execute(
        "UPDATE incidencias SET evidencia_datos = %s, evidencia_mime = %s, evidencia_nombre = %s, "
        "actualizada_en = now() WHERE id = %s AND empresa_id = %s",
        (datos, mime, ev_nombre, incidencia_id, empresa_id),
    )
    seguridad.auditar(conexion, actor, "incidencia_evidencia", incidencia_id, mime)
    return obtener(conexion, empresa_id, incidencia_id)


def leer_evidencia(conexion: psycopg.Connection, empresa_id: str, incidencia_id: str) -> tuple[bytes, str, str]:
    fila = conexion.execute(
        "SELECT evidencia_datos, evidencia_mime, evidencia_nombre FROM incidencias "
        "WHERE id = %s AND empresa_id = %s",
        (incidencia_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise IncidenciaNoEncontrada("acceso denegado")
    if fila[0] is None:
        raise IncidenciaNoEncontrada("la incidencia no tiene evidencia adjunta")
    return bytes(fila[0]), fila[1] or "application/octet-stream", fila[2] or "evidencia"
