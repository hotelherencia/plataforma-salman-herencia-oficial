"""Modelos de entrada HTTP (pydantic), extraídos de aplicacion.py.

ARC-A01 (#334): viven aparte de la fábrica de la app para que los módulos
de rutas los importen sin circularidad.
"""
from datetime import date

from pydantic import BaseModel, Field, field_validator

from .. import agente, canal_publico
from .. import leads as leads_mod


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


class TarifaIn(BaseModel):
    habitacion_id: str = Field(min_length=1, max_length=50)
    fecha_desde: date
    fecha_hasta: date
    tarifa_noche_clp: int = Field(gt=0, le=100_000_000)


class HuespedIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    documento: str | None = Field(default=None, max_length=50)


class ReservaIn(BaseModel):
    habitacion_id: str = Field(min_length=1, max_length=50)
    inicio: date
    fin: date
    huesped: HuespedIn


class PagoIn(BaseModel):
    monto_clp: int = Field(gt=0, le=1_000_000_000)
    clave: str = Field(min_length=1, max_length=100)
    modo: str = Field(pattern="^(manual|pasarela)$")


class UsuarioIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    rol: str = Field(pattern="^(administrador|recepcion|caja)$")
    clave: str = Field(min_length=6, max_length=200)


class ClaveIn(BaseModel):
    clave: str = Field(min_length=6, max_length=200)


class MantenimientoIn(BaseModel):
    abierto: bool


class CargoIn(BaseModel):
    concepto: str = Field(min_length=1, max_length=200)
    monto_clp: int = Field(gt=0, le=1_000_000_000)


class SolicitudPublicaIn(BaseModel):
    habitacion_id: str = Field(min_length=1, max_length=50)
    inicio: date
    fin: date
    personas: int = Field(gt=0, le=canal_publico.MAX_PERSONAS)
    huesped_nombre: str = Field(min_length=1, max_length=120)
    huesped_contacto: str = Field(min_length=1, max_length=120)


class RechazoSolicitudIn(BaseModel):
    motivo: str = Field(min_length=1, max_length=300)


class LeadPublicoIn(BaseModel):
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
