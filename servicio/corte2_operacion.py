"""Corte 2 Operativo P1 (#418 parte 2 — ref. Orquestia; comunicados en servicio/comunicados.py):
- Vista semanal de turnos por área (recepción, aseo, desayunos, mantención) y cambios aprobados.
- Biblioteca documental por rol y buzón de sugerencias.
- Inventario de activos por habitación/área y mantenimiento preventivo periódico.

Fuera de alcance: remuneraciones y asistencia legal (se integra externamente).
"""
from __future__ import annotations

from datetime import date, timedelta

import psycopg
from fastapi import HTTPException

from . import contabilidad, roles, seguridad

AREAS_TURNO = ("recepcion", "aseo", "desayunos", "mantencion")
CATEGORIAS_BIBLIOTECA = ("manual", "instructivo", "politica", "protocolo")
CATEGORIAS_SUGERENCIA = ("operacion", "mantencion", "huespedes", "equipo", "otro")
ESTADOS_SUGERENCIA = ("recibida", "en_revision", "implementada", "archivada")
ESTADOS_ACTIVO = ("operativo", "en_mantencion", "fuera_de_servicio", "baja")
TIPOS_MANTENCION = ("preventiva", "correctiva")


def _rango_semana(desde: date | None, hasta: date | None) -> tuple[date, date]:
    hoy = contabilidad.hoy_chile()
    if desde is None:
        desde = hoy - timedelta(days=hoy.weekday())
    if hasta is None:
        hasta = desde + timedelta(days=6)
    if hasta < desde:
        raise HTTPException(status_code=422, detail="la fecha hasta debe ser igual o posterior a desde")
    if (hasta - desde).days > 62:
        raise HTTPException(status_code=422, detail="el rango máximo de consulta es 62 días")
    return desde, hasta


# ---------------------------------------------------------------------------
# 1. Turnos semanales por área y cambios de turno aprobados
# ---------------------------------------------------------------------------


def listar_turnos_semana(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    area: str | None = None,
) -> dict:
    inicio, fin = _rango_semana(desde, hasta)
    if area is not None and area not in AREAS_TURNO:
        raise HTTPException(status_code=422, detail="área de turno no válida")

    filtros = ["empresa_id = %s", "fecha BETWEEN %s AND %s"]
    params: list = [empresa_id, inicio, fin]
    if area:
        filtros.append("area = %s")
        params.append(area)

    filas = conexion.execute(
        f"""
        SELECT id, usuario_nombre, area, fecha, hora_inicio, hora_fin, nota, estado, creado_por, creado_en
        FROM turnos_personal
        WHERE {' AND '.join(filtros)}
        ORDER BY fecha ASC, hora_inicio ASC, id ASC
        """,
        params,
    ).fetchall()

    turnos = [
        {
            "turno_id": r[0],
            "usuario_nombre": r[1],
            "area": r[2],
            "fecha": r[3].isoformat(),
            "hora_inicio": r[4],
            "hora_fin": r[5],
            "nota": r[6],
            "estado": r[7],
            "creado_por": r[8],
            "creado_en": r[9].isoformat(),
        }
        for r in filas
    ]

    cambios_filas = conexion.execute(
        """
        SELECT c.id, c.turno_id, t.fecha, t.area, c.solicitante, c.reemplazo_usuario,
               c.motivo, c.estado, c.revisado_por, c.revisado_en, c.nota_revision, c.creado_en
        FROM cambios_turno c
        JOIN turnos_personal t ON t.id = c.turno_id
        WHERE c.empresa_id = %s
          AND (t.fecha BETWEEN %s AND %s OR c.estado = 'pendiente')
        ORDER BY CASE WHEN c.estado = 'pendiente' THEN 0 ELSE 1 END, c.creado_en DESC
        LIMIT 100
        """,
        (empresa_id, inicio, fin),
    ).fetchall()

    cambios = [
        {
            "cambio_id": c[0],
            "turno_id": c[1],
            "fecha": c[2].isoformat(),
            "area": c[3],
            "solicitante": c[4],
            "reemplazo_usuario": c[5],
            "motivo": c[6],
            "estado": c[7],
            "revisado_por": c[8],
            "revisado_en": c[9].isoformat() if c[9] else None,
            "nota_revision": c[10],
            "creado_en": c[11].isoformat(),
        }
        for c in cambios_filas
    ]

    por_area = {a: sum(1 for t in turnos if t["area"] == a and t["estado"] != "cancelado") for a in AREAS_TURNO}
    return {
        "desde": inicio.isoformat(),
        "hasta": fin.isoformat(),
        "turnos": turnos,
        "cambios_pendientes": sum(1 for c in cambios if c["estado"] == "pendiente"),
        "cambios": cambios,
        "por_area": por_area,
    }


def crear_turno(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    usuario_nombre: str,
    area: str,
    fecha: date,
    hora_inicio: str,
    hora_fin: str,
    nota: str,
    actor: str,
) -> dict:
    if area not in AREAS_TURNO:
        raise HTTPException(status_code=422, detail="área de turno no válida")
    if hora_fin <= hora_inicio:
        raise HTTPException(status_code=422, detail="la hora de término debe ser posterior a la de inicio")
    fila = conexion.execute(
        """
        INSERT INTO turnos_personal (empresa_id, usuario_nombre, area, fecha, hora_inicio, hora_fin, nota, creado_por)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, usuario_nombre, area, fecha, hora_inicio, hora_fin, nota, estado, creado_por, creado_en
        """,
        (empresa_id, usuario_nombre.strip(), area, fecha, hora_inicio, hora_fin, nota.strip(), actor),
    ).fetchone()
    seguridad.auditar(conexion, actor, "turno_creado", f"turno:{fila[0]}", f"area={area} fecha={fecha.isoformat()}")
    conexion.commit()
    return {
        "turno_id": fila[0],
        "usuario_nombre": fila[1],
        "area": fila[2],
        "fecha": fila[3].isoformat(),
        "hora_inicio": fila[4],
        "hora_fin": fila[5],
        "nota": fila[6],
        "estado": fila[7],
        "creado_por": fila[8],
        "creado_en": fila[9].isoformat(),
    }


def solicitar_cambio_turno(
    conexion: psycopg.Connection,
    empresa_id: str,
    turno_id: int,
    *,
    reemplazo_usuario: str,
    motivo: str,
    actor: str,
) -> dict:
    turno = conexion.execute(
        "SELECT id, estado FROM turnos_personal WHERE id = %s AND empresa_id = %s",
        (turno_id, empresa_id),
    ).fetchone()
    if turno is None:
        raise HTTPException(status_code=404, detail="turno no encontrado")
    if turno[1] == "cancelado":
        raise HTTPException(status_code=409, detail="no se puede solicitar cambio sobre un turno cancelado")

    fila = conexion.execute(
        """
        INSERT INTO cambios_turno (empresa_id, turno_id, solicitante, reemplazo_usuario, motivo)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, turno_id, solicitante, reemplazo_usuario, motivo, estado, creado_en
        """,
        (empresa_id, turno_id, actor, reemplazo_usuario.strip(), motivo.strip()),
    ).fetchone()
    seguridad.auditar(conexion, actor, "cambio_turno_solicitado", f"cambio:{fila[0]}", f"turno={turno_id}")
    conexion.commit()
    return {
        "cambio_id": fila[0],
        "turno_id": fila[1],
        "solicitante": fila[2],
        "reemplazo_usuario": fila[3],
        "motivo": fila[4],
        "estado": fila[5],
        "creado_en": fila[6].isoformat(),
    }


def resolver_cambio_turno(
    conexion: psycopg.Connection,
    empresa_id: str,
    cambio_id: int,
    *,
    decision: str,
    nota_revision: str,
    actor: str,
) -> dict:
    if decision not in ("aprobado", "rechazado"):
        raise HTTPException(status_code=422, detail="decisión debe ser aprobado o rechazado")
    cambio = conexion.execute(
        """
        SELECT id, turno_id, reemplazo_usuario, estado
        FROM cambios_turno
        WHERE id = %s AND empresa_id = %s
        FOR UPDATE
        """,
        (cambio_id, empresa_id),
    ).fetchone()
    if cambio is None:
        raise HTTPException(status_code=404, detail="solicitud de cambio no encontrada")
    if cambio[3] != "pendiente":
        raise HTTPException(status_code=409, detail="la solicitud de cambio ya fue resuelta")

    fila = conexion.execute(
        """
        UPDATE cambios_turno
        SET estado = %s, revisado_por = %s, revisado_en = NOW(), nota_revision = %s
        WHERE id = %s
        RETURNING id, turno_id, solicitante, reemplazo_usuario, motivo, estado, revisado_por, revisado_en, nota_revision
        """,
        (decision, actor, nota_revision.strip(), cambio_id),
    ).fetchone()

    if decision == "aprobado":
        conexion.execute(
            """
            UPDATE turnos_personal
            SET usuario_nombre = %s, estado = 'cambiado'
            WHERE id = %s AND empresa_id = %s
            """,
            (cambio[2], cambio[1], empresa_id),
        )

    seguridad.auditar(conexion, actor, f"cambio_turno_{decision}", f"cambio:{cambio_id}", f"turno={cambio[1]}")
    conexion.commit()
    return {
        "cambio_id": fila[0],
        "turno_id": fila[1],
        "solicitante": fila[2],
        "reemplazo_usuario": fila[3],
        "motivo": fila[4],
        "estado": fila[5],
        "revisado_por": fila[6],
        "revisado_en": fila[7].isoformat() if fila[7] else None,
        "nota_revision": fila[8],
    }


# ---------------------------------------------------------------------------
# 2. Biblioteca documental por rol y buzón de sugerencias
# ---------------------------------------------------------------------------


def listar_biblioteca(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    rol_usuario: str,
    categoria: str | None = None,
) -> dict:
    if categoria is not None and categoria not in CATEGORIAS_BIBLIOTECA:
        raise HTTPException(status_code=422, detail="categoría documental no válida")
    filtros = ["empresa_id = %s", "activo = TRUE"]
    params: list = [empresa_id]
    if categoria:
        filtros.append("categoria = %s")
        params.append(categoria)
    if not roles.es_admin_hotel(rol_usuario):
        filtros.append("(rol_objetivo = 'todos' OR rol_objetivo = %s)")
        params.append(rol_usuario)

    filas = conexion.execute(
        f"""
        SELECT id, titulo, categoria, rol_objetivo, contenido, version, creado_por, actualizado_en
        FROM biblioteca_documentos
        WHERE {' AND '.join(filtros)}
        ORDER BY categoria ASC, titulo ASC
        """,
        params,
    ).fetchall()

    return {
        "documentos": [
            {
                "documento_id": r[0],
                "titulo": r[1],
                "categoria": r[2],
                "rol_objetivo": r[3],
                "contenido": r[4],
                "version": r[5],
                "creado_por": r[6],
                "actualizado_en": r[7].isoformat(),
            }
            for r in filas
        ]
    }


def crear_documento_biblioteca(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    titulo: str,
    categoria: str,
    rol_objetivo: str,
    contenido: str,
    version: str,
    actor: str,
) -> dict:
    if categoria not in CATEGORIAS_BIBLIOTECA:
        raise HTTPException(status_code=422, detail="categoría documental no válida")
    fila = conexion.execute(
        """
        INSERT INTO biblioteca_documentos (empresa_id, titulo, categoria, rol_objetivo, contenido, version, creado_por)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, titulo, categoria, rol_objetivo, contenido, version, creado_por, actualizado_en
        """,
        (empresa_id, titulo.strip(), categoria, rol_objetivo.strip() or "todos", contenido.strip(), version.strip() or "1.0", actor),
    ).fetchone()
    seguridad.auditar(conexion, actor, "biblioteca_documento_creado", f"doc:{fila[0]}", f"categoria={categoria} rol={fila[3]}")
    conexion.commit()
    return {
        "documento_id": fila[0],
        "titulo": fila[1],
        "categoria": fila[2],
        "rol_objetivo": fila[3],
        "contenido": fila[4],
        "version": fila[5],
        "creado_por": fila[6],
        "actualizado_en": fila[7].isoformat(),
    }


def listar_sugerencias(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    usuario_nombre: str,
    es_admin: bool,
) -> dict:
    if es_admin:
        filas = conexion.execute(
            """
            SELECT id, categoria, mensaje, anonimo, autor, estado, respuesta_admin, revisado_por, creado_en, actualizado_en
            FROM sugerencias_equipo
            WHERE empresa_id = %s
            ORDER BY CASE WHEN estado = 'recibida' THEN 0 ELSE 1 END, creado_en DESC
            LIMIT 100
            """,
            (empresa_id,),
        ).fetchall()
    else:
        filas = conexion.execute(
            """
            SELECT id, categoria, mensaje, anonimo, autor, estado, respuesta_admin, revisado_por, creado_en, actualizado_en
            FROM sugerencias_equipo
            WHERE empresa_id = %s AND autor = %s
            ORDER BY creado_en DESC
            LIMIT 50
            """,
            (empresa_id, usuario_nombre),
        ).fetchall()

    return {
        "sugerencias": [
            {
                "sugerencia_id": r[0],
                "categoria": r[1],
                "mensaje": r[2],
                "anonimo": bool(r[3]),
                "autor": None if r[3] else r[4],
                "estado": r[5],
                "respuesta_admin": r[6],
                "revisado_por": r[7],
                "creado_en": r[8].isoformat(),
                "actualizado_en": r[9].isoformat(),
            }
            for r in filas
        ]
    }


def crear_sugerencia(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    categoria: str,
    mensaje: str,
    anonimo: bool,
    actor: str,
) -> dict:
    if categoria not in CATEGORIAS_SUGERENCIA:
        raise HTTPException(status_code=422, detail="categoría de sugerencia no válida")
    autor_guardado = None if anonimo else actor
    fila = conexion.execute(
        """
        INSERT INTO sugerencias_equipo (empresa_id, categoria, mensaje, anonimo, autor)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, categoria, mensaje, anonimo, autor, estado, respuesta_admin, creado_en, actualizado_en
        """,
        (empresa_id, categoria, mensaje.strip(), anonimo, autor_guardado),
    ).fetchone()
    seguridad.auditar(conexion, "anonimo" if anonimo else actor, "sugerencia_creada", f"sugerencia:{fila[0]}", f"categoria={categoria}")
    conexion.commit()
    return {
        "sugerencia_id": fila[0],
        "categoria": fila[1],
        "mensaje": fila[2],
        "anonimo": bool(fila[3]),
        "autor": fila[4],
        "estado": fila[5],
        "respuesta_admin": fila[6],
        "creado_en": fila[7].isoformat(),
        "actualizado_en": fila[8].isoformat(),
    }


def actualizar_estado_sugerencia(
    conexion: psycopg.Connection,
    empresa_id: str,
    sugerencia_id: int,
    *,
    estado: str,
    respuesta_admin: str,
    actor: str,
) -> dict:
    if estado not in ESTADOS_SUGERENCIA:
        raise HTTPException(status_code=422, detail="estado de sugerencia no válido")
    fila = conexion.execute(
        """
        UPDATE sugerencias_equipo
        SET estado = %s, respuesta_admin = %s, revisado_por = %s, actualizado_en = NOW()
        WHERE id = %s AND empresa_id = %s
        RETURNING id, categoria, mensaje, anonimo, autor, estado, respuesta_admin, revisado_por, creado_en, actualizado_en
        """,
        (estado, respuesta_admin.strip(), actor, sugerencia_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise HTTPException(status_code=404, detail="sugerencia no encontrada")
    seguridad.auditar(conexion, actor, "sugerencia_actualizada", f"sugerencia:{sugerencia_id}", f"estado={estado}")
    conexion.commit()
    return {
        "sugerencia_id": fila[0],
        "categoria": fila[1],
        "mensaje": fila[2],
        "anonimo": bool(fila[3]),
        "autor": None if fila[3] else fila[4],
        "estado": fila[5],
        "respuesta_admin": fila[6],
        "revisado_por": fila[7],
        "creado_en": fila[8].isoformat(),
        "actualizado_en": fila[9].isoformat(),
    }


# ---------------------------------------------------------------------------
# 3. Inventario de activos por habitación/área y mantenimiento preventivo
# ---------------------------------------------------------------------------


def _estado_preventivo(proxima: date | None, hoy: date) -> str:
    if proxima is None:
        return "sin_calendario"
    if proxima < hoy:
        return "vencido"
    if proxima <= hoy + timedelta(days=7):
        return "por_vencer"
    return "al_dia"


def listar_activos(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    habitacion_id: str | None = None,
    estado: str | None = None,
    solo_vencidos: bool = False,
) -> dict:
    hoy = contabilidad.hoy_chile()
    if estado is not None and estado not in ESTADOS_ACTIVO:
        raise HTTPException(status_code=422, detail="estado de activo no válido")

    filtros = ["empresa_id = %s"]
    params: list = [empresa_id]
    if habitacion_id:
        filtros.append("habitacion_id = %s")
        params.append(habitacion_id)
    if estado:
        filtros.append("estado = %s")
        params.append(estado)

    filas = conexion.execute(
        f"""
        SELECT id, nombre, categoria, habitacion_id, area, numero_serie, estado,
               frecuencia_mantencion_dias, ultima_mantencion, proxima_mantencion, notas, creado_por, actualizado_en
        FROM activos_hotel
        WHERE {' AND '.join(filtros)}
        ORDER BY proxima_mantencion ASC NULLS LAST, habitacion_id ASC NULLS LAST, id ASC
        """,
        params,
    ).fetchall()

    activos = []
    for r in filas:
        est_prev = _estado_preventivo(r[9], hoy)
        if solo_vencidos and est_prev not in ("vencido", "por_vencer"):
            continue
        activos.append(
            {
                "activo_id": r[0],
                "nombre": r[1],
                "categoria": r[2],
                "habitacion_id": r[3],
                "area": r[4],
                "numero_serie": r[5],
                "estado": r[6],
                "frecuencia_mantencion_dias": r[7],
                "ultima_mantencion": r[8].isoformat() if r[8] else None,
                "proxima_mantencion": r[9].isoformat() if r[9] else None,
                "estado_preventivo": est_prev,
                "notas": r[10],
                "creado_por": r[11],
                "actualizado_en": r[12].isoformat(),
            }
        )

    return {
        "fecha_corte": hoy.isoformat(),
        "activos": activos,
        "resumen": {
            "total": len(activos),
            "vencidos": sum(1 for a in activos if a["estado_preventivo"] == "vencido"),
            "por_vencer": sum(1 for a in activos if a["estado_preventivo"] == "por_vencer"),
            "al_dia": sum(1 for a in activos if a["estado_preventivo"] == "al_dia"),
        },
    }


def crear_activo(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    nombre: str,
    categoria: str,
    habitacion_id: str | None,
    area: str | None,
    numero_serie: str,
    frecuencia_mantencion_dias: int | None,
    ultima_mantencion: date | None,
    proxima_mantencion: date | None,
    notas: str,
    actor: str,
) -> dict:
    if not habitacion_id and not area:
        raise HTTPException(status_code=422, detail="indica la habitación o el área del activo")
    if habitacion_id:
        hab = conexion.execute(
            "SELECT 1 FROM habitaciones WHERE id = %s",
            (habitacion_id,),
        ).fetchone()
        if hab is None:
            raise HTTPException(status_code=404, detail="habitación no encontrada")

    proxima = proxima_mantencion
    if proxima is None and frecuencia_mantencion_dias:
        base = ultima_mantencion or contabilidad.hoy_chile()
        proxima = base + timedelta(days=frecuencia_mantencion_dias)

    fila = conexion.execute(
        """
        INSERT INTO activos_hotel (
            empresa_id, nombre, categoria, habitacion_id, area, numero_serie,
            frecuencia_mantencion_dias, ultima_mantencion, proxima_mantencion, notas, creado_por
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, nombre, categoria, habitacion_id, area, numero_serie, estado,
                  frecuencia_mantencion_dias, ultima_mantencion, proxima_mantencion, notas, creado_por, actualizado_en
        """,
        (
            empresa_id,
            nombre.strip(),
            categoria.strip() or "equipamiento",
            habitacion_id,
            area.strip() if area else None,
            numero_serie.strip(),
            frecuencia_mantencion_dias,
            ultima_mantencion,
            proxima,
            notas.strip(),
            actor,
        ),
    ).fetchone()
    seguridad.auditar(conexion, actor, "activo_creado", f"activo:{fila[0]}", f"ubicacion={habitacion_id or area}")
    conexion.commit()
    hoy = contabilidad.hoy_chile()
    return {
        "activo_id": fila[0],
        "nombre": fila[1],
        "categoria": fila[2],
        "habitacion_id": fila[3],
        "area": fila[4],
        "numero_serie": fila[5],
        "estado": fila[6],
        "frecuencia_mantencion_dias": fila[7],
        "ultima_mantencion": fila[8].isoformat() if fila[8] else None,
        "proxima_mantencion": fila[9].isoformat() if fila[9] else None,
        "estado_preventivo": _estado_preventivo(fila[9], hoy),
        "notas": fila[10],
        "creado_por": fila[11],
        "actualizado_en": fila[12].isoformat(),
    }


def registrar_mantencion_activo(
    conexion: psycopg.Connection,
    empresa_id: str,
    activo_id: int,
    *,
    fecha_realizada: date | None,
    tipo: str,
    descripcion: str,
    costo_clp: int,
    nuevo_estado: str | None,
    actor: str,
) -> dict:
    if tipo not in TIPOS_MANTENCION:
        raise HTTPException(status_code=422, detail="tipo de mantención no válido")
    if nuevo_estado is not None and nuevo_estado not in ESTADOS_ACTIVO:
        raise HTTPException(status_code=422, detail="estado de activo no válido")

    activo = conexion.execute(
        """
        SELECT id, frecuencia_mantencion_dias, estado
        FROM activos_hotel
        WHERE id = %s AND empresa_id = %s
        FOR UPDATE
        """,
        (activo_id, empresa_id),
    ).fetchone()
    if activo is None:
        raise HTTPException(status_code=404, detail="activo no encontrado")

    fecha_ef = fecha_realizada or contabilidad.hoy_chile()
    frecuencia = activo[1]
    proxima = fecha_ef + timedelta(days=frecuencia) if frecuencia else None
    estado_final = nuevo_estado or "operativo"

    mant = conexion.execute(
        """
        INSERT INTO activos_mantenciones (empresa_id, activo_id, fecha_realizada, tipo, descripcion, costo_clp, realizado_por)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, fecha_realizada, tipo, descripcion, costo_clp, realizado_por, registrado_en
        """,
        (empresa_id, activo_id, fecha_ef, tipo, descripcion.strip(), costo_clp, actor),
    ).fetchone()

    conexion.execute(
        """
        UPDATE activos_hotel
        SET ultima_mantencion = %s,
            proxima_mantencion = %s,
            estado = %s,
            actualizado_en = NOW()
        WHERE id = %s AND empresa_id = %s
        """,
        (fecha_ef, proxima, estado_final, activo_id, empresa_id),
    )
    seguridad.auditar(
        conexion,
        actor,
        "activo_mantencion_registrada",
        f"activo:{activo_id}",
        f"tipo={tipo} fecha={fecha_ef.isoformat()}",
    )
    conexion.commit()
    return {
        "mantencion_id": mant[0],
        "activo_id": activo_id,
        "fecha_realizada": mant[1].isoformat(),
        "tipo": mant[2],
        "descripcion": mant[3],
        "costo_clp": mant[4],
        "realizado_por": mant[5],
        "registrado_en": mant[6].isoformat(),
        "proxima_mantencion": proxima.isoformat() if proxima else None,
        "estado_activo": estado_final,
    }
