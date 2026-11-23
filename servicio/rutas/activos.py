"""Rutas de activos por habitación y mantenimiento preventivo (#418, Corte 2)."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi import Path as RutaParam
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .. import activos, seguridad
from . import comun
from .operacion import PATRON_ID, ROLES_GESTION, ROLES_OPERACION, _cuerpo, _ejecutar

router = APIRouter()

Categoria = Literal["mobiliario", "electrico", "climatizacion", "sanitario", "electronico", "otro"]
EstadoActivo = Literal["operativo", "en_reparacion", "de_baja"]


class ActivoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    habitacion_id: str | None = Field(default=None, pattern=PATRON_ID)
    area: str | None = Field(default=None, min_length=2, max_length=60)
    nombre: str = Field(min_length=2, max_length=80)
    categoria: Categoria = "otro"
    notas: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _ubicacion(self):
        if not self.habitacion_id and not self.area:
            raise ValueError("indica la habitación o el área")
        return self


class ActivoCambioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: EstadoActivo | None = None
    notas: str | None = Field(default=None, max_length=300)


class PlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descripcion: str = Field(min_length=3, max_length=200)
    cada_dias: int = Field(ge=1, le=1830)
    proxima: date | None = None


class RealizadaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fecha: date | None = None
    nota: str | None = Field(default=None, max_length=300)


@router.get("/hotel/activos")
def listar_activos(
    habitacion_id: str | None = Query(default=None, pattern=PATRON_ID),
    estado: EstadoActivo | None = None,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    return activos.listar_activos(conexion, habitacion_id, estado)


@router.post("/hotel/activos")
def crear_activo(
    request: Request,
    datos: ActivoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_GESTION)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("activo", **datos.model_dump()),
        "activo_creado", "activo_id",
        lambda hotel: activos.crear_activo(conexion, sesion.nombre, datos.model_dump()),
    )


@router.post("/hotel/activos/{activo_id}/actualizacion")
def actualizar_activo(
    request: Request,
    cambios: ActivoCambioIn,
    activo_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_GESTION)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("activo_cambio", activo_id=activo_id, **cambios.model_dump()),
        "activo_actualizado", "activo_id",
        lambda hotel: activos.actualizar_activo(conexion, activo_id, cambios.model_dump()),
    )


@router.post("/hotel/activos/{activo_id}/plan")
def crear_plan(
    request: Request,
    datos: PlanIn,
    activo_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_GESTION)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("mantencion_plan", activo_id=activo_id, **datos.model_dump(mode="json")),
        "mantencion_plan_creado", "plan_id",
        lambda hotel: activos.crear_plan(conexion, sesion.nombre, activo_id, datos.model_dump()),
    )


@router.get("/hotel/mantenciones")
def listar_mantenciones(
    dentro_de_dias: int = Query(default=14, ge=0, le=365),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    return activos.listar_mantenciones(conexion, dentro_de_dias, date.today())


@router.post("/hotel/mantenciones/{plan_id}/realizada")
def registrar_mantencion(
    request: Request,
    datos: RealizadaIn,
    plan_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    hoy = date.today()
    fecha = datos.fecha or hoy
    return _ejecutar(
        request, sesion, conexion, idempotency_key,
        _cuerpo("mantencion_realizada", plan_id=plan_id, fecha=fecha.isoformat(), nota=datos.nota),
        "mantencion_realizada", "plan_id",
        lambda hotel: activos.registrar_realizada(conexion, plan_id, sesion.nombre, fecha, datos.nota, hoy),
    )
