"""Resolvedor único del precio por noche (entrega 1A, plan modulo-hotel §3.1).

Reemplaza las cuatro copias de la regla de vigencia que vivían en
`reservas.py` (tarifa_vigente, precio_noches, tarifas_por_noche y
primera_noche_sin_tarifa) y el subquery de la tarifa vigente hoy del listado.

Orden de resolución de una (habitación, noche), de menor a mayor prioridad:

1. **Precio base del tipo** (`tipos_habitacion.precio_base_clp`), heredado por
   todas las habitaciones del tipo.
2. **Precio propio de la habitación** (`habitaciones.precio_propio_clp`,
   reservado: aún sin pantalla de edición; la entrega 1B lo expone).
3. **Tarifa por habitación y fechas** (tabla `tarifas`, la de siempre): la de
   mayor `fecha_desde` que cubre la noche; a igualdad, la registrada más
   recientemente (spec-hotel-operacion-v1 §2.5). El orden lo hace PostgreSQL
   con el mismo ORDER BY de antes, así que el desempate es idéntico.

Sin ninguno de los tres, la noche queda «sin tarifa» (no se vende), igual
que antes. Las habitaciones existentes tienen tarifas en todas sus fechas y
sus tipos nacen sin precio base: ningún precio efectivo cambia.

Rendimiento: dos consultas por rango (habitaciones+tipos y tarifas que tocan
el rango) y el resto en memoria; sin consultas por noche.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable

import psycopg

ORDEN_VIGENCIA_TARIFA = "ORDER BY t.fecha_desde DESC, t.creado_en DESC, t.id DESC"

ORIGEN_TIPO = "tipo"
ORIGEN_HABITACION = "habitacion"
ORIGEN_TARIFA = "tarifa"


@dataclass(frozen=True)
class PrecioNoche:
    precio_clp: int
    origen: str  # "tarifa:TAR-…", "habitacion", "tipo:matrimonial"


@dataclass
class _Unidad:
    tipo: str
    precio_base: int | None
    precio_propio: int | None
    # (fecha_desde, fecha_hasta, precio, tarifa_id) en orden de vigencia.
    tarifas: list[tuple[date, date, int, str]] = field(default_factory=list)


class TablaPrecios:
    """Precios resueltos de un conjunto de habitaciones en [desde, hasta)."""

    def __init__(self, unidades: dict[str, _Unidad], desde: date, hasta: date):
        self._unidades = unidades
        self.desde = desde
        self.hasta = hasta

    def habitaciones(self) -> list[str]:
        return list(self._unidades)

    def precio(self, habitacion_id: str, noche: date) -> PrecioNoche | None:
        unidad = self._unidades.get(habitacion_id)
        if unidad is None:
            return None
        for desde, hasta, monto, tarifa_id in unidad.tarifas:
            if desde <= noche < hasta:
                return PrecioNoche(monto, f"{ORIGEN_TARIFA}:{tarifa_id}")
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
    if unidades and hasta > desde:
        filas = conexion.execute(
            "SELECT t.habitacion_id, t.fecha_desde, t.fecha_hasta, t.tarifa_noche_clp, t.id FROM tarifas t "
            "WHERE t.habitacion_id = ANY(%s) AND t.fecha_desde < %s AND t.fecha_hasta > %s "
            f"{ORDEN_VIGENCIA_TARIFA}",
            (list(unidades), hasta, desde),
        ).fetchall()
        for habitacion_id, f_desde, f_hasta, monto, tarifa_id in filas:
            unidades[habitacion_id].tarifas.append((f_desde, f_hasta, monto, tarifa_id))
    return TablaPrecios(unidades, desde, hasta)


@dataclass(frozen=True)
class Cotizacion:
    """Cotización de una estadía [inicio, fin) en una habitación."""

    inicio: date
    noches: list[tuple[date, PrecioNoche]]
    sin_tarifa: date | None  # primera noche descubierta, o None si todas tienen precio

    @property
    def tarifa_primera(self) -> int | None:
        """Precio de la noche de inicio: referencia de `tarifa_noche_aceptada_clp`
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
