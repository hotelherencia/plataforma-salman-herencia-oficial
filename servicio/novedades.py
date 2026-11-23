"""SPEC-NOV-01 (#448): Libro de novedades turno a turno, asignación de cupos
de estacionamiento (~14 cupos por habitación/patente) y conteos de desayunos
y bebestibles."""
from __future__ import annotations

import json
import uuid
from datetime import date

import psycopg
from fastapi import HTTPException

from . import contabilidad, roles, seguridad

TURNOS_VALIDOS = ("manana", "tarde", "noche")
ESTADOS_ESTACIONAMIENTO = ("reservado", "ocupado", "liberado")
CATEGORIAS_CONTEO = ("desayuno", "bebestible")
CUPOS_ESTACIONAMIENTO_DEFECTO = 14

ROLES_NOVEDADES = roles.con_admin_hotel("recepcion", "caja")


def _cupos_maximos(conexion: psycopg.Connection, empresa_id: str) -> int:
    fila = conexion.execute(
        "SELECT valor FROM ajustes WHERE empresa_id = %s AND clave = 'estacionamiento_cupos'",
        (empresa_id,),
    ).fetchone()
    if fila and isinstance(fila[0], dict):
        n = fila[0].get("cupos")
        if isinstance(n, int) and 1 <= n <= 50:
            return n
    return CUPOS_ESTACIONAMIENTO_DEFECTO


def obtener_novedades_dia(
    conexion: psycopg.Connection,
    empresa_id: str,
    fecha: date | None = None,
) -> dict:
    dia = fecha or contabilidad.hoy_chile()
    max_cupos = _cupos_maximos(conexion, empresa_id)

    novs = [
        {
            "novedad_id": r[0],
            "fecha_contable": r[1].isoformat(),
            "turno": r[2],
            "autor": r[3],
            "resumen": r[4],
            "desayunos_servidos": int(r[5]),
            "bebestibles_detalle": list(r[6] or []),
            "creado_en": r[7].isoformat(),
        }
        for r in conexion.execute(
            """
            SELECT id, fecha_contable, turno, autor, resumen, desayunos_servidos, bebestibles_detalle, creado_en
            FROM libro_novedades
            WHERE empresa_id = %s AND fecha_contable = %s
            ORDER BY creado_en DESC
            """,
            (empresa_id, dia),
        ).fetchall()
    ]

    asig_map: dict[int, dict] = {}
    for r in conexion.execute(
        """
        SELECT cupo, habitacion_id, reserva_id, patente, estado, observacion, creado_por, actualizado_en
        FROM estacionamiento_asignaciones
        WHERE empresa_id = %s AND fecha = %s
        ORDER BY cupo ASC
        """,
        (empresa_id, dia),
    ).fetchall():
        asig_map[int(r[0])] = {
            "cupo": int(r[0]),
            "habitacion_id": r[1],
            "reserva_id": r[2],
            "patente": r[3],
            "estado": r[4],
            "observacion": r[5],
            "creado_por": r[6],
            "actualizado_en": r[7].isoformat(),
        }

    mapa_estacionamiento = [
        asig_map.get(
            c,
            {
                "cupo": c,
                "habitacion_id": None,
                "reserva_id": None,
                "patente": "",
                "estado": "liberado",
                "observacion": "",
                "creado_por": None,
                "actualizado_en": None,
            },
        )
        for c in range(1, max_cupos + 1)
    ]

    conteos = [
        {
            "conteo_id": int(r[0]),
            "fecha_contable": r[1].isoformat(),
            "turno": r[2],
            "categoria": r[3],
            "producto_id": r[4],
            "producto_nombre": r[5],
            "cantidad": int(r[6]),
            "observacion": r[7],
            "actor": r[8],
            "creado_en": r[9].isoformat(),
        }
        for r in conexion.execute(
            """
            SELECT c.id, c.fecha_contable, c.turno, c.categoria, c.producto_id, p.nombre,
                   c.cantidad, c.observacion, c.actor, c.creado_en
            FROM conteos_turno_fnb c
            LEFT JOIN productos p ON p.id = c.producto_id
            WHERE c.empresa_id = %s AND c.fecha_contable = %s
            ORDER BY c.creado_en DESC
            """,
            (empresa_id, dia),
        ).fetchall()
    ]

    ocupados = sum(1 for x in mapa_estacionamiento if x["estado"] in ("ocupado", "reservado"))
    total_desayunos = sum(c["cantidad"] for c in conteos if c["categoria"] == "desayuno") + sum(
        n["desayunos_servidos"] for n in novs
    )
    total_bebestibles = sum(c["cantidad"] for c in conteos if c["categoria"] == "bebestible")

    return {
        "fecha": dia.isoformat(),
        "cupos_estacionamiento": max_cupos,
        "estacionamiento_ocupados": ocupados,
        "estacionamiento_libres": max(0, max_cupos - ocupados),
        "estacionamiento": mapa_estacionamiento,
        "novedades": novs,
        "conteos": conteos,
        "resumen_fnb": {
            "desayunos_total": total_desayunos,
            "bebestibles_total": total_bebestibles,
        },
    }


def registrar_novedad(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    fecha_contable: date | None,
    turno: str,
    resumen: str,
    desayunos_servidos: int,
    bebestibles_detalle: list[dict],
    actor: str,
) -> dict:
    if turno not in TURNOS_VALIDOS:
        raise HTTPException(status_code=422, detail="turno debe ser manana, tarde o noche")
    dia = fecha_contable or contabilidad.hoy_chile()
    nov_id = f"NOV-{uuid.uuid4().hex[:12]}"
    fila = conexion.execute(
        """
        INSERT INTO libro_novedades (id, empresa_id, fecha_contable, turno, autor, resumen, desayunos_servidos, bebestibles_detalle)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        RETURNING id, fecha_contable, turno, autor, resumen, desayunos_servidos, bebestibles_detalle, creado_en
        """,
        (nov_id, empresa_id, dia, turno, actor, resumen.strip(), int(desayunos_servidos), json.dumps(bebestibles_detalle)),
    ).fetchone()
    seguridad.auditar(conexion, actor, "libro_novedad_registrada", nov_id, f"fecha={dia.isoformat()} turno={turno}")
    return {
        "novedad_id": fila[0],
        "fecha_contable": fila[1].isoformat(),
        "turno": fila[2],
        "autor": fila[3],
        "resumen": fila[4],
        "desayunos_servidos": int(fila[5]),
        "bebestibles_detalle": list(fila[6] or []),
        "creado_en": fila[7].isoformat(),
    }


def asignar_estacionamiento(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    fecha: date | None,
    cupo: int,
    habitacion_id: str | None,
    reserva_id: str | None,
    patente: str,
    estado: str,
    observacion: str,
    actor: str,
) -> dict:
    dia = fecha or contabilidad.hoy_chile()
    max_cupos = _cupos_maximos(conexion, empresa_id)
    if cupo < 1 or cupo > max_cupos:
        raise HTTPException(status_code=422, detail=f"el cupo debe estar entre 1 y {max_cupos}")
    if estado not in ESTADOS_ESTACIONAMIENTO:
        raise HTTPException(status_code=422, detail="estado de estacionamiento no válido")
    if estado != "liberado" and not habitacion_id and not patente.strip():
        raise HTTPException(status_code=422, detail="indica la habitación o la patente para asignar el cupo")

    hab = None if estado == "liberado" else (habitacion_id.strip() if habitacion_id else None)
    res_id = None if estado == "liberado" else (reserva_id.strip() if reserva_id else None)
    pat = "" if estado == "liberado" else patente.strip().upper()[:20]
    obs = "" if estado == "liberado" else observacion.strip()[:240]

    if hab:
        existe_hab = conexion.execute("SELECT 1 FROM habitaciones WHERE id = %s", (hab,)).fetchone()
        if existe_hab is None:
            raise HTTPException(status_code=404, detail="habitación no encontrada")

    fila = conexion.execute(
        """
        INSERT INTO estacionamiento_asignaciones
            (empresa_id, fecha, cupo, habitacion_id, reserva_id, patente, estado, observacion, creado_por, actualizado_en)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (empresa_id, fecha, cupo)
        DO UPDATE SET
            habitacion_id = EXCLUDED.habitacion_id,
            reserva_id = EXCLUDED.reserva_id,
            patente = EXCLUDED.patente,
            estado = EXCLUDED.estado,
            observacion = EXCLUDED.observacion,
            creado_por = EXCLUDED.creado_por,
            actualizado_en = NOW()
        RETURNING cupo, fecha, habitacion_id, reserva_id, patente, estado, observacion, creado_por, actualizado_en
        """,
        (empresa_id, dia, cupo, hab, res_id, pat, estado, obs, actor),
    ).fetchone()
    seguridad.auditar(
        conexion,
        actor,
        "estacionamiento_asignado",
        f"cupo:{cupo}:{dia.isoformat()}",
        f"estado={estado} hab={hab or '-'}",
    )
    return {
        "cupo": int(fila[0]),
        "fecha": fila[1].isoformat(),
        "habitacion_id": fila[2],
        "reserva_id": fila[3],
        "patente": fila[4],
        "estado": fila[5],
        "observacion": fila[6],
        "creado_por": fila[7],
        "actualizado_en": fila[8].isoformat(),
    }


def registrar_conteo_fnb(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    fecha_contable: date | None,
    turno: str,
    categoria: str,
    producto_id: str | None,
    cantidad: int,
    observacion: str,
    actor: str,
) -> dict:
    if turno not in TURNOS_VALIDOS:
        raise HTTPException(status_code=422, detail="turno debe ser manana, tarde o noche")
    if categoria not in CATEGORIAS_CONTEO:
        raise HTTPException(status_code=422, detail="categoría debe ser desayuno o bebestible")
    dia = fecha_contable or contabilidad.hoy_chile()
    prod_id = producto_id.strip() if producto_id else None
    if prod_id:
        p = conexion.execute(
            "SELECT 1 FROM productos WHERE id = %s AND empresa_id = %s",
            (prod_id, empresa_id),
        ).fetchone()
        if p is None:
            raise HTTPException(status_code=404, detail="producto no encontrado")

    fila = conexion.execute(
        """
        INSERT INTO conteos_turno_fnb (empresa_id, fecha_contable, turno, categoria, producto_id, cantidad, observacion, actor)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, fecha_contable, turno, categoria, producto_id, cantidad, observacion, actor, creado_en
        """,
        (empresa_id, dia, turno, categoria, prod_id, int(cantidad), observacion.strip()[:240], actor),
    ).fetchone()
    seguridad.auditar(
        conexion,
        actor,
        "conteo_fnb_registrado",
        f"conteo:{fila[0]}",
        f"categoria={categoria} turno={turno} cantidad={cantidad}",
    )
    return {
        "conteo_id": int(fila[0]),
        "fecha_contable": fila[1].isoformat(),
        "turno": fila[2],
        "categoria": fila[3],
        "producto_id": fila[4],
        "cantidad": int(fila[5]),
        "observacion": fila[6],
        "actor": fila[7],
        "creado_en": fila[8].isoformat(),
    }
