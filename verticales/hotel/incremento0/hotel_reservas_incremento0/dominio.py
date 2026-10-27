from dataclasses import dataclass
from datetime import date
from enum import Enum


class EstadoReserva(Enum):
    CONFIRMADA = "confirmada"
    RECHAZADA = "rechazada"


class EstadoOperativo(Enum):
    DISPONIBLE = "disponible"
    BLOQUEADA = "bloqueada"
    FUERA_DE_SERVICIO = "fuera_de_servicio"


class EstadoPreparacion(Enum):
    LIMPIA = "limpia"
    SUCIA = "sucia"
    INSPECCIONADA = "inspeccionada"


@dataclass(frozen=True)
class TipoHabitacion:
    id: str
    nombre: str
    capacidad: int


@dataclass(frozen=True)
class UnidadHabitacion:
    id: str
    tipo: TipoHabitacion
    estado_operativo: EstadoOperativo = EstadoOperativo.DISPONIBLE
    estado_preparacion: EstadoPreparacion = EstadoPreparacion.SUCIA


@dataclass(frozen=True)
class Huesped:
    nombre: str
    documento: str


@dataclass(frozen=True)
class Reserva:
    id: str
    empresa_id: str
    unidad_id: str
    fecha_inicio: date
    fecha_fin: date
    huesped: Huesped
    estado: EstadoReserva
    motivo_rechazo: str | None = None


@dataclass(frozen=True)
class OfertaDisponible:
    unidad: UnidadHabitacion
    fecha_inicio: date
    fecha_fin: date


@dataclass(frozen=True)
class ResultadoReserva:
    confirmada: bool
    reserva: Reserva | None
    motivo: str | None = None
