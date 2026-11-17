"""Resolvedor único del precio por noche (una sola fuente de precio).

Todo precio se define en el mantenedor «Tipos, habitaciones y precios»
(entregas 1A y 1A.2, migración 0022). Orden de resolución de una
(habitación, noche), de mayor a menor prioridad:

1. **Excepción por fecha de la habitación** (`excepciones_precio` con
   `habitacion_id`).
2. **Excepción por fecha del tipo** (`excepciones_precio` con `tipo_id`):
   temporadas, feriados, cierres; aplica a todas las habitaciones del tipo.
3. **Precio propio de la habitación** (`habitaciones.precio_propio_clp`).
4. **Precio base del tipo** (`tipos_habitacion.precio_base_clp`).

Dentro de un mismo nivel de excepción gana la de mayor `fecha_desde`; a
igualdad, la registrada más recientemente (`creado_en`, luego `id`): la misma
regla de vigencia que tenían las tarifas heredadas (spec-hotel-operacion-v1
§2.5). Una excepción con precio NULL deja esas noches «sin venta». Sin
ningún precio la noche queda «sin tarifa» (no se vende).

Todos los montos son CON IVA (servicio/iva.py deriva neto e IVA).

Rendimiento: dos consultas por rango (habitaciones+tipos y excepciones que
tocan el rango) y el resto en memoria.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable

import psycopg

ORDEN_VIGENCIA = "ORDER BY e.fecha_desde DESC, e.creado_en DESC, e.id DESC"

ORIGEN_TIPO = "tipo"
ORIGEN_HABITACION = "habitacion"
ORIGEN_EXCEPCION_TIPO = "excepcion_tipo"
ORIGEN_EXCEPCION_HABITACION = "excepcion_habitacion"


@dataclass(frozen=True)
class PrecioNoche:
    precio_clp: int
    # "tipo:<id>", "habitacion", "excepcion_tipo:EXC-…", "excepcion_habitacion:EXC-…"
    origen: str


# (fecha_desde, fecha_hasta, precio|None, excepcion_id) en orden de vigencia.
_Excepcion = tuple[date, date, "int | None", str]


@dataclass
class _Unidad:
    tipo: str
    precio_base: int | None
    precio_propio: int | None
    excepciones: list[_Excepcion] = field(default_factory=list)


class TablaPrecios:
    """Precios resueltos de un conjunto de habitaciones en [desde, hasta)."""

    def __init__(self, unidades: dict[str, _Unidad], por_tipo: dict[str, list[_Excepcion]], desde: date, hasta: date):
        self._unidades = unidades
        self._por_tipo = por_tipo
        self.desde = desde
        self.hasta = hasta

    def habitaciones(self) -> list[str]:
        return list(self._unidades)

    def precio(self, habitacion_id: str, noche: date) -> PrecioNoche | None:
        unidad = self._unidades.get(habitacion_id)
        if unidad is None:
            return None
        for lista, origen in (
            (unidad.excepciones, ORIGEN_EXCEPCION_HABITACION),
            (self._por_tipo.get(unidad.tipo, ()), ORIGEN_EXCEPCION_TIPO),
        ):
            for desde, hasta, monto, excepcion_id in lista:
                if desde <= noche < hasta:
                    return PrecioNoche(monto, f"{origen}:{excepcion_id}") if monto else None
        if unidad.precio_propio:
            return PrecioNoche(unidad.precio_propio, ORIGEN_HABITACION)
        if unidad.precio_base:
            return PrecioNoche(unidad.precio_base, f"{ORIGEN_TIPO}:{unidad.tipo}")
        return None


def _noches(inicio: date, fin: date) -> Iterable[date]:
    noche = inicio
    while noche < fin:
        yield noche
        noche += timedelta(days=1)


def cargar(
    conexion: psycopg.Connection,
    desde: date,
    hasta: date,
    habitacion_ids: list[str] | None = None,
) -> TablaPrecios:
    """Carga las reglas que tocan [desde, hasta) para las habitaciones dadas
    (todas si `habitacion_ids` es None)."""
    filtro = "" if habitacion_ids is None else " WHERE h.id = ANY(%s)"
    parametros: tuple = () if habitacion_ids is None else (list(habitacion_ids),)
    unidades = {
        f[0]: _Unidad(tipo=f[1], precio_base=f[2], precio_propio=f[3])
        for f in conexion.execute(
            "SELECT h.id, h.tipo, t.precio_base_clp, h.precio_propio_clp FROM habitaciones h "
            f"LEFT JOIN tipos_habitacion t ON t.id = h.tipo{filtro} ORDER BY h.id",
            parametros,
        ).fetchall()
    }
    por_tipo: dict[str, list[_Excepcion]] = {}
    if unidades and hasta > desde:
        tipos = sorted({u.tipo for u in unidades.values()})
        filas = conexion.execute(
            "SELECT e.habitacion_id, e.tipo_id, e.fecha_desde, e.fecha_hasta, e.precio_clp, e.id "
            "FROM excepciones_precio e WHERE e.activa "
            "AND (e.habitacion_id = ANY(%s) OR e.tipo_id = ANY(%s)) "
            f"AND e.fecha_desde < %s AND e.fecha_hasta > %s {ORDEN_VIGENCIA}",
            (list(unidades), tipos, hasta, desde),
        ).fetchall()
        for habitacion_id, tipo_id, f_desde, f_hasta, monto, excepcion_id in filas:
            regla = (f_desde, f_hasta, monto, excepcion_id)
            if habitacion_id is not None:
                unidades[habitacion_id].excepciones.append(regla)
            else:
                por_tipo.setdefault(tipo_id, []).append(regla)
    return TablaPrecios(unidades, por_tipo, desde, hasta)


@dataclass(frozen=True)
class Cotizacion:
    """Cotización de una estadía [inicio, fin) en una habitación."""

    inicio: date
    noches: list[tuple[date, PrecioNoche]]
    sin_tarifa: date | None  # primera noche sin precio, o None si todas tienen

    @property
    def tarifa_primera(self) -> int | None:
        """Precio de la noche de llegada: referencia de `tarifa_noche_aceptada_clp`
        (base de la penalidad de cancelación, spec-hotel-operacion §3)."""
        if self.noches and self.noches[0][0] == self.inicio:
            return self.noches[0][1].precio_clp
        return None

    @property
    def total(self) -> int:
        return sum(p.precio_clp for _, p in self.noches)


def cotizar_en(tabla: TablaPrecios, habitacion_id: str, inicio: date, fin: date) -> Cotizacion:
    noches: list[tuple[date, PrecioNoche]] = []
    sin_tarifa = None
    for noche in _noches(inicio, fin):
        precio = tabla.precio(habitacion_id, noche)
        if precio is None:
            if sin_tarifa is None:
                sin_tarifa = noche
            continue
        noches.append((noche, precio))
    return Cotizacion(inicio=inicio, noches=noches, sin_tarifa=sin_tarifa)


def cotizar(conexion: psycopg.Connection, habitacion_id: str, inicio: date, fin: date) -> Cotizacion:
    return cotizar_en(cargar(conexion, inicio, fin, [habitacion_id]), habitacion_id, inicio, fin)


def precio_noche(conexion: psycopg.Connection, habitacion_id: str, noche: date) -> PrecioNoche | None:
    return cargar(conexion, noche, noche + timedelta(days=1), [habitacion_id]).precio(habitacion_id, noche)


def precios_del_rango(
    conexion: psycopg.Connection, desde: date, hasta: date, habitacion_ids: list[str] | None = None
) -> dict[tuple[str, date], PrecioNoche]:
    """Precio de cada (habitación, noche) con precio en [desde, hasta)."""
    tabla = cargar(conexion, desde, hasta, habitacion_ids)
    salida: dict[tuple[str, date], PrecioNoche] = {}
    for habitacion_id in tabla.habitaciones():
        for noche in _noches(desde, hasta):
            precio = tabla.precio(habitacion_id, noche)
            if precio is not None:
                salida[(habitacion_id, noche)] = precio
    return salida


def precio_por_noche(conexion: psycopg.Connection, desde: date, hasta: date) -> dict[tuple[str, date], int]:
    """Monto de cada (habitación, noche) con precio en [desde, hasta)."""
    return {clave: p.precio_clp for clave, p in precios_del_rango(conexion, desde, hasta).items()}
