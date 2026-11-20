"""Stock en el core compartido entre verticales (#358 / V1-ISSUE-57).

Modelo agnóstico de vertical: productos, bodegas/ubicaciones (`bodega_principal`,
`minibar`, `cafeteria`), movimientos trazables (entrada, salida, ajuste,
transferencia, reverso) y cálculo de alertas/sugerencias de reposición.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

BODEGA_PRINCIPAL = "bodega_principal"
BODEGA_MINIBAR = "minibar"
BODEGA_CAFETERIA = "cafeteria"

TIPOS_MOVIMIENTO = frozenset({"entrada", "salida", "ajuste", "transferencia", "reverso"})


class ErrorStockCore(Exception):
    """Violación de invariante de inventario (stock negativo, bodega inválida, etc.)."""


@dataclass(frozen=True)
class Bodega:
    id: str
    codigo: str
    nombre: str
    modulo: str
    activa: bool = True

    def a_dict(self) -> dict:
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "modulo": self.modulo,
            "activa": self.activa,
        }


BODEGAS_BASE: tuple[Bodega, ...] = (
    Bodega("BOD-CORE", BODEGA_PRINCIPAL, "Bodega principal", "core"),
    Bodega("BOD-MINIBAR", BODEGA_MINIBAR, "Minibar habitaciones", "hotel"),
    Bodega("BOD-CAFE", BODEGA_CAFETERIA, "Cafetería", "cafeteria"),
)


def bodega_por_categoria(categoria: str | None) -> str:
    """Ubicación por defecto según la categoría del producto."""
    if categoria == "minibar":
        return BODEGA_MINIBAR
    if categoria == "cafeteria":
        return BODEGA_CAFETERIA
    return BODEGA_PRINCIPAL


@dataclass(frozen=True)
class EstadoReposicion:
    producto_id: str
    nombre: str
    categoria: str
    stock_actual: int
    stock_minimo: int
    costo_clp: int | None
    nivel: str  # 'sin_stock' | 'bajo_minimo' | 'ok'
    sugerido_reponer: int
    valorizacion_costo_clp: int
    por_bodega: dict[str, int] = field(default_factory=dict)

    def a_dict(self) -> dict:
        return {
            "producto_id": self.producto_id,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "stock_actual": self.stock_actual,
            "stock_minimo": self.stock_minimo,
            "costo_clp": self.costo_clp,
            "nivel": self.nivel,
            "sugerido_reponer": self.sugerido_reponer,
            "valorizacion_costo_clp": self.valorizacion_costo_clp,
            "por_bodega": dict(self.por_bodega),
        }


def evaluar_reposicion(
    producto_id: str,
    nombre: str,
    categoria: str,
    stock_actual: int,
    stock_minimo: int = 0,
    costo_clp: int | None = None,
    por_bodega: dict[str, int] | None = None,
) -> EstadoReposicion:
    """Clasifica el nivel de stock y calcula la cantidad sugerida de reposición.

    Reglas:
    - `sin_stock`: stock_actual == 0 (sugiere al menos max(stock_minimo * 2, 1) si hay mínimo, o 1).
    - `bajo_minimo`: stock_minimo > 0 y 0 < stock_actual <= stock_minimo (sugiere llevar al doble del mínimo).
    - `ok`: en otro caso (sugerido = 0).
    """
    stock = max(0, int(stock_actual or 0))
    minimo = max(0, int(stock_minimo or 0))
    if stock == 0:
        nivel = "sin_stock"
        objetivo = max(minimo * 2, minimo, 1)
        sugerido = objetivo
    elif minimo > 0 and stock <= minimo:
        nivel = "bajo_minimo"
        objetivo = max(minimo * 2, minimo + 1)
        sugerido = max(1, objetivo - stock)
    else:
        nivel = "ok"
        sugerido = 0
    valorizacion = stock * int(costo_clp) if costo_clp is not None and costo_clp > 0 else 0
    return EstadoReposicion(
        producto_id=producto_id,
        nombre=nombre,
        categoria=categoria,
        stock_actual=stock,
        stock_minimo=minimo,
        costo_clp=costo_clp,
        nivel=nivel,
        sugerido_reponer=sugerido,
        valorizacion_costo_clp=valorizacion,
        por_bodega=dict(por_bodega or {}),
    )


def resumir_reposicion(items: Iterable[EstadoReposicion]) -> dict:
    lista = list(items)
    sin_stock = sum(1 for i in lista if i.nivel == "sin_stock")
    bajo_minimo = sum(1 for i in lista if i.nivel == "bajo_minimo")
    ok = sum(1 for i in lista if i.nivel == "ok")
    unidades_totales = sum(i.stock_actual for i in lista)
    valorizacion_total = sum(i.valorizacion_costo_clp for i in lista)
    return {
        "productos_controlados": len(lista),
        "sin_stock": sin_stock,
        "bajo_minimo": bajo_minimo,
        "con_alerta": sin_stock + bajo_minimo,
        "ok": ok,
        "unidades_totales": unidades_totales,
        "valorizacion_costo_clp": valorizacion_total,
    }


class ServicioStockCore:
    """Servicio de dominio en memoria para pruebas y composición entre verticales."""

    def __init__(self, bodegas: Iterable[Bodega] = BODEGAS_BASE) -> None:
        self._bodegas: dict[str, Bodega] = {b.codigo: b for b in bodegas}
        # {(producto_id, bodega_codigo): cantidad}
        self._saldos: dict[tuple[str, str], int] = {}
        self._productos: dict[str, dict] = {}
        self._movimientos: list[dict] = []

    def registrar_producto(
        self,
        producto_id: str,
        nombre: str,
        categoria: str,
        stock_minimo: int = 0,
        costo_clp: int | None = None,
    ) -> None:
        if stock_minimo < 0:
            raise ErrorStockCore("stock_minimo no puede ser negativo")
        self._productos[producto_id] = {
            "producto_id": producto_id,
            "nombre": nombre,
            "categoria": categoria,
            "stock_minimo": stock_minimo,
            "costo_clp": costo_clp,
        }

    def mover(
        self,
        producto_id: str,
        bodega_codigo: str,
        tipo: str,
        delta: int,
        motivo: str,
        referencia: str | None = None,
    ) -> int:
        if producto_id not in self._productos:
            raise ErrorStockCore(f"producto {producto_id} no registrado")
        if bodega_codigo not in self._bodegas or not self._bodegas[bodega_codigo].activa:
            raise ErrorStockCore(f"bodega {bodega_codigo} inválida o inactiva")
        if tipo not in TIPOS_MOVIMIENTO:
            raise ErrorStockCore(f"tipo de movimiento inválido: {tipo}")
        if delta == 0:
            raise ErrorStockCore("delta no puede ser cero")
        actual = self._saldos.get((producto_id, bodega_codigo), 0)
        nuevo = actual + delta
        if nuevo < 0:
            raise ErrorStockCore(f"stock insuficiente en {bodega_codigo}: hay {actual}")
        self._saldos[(producto_id, bodega_codigo)] = nuevo
        self._movimientos.append({
            "producto_id": producto_id,
            "bodega_codigo": bodega_codigo,
            "tipo": tipo,
            "delta": delta,
            "motivo": motivo,
            "referencia": referencia,
        })
        return nuevo

    def transferir(
        self,
        producto_id: str,
        origen: str,
        destino: str,
        cantidad: int,
        motivo: str = "reposición interna",
    ) -> tuple[int, int]:
        if origen == destino:
            raise ErrorStockCore("la bodega de origen y destino deben ser distintas")
        if cantidad <= 0:
            raise ErrorStockCore("la cantidad a transferir debe ser mayor que cero")
        saldo_origen = self.mover(producto_id, origen, "transferencia", -cantidad, motivo, referencia=destino)
        saldo_destino = self.mover(producto_id, destino, "transferencia", cantidad, motivo, referencia=origen)
        return saldo_origen, saldo_destino

    def stock_de(self, producto_id: str, bodega_codigo: str | None = None) -> int:
        if bodega_codigo is not None:
            return self._saldos.get((producto_id, bodega_codigo), 0)
        return sum(v for (pid, _), v in self._saldos.items() if pid == producto_id)

    def reporte_reposicion(self, solo_alertas: bool = False) -> dict:
        estados: list[EstadoReposicion] = []
        for pid, meta in self._productos.items():
            por_bodega = {
                bod: cant
                for (p, bod), cant in self._saldos.items()
                if p == pid and cant > 0
            }
            est = evaluar_reposicion(
                producto_id=pid,
                nombre=meta["nombre"],
                categoria=meta["categoria"],
                stock_actual=sum(por_bodega.values()),
                stock_minimo=meta["stock_minimo"],
                costo_clp=meta["costo_clp"],
                por_bodega=por_bodega,
            )
            if not solo_alertas or est.nivel != "ok":
                estados.append(est)
        estados.sort(key=lambda e: ({"sin_stock": 0, "bajo_minimo": 1, "ok": 2}[e.nivel], e.nombre.lower()))
        return {
            "resumen": resumir_reposicion(estados),
            "bodegas": [b.a_dict() for b in self._bodegas.values() if b.activa],
            "items": [e.a_dict() for e in estados],
        }
