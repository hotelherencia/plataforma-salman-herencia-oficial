from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EstadoMesa(Enum):
    ACTIVA = "activa"
    REVOCADA = "revocada"


class EstadoPedido(Enum):
    ABIERTO = "abierto"
    ENVIADO = "enviado"


class EstadoGasto(Enum):
    PENDIENTE = "pendiente"
    APROBADO = "aprobado"


class EstadoPropuesta(Enum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    EXPIRADA = "expirada"
    EJECUTADA = "ejecutada"
    RECHAZADA = "rechazada"


@dataclass(frozen=True)
class Mesa:
    id: str
    qr_token: str
    estado: EstadoMesa


@dataclass(frozen=True)
class Producto:
    id: str
    nombre: str
    precio_clp: int
    receta: tuple[tuple[str, float], ...] = ()
    version: int = 1
    tiene_receta: bool = True


@dataclass(frozen=True)
class Insumo:
    id: str
    nombre: str
    stock: float
    costo_clp: float | None
    stock_minimo: float


@dataclass(frozen=True)
class ItemPedido:
    producto_id: str
    cantidad: int
    cliente: str
    precio_clp: int
    enviado: bool = False


@dataclass(frozen=True)
class Comanda:
    id: str
    pedido_id: str
    mesa_id: str
    hora: datetime
    estado: str


@dataclass(frozen=True)
class PagoItem:
    id: str
    mesa_id: str
    item_clave: str
    cliente: str
    monto_clp: int


@dataclass(frozen=True)
class Parte:
    cliente: str
    monto_clp: int
    pagada: bool = False
    clave_pago: str | None = None


@dataclass(frozen=True)
class Reparto:
    mesa_id: str
    partes: tuple[Parte, ...]
    descuento_clp: int
    propina_clp: int


@dataclass(frozen=True)
class MovimientoInsumo:
    insumo_id: str
    cantidad: float
    venta_id: str


@dataclass(frozen=True)
class GastoBorrador:
    id: str
    proveedor: str
    monto_clp: int
    fecha: str
    estado: EstadoGasto
    lineas_erroneas: int
    correcciones: tuple[str, ...] = ()


@dataclass(frozen=True)
class PropuestaCompra:
    id: str
    insumo_id: str
    cantidad: float
    costo_clp: int
    creada_en: datetime
    expira_en: datetime
    estado: EstadoPropuesta


@dataclass(frozen=True)
class Alerta:
    id: str
    hecho_id: str
    umbral_clp: int
    monto_clp: int
    creada_en: datetime


@dataclass(frozen=True)
class EntradaLedger:
    fuente: str
    regla: str
    actor: str
    resultado: str
    cuando: datetime
