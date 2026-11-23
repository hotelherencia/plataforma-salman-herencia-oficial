"""Tareas operativas generales, checklists con subtareas y estado «En limpieza» (#416).

Extiende `tareas_operativas` para soportar:
- Estado intermedio «En limpieza» (`estado_preparacion = 'en_limpieza'`) al iniciar
  la limpieza de una habitación.
- Subtareas marcables individualmente (`tarea_subtareas`); si existen subtareas
  obligatorias sin completar, la tarea principal no se puede cerrar (409).
- Tareas manuales por habitación o área común (limpieza, baños, lavandería,
  desayunos, mantenimiento, general) con responsable, prioridad, vencimiento y
  observaciones.

Toda mutación queda en `auditoria` sin PII.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import psycopg

from . import hotel_sql, roles, seguridad

ROLES_OPERACION = roles.con_admin_hotel("recepcion", "aseo")
ROLES_GESTION = roles.con_admin_hotel("recepcion")

TIPOS_TAREA = ("limpieza", "mantenimiento", "banos", "lavanderia", "desayunos", "general")
ESTADOS_TAREA = ("pendiente", "en_proceso", "completada", "cancelada")
PRIORIDADES = ("baja", "media", "alta", "urgente")


class TareaInvalida(Exception):
    """422: parámetros inválidos para tarea o subtarea."""


class TareaNoEncontrada(Exception):
    """403/404: tarea o subtarea inexistente."""


class TareaConflicto(Exception):
    """409: transición no permitida (p. ej. subtareas obligatorias pendientes)."""


def subtareas_de_tareas(conexion: psycopg.Connection, tarea_ids: list[str]) -> dict[str, list[dict]]:
    if not tarea_ids:
        return {}
    filas = conexion.execute(
        "SELECT id, tarea_id, descripcion, obligatoria, completada, completada_por, completada_en, orden "
        "FROM tarea_subtareas WHERE tarea_id = ANY(%s) ORDER BY orden, id",
        (tarea_ids,),
    ).fetchall()
    mapa: dict[str, list[dict]] = {}
    for f in filas:
        mapa.setdefault(f[1], []).append(
            {
                "subtarea_id": f[0],
                "descripcion": f[2],
                "obligatoria": bool(f[3]),
                "completada": bool(f[4]),
                "completada_por": f[5],
                "completada_en": f[6].isoformat() if f[6] else None,
                "orden": int(f[7]),
            }
        )
    return mapa


def plantillas_activas(conexion: psycopg.Connection, tipo: str | None = None) -> list[dict]:
    if tipo:
        filas = conexion.execute(
            "SELECT id, tipo, descripcion, obligatoria, orden FROM checklist_plantillas "
            "WHERE activo AND tipo = %s ORDER BY orden, id",
            (tipo,),
        ).fetchall()
    else:
        filas = conexion.execute(
            "SELECT id, tipo, descripcion, obligatoria, orden FROM checklist_plantillas "
            "WHERE activo ORDER BY tipo, orden, id"
        ).fetchall()
    return [
        {
            "plantilla_id": f[0],
            "tipo": f[1],
            "descripcion": f[2],
            "obligatoria": bool(f[3]),
            "orden": int(f[4]),
        }
        for f in filas
    ]


def _insertar_subtareas_desde_plantilla(conexion: psycopg.Connection, tarea_id: str, tipo: str) -> int:
    items = plantillas_activas(conexion, tipo)
    for item in items:
        conexion.execute(
            "INSERT INTO tarea_subtareas (id, tarea_id, descripcion, obligatoria, orden) "
            "VALUES (%s, %s, %s, %s, %s)",
            (f"SUB-{uuid.uuid4().hex[:12]}", tarea_id, item["descripcion"], item["obligatoria"], item["orden"]),
        )
    return len(items)


def _exigir_obligatorias_completas(conexion: psycopg.Connection, tarea_id: str) -> None:
    (pendientes,) = conexion.execute(
        "SELECT count(*) FROM tarea_subtareas WHERE tarea_id = %s AND obligatoria AND NOT completada",
        (tarea_id,),
    ).fetchone()
    if pendientes > 0:
        raise TareaConflicto(
            f"faltan {pendientes} subtarea(s) obligatoria(s) por completar antes de cerrar la tarea"
        )


def _a_dict(f, subtareas: list[dict]) -> dict:
    obligatorias_pend = sum(1 for s in subtareas if s["obligatoria"] and not s["completada"])
    return {
        "tarea_id": f[0],
        "habitacion_id": f[1],
        "area": f[2] or ("habitacion" if f[1] else "general"),
        "tipo": f[3],
        "titulo": f[4] or f"{f[3].capitalize()}{' · ' + f[1] if f[1] else ''}",
        "estado": f[5],
        "prioridad": f[6] or "media",
        "responsable": f[7],
        "vence_en": f[8].isoformat() if f[8] else None,
        "observacion": f[9],
        "creada_en": f[10].isoformat() if f[10] else None,
        "creada_por": f[11],
        "iniciada_en": f[12].isoformat() if f[12] else None,
        "iniciada_por": f[13],
        "completada_en": f[14].isoformat() if f[14] else None,
        "completada_por": f[15],
        "verificacion": f[16],
        "subtareas": subtareas,
        "subtareas_total": len(subtareas),
        "subtareas_completadas": sum(1 for s in subtareas if s["completada"]),
        "obligatorias_pendientes": obligatorias_pend,
    }


_COLS = (
    "id, habitacion_id, area, tipo, titulo, estado, prioridad, responsable, vence_en, "
    "observacion, creado_en, creada_por, iniciada_en, iniciada_por, completada_en, "
    "completada_por, verificacion"
)


def obtener(conexion: psycopg.Connection, empresa_id: str, tarea_id: str) -> dict:
    fila = conexion.execute(
        f"SELECT {_COLS} FROM tareas_operativas "
        "WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)",
        (tarea_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise TareaNoEncontrada("acceso denegado")
    subs = subtareas_de_tareas(conexion, [tarea_id]).get(tarea_id, [])
    return _a_dict(fila, subs)


def iniciar_limpieza(
    conexion: psycopg.Connection,
    empresa_id: str,
    habitacion_id: str,
    actor: str,
    *,
    aplicar_plantilla: bool = True,
) -> dict:
    """#416: pasa la habitación a estado intermedio «En limpieza» y la tarea a `en_proceso`,
    instanciando el checklist base de limpieza si aún no tiene subtareas."""
    hab = conexion.execute(
        "SELECT estado_operativo, estado_preparacion FROM habitaciones WHERE id = %s FOR UPDATE",
        (habitacion_id,),
    ).fetchone()
    if hab is None:
        raise TareaNoEncontrada("acceso denegado")
    estado_op, estado_prep = hab
    tarea = conexion.execute(
        "SELECT id, estado FROM tareas_operativas "
        "WHERE habitacion_id = %s AND tipo = 'limpieza' AND estado IN ('pendiente', 'en_proceso') "
        "ORDER BY creado_en LIMIT 1 FOR UPDATE",
        (habitacion_id,),
    ).fetchone()
    if tarea is None:
        if estado_prep in ("sucia", "en_limpieza"):
            tarea_id = f"TSK-{uuid.uuid4().hex[:12]}"
            conexion.execute(
                "INSERT INTO tareas_operativas "
                "(id, empresa_id, habitacion_id, area, tipo, titulo, estado, prioridad, iniciada_en, iniciada_por, creada_por) "
                "VALUES (%s, %s, %s, 'habitacion', 'limpieza', %s, 'en_proceso', 'alta', now(), %s, %s)",
                (tarea_id, empresa_id, habitacion_id, f"Limpieza {habitacion_id}", actor, actor),
            )
        else:
            raise TareaConflicto("no hay una limpieza pendiente en la habitación")
    else:
        tarea_id = tarea[0]
        conexion.execute(
            "UPDATE tareas_operativas SET estado = 'en_proceso', empresa_id = COALESCE(empresa_id, %s), "
            "iniciada_en = COALESCE(iniciada_en, now()), iniciada_por = COALESCE(iniciada_por, %s), "
            "responsable = COALESCE(responsable, %s) WHERE id = %s",
            (empresa_id, actor, actor, tarea_id),
        )
    conexion.execute(
        "UPDATE habitaciones SET estado_preparacion = 'en_limpieza' WHERE id = %s",
        (habitacion_id,),
    )
    if aplicar_plantilla:
        (ya_tiene,) = conexion.execute(
            "SELECT count(*) FROM tarea_subtareas WHERE tarea_id = %s", (tarea_id,)
        ).fetchone()
        if ya_tiene == 0:
            _insertar_subtareas_desde_plantilla(conexion, tarea_id, "limpieza")
    seguridad.auditar(conexion, actor, "limpieza_iniciada", habitacion_id, tarea_id)
    datos = obtener(conexion, empresa_id, tarea_id)
    datos["estado_preparacion"] = "en_limpieza"
    datos["estado_operativo"] = estado_op
    return datos


def crear_tarea(
    conexion: psycopg.Connection,
    empresa_id: str,
    actor: str,
    *,
    tipo: str,
    titulo: str,
    habitacion_id: str | None = None,
    area: str | None = None,
    prioridad: str = "media",
    responsable: str | None = None,
    vence_en: datetime | None = None,
    observacion: str | None = None,
    subtareas: list[dict] | None = None,
    aplicar_plantilla: bool = False,
) -> dict:
    if tipo not in TIPOS_TAREA:
        raise TareaInvalida("tipo de tarea inválido")
    if prioridad not in PRIORIDADES:
        raise TareaInvalida("prioridad inválida")
    titulo = " ".join((titulo or "").split())
    if len(titulo) < 3 or len(titulo) > 160:
        raise TareaInvalida("el título debe tener entre 3 y 160 caracteres")
    if habitacion_id:
        habitacion_id = habitacion_id.strip()
        if conexion.execute("SELECT 1 FROM habitaciones WHERE id = %s", (habitacion_id,)).fetchone() is None:
            raise TareaInvalida(f"la habitación {habitacion_id} no existe")
        area_final = "habitacion"
    else:
        area_final = (area or tipo).strip().lower()[:60] or "general"

    tarea_id = f"TSK-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO tareas_operativas "
        "(id, empresa_id, habitacion_id, area, tipo, titulo, estado, prioridad, responsable, vence_en, observacion, creada_por) "
        "VALUES (%s, %s, %s, %s, %s, %s, 'pendiente', %s, %s, %s, %s, %s)",
        (
            tarea_id,
            empresa_id,
            habitacion_id,
            area_final,
            tipo,
            titulo,
            prioridad,
            (responsable or "").strip()[:100] or None,
            vence_en,
            (observacion or "").strip()[:500] or None,
            actor,
        ),
    )
    orden = 10
    if subtareas:
        for item in subtareas:
            desc = " ".join(str(item.get("descripcion") or "").split())
            if len(desc) < 2 or len(desc) > 240:
                raise TareaInvalida("cada subtarea debe tener entre 2 y 240 caracteres")
            conexion.execute(
                "INSERT INTO tarea_subtareas (id, tarea_id, descripcion, obligatoria, orden) "
                "VALUES (%s, %s, %s, %s, %s)",
                (f"SUB-{uuid.uuid4().hex[:12]}", tarea_id, desc, bool(item.get("obligatoria", True)), orden),
            )
            orden += 10
    elif aplicar_plantilla:
        _insertar_subtareas_desde_plantilla(conexion, tarea_id, tipo)

    destino = habitacion_id or area_final
    seguridad.auditar(conexion, actor, "tarea_creada", tarea_id, f"{tipo}:{prioridad}:{destino}")
    return obtener(conexion, empresa_id, tarea_id)


def listar_tareas(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    estado: str | None = None,
    tipo: str | None = None,
    habitacion_id: str | None = None,
    area: str | None = None,
    prioridad: str | None = None,
    responsable: str | None = None,
    solo_abiertas: bool = False,
) -> dict:
    filtros = ["(empresa_id IS NULL OR empresa_id = %s)"]
    params: list = [empresa_id]
    if solo_abiertas:
        filtros.append("estado IN ('pendiente', 'en_proceso')")
    elif estado:
        if estado not in ESTADOS_TAREA:
            raise TareaInvalida("estado inválido")
        filtros.append("estado = %s")
        params.append(estado)
    if tipo:
        if tipo not in TIPOS_TAREA:
            raise TareaInvalida("tipo inválido")
        filtros.append("tipo = %s")
        params.append(tipo)
    if habitacion_id:
        filtros.append("habitacion_id = %s")
        params.append(habitacion_id)
    if area:
        filtros.append("area = %s")
        params.append(area)
    if prioridad:
        if prioridad not in PRIORIDADES:
            raise TareaInvalida("prioridad inválida")
        filtros.append("prioridad = %s")
        params.append(prioridad)
    if responsable:
        filtros.append("responsable = %s")
        params.append(responsable)

    orden = (
        "CASE estado WHEN 'en_proceso' THEN 0 WHEN 'pendiente' THEN 1 WHEN 'completada' THEN 2 ELSE 3 END, "
        "CASE prioridad WHEN 'urgente' THEN 0 WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END, "
        "vence_en ASC NULLS LAST, creado_en DESC, id DESC"
    )
    filas = conexion.execute(
        f"SELECT {_COLS} FROM tareas_operativas WHERE {' AND '.join(filtros)} ORDER BY {orden} LIMIT 200",
        params,
    ).fetchall()
    subs = subtareas_de_tareas(conexion, [f[0] for f in filas])
    tareas = [_a_dict(f, subs.get(f[0], [])) for f in filas]
    return {
        "tareas": tareas,
        "total": len(tareas),
        "abiertas": sum(1 for t in tareas if t["estado"] in ("pendiente", "en_proceso")),
        "plantillas": plantillas_activas(conexion),
    }


def actualizar_tarea(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    tarea_id: str,
    actor: str,
    cambios: dict,
) -> dict:
    fila = conexion.execute(
        "SELECT habitacion_id, tipo, estado FROM tareas_operativas "
        "WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s) FOR UPDATE",
        (tarea_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise TareaNoEncontrada("acceso denegado")
    hab_id, tipo, estado_actual = fila

    sets: list[str] = []
    params: list = []
    campos_audit: list[str] = []

    if "titulo" in cambios and cambios["titulo"] is not None:
        t = " ".join(str(cambios["titulo"]).split())
        if len(t) < 3 or len(t) > 160:
            raise TareaInvalida("el título debe tener entre 3 y 160 caracteres")
        sets.append("titulo = %s")
        params.append(t)
        campos_audit.append("titulo")
    if "prioridad" in cambios and cambios["prioridad"] is not None:
        if cambios["prioridad"] not in PRIORIDADES:
            raise TareaInvalida("prioridad inválida")
        sets.append("prioridad = %s")
        params.append(cambios["prioridad"])
        campos_audit.append("prioridad")
    if "responsable" in cambios:
        resp = (cambios["responsable"] or "").strip()[:100] or None
        sets.append("responsable = %s")
        params.append(resp)
        campos_audit.append("responsable")
    if "vence_en" in cambios:
        sets.append("vence_en = %s")
        params.append(cambios["vence_en"])
        campos_audit.append("vence_en")
    if "observacion" in cambios:
        obs = (cambios["observacion"] or "").strip()[:500] or None
        sets.append("observacion = %s")
        params.append(obs)
        campos_audit.append("observacion")

    nuevo_estado = cambios.get("estado")
    if nuevo_estado is not None:
        if nuevo_estado not in ESTADOS_TAREA:
            raise TareaInvalida("estado inválido")
        if nuevo_estado == "completada":
            _exigir_obligatorias_completas(conexion, tarea_id)
            if tipo == "limpieza" and hab_id:
                hotel_sql.completar_limpieza(conexion, hotel, empresa_id, hab_id, actor=actor)
                campos_audit.append("estado:completada")
            else:
                sets.append("estado = 'completada'")
                sets.append("completada_en = COALESCE(completada_en, now())")
                sets.append("completada_por = COALESCE(completada_por, %s)")
                params.append(actor)
                campos_audit.append("estado:completada")
        else:
            sets.append("estado = %s")
            params.append(nuevo_estado)
            if nuevo_estado == "en_proceso":
                sets.append("iniciada_en = COALESCE(iniciada_en, now())")
                sets.append("iniciada_por = COALESCE(iniciada_por, %s)")
                params.append(actor)
                if tipo == "limpieza" and hab_id:
                    conexion.execute(
                        "UPDATE habitaciones SET estado_preparacion = 'en_limpieza' "
                        "WHERE id = %s AND estado_preparacion IN ('sucia', 'en_limpieza')",
                        (hab_id,),
                    )
            campos_audit.append(f"estado:{nuevo_estado}")

    if sets:
        params.append(tarea_id)
        conexion.execute(f"UPDATE tareas_operativas SET {', '.join(sets)} WHERE id = %s", params)
    if campos_audit:
        seguridad.auditar(conexion, actor, "tarea_actualizada", tarea_id, ",".join(campos_audit))
    return obtener(conexion, empresa_id, tarea_id)


def agregar_subtarea(
    conexion: psycopg.Connection,
    empresa_id: str,
    tarea_id: str,
    actor: str,
    *,
    descripcion: str,
    obligatoria: bool = True,
) -> dict:
    fila = conexion.execute(
        "SELECT estado FROM tareas_operativas WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s) FOR UPDATE",
        (tarea_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise TareaNoEncontrada("acceso denegado")
    if fila[0] in ("completada", "cancelada"):
        raise TareaConflicto("no se pueden agregar subtareas a una tarea cerrada")
    desc = " ".join((descripcion or "").split())
    if len(desc) < 2 or len(desc) > 240:
        raise TareaInvalida("la descripción de la subtarea debe tener entre 2 y 240 caracteres")
    (max_orden,) = conexion.execute(
        "SELECT COALESCE(MAX(orden), 0) FROM tarea_subtareas WHERE tarea_id = %s", (tarea_id,)
    ).fetchone()
    sub_id = f"SUB-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO tarea_subtareas (id, tarea_id, descripcion, obligatoria, orden) "
        "VALUES (%s, %s, %s, %s, %s)",
        (sub_id, tarea_id, desc, bool(obligatoria), int(max_orden) + 10),
    )
    seguridad.auditar(conexion, actor, "subtarea_creada", sub_id, tarea_id)
    return obtener(conexion, empresa_id, tarea_id)


def marcar_subtarea(
    conexion: psycopg.Connection,
    empresa_id: str,
    tarea_id: str,
    subtarea_id: str,
    actor: str,
    completada: bool,
) -> dict:
    fila = conexion.execute(
        "SELECT t.estado FROM tareas_operativas t JOIN tarea_subtareas s ON s.tarea_id = t.id "
        "WHERE t.id = %s AND s.id = %s AND (t.empresa_id IS NULL OR t.empresa_id = %s) FOR UPDATE",
        (tarea_id, subtarea_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise TareaNoEncontrada("acceso denegado")
    if fila[0] in ("completada", "cancelada"):
        raise TareaConflicto("la tarea ya está cerrada")
    conexion.execute(
        "UPDATE tarea_subtareas SET completada = %s, "
        "completada_por = CASE WHEN %s THEN %s ELSE NULL END, "
        "completada_en = CASE WHEN %s THEN now() ELSE NULL END "
        "WHERE id = %s AND tarea_id = %s",
        (bool(completada), bool(completada), actor, bool(completada), subtarea_id, tarea_id),
    )
    seguridad.auditar(
        conexion,
        actor,
        "subtarea_actualizada",
        subtarea_id,
        "completada" if completada else "pendiente",
    )
    return obtener(conexion, empresa_id, tarea_id)
