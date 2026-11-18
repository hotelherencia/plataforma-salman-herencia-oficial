"""Modelos de entrada HTTP (pydantic), extraídos de aplicacion.py.

ARC-A01 (#334): viven aparte de la fábrica de la app para que los módulos
de rutas los importen sin circularidad.
"""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .. import agente, canal_publico, roles
from .. import leads as leads_mod
from ..tipos_habitacion import MAX_LOTE, PATRON_ID_TIPO, PATRON_PREFIJO


class Credenciales(BaseModel):
    usuario: str
    clave: str
    totp: str | None = Field(default=None, min_length=6, max_length=10)


class CodigoTotpIn(BaseModel):
    codigo: str = Field(min_length=6, max_length=10)


class ClaveActualIn(BaseModel):
    """SEC-A02 (#327): clave actual para reautenticar operaciones sensibles
    del segundo factor (reemplazar el autenticador o desactivarlo). Cualquier
    largo no vacío: la validación de la clave la hace `reautenticar_clave`
    (401), no el esquema — un 422 aquí filtraría el chequeo de autorización."""
    clave: str = Field(min_length=1)


class HabitacionIn(BaseModel):
    tipo: str = Field(min_length=1, max_length=50)
    capacidad: int = Field(gt=0, le=30)

    @field_validator("tipo")
    @classmethod
    def _tipo_sin_bordes(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("el tipo no puede quedar vacío")
        return valor


# spec-hotel-operacion-v1 §2.2: id estable y apto para URL (clave primaria).
PATRON_ID_HABITACION = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$"


class ServicioIn(BaseModel):
    en_servicio: bool
    motivo: str | None = Field(default=None, max_length=200)


class HuespedIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    documento: str | None = Field(default=None, max_length=50)


class ReservaIn(BaseModel):
    habitacion_id: str = Field(min_length=1, max_length=50)
    inicio: date
    fin: date
    huesped: HuespedIn
    # #298 (DECISIÓN 2026-11-06): se persiste y se valida contra la capacidad
    # al confirmar; opcional porque no todo flujo lo conoce (conversiones).
    personas: int | None = Field(default=None, ge=1, le=30)
    # Entrega 1A.3: recargos de la política (llegada anticipada, salida tardía, etc.).
    hora_llegada: str | None = Field(default=None, pattern=r"^\d{1,2}:\d{2}$")
    hora_salida: str | None = Field(default=None, pattern=r"^\d{1,2}:\d{2}$")
    cama_adicional: bool | None = None
    ninos: int | None = Field(default=None, ge=1, le=30)
    mascotas: bool | None = None


class PagoIn(BaseModel):
    monto_clp: int = Field(gt=0, le=1_000_000_000)
    clave: str = Field(min_length=1, max_length=100)
    modo: str = Field(pattern="^(manual|pasarela)$")
    # #365: un monto mayor que el saldo exige confirmación explícita.
    confirmar_exceso: bool = False


class UsuarioIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    rol: str = Field(pattern=roles.PATRON_ROL)
    clave: str = Field(min_length=6, max_length=200)


class ClaveIn(BaseModel):
    clave: str = Field(min_length=6, max_length=200)
    # Obligatoria cuando la sesión cambia su propia clave. Un administrador
    # que cambia la de otro usuario no la envía: es un reemplazo, no una
    # reautenticación.
    clave_actual: str | None = None


class MantenimientoIn(BaseModel):
    abierto: bool


class CargoIn(BaseModel):
    concepto: str = Field(min_length=1, max_length=200)
    monto_clp: int = Field(gt=0, le=1_000_000_000)


class ReversoCargoIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=150)


class SolicitudPublicaIn(BaseModel):
    # Lista blanca: un campo no declarado es 422, no se ignora en silencio.
    model_config = ConfigDict(extra="forbid")

    # #346: la solicitud es por tipo. `habitacion_id` solo se acepta por
    # compatibilidad con el front ya desplegado y se traduce a su tipo; la
    # unidad nunca se guarda ni se devuelve al visitante.
    tipo: str | None = Field(default=None, min_length=1, max_length=50)
    habitacion_id: str | None = Field(default=None, min_length=1, max_length=50)
    inicio: date
    fin: date
    personas: int = Field(gt=0, le=canal_publico.MAX_PERSONAS)
    huesped_nombre: str = Field(min_length=1, max_length=120)
    huesped_contacto: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def _tipo_o_unidad(self):
        if (self.tipo is None) == (self.habitacion_id is None):
            raise ValueError("indica tipo (o, por compatibilidad, habitacion_id), no ambos")
        return self


class RechazoSolicitudIn(BaseModel):
    motivo: str = Field(min_length=1, max_length=300)


class LeadPublicoIn(BaseModel):
    # Lista blanca: un campo no declarado es 422, no se ignora en silencio.
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=leads_mod.MAX_NOMBRE)
    correo: str = Field(min_length=1, max_length=leads_mod.MAX_CORREO)
    telefono: str = Field(min_length=1, max_length=leads_mod.MAX_TELEFONO)
    huespedes: int | None = Field(default=None, ge=1, le=leads_mod.MAX_PERSONAS)
    check_in: date | None = None
    check_out: date | None = None
    mensaje: str | None = Field(default=None, max_length=leads_mod.MAX_MENSAJE)


class GestionLeadIn(BaseModel):
    estado: str = Field(min_length=1, max_length=20)
    nota: str | None = Field(default=None, max_length=500)


class ConsultaAgenteIn(BaseModel):
    canal_origen: str = Field(min_length=1, max_length=20)
    texto: str = Field(min_length=1, max_length=agente.MAX_TEXTO_CONSULTA)


class AprobacionBorradorIn(BaseModel):
    texto_editado: str | None = Field(default=None, max_length=4000)


class DescarteBorradorIn(BaseModel):
    motivo: str = Field(min_length=1, max_length=300)


class PoliticaAgenteIn(BaseModel):
    nivel: str | None = Field(default=None, pattern=r"^N[012]$")
    horario: str | None = Field(default=None, max_length=100)
    max_noches: int | None = Field(default=None, ge=1, le=30)
    max_personas: int | None = Field(default=None, ge=1, le=30)
    tope_mensual_clp: int | None = Field(default=None, ge=0)
    evaluacion_ref: str | None = Field(default=None, max_length=200)


class DocumentoHuespedIn(BaseModel):
    """D-ENT-01 (DECISIÓN 2026-11-06, #296 opción b): documento exigido antes
    de `en_estadia`. Las solicitudes públicas convierten sin documento, así
    que la entrada lo captura cuando la reserva aún no lo trae. El campo es
    opcional en el esquema (un cuerpo vacío es legal y lo resuelve el
    dominio con 409); la obligatoriedad la fija `cobro.entrada`."""
    documento: str | None = Field(default=None, min_length=1, max_length=50)


# --- Entrega 1A: tipos de habitación y alta por lote -----------------------


PrecioEn = Literal["con_iva", "neto"]


class TipoHabitacionIn(BaseModel):
    tipo_id: str = Field(pattern=PATRON_ID_TIPO)
    nombre: str = Field(min_length=1, max_length=80)
    capacidad_base: int = Field(gt=0, le=30)
    precio_base_clp: int | None = Field(default=None, gt=0, le=100_000_000)
    # Cómo se ingresó el monto: con IVA (se guarda tal cual) o neto (se
    # convierte a con IVA con la tasa vigente; servicio/iva.py).
    precio_en: PrecioEn = "con_iva"
    orden: int = Field(default=100, ge=0, le=10_000)

    @field_validator("nombre")
    @classmethod
    def _nombre_sin_bordes(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("el nombre no puede quedar vacío")
        return valor


class TipoHabitacionEdicionIn(BaseModel):
    """Campos omitidos no cambian; `precio_base_clp: null` quita el precio base."""

    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    capacidad_base: int | None = Field(default=None, gt=0, le=30)
    precio_base_clp: int | None = Field(default=None, gt=0, le=100_000_000)
    precio_en: PrecioEn = "con_iva"
    orden: int | None = Field(default=None, ge=0, le=10_000)
    activo: bool | None = None

    @field_validator("nombre")
    @classmethod
    def _nombre_sin_bordes(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = valor.strip()
        if not valor:
            raise ValueError("el nombre no puede quedar vacío")
        return valor


class LoteHabitacionesIn(BaseModel):
    tipo_id: str = Field(pattern=PATRON_ID_TIPO)
    cantidad: int = Field(ge=1, le=MAX_LOTE)
    prefijo: str = Field(default="HAB-", pattern=PATRON_PREFIJO)
    desde_numero: int = Field(ge=0, le=99_999)
    digitos: int = Field(default=2, ge=1, le=5)
    capacidad: int | None = Field(default=None, gt=0, le=30)


class PrecioPropioIn(BaseModel):
    """Precio propio de una habitación (gana al base del tipo); null lo quita."""

    precio_clp: int | None = Field(gt=0, le=100_000_000)
    precio_en: PrecioEn = "con_iva"


class ExcepcionPrecioIn(BaseModel):
    """Excepción por fecha [fecha_desde, fecha_hasta) de un tipo o de una
    habitación. `precio_clp: null` = sin venta esas noches."""

    tipo_id: str | None = Field(default=None, min_length=1, max_length=50)
    habitacion_id: str | None = Field(default=None, min_length=1, max_length=50)
    fecha_desde: date
    fecha_hasta: date
    precio_clp: int | None = Field(gt=0, le=100_000_000)
    precio_en: PrecioEn = "con_iva"
    motivo: str | None = Field(default=None, max_length=120)


class TasaIvaIn(BaseModel):
    iva_porcentaje: Decimal = Field(ge=0, le=100, max_digits=6, decimal_places=3)


class PoliticasHotelIn(BaseModel):
    """Cuerpo completo de las políticas (el servidor valida y normaliza)."""

    model_config = ConfigDict(extra="forbid")
    cuerpo: dict


class SimulacionPoliticaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicio: date
    fin: date
    habitacion_id: str | None = Field(default=None, max_length=50)
    precio_noche_clp: int | None = Field(default=None, gt=0, le=100_000_000)
    hora_llegada: str | None = Field(default=None, pattern=r"^\d{1,2}:\d{2}$")
    hora_salida: str | None = Field(default=None, pattern=r"^\d{1,2}:\d{2}$")
    cama_adicional: bool | None = None
    ninos: int | None = Field(default=None, ge=1, le=30)
    mascotas: bool | None = None

    def extras(self) -> dict:
        return {
            clave: valor
            for clave, valor in {
                "hora_llegada": self.hora_llegada,
                "hora_salida": self.hora_salida,
                "cama_adicional": self.cama_adicional,
                "ninos": self.ninos,
                "mascotas": self.mascotas,
            }.items()
            if valor not in (None, False)
        }
