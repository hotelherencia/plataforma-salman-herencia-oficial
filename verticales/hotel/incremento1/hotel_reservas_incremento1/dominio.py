from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EstadoUnidad(Enum):
    LIMPIA = "limpia"
    SUCIA = "sucia"
    INSPECCIONADA = "inspeccionada"
    BLOQUEADA = "bloqueada"
    FUERA_DE_SERVICIO = "fuera_de_servicio"


ESTADOS_VENDIBLES = frozenset(
    {EstadoUnidad.LIMPIA, EstadoUnidad.SUCIA, EstadoUnidad.INSPECCIONADA}
)


class EstadoReserva(Enum):
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"
    RECHAZADA = "rechazada"


@dataclass(frozen=True)
class TipoHabitacion:
    id: str
    nombre: str
    capacidad: int
    tarifa_noche_clp: int


@dataclass(frozen=True)
class UnidadHabitacion:
    id: str
    tipo: TipoHabitacion
    establecimiento_id: str
    estado: EstadoUnidad = EstadoUnidad.SUCIA


@dataclass(frozen=True)
class Huesped:
    nombre: str
    documento: str


@dataclass(frozen=True)
class Reserva:
    id: str
    empresa_id: str
    establecimiento_id: str
    unidad_id: str
    inicio: datetime
    fin: datetime
    llegada: datetime
    huesped: Huesped
    estado: EstadoReserva
    motivo_rechazo: str | None = None


@dataclass(frozen=True)
class CuentaEstadia:
    id: str
    empresa_id: str
    reserva_id: str


@dataclass(frozen=True)
class Cargo:
    id: str
    empresa_id: str
    cuenta_id: str
    concepto: str
    monto_clp: int
    cargo_origen_id: str | None = None


@dataclass(frozen=True)
class OfertaDisponible:
    unidad: UnidadHabitacion
    inicio: datetime
    fin: datetime


@dataclass(frozen=True)
class ResultadoReserva:
    confirmada: bool
    reserva: Reserva | None
    motivo: str | None = None
