"""Corte 1 operativo (#415 incidencias, #416 tareas y checklists, #417 atención).

Incidencias con evidencia y bloqueo de disponibilidad (reutiliza el mantenimiento por
fechas de `hotel_sql.fijar_mantenimiento`), tareas generales con subtareas y plantillas
de checklist, estado «En limpieza» y el resumen «Lo que necesita atención». Sin datos
personales de huéspedes: solo ids de habitación, textos operativos y nombres de personal.
"""
from __future__ import annotations

import base64
import binascii
import uuid
from datetime import date, timedelta

import psycopg
from psycopg.types.json import Jsonb

from . import hotel_sql

GRAVEDADES = ("baja", "media", "alta", "critica")
ESTADOS_INCIDENCIA = ("abierta", "en_curso", "resuelta", "cerrada")
ABIERTAS = ("abierta", "en_curso")
AREAS = ("limpieza", "banos", "lavanderia", "desayunos", "mantencion", "general")
PRIORIDADES = ("baja", "normal", "alta", "urgente")
MIMES = ("image/jpeg", "image/png", "image/webp")
MAX_EVIDENCIA_BYTES = 180_000  # el tope general del cuerpo HTTP es 256 KB (base64 +33 %)
MAX_EVIDENCIAS = 6
_PESO_GRAVEDAD = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
_PESO_PRIORIDAD = {"urgente": 0, "alta": 1, "normal": 2, "baja": 3}


class OperacionInvalida(Exception):
    """409: la operación no aplica al estado actual."""


class NoEncontrado(Exception):
    """404: el recurso no existe."""


def _id(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:12]}"


def _habitacion_existe(conexion: psycopg.Connection, habitacion_id: str) -> None:
    if conexion.execute("SELECT 1 FROM habitaciones WHERE id = %s", (habitacion_id,)).fetchone() is None:
        raise NoEncontrado("la habitación no existe")


def _evento(conexion: psycopg.Connection, incidencia_id: str, accion: str, detalle: str | None, actor: str) -> None:
    conexion.execute(
        "INSERT INTO incidencia_eventos (incidencia_id, accion, detalle, actor) VALUES (%s, %s, %s, %s)",
        (incidencia_id, accion, detalle, actor),
    )


# --- Incidencias (#415) ---

_COLUMNAS_INCIDENCIA = (
    "id, habitacion_id, area, descripcion, gravedad, responsable, plazo, estado, costo_clp, "
    "bloquea_disponibilidad, bloqueo_aplicado, creada_por, creada_en, cerrada_en"
)


def _incidencia(f: tuple, evidencias: int = 0) -> dict:
    return {
        "incidencia_id": f[0], "habitacion_id": f[1], "area": f[2], "descripcion": f[3], "gravedad": f[4],
        "responsable": f[5], "plazo": f[6].isoformat() if f[6] else None, "estado": f[7], "costo_clp": f[8],
        "bloquea_disponibilidad": f[9], "bloqueo_activo": f[10], "creada_por": f[11],
        "creada_en": f[12].isoformat(), "cerrada_en": f[13].isoformat() if f[13] else None,
        "evidencias": evidencias,
    }


def _bloquear(conexion, hotel, empresa_id: str, incidencia_id: str, habitacion_id: str, plazo: date | None) -> bool:
    """Saca la unidad del cupo si no estaba ya en mantenimiento. True si lo aplicó esta incidencia."""
    (ya,) = conexion.execute("SELECT mantenimiento FROM habitaciones WHERE id = %s", (habitacion_id,)).fetchone()
    if ya:
        return False
    hasta = plazo + timedelta(days=1) if plazo and plazo >= date.today() else None
    hotel_sql.fijar_mantenimiento(conexion, hotel, empresa_id, habitacion_id, True, date.today(), hasta)
    conexion.execute("UPDATE incidencias SET bloqueo_aplicado = true WHERE id = %s", (incidencia_id,))
    return True


def _liberar(conexion, hotel, empresa_id: str, incidencia_id: str, habitacion_id: str | None) -> bool:
    """Devuelve la unidad al cupo si esta incidencia la había bloqueado y no queda otra que lo haga."""
    (aplicado,) = conexion.execute("SELECT bloqueo_aplicado FROM incidencias WHERE id = %s", (incidencia_id,)).fetchone()
    if not aplicado or habitacion_id is None:
        return False
    conexion.execute("UPDATE incidencias SET bloqueo_aplicado = false WHERE id = %s", (incidencia_id,))
    (otras,) = conexion.execute(
        "SELECT count(*) FROM incidencias WHERE habitacion_id = %s AND id <> %s AND bloqueo_aplicado "
        "AND estado IN ('abierta', 'en_curso')",
        (habitacion_id, incidencia_id),
    ).fetchone()
    if otras:
        return False
    hotel_sql.fijar_mantenimiento(conexion, hotel, empresa_id, habitacion_id, False)
    return True


def crear_incidencia(conexion, hotel, empresa_id: str, actor: str, datos: dict) -> dict:
    habitacion_id = datos.get("habitacion_id")
    if habitacion_id:
        _habitacion_existe(conexion, habitacion_id)
    incidencia_id = _id("INC")
    conexion.execute(
        "INSERT INTO incidencias (id, habitacion_id, area, descripcion, gravedad, responsable, plazo, costo_clp, "
        "bloquea_disponibilidad, creada_por) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (incidencia_id, habitacion_id, datos.get("area"), datos["descripcion"].strip(), datos["gravedad"],
         datos.get("responsable"), datos.get("plazo"), datos.get("costo_clp"),
         bool(datos.get("bloquea_disponibilidad")), actor),
    )
    _evento(conexion, incidencia_id, "creada", f"gravedad={datos['gravedad']}", actor)
    bloqueada = False
    if datos.get("bloquea_disponibilidad"):
        bloqueada = _bloquear(conexion, hotel, empresa_id, incidencia_id, habitacion_id, datos.get("plazo"))
        _evento(conexion, incidencia_id, "bloqueo", "aplicado" if bloqueada else "ya estaba en mantenimiento", actor)
    return {**obtener_incidencia(conexion, incidencia_id), "bloqueo_aplicado_ahora": bloqueada}


def obtener_incidencia(conexion, incidencia_id: str) -> dict:
    fila = conexion.execute(f"SELECT {_COLUMNAS_INCIDENCIA} FROM incidencias WHERE id = %s", (incidencia_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("la incidencia no existe")
    (n,) = conexion.execute(
        "SELECT count(*) FROM incidencia_evidencias WHERE incidencia_id = %s", (incidencia_id,)
    ).fetchone()
    eventos = [
        {"accion": e[0], "detalle": e[1], "actor": e[2], "registrado_en": e[3].isoformat()}
        for e in conexion.execute(
            "SELECT accion, detalle, actor, registrado_en FROM incidencia_eventos WHERE incidencia_id = %s ORDER BY id",
            (incidencia_id,),
        ).fetchall()
    ]
    return {**_incidencia(fila, n), "eventos": eventos}


def listar_incidencias(conexion, estado: str | None = None, habitacion_id: str | None = None) -> dict:
    filtros, params = [], []
    if estado == "abiertas":
        filtros.append("estado IN ('abierta', 'en_curso')")
    elif estado:
        filtros.append("estado = %s")
        params.append(estado)
    if habitacion_id:
        filtros.append("habitacion_id = %s")
        params.append(habitacion_id)
    donde = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    filas = conexion.execute(
        f"SELECT {_COLUMNAS_INCIDENCIA}, (SELECT count(*) FROM incidencia_evidencias e WHERE e.incidencia_id = incidencias.id) "
        f"FROM incidencias {donde} ORDER BY creada_en DESC LIMIT 200",
        params,
    ).fetchall()
    items = [_incidencia(f[:14], f[14]) for f in filas]
    items.sort(key=lambda i: (i["estado"] not in ABIERTAS, not i["bloqueo_activo"], _PESO_GRAVEDAD[i["gravedad"]]))
    return {"items": items, "abiertas": sum(1 for i in items if i["estado"] in ABIERTAS)}


def actualizar_incidencia(conexion, hotel, empresa_id: str, actor: str, incidencia_id: str, cambios: dict) -> dict:
    actual = obtener_incidencia(conexion, incidencia_id)
    if actual["estado"] == "cerrada":
        raise OperacionInvalida("la incidencia ya está cerrada")
    nuevo = cambios.get("estado")
    if nuevo == "cerrada":
        raise OperacionInvalida("para cerrar usa la operación de cierre")
    if nuevo and nuevo not in ESTADOS_INCIDENCIA:
        raise OperacionInvalida("estado inválido")
    sets, params = [], []
    for campo in ("gravedad", "responsable", "plazo", "costo_clp", "estado"):
        if cambios.get(campo) is not None:
            sets.append(f"{campo} = %s")
            params.append(cambios[campo])
    if not sets:
        raise OperacionInvalida("no hay cambios")
    conexion.execute(f"UPDATE incidencias SET {', '.join(sets)} WHERE id = %s", (*params, incidencia_id))
    detalle = ", ".join(f"{c}={cambios[c]}" for c in ("estado", "gravedad", "responsable", "plazo", "costo_clp")
                        if cambios.get(c) is not None)
    _evento(conexion, incidencia_id, "estado" if nuevo else "actualizada", detalle, actor)
    if nuevo == "resuelta":
        _liberar(conexion, hotel, empresa_id, incidencia_id, actual["habitacion_id"])
    return obtener_incidencia(conexion, incidencia_id)


def cerrar_incidencia(conexion, hotel, empresa_id: str, actor: str, incidencia_id: str,
                      costo_clp: int | None, nota: str | None) -> dict:
    actual = obtener_incidencia(conexion, incidencia_id)
    if actual["estado"] == "cerrada":
        raise OperacionInvalida("la incidencia ya está cerrada")
    conexion.execute(
        "UPDATE incidencias SET estado = 'cerrada', cerrada_en = now(), costo_clp = COALESCE(%s, costo_clp) WHERE id = %s",
        (costo_clp, incidencia_id),
    )
    liberada = _liberar(conexion, hotel, empresa_id, incidencia_id, actual["habitacion_id"])
    _evento(conexion, incidencia_id, "cierre", (nota or "")[:300] or None, actor)
    return {**obtener_incidencia(conexion, incidencia_id), "unidad_liberada": liberada}


def agregar_evidencia(conexion, actor: str, incidencia_id: str, mime: str, contenido_base64: str) -> dict:
    if mime not in MIMES:
        raise OperacionInvalida("formato de imagen no admitido")
    try:
        contenido = base64.b64decode(contenido_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise OperacionInvalida("la imagen no es base64 válido") from error
    if not contenido or len(contenido) > MAX_EVIDENCIA_BYTES:
        raise OperacionInvalida(f"la imagen debe pesar hasta {MAX_EVIDENCIA_BYTES // 1000} KB")
    obtener_incidencia(conexion, incidencia_id)
    (n,) = conexion.execute(
        "SELECT count(*) FROM incidencia_evidencias WHERE incidencia_id = %s", (incidencia_id,)
    ).fetchone()
    if n >= MAX_EVIDENCIAS:
        raise OperacionInvalida(f"máximo {MAX_EVIDENCIAS} fotos por incidencia")
    evidencia_id = _id("EVD")
    conexion.execute(
        "INSERT INTO incidencia_evidencias (id, incidencia_id, mime, contenido, subida_por) VALUES (%s, %s, %s, %s, %s)",
        (evidencia_id, incidencia_id, mime, contenido, actor),
    )
    _evento(conexion, incidencia_id, "evidencia", evidencia_id, actor)
    return {"evidencia_id": evidencia_id, "incidencia_id": incidencia_id, "bytes": len(contenido)}


def leer_evidencia(conexion, incidencia_id: str, evidencia_id: str) -> tuple[str, bytes]:
    fila = conexion.execute(
        "SELECT mime, contenido FROM incidencia_evidencias WHERE id = %s AND incidencia_id = %s",
        (evidencia_id, incidencia_id),
    ).fetchone()
    if fila is None:
        raise NoEncontrado("la evidencia no existe")
    return fila[0], bytes(fila[1])


# --- Tareas generales y checklists (#416) ---

def _tarea(conexion, f: tuple) -> dict:
    subtareas = [
        {"subtarea_id": s[0], "texto": s[1], "obligatoria": s[2], "hecha": s[3], "hecha_por": s[4]}
        for s in conexion.execute(
            "SELECT id, texto, obligatoria, hecha, hecha_por FROM tarea_subtareas WHERE tarea_id = %s ORDER BY orden, id",
            (f[0],),
        ).fetchall()
    ]
    obligatorias = [s for s in subtareas if s["obligatoria"]]
    return {
        "tarea_id": f[0], "titulo": f[1], "area": f[2], "habitacion_id": f[3], "prioridad": f[4],
        "vence": f[5].isoformat() if f[5] else None, "responsable": f[6], "observaciones": f[7], "estado": f[8],
        "creada_por": f[9], "completada_por": f[10], "subtareas": subtareas,
        "obligatorias_pendientes": sum(1 for s in obligatorias if not s["hecha"]),
        "progreso": {"hechas": sum(1 for s in subtareas if s["hecha"]), "total": len(subtareas)},
    }


_COLUMNAS_TAREA = "id, titulo, area, habitacion_id, prioridad, vence, responsable, observaciones, estado, creada_por, completada_por"


def crear_tarea(conexion, actor: str, datos: dict) -> dict:
    if datos.get("habitacion_id"):
        _habitacion_existe(conexion, datos["habitacion_id"])
    items = list(datos.get("subtareas") or [])
    plantilla_id = datos.get("plantilla_id")
    if plantilla_id:
        fila = conexion.execute("SELECT items FROM checklist_plantillas WHERE id = %s", (plantilla_id,)).fetchone()
        if fila is None:
            raise NoEncontrado("la plantilla no existe")
        items = [*fila[0], *items]
    tarea_id = _id("TGN")
    conexion.execute(
        "INSERT INTO tareas_generales (id, titulo, area, habitacion_id, prioridad, vence, responsable, observaciones, creada_por) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (tarea_id, datos["titulo"].strip(), datos["area"], datos.get("habitacion_id"), datos["prioridad"],
         datos.get("vence"), datos.get("responsable"), datos.get("observaciones"), actor),
    )
    for orden, item in enumerate(items):
        conexion.execute(
            "INSERT INTO tarea_subtareas (id, tarea_id, orden, texto, obligatoria) VALUES (%s, %s, %s, %s, %s)",
            (_id("SUB"), tarea_id, orden, item["texto"].strip(), bool(item.get("obligatoria", True))),
        )
    return obtener_tarea(conexion, tarea_id)


def obtener_tarea(conexion, tarea_id: str) -> dict:
    fila = conexion.execute(f"SELECT {_COLUMNAS_TAREA} FROM tareas_generales WHERE id = %s", (tarea_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("la tarea no existe")
    return _tarea(conexion, fila)


def listar_tareas(conexion, estado: str | None = None, habitacion_id: str | None = None) -> dict:
    filtros, params = [], []
    if estado:
        filtros.append("estado = %s")
        params.append(estado)
    if habitacion_id:
        filtros.append("habitacion_id = %s")
        params.append(habitacion_id)
    donde = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    filas = conexion.execute(
        f"SELECT {_COLUMNAS_TAREA} FROM tareas_generales {donde} ORDER BY creada_en DESC LIMIT 200", params
    ).fetchall()
    items = [_tarea(conexion, f) for f in filas]
    items.sort(key=lambda t: (t["estado"] != "pendiente", _PESO_PRIORIDAD[t["prioridad"]], t["vence"] or "9999"))
    return {"items": items, "pendientes": sum(1 for t in items if t["estado"] == "pendiente")}


def marcar_subtarea(conexion, actor: str, tarea_id: str, subtarea_id: str, hecha: bool) -> dict:
    tarea = obtener_tarea(conexion, tarea_id)
    if tarea["estado"] == "completada":
        raise OperacionInvalida("la tarea ya está completada")
    cambiadas = conexion.execute(
        "UPDATE tarea_subtareas SET hecha = %s, hecha_por = %s, hecha_en = CASE WHEN %s THEN now() END "
        "WHERE id = %s AND tarea_id = %s",
        (hecha, actor if hecha else None, hecha, subtarea_id, tarea_id),
    ).rowcount
    if not cambiadas:
        raise NoEncontrado("la subtarea no existe")
    return obtener_tarea(conexion, tarea_id)


def cerrar_tarea(conexion, actor: str, tarea_id: str) -> dict:
    tarea = obtener_tarea(conexion, tarea_id)
    if tarea["estado"] == "completada":
        raise OperacionInvalida("la tarea ya está completada")
    if tarea["obligatorias_pendientes"]:
        raise OperacionInvalida(f"faltan {tarea['obligatorias_pendientes']} subtareas obligatorias")
    conexion.execute(
        "UPDATE tareas_generales SET estado = 'completada', completada_por = %s, completada_en = now() WHERE id = %s",
        (actor, tarea_id),
    )
    return obtener_tarea(conexion, tarea_id)


def listar_plantillas(conexion) -> dict:
    return {"items": [
        {"plantilla_id": f[0], "nombre": f[1], "area": f[2], "items": f[3]}
        for f in conexion.execute("SELECT id, nombre, area, items FROM checklist_plantillas ORDER BY nombre").fetchall()
    ]}


def crear_plantilla(conexion, actor: str, nombre: str, area: str, items: list[dict]) -> dict:
    plantilla_id = _id("CHK")
    if conexion.execute("SELECT 1 FROM checklist_plantillas WHERE nombre = %s", (nombre.strip(),)).fetchone():
        raise OperacionInvalida("ya existe una plantilla con ese nombre")
    try:
        conexion.execute(
            "INSERT INTO checklist_plantillas (id, nombre, area, items, creada_por) VALUES (%s, %s, %s, %s::jsonb, %s)",
            (plantilla_id, nombre.strip(), area,
             Jsonb([{"texto": i["texto"].strip(), "obligatoria": bool(i.get("obligatoria", True))} for i in items]),
             actor),
        )
    except psycopg.errors.UniqueViolation as error:
        raise OperacionInvalida("ya existe una plantilla con ese nombre") from error
    return next(p for p in listar_plantillas(conexion)["items"] if p["plantilla_id"] == plantilla_id)


# --- «En limpieza» (#416) ---

def iniciar_limpieza(conexion, actor: str, habitacion_id: str) -> dict:
    fila = conexion.execute(
        "SELECT estado_preparacion, en_limpieza_desde FROM habitaciones WHERE id = %s", (habitacion_id,)
    ).fetchone()
    if fila is None:
        raise NoEncontrado("la habitación no existe")
    if fila[0] != "sucia":
        raise OperacionInvalida("solo una habitación sucia puede pasar a «En limpieza»")
    if fila[1] is None:
        conexion.execute(
            "UPDATE habitaciones SET en_limpieza_desde = now(), en_limpieza_por = %s WHERE id = %s", (actor, habitacion_id)
        )
    return {"habitacion_id": habitacion_id, "en_limpieza": True, "estado_preparacion": "sucia"}


# --- «Lo que necesita atención» (#417) ---

def atencion(conexion, hoy: date, reposicion: dict | None = None) -> dict:
    """Asuntos urgentes cruzando áreas, cada uno con el enlace al registro de origen.
    Sin nombres de huéspedes: solo ids de reserva y de habitación."""
    def reservas(condicion: str) -> list[dict]:
        return [
            {"id": f[0], "habitacion_id": f[1], "fecha": f[2].isoformat(), "enlace": f"/hotel/reservas/{f[0]}"}
            for f in conexion.execute(
                f"SELECT id, habitacion_id, {'inicio' if 'confirmada' in condicion else 'fin'} FROM reservas "
                f"WHERE {condicion} ORDER BY 3, id LIMIT 50", (hoy,)
            ).fetchall()
        ]

    por_verificar = [
        {"id": f[0], "habitacion_id": f[1], "enlace": "/hotel/aseo"}
        for f in conexion.execute(
            "SELECT id, habitacion_id FROM ("
            " SELECT DISTINCT ON (habitacion_id) id, habitacion_id, verificacion FROM tareas_operativas"
            " WHERE tipo = 'limpieza' AND estado = 'completada' ORDER BY habitacion_id, completada_en DESC"
            ") u WHERE verificacion IS NULL ORDER BY habitacion_id"
        ).fetchall()
    ]
    incidencias = [
        {"id": f[0], "habitacion_id": f[1], "gravedad": f[2], "bloquea": f[3], "descripcion": f[4][:80],
         "enlace": f"/hotel/habitaciones/{f[1]}" if f[1] else "/hotel/aseo"}
        for f in conexion.execute(
            "SELECT id, habitacion_id, gravedad, bloqueo_aplicado, descripcion FROM incidencias "
            "WHERE estado IN ('abierta', 'en_curso') "
            "ORDER BY bloqueo_aplicado DESC, CASE gravedad WHEN 'critica' THEN 0 WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END, creada_en "
            "LIMIT 50"
        ).fetchall()
    ]
    bajo_stock = [
        {"id": i["producto_id"], "nombre": i["nombre"], "nivel": i["nivel"], "enlace": "/hotel/productos"}
        for i in (reposicion or {}).get("items", []) if i.get("nivel") != "ok"
    ][:50]
    grupos = {
        "llegadas_atrasadas": reservas("estado = 'confirmada' AND inicio < %s"),
        "salidas_atrasadas": reservas("estado = 'en_estadia' AND fin < %s"),
        "limpiezas_por_verificar": por_verificar,
        "incidencias_abiertas": incidencias,
        "productos_bajo_minimo": bajo_stock,
    }
    return {
        "total": sum(len(v) for v in grupos.values()),
        "bloqueos_por_incidencia": sum(1 for i in incidencias if i["bloquea"]),
        **grupos,
    }
