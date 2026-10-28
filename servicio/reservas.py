"""Acceso a datos del hotel: habitaciones, tarifas, oferta y reservas.

La base de datos es la fuente de verdad de las reservas: la confirmación es
transaccional y el constraint de exclusión `reservas_sin_solape` rechaza el
solape en (habitación, rango). La tarifa aceptada queda congelada en la
reserva: cambiar tarifas no altera precios ya aceptados (spec-api-v1).
"""
import uuid
from datetime import date, datetime, timedelta

import psycopg
from psycopg.errors import ExclusionViolation

VIGENCIA_OFERTA = timedelta(minutes=15)
ESTABLECIMIENTO_SINTETICO = "EST-SINT-001"
POLITICA_CANCELACION = "politica del manual §9 pendiente; oferta informativa"


class SinCupo(Exception):
    """409: la unidad ya está reservada en ese rango."""


class SinTarifaVigente(Exception):
    """409: no hay tarifa para la fecha de inicio."""


def sembrar_habitaciones(conexion: psycopg.Connection) -> None:
    for n in range(1, 4):
        conexion.execute(
            "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (f"HAB-SINT-10{n}", ESTABLECIMIENTO_SINTETICO, "doble", 2),
        )


def upsert_habitacion(conexion: psycopg.Connection, habitacion_id: str, tipo: str, capacidad: int) -> None:
    conexion.execute(
        "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET tipo = EXCLUDED.tipo, capacidad = EXCLUDED.capacidad",
        (habitacion_id, ESTABLECIMIENTO_SINTETICO, tipo, capacidad),
    )


def insertar_tarifa(
    conexion: psycopg.Connection, habitacion_id: str, fecha_desde: date, fecha_hasta: date, tarifa_noche_clp: int
) -> str:
    tarifa_id = f"TAR-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
        "VALUES (%s, %s, %s, %s, %s)",
        (tarifa_id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp),
    )
    return tarifa_id


def tarifa_vigente(conexion: psycopg.Connection, habitacion_id: str, fecha: date) -> int | None:
    fila = conexion.execute(
        "SELECT tarifa_noche_clp FROM tarifas WHERE habitacion_id = %s AND fecha_desde <= %s AND fecha_hasta > %s "
        "ORDER BY fecha_desde DESC LIMIT 1",
        (habitacion_id, fecha, fecha),
    ).fetchone()
    return fila[0] if fila else None


def _libre(conexion: psycopg.Connection, habitacion_id: str, inicio: date, fin: date) -> bool:
    fila = conexion.execute(
        "SELECT count(*) FROM reservas WHERE habitacion_id = %s AND estado = 'confirmada' "
        "AND daterange(inicio, fin, '[)') && daterange(%s, %s, '[)')",
        (habitacion_id, inicio, fin),
    ).fetchone()
    return fila[0] == 0


def oferta(conexion: psycopg.Connection, inicio: date, fin: date, personas: int, ahora: datetime) -> dict:
    unidades = conexion.execute(
        "SELECT id, tipo, capacidad FROM habitaciones WHERE capacidad >= %s AND estado_operativo = 'disponible' ORDER BY id",
        (personas,),
    ).fetchall()
    noches = (fin - inicio).days
    items = []
    for habitacion_id, tipo, _capacidad in unidades:
        tarifa = tarifa_vigente(conexion, habitacion_id, inicio)
        if tarifa is None or not _libre(conexion, habitacion_id, inicio, fin):
            continue
        items.append(
            {
                "habitacion_id": habitacion_id,
                "tipo": tipo,
                "tarifa_noche_clp": tarifa,
                "total_clp": tarifa * noches,
                "politica_cancelacion": POLITICA_CANCELACION,
                "vigente_hasta": (ahora + VIGENCIA_OFERTA).isoformat(),
            }
        )
    return {"oferta": items, "emitida_en": ahora.isoformat(), "vigencia_minutos": VIGENCIA_OFERTA.total_seconds() // 60}


def crear_reserva(
    conexion: psycopg.Connection,
    empresa_id: str,
    habitacion_id: str,
    inicio: date,
    fin: date,
    huesped_nombre: str,
    huesped_documento: str | None,
) -> dict:
    conexion.execute("SELECT id FROM habitaciones WHERE id = %s FOR UPDATE", (habitacion_id,))
    tarifa = tarifa_vigente(conexion, habitacion_id, inicio)
    if tarifa is None:
        raise SinTarifaVigente(f"sin tarifa vigente para {habitacion_id} en {inicio}")
    reserva_id = f"RSV-{uuid.uuid4().hex[:12]}"
    try:
        with conexion.transaction():  # savepoint: la violación no aborta la transacción externa
            conexion.execute(
                "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, "
                "tarifa_noche_aceptada_clp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (reserva_id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, tarifa),
            )
    except ExclusionViolation as error:
        raise SinCupo(f"sin cupo para {habitacion_id} en [{inicio}, {fin})") from error
    return {
        "reserva_id": reserva_id,
        "habitacion_id": habitacion_id,
        "inicio": inicio.isoformat(),
        "fin": fin.isoformat(),
        "estado": "confirmada",
        "tarifa_noche_aceptada_clp": tarifa,
        "total_clp": tarifa * (fin - inicio).days,
    }
