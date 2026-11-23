"""Rutas HTTP de SPEC-NOV-01 (#448): Libro de novedades turno a turno,
estacionamiento (~14 cupos) y conteos de desayunos y bebestibles."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .. import idempotencia, novedades, seguridad
from . import comun

router = APIRouter()

Turno = Literal["manana", "tarde", "noche"]
EstadoEstacionamiento = Literal["reservado", "ocupado", "liberado"]
CategoriaConteo = Literal["desayuno", "bebestible"]


class BebestibleItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=1, max_length=80)
    cantidad: int = Field(ge=0, le=1000)


class NovedadIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fecha_contable: date | None = None
    turno: Turno
    resumen: str = Field(min_length=3, max_length=2000)
    desayunos_servidos: int = Field(default=0, ge=0, le=500)
    bebestibles_detalle: list[BebestibleItemIn] = Field(default_factory=list, max_length=30)


class EstacionamientoAsignacionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fecha: date | None = None
    cupo: int = Field(ge=1, le=50)
    habitacion_id: str | None = Field(default=None, max_length=64)
    reserva_id: str | None = Field(default=None, max_length=64)
    patente: str = Field(default="", max_length=20)
    estado: EstadoEstacionamiento = "ocupado"
    observacion: str = Field(default="", max_length=240)


class ConteoFnbIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fecha_contable: date | None = None
    turno: Turno
    categoria: CategoriaConteo
    producto_id: str | None = Field(default=None, max_length=64)
    cantidad: int = Field(ge=0, le=1000)
    observacion: str = Field(default="", max_length=240)


@router.get("/hotel/novedades")
def ver_novedades(
    fecha: date | None = Query(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, novedades.ROLES_NOVEDADES)
    return novedades.obtener_novedades_dia(conn, sesion.empresa_id, fecha=fecha)


@router.post("/hotel/novedades")
def crear_novedad(
    cuerpo: NovedadIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, novedades.ROLES_NOVEDADES)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    payload = {"operacion": "libro_novedad", **cuerpo.model_dump(mode="json")}

    def operacion() -> tuple[int, dict]:
        res = novedades.registrar_novedad(
            conn,
            sesion.empresa_id,
            fecha_contable=cuerpo.fecha_contable,
            turno=cuerpo.turno,
            resumen=cuerpo.resumen,
            desayunos_servidos=cuerpo.desayunos_servidos,
            bebestibles_detalle=[b.model_dump() for b in cuerpo.bebestibles_detalle],
            actor=sesion.nombre,
        )
        return 201, res

    try:
        codigo, respuesta = idempotencia.ejecutar(conn, sesion.empresa_id, clave, payload, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conn.commit()
    return JSONResponse(status_code=codigo, content=respuesta)


@router.put("/hotel/estacionamiento/asignacion")
def guardar_asignacion_estacionamiento(
    cuerpo: EstacionamientoAsignacionIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, novedades.ROLES_NOVEDADES)
    res = novedades.asignar_estacionamiento(
        conn,
        sesion.empresa_id,
        fecha=cuerpo.fecha,
        cupo=cuerpo.cupo,
        habitacion_id=cuerpo.habitacion_id,
        reserva_id=cuerpo.reserva_id,
        patente=cuerpo.patente,
        estado=cuerpo.estado,
        observacion=cuerpo.observacion,
        actor=sesion.nombre,
    )
    conn.commit()
    return res


@router.post("/hotel/novedades/conteos")
def crear_conteo_fnb(
    cuerpo: ConteoFnbIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, novedades.ROLES_NOVEDADES)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    payload = {"operacion": "conteo_fnb", **cuerpo.model_dump(mode="json")}

    def operacion() -> tuple[int, dict]:
        res = novedades.registrar_conteo_fnb(
            conn,
            sesion.empresa_id,
            fecha_contable=cuerpo.fecha_contable,
            turno=cuerpo.turno,
            categoria=cuerpo.categoria,
            producto_id=cuerpo.producto_id,
            cantidad=cuerpo.cantidad,
            observacion=cuerpo.observacion,
            actor=sesion.nombre,
        )
        return 201, res

    try:
        codigo, respuesta = idempotencia.ejecutar(conn, sesion.empresa_id, clave, payload, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conn.commit()
    return JSONResponse(status_code=codigo, content=respuesta)
