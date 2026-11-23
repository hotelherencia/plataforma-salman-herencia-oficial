"""Mensajes preformateados al huésped y datos que faltan (#452, #454)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, Request
from fastapi import Path as RutaParam
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from .. import mensajes_huesped, roles, seguridad
from . import comun
from .operacion import PATRON_ID, _cuerpo, _ejecutar

router = APIRouter()
ROLES_MENSAJES = roles.con_admin_hotel("recepcion")


class MensajeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plantilla: Literal["confirmacion", "recordatorio", "solicitar_datos", "cancelacion", "gracias"]
    canal: Literal["correo", "whatsapp"]


@router.get("/hotel/reservas/{reserva_id}/mensajes")
def mensajes_de_reserva(
    reserva_id: str = RutaParam(pattern=PATRON_ID),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_MENSAJES)
    resultado = mensajes_huesped.armar(conexion, sesion.empresa_id, reserva_id)
    if resultado is None:
        raise seguridad.ErrorPermiso("acceso denegado")
    resultado["historial"] = mensajes_huesped.historial(conexion, sesion.empresa_id, reserva_id)
    return resultado


@router.post("/hotel/reservas/{reserva_id}/mensajes")
def registrar_mensaje(
    request: Request,
    datos: MensajeIn,
    reserva_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_MENSAJES)
    if mensajes_huesped.armar(conexion, sesion.empresa_id, reserva_id) is None:
        raise seguridad.ErrorPermiso("acceso denegado")

    def hacer(hotel) -> dict:
        if datos.canal == "correo":
            return mensajes_huesped.enviar_por_correo(
                conexion, sesion.empresa_id, reserva_id, datos.plantilla, sesion.nombre)
        return mensajes_huesped.registrar_whatsapp_abierto(
            conexion, sesion.empresa_id, reserva_id, datos.plantilla, sesion.nombre)

    return _ejecutar(
        request, sesion, conexion, idempotency_key,
        _cuerpo("mensaje_huesped", reserva_id=reserva_id, **datos.model_dump()),
        "mensaje_huesped", "reserva_id", hacer,
    )
