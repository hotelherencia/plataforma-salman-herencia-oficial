from dataclasses import dataclass
from datetime import date
from enum import Enum


class EstadoUnidad(Enum):
    LIMPIA = "limpia"
    SUCIA = "sucia"
    INSPECCIONADA = "inspeccionada"
    OCUPADA = "ocupada"
    BLOQUEADA = "bloqueada"
    FUERA_DE_SERVICIO = "fuera_de_servicio"


# Convención de hotel del incremento 1: bloqueada y fuera de servicio no entran al
# cupo para ninguna fecha. Ocupada, sucia, limpia e inspeccionada sí se venden:
# la ocupación actual protege solo su rango (se controla por solape de fechas), no
# elimina inventario futuro (AC-US-HOT-001-02).
ESTADOS_VENDIBLES = frozenset(
    {
        EstadoUnidad.LIMPIA,
        EstadoUnidad.SUCIA,
        EstadoUnidad.INSPECCIONADA,
        EstadoUnidad.OCUPADA,
    }
)


class EstadoReserva(Enum):
    CONFIRMADA = "confirmada"
    HOSPEDADA = "hospedada"
    SALIDA = "salida"
    PENDIENTE = "pendiente"
    CANCELADA = "cancelada"
    RECHAZADA = "rechazada"


class TipoCargo(Enum):
    CARGO = "cargo"
    REVERSO = "reverso"


class EstadoTarea(Enum):
    PENDIENTE = "pendiente"
    COMPLETADA = "completada"


@dataclass(frozen=True)
class Establecimiento:
    id: str
    empresa_id: str
    nombre: str


@dataclass(frozen=True)
class Unidad:
    id: str
    establecimiento_id: str
    capacidad: int
    tarifa_noche_clp: int
    estado: EstadoUnidad = EstadoUnidad.LIMPIA
    # Mantenimiento abierto: independiente de la limpieza (data-model: «una habitación
    # limpia puede seguir no asignable por mantenimiento»). Quita la unidad del cupo.
    mantenimiento: bool = False


@dataclass(frozen=True)
class Huesped:
    nombre: str
    documento: str | None = None
    sintetico: bool = True


@dataclass(frozen=True)
class Reserva:
    id: str
    empresa_id: str
    unidad_id: str
    inicio: date
    fin: date
    huesped: Huesped
    estado: EstadoReserva
    motivo: str | None = None


@dataclass(frozen=True)
class Cargo:
    """Asiento inmutable de la cuenta de estadía. Una corrección es otro asiento."""

    id: str
    reserva_id: str
    tipo: TipoCargo
    concepto: str
    monto_clp: int
    referencia: str | None = None


@dataclass(frozen=True)
class ResultadoReserva:
    confirmada: bool
    reserva: Reserva
    motivo: str | None = None


@dataclass(frozen=True)
class ResultadoCancelacion:
    reserva: Reserva
    cargo: Cargo | None


@dataclass(frozen=True)
class TareaOperativa:
    id: str
    empresa_id: str
    unidad_id: str
    tipo: str
    estado: EstadoTarea


@dataclass(frozen=True)
class Pago:
    """Abono o anticipo inmutable de la cuenta de estadía."""

    id: str
    reserva_id: str
    monto_clp: int
    clave: str | None = None


@dataclass(frozen=True)
class Liquidacion:
    reserva_id: str
    total_cargos_clp: int
    total_pagos_clp: int
    saldo_clp: int


@dataclass(frozen=True)
class PedidoHabitacion:
    id: str
    reserva_id: str
    items: tuple[str, ...]
    comanda_id: str
    clave: str | None = None
    entregado: bool = False


@dataclass(frozen=True)
class ResultadoPedido:
    confirmado: bool
    pedido: PedidoHabitacion | None
    motivo: str | None = None


class EstadoDevolucion(Enum):
    PENDIENTE = "pendiente"
    AUTORIZADA = "autorizada"
    EFECTUADA = "efectuada"


@dataclass(frozen=True)
class SolicitudDevolucion:
    id: str
    reserva_id: str
    monto_clp: int
    estado: EstadoDevolucion
    aprobador: str | None = None


class ReglaCantidad(Enum):
    POR_PERSONA_NOCHE = "por_persona_noche"
    POR_ESTADIA = "por_estadia"


@dataclass(frozen=True)
class ExtraHotel:
    id: str
    nombre: str
    precio_clp: int
    regla: ReglaCantidad


@dataclass(frozen=True)
class LineaExtra:
    extra_id: str
    nombre: str
    cantidad: int
    monto_clp: int
    regla_visible: str


@dataclass(frozen=True)
class PropuestaCambio:
    reserva_id: str
    tarifa_actual_clp: int
    tarifa_nueva_clp: int
    noches: int
    diferencia_total_clp: int


@dataclass(frozen=True)
class OfertaVigente:
    unidad_id: str
    tarifa_noche_clp: int
    politica_cancelacion: str
    emitida_en: datetime
    vigente_hasta: datetime
    inicio: date
    fin: date


@dataclass(frozen=True)
class ResultadoBorrador:
    aplicado: bool
    escalado: bool
    motivo: str


@dataclass(frozen=True)
class AccionRegistrada:
    fuente: str
    regla: str
    actor: str
    resultado: str
    cuando: datetime


@dataclass(frozen=True)
class ProyeccionPublica:
    unidad_id: str
    capacidad: int


@dataclass(frozen=True)
class Aprobacion:
    id: str
    descripcion: str
    parametros: tuple[tuple[str, object], ...]
    monto_clp: int
    vigente_hasta: datetime


@dataclass(frozen=True)
class PropuestaUpsell:
    id: str
    reserva_id: str
    extra_id: str
    descripcion: str
    monto_clp: int
    link: str
    creada_en: datetime


@dataclass(frozen=True)
class TransferenciaHumana:
    id: str
    reserva_id: str
    receptor: str
    estado: str
    resuelto: bool


@dataclass(frozen=True)
class RespuestaConcierge:
    texto: str
    accion: str
    escalado: bool
    transferencia_id: str | None = None
    link: str | None = None
