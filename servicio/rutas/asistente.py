"""Asistente de preguntas: público (sin sesión, con freno) e interno (recepción y administración, solo lectura)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .. import asistente, canal_publico, observabilidad, roles, seguridad
from . import comun
from .hotel import _exigir_captcha, tarifas_publicas_lista

router = APIRouter()
_log = logging.getLogger("servicio.asistente")
MENSAJE_NO_DISPONIBLE = (
    f"El asistente no está disponible ahora. Escribe a recepción por WhatsApp al {asistente.TELEFONO_RECEPCION}."
)


class PreguntaIn(BaseModel):
    pregunta: str = Field(min_length=2, max_length=asistente.MAX_PREGUNTA)


class TurnoChatIn(BaseModel):
    rol: str = Field(pattern="^(usuario|asistente)$")
    texto: str = Field(min_length=1, max_length=800)


class PreguntaInternaIn(BaseModel):
    pregunta: str = Field(min_length=2, max_length=500)
    ruta: str | None = Field(default=None, max_length=120)
    historial: list[TurnoChatIn] = Field(default_factory=list, max_length=8)


def _cache(request: Request) -> asistente.CacheRespuestas:
    if not hasattr(request.app.state, "cache_asistente"):
        request.app.state.cache_asistente = asistente.CacheRespuestas()
    return request.app.state.cache_asistente


def _freno(request: Request) -> canal_publico.FrenoDeSolicitudes:
    """5 consultas por minuto por IP y 25 en total (el tope global es 5 veces el de cada clave)."""
    if not hasattr(request.app.state, "freno_asistente"):
        config = getattr(request.app.state, "configuracion", None)
        request.app.state.freno_asistente = canal_publico.FrenoDeSolicitudes(
            max_por_minuto=5, database_url=config.database_url if config else None,
        )
    return request.app.state.freno_asistente


@router.post("/publico/asistente")
def preguntar_publico(request: Request, cuerpo: PreguntaIn, conexion=Depends(comun.conexion)) -> dict:
    ip = canal_publico.ip_visible(request)
    if not _freno(request).permite(f"ip:{ip}", ambito="asistente"):
        raise HTTPException(status_code=429, detail="demasiadas consultas; espera un minuto e intenta de nuevo")
    _exigir_captcha(request, "asistente", ip)
    empresa_id = request.app.state.aplicacion.nucleo.empresa.id
    try:
        resultado = asistente.responder_publico(
            conexion, empresa_id, cuerpo.pregunta, getattr(request.app.state, "modelo_agente", None),
            _cache(request), tarifas_publicas_lista(request, conexion),
        )
    except asistente.DatosPersonales as error:
        raise HTTPException(status_code=422, detail=str(error))
    except asistente.NoDisponible:
        observabilidad.evento_seguridad("asistente_no_disponible", nivel=logging.WARNING, ambito="publico")
        raise HTTPException(status_code=503, detail=MENSAJE_NO_DISPONIBLE)
    observabilidad.evento_seguridad("asistente_publico", nivel=logging.INFO, fuente=resultado["fuente"])
    return resultado


@router.post("/hotel/asistente")
def preguntar_interno(
    request: Request,
    cuerpo: PreguntaInternaIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, roles.con_admin_hotel("recepcion"))
    if not _freno(request).permite(f"usuario:{sesion.nombre}", ambito="asistente_interno"):
        raise HTTPException(status_code=429, detail="demasiadas consultas; espera un minuto e intenta de nuevo")
    try:
        resultado = asistente.responder_interno(
            conexion, sesion.empresa_id, cuerpo.pregunta, getattr(request.app.state, "modelo_agente", None),
            tarifas_publicas_lista(request, conexion),
            ruta=cuerpo.ruta,
            historial=[{"rol": t.rol, "texto": t.texto} for t in cuerpo.historial],
        )
    except asistente.NoDisponible:
        raise HTTPException(status_code=503, detail="el asistente no está disponible; consulta la guía o a administración")
    return resultado
