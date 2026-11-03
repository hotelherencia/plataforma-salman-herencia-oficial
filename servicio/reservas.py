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
# HECHO DOCUMENTADO: texto de hotel_inventario.servicio.POLITICA_CANCELACION
# (LIMITE_CANCELACION_GRATUITA 48 h, HORA_LLEGADA 15:00).
POLITICA_CANCELACION = (
    "cancelación gratuita hasta 48 horas antes de la llegada; "
    "después se carga la primera noche"
)
ESTADOS_VALIDOS = ("confirmada", "en_estadia", "finalizada", "cancelada")
ESTADOS_QUE_OCUPAN_CUPO = ("confirmada", "en_estadia")


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
        "SELECT count(*) FROM reservas WHERE habitacion_id = %s AND estado IN ('confirmada', 'en_estadia') "
        "AND daterange(inicio, fin, '[)') && daterange(%s, %s, '[)')",
        (habitacion_id, inicio, fin),
    ).fetchone()
    return fila[0] == 0


def oferta(conexion: psycopg.Connection, inicio: date, fin: date, personas: int, ahora: datetime) -> dict:
    # HECHO DOCUMENTADO (dominio, ESTADOS_VENDIBLES): ocupada y sucia se venden
    # en otras fechas; mantenimiento, bloqueada y fuera_de_servicio quedan fuera.
    unidades = conexion.execute(
        "SELECT id, tipo, capacidad FROM habitaciones WHERE capacidad >= %s "
        "AND mantenimiento = false AND estado_operativo NOT IN ('bloqueada', 'fuera_de_servicio') "
        "ORDER BY id",
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


def listar_habitaciones(conexion: psycopg.Connection) -> list[dict]:
    """Inventario operativo de las unidades (GET /hotel/habitaciones,
    spec-api-v1 «Operación de la habitación»): estado operativo, preparación,
    mantenimiento y tareas pendientes, con la última tarifa configurada como
    referencia de contexto. Solo lectura, sin reglas de negocio."""
    filas = conexion.execute(
        "SELECT h.id, h.tipo, h.capacidad, h.estado_operativo, h.estado_preparacion, h.mantenimiento, "
        "COALESCE((SELECT t.tarifa_noche_clp FROM tarifas t WHERE t.habitacion_id = h.id "
        "ORDER BY t.fecha_desde DESC LIMIT 1), 0), "
        "(SELECT COUNT(*) FROM tareas_operativas ta WHERE ta.habitacion_id = h.id AND ta.estado = 'pendiente'), "
        "EXISTS(SELECT 1 FROM tareas_operativas ta WHERE ta.habitacion_id = h.id "
        "AND ta.estado = 'pendiente' AND ta.tipo = 'limpieza') "
        "FROM habitaciones h ORDER BY h.id"
    ).fetchall()
    return [
        {
            "habitacion_id": f[0],
            "tipo": f[1],
            "capacidad": f[2],
            "estado_operativo": f[3],
            "estado_preparacion": f[4],
            "mantenimiento": f[5],
            "tarifa_noche_clp": f[6],
            "tareas_pendientes": f[7],
            "limpieza_pendiente": f[8],
        }
        for f in filas
    ]


def buscar_reservas(
    conexion: psycopg.Connection,
    empresa_id: str,
    fecha: date | None = None,
    estado: str | None = None,
    texto: str | None = None,
    ver_documento: bool = False,
) -> list[dict]:
    """Búsqueda de reservas de la empresa (spec-api-v1): filtros opcionales con
    AND, orden por inicio, id. huesped_documento solo para ROLES_DOCUMENTO."""
    consulta = (
        "SELECT id, habitacion_id, inicio, fin, huesped_nombre, estado, "
        "tarifa_noche_aceptada_clp, huesped_documento FROM reservas WHERE empresa_id = %s"
    )
    parametros: list = [empresa_id]
    if fecha is not None:
        consulta += " AND inicio <= %s AND fin > %s"
        parametros += [fecha, fecha]
    if estado is not None:
        consulta += " AND estado = %s"
        parametros.append(estado)
    if texto:
        patron = f"%{texto}%"
        consulta += " AND (id ILIKE %s OR huesped_nombre ILIKE %s OR huesped_documento ILIKE %s OR habitacion_id ILIKE %s)"
        parametros += [patron, patron, patron, patron]
    consulta += " ORDER BY inicio, id"
    filas = conexion.execute(consulta, parametros).fetchall()
    items = []
    for fila in filas:
        item = {
            "reserva_id": fila[0],
            "habitacion_id": fila[1],
            "inicio": fila[2].isoformat(),
            "fin": fila[3].isoformat(),
            "huesped_nombre": fila[4],
            "estado": fila[5],
            "tarifa_noche_aceptada_clp": fila[6],
        }
        if ver_documento:
            item["huesped_documento"] = fila[7]
        items.append(item)
    return items


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
    total = tarifa * (fin - inicio).days
    try:
        with conexion.transaction():  # savepoint: la violación no aborta la transacción externa
            conexion.execute(
                "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, "
                "tarifa_noche_aceptada_clp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (reserva_id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, tarifa),
            )
            conexion.execute(
                "INSERT INTO cargos (id, reserva_id, concepto, monto_clp) VALUES (%s, %s, %s, %s)",
                (f"CRG-{uuid.uuid4().hex[:12]}", reserva_id, f"Alojamiento {(fin - inicio).days} noches", total),
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
        "total_clp": total,
    }
