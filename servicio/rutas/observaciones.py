"""Observaciones del dueño a la administración (rol dueño de solo lectura)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi import Path as RutaParam
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .. import observaciones, roles, seguridad
from . import comun
from .operacion import PATRON_ID, _cuerpo, _ejecutar

router = APIRouter()
ROLES_VER = roles.con_admin_hotel(roles.DUENO)
ROLES_DUENO = frozenset({roles.DUENO})


class ObservacionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texto: str = Field(min_length=3, max_length=1000)
    referencia: str | None = Field(default=None, max_length=120)


class RespuestaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    respuesta: str = Field(min_length=1, max_length=1000)


@router.get("/hotel/observaciones")
def listar_observaciones(
    estado: Literal["abierta", "respondida", "cerrada"] | None = Query(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_VER)
    return observaciones.listar(conexion, sesion.empresa_id, estado)


@router.post("/hotel/observaciones")
def dejar_observacion(
    request: Request,
    datos: ObservacionIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_DUENO)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("observacion", **datos.model_dump()),
        "observacion_creada", "observacion_id",
        lambda hotel: observaciones.crear(conexion, sesion.empresa_id, sesion.nombre, datos.texto, datos.referencia),
    )


@router.post("/hotel/observaciones/{observacion_id}/respuesta")
def responder_observacion(
    request: Request,
    datos: RespuestaIn,
    observacion_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, roles.ROLES_ADMIN_HOTEL)
    return _ejecutar(
        request, sesion, conexion, idempotency_key,
        _cuerpo("observacion_respuesta", observacion_id=observacion_id, **datos.model_dump()),
        "observacion_respondida", "observacion_id",
        lambda hotel: observaciones.responder(conexion, sesion.empresa_id, sesion.nombre, observacion_id, datos.respuesta),
    )


@router.post("/hotel/observaciones/{observacion_id}/cierre")
def cerrar_observacion(
    request: Request,
    observacion_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_DUENO)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("observacion_cierre", observacion_id=observacion_id),
        "observacion_cerrada", "observacion_id",
        lambda hotel: observaciones.cerrar(conexion, sesion.empresa_id, sesion.nombre, observacion_id),
    )
