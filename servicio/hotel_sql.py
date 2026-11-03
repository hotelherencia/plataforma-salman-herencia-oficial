"""Adaptador entre el dominio hotel_inventario y PostgreSQL (ADP, 2026-10-30).

PostgreSQL es el almacén y la proyección de lectura; el único que decide
cupo, oferta, confirmación, check-in, check-out, cancelación, penalización,
cargos, limpieza y mantenimiento es `ServicioHotelInventario`. Cada operación
HTTP de hotel, dentro de la misma transacción: (1) `recargar_hotel` vuelve a
llenar el singleton desde las filas actuales, (2) la ruta llama un método
público del dominio, (3) `persistir` escribe el estado que ese método dejó.

Proyección de nombres (una sola tabla, sin decidir): `hospedada` se guarda
`en_estadia`; `salida` se guarda `finalizada`; `confirmada` y `cancelada`
iguales. `EstadoUnidad.OCUPADA` → `estado_operativo=ocupada`. `SUCIA` →
`estado_operativo=disponible` y `estado_preparacion=sucia` (el dominio vende
esa unidad en otras fechas). `mantenimiento=true` → columna `mantenimiento`.
`LIMPIA`/`INSPECCIONADA` → `estado_preparacion`. Esta tabla no decide si el
check-in procede.

Persistencia: upserts por id (`reservas`, `habitaciones`, `tareas_operativas`),
insert append-only de `cargos` (inmutables en el dominio: jamás UPDATE ni
DELETE) y `pagos` escrito por el flujo de pago (conserva `efecto_nucleo_id`).
Sin deletes.
"""
from datetime import date, timedelta

import psycopg

from hotel_inventario.dominio import (
    Cargo,
    EstadoReserva,
    EstadoTarea,
    EstadoUnidad,
    Huesped,
    Pago,
    Reserva,
    TareaOperativa,
    TipoCargo,
    Unidad,
)

ESTABLECIMIENTO_SINTETICO = "EST-SINT-001"
TIPO_TARIFA_BASE = "base"

ESTADO_A_SQL = {
    EstadoReserva.CONFIRMADA: "confirmada",
    EstadoReserva.HOSPEDADA: "en_estadia",
    EstadoReserva.SALIDA: "finalizada",
    EstadoReserva.CANCELADA: "cancelada",
}

ESTABLECIMIENTO_ID = ESTABLECIMIENTO_SINTETICO


def _unidad_a_sql(unidad: Unidad) -> tuple[str, str]:
    """Proyección de nombres EstadoUnidad → (estado_operativo, estado_preparacion)."""
    if unidad.estado is EstadoUnidad.OCUPADA:
        return "ocupada", "limpia"
    if unidad.estado is EstadoUnidad.BLOQUEADA:
        return "bloqueada", "limpia"
    if unidad.estado is EstadoUnidad.FUERA_DE_SERVICIO:
        return "fuera_de_servicio", "limpia"
    if unidad.estado is EstadoUnidad.SUCIA:
        return "disponible", "sucia"
    if unidad.estado is EstadoUnidad.INSPECCIONADA:
        return "disponible", "inspeccionada"
    return "disponible", "limpia"


def _sql_a_unidad_estado(estado_operativo: str, estado_preparacion: str) -> EstadoUnidad:
    if estado_operativo == "ocupada":
        return EstadoUnidad.OCUPADA
    if estado_operativo == "bloqueada":
        return EstadoUnidad.BLOQUEADA
    if estado_operativo == "fuera_de_servicio":
        return EstadoUnidad.FUERA_DE_SERVICIO
    if estado_preparacion == "sucia":
        return EstadoUnidad.SUCIA
    if estado_preparacion == "inspeccionada":
        return EstadoUnidad.INSPECCIONADA
    return EstadoUnidad.LIMPIA


def cargar_estado(conexion: psycopg.Connection) -> dict:
    """Lee las filas actuales y las traduce a las tuplas que `hotel.recargar`
    espera. La tarifa base de cada unidad es la última tarifa configurada
    (respaldo del dominio cuando no hay entrada por fecha); 0 si no tiene
    ninguna (la oferta/reserva la excluyen por guarda del adaptador)."""
    filas = conexion.execute(
        "SELECT h.id, h.capacidad, h.estado_operativo, h.estado_preparacion, h.mantenimiento, "
        "COALESCE((SELECT t.tarifa_noche_clp FROM tarifas t WHERE t.habitacion_id = h.id "
        "ORDER BY t.fecha_desde DESC, t.creado_en DESC, t.id DESC LIMIT 1), 0) "
        "FROM habitaciones h ORDER BY h.id"
    ).fetchall()
    unidades = tuple(
        Unidad(
            id=f[0],
            establecimiento_id=ESTABLECIMIENTO_ID,
            capacidad=f[1],
            tarifa_noche_clp=f[5],
            estado=_sql_a_unidad_estado(f[2], f[3]),
            mantenimiento=f[4],
        )
        for f in filas
    )
    reservas = tuple(
        Reserva(
            id=f[0],
            empresa_id=f[1],
            unidad_id=f[2],
            inicio=f[3],
            fin=f[4],
            huesped=Huesped(nombre=f[5], documento=f[6], sintetico=True),
            estado=ESTADO_A_SQL_INVERSO[f[7]],
        )
        for f in conexion.execute(
            "SELECT id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, estado "
            "FROM reservas"
        ).fetchall()
    )
    cargos = tuple(
        Cargo(
            id=f[0],
            reserva_id=f[1],
            tipo=TipoCargo.CARGO if f[2] == "cargo" else TipoCargo.REVERSO,
            concepto=f[3],
            monto_clp=f[4],
            referencia=f[5],
        )
        for f in conexion.execute(
            "SELECT id, reserva_id, tipo, concepto, monto_clp, referencia FROM cargos ORDER BY creado_en"
        ).fetchall()
    )
    pagos = tuple(
        Pago(id=f[0], reserva_id=f[1], monto_clp=f[2], clave=f[3])
        for f in conexion.execute(
            "SELECT id, reserva_id, monto_clp, clave FROM pagos"
        ).fetchall()
    )
    tareas = tuple(
        TareaOperativa(
            id=f[0],
            empresa_id="",
            unidad_id=f[1],
            tipo=f[2],
            estado=EstadoTarea.PENDIENTE if f[3] == "pendiente" else EstadoTarea.COMPLETADA,
        )
        for f in conexion.execute(
            "SELECT id, habitacion_id, tipo, estado FROM tareas_operativas"
        ).fetchall()
    )
    # Las tarifas por rango se expanden a entradas por día: la granularidad
    # que usa el dominio en `_tarifas_por_fecha`. En orden de vigencia
    # ascendente, la que gana (spec-hotel-operacion-v1 §2.5) se escribe última.
    tarifas_por_fecha: dict[tuple[str, date], tuple[str, int]] = {}
    for habitacion_id, desde, hasta, monto in conexion.execute(
        "SELECT habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp FROM tarifas "
        "ORDER BY fecha_desde, creado_en, id"
    ).fetchall():
        dia = desde
        while dia < hasta:
            tarifas_por_fecha[(habitacion_id, dia)] = (TIPO_TARIFA_BASE, monto)
            dia += timedelta(days=1)
    tarifas_aceptadas = {
        f[0]: f[1]
        for f in conexion.execute(
            "SELECT id, tarifa_noche_aceptada_clp FROM reservas"
        ).fetchall()
    }
    return {
        "unidades": unidades,
        "reservas": reservas,
        "cargos": cargos,
        "pagos": pagos,
        "tareas": tareas,
        "tarifas_por_fecha": tarifas_por_fecha,
        "tarifas_aceptadas": tarifas_aceptadas,
    }


ESTADO_A_SQL_INVERSO = {
    "confirmada": EstadoReserva.CONFIRMADA,
    "en_estadia": EstadoReserva.HOSPEDADA,
    "finalizada": EstadoReserva.SALIDA,
    "cancelada": EstadoReserva.CANCELADA,
}

# Estados del dominio que el CHECK de la tabla admite; los rechazados/pendientes
# viven solo en memoria (respuesta) y no se proyectan.
_ESTADOS_PROYECTABLES = (EstadoReserva.CONFIRMADA, EstadoReserva.HOSPEDADA,
                         EstadoReserva.SALIDA, EstadoReserva.CANCELADA)


def recargar_hotel(conexion: psycopg.Connection, hotel) -> None:
    estado = cargar_estado(conexion)
    hotel.recargar(
        unidades=estado["unidades"],
        reservas=estado["reservas"],
        cargos=estado["cargos"],
        pagos=estado["pagos"],
        tareas=estado["tareas"],
        tarifas_por_fecha=estado["tarifas_por_fecha"],
        tarifas_aceptadas=estado["tarifas_aceptadas"],
    )


def persistir(conexion: psycopg.Connection, hotel, tipos: dict[str, str] | None = None) -> None:
    """Espejo del estado del dominio a las tablas (sin deletes).

    `tipos`: tipo de habitación para unidades NUEVAS (el dominio no modela
    tipo; viene del cuerpo de `PUT /hotel/habitaciones`)."""
    tipos = tipos or {}
    for unidad in hotel._unidades.values():
        operativo, preparacion = _unidad_a_sql(unidad)
        conexion.execute(
            "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, "
            "estado_preparacion, mantenimiento) VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET capacidad = EXCLUDED.capacidad, "
            "estado_operativo = EXCLUDED.estado_operativo, estado_preparacion = EXCLUDED.estado_preparacion, "
            "mantenimiento = EXCLUDED.mantenimiento",
            (unidad.id, ESTABLECIMIENTO_ID, tipos.get(unidad.id, "doble"), unidad.capacidad,
             operativo, preparacion, unidad.mantenimiento),
        )
    for reserva in hotel._reservas.values():
        if reserva.estado not in _ESTADOS_PROYECTABLES:
            continue
        conexion.execute(
            "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, "
            "huesped_documento, tarifa_noche_aceptada_clp, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET estado = EXCLUDED.estado",
            (reserva.id, reserva.empresa_id, reserva.unidad_id, reserva.inicio, reserva.fin,
             reserva.huesped.nombre, reserva.huesped.documento,
             hotel._tarifas_aceptadas.get(reserva.id, 0), ESTADO_A_SQL[reserva.estado]),
        )
    for cargo in hotel._cargos:
        conexion.execute(
            "INSERT INTO cargos (id, reserva_id, concepto, monto_clp, tipo, referencia) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (cargo.id, cargo.reserva_id, cargo.concepto, cargo.monto_clp,
             "cargo" if cargo.tipo is TipoCargo.CARGO else "reverso", cargo.referencia),
        )
    for tarea in hotel._tareas.values():
        conexion.execute(
            "INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado, completada_en) "
            "VALUES (%s, %s, %s, %s, CASE WHEN %s = 'completada' THEN now() END) "
            "ON CONFLICT (id) DO UPDATE SET estado = EXCLUDED.estado, "
            "completada_en = CASE WHEN EXCLUDED.estado = 'completada' THEN now() END",
            (tarea.id, tarea.unidad_id, tarea.tipo,
             "pendiente" if tarea.estado is EstadoTarea.PENDIENTE else "completada",
             "pendiente" if tarea.estado is EstadoTarea.PENDIENTE else "completada"),
        )


def persistir_liquidacion(conexion: psycopg.Connection, liquidacion, liquidacion_id: str) -> None:
    conexion.execute(
        "INSERT INTO liquidaciones (id, reserva_id, total_clp, pagado_clp, saldo_clp) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (reserva_id) DO NOTHING",
        (liquidacion_id, liquidacion.reserva_id, liquidacion.total_cargos_clp,
         liquidacion.total_pagos_clp, liquidacion.saldo_clp),
    )
