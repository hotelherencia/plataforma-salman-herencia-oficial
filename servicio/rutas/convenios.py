"""Rutas HTTP para convenios tarifarios por institución, delegación o evento (SPEC-CONV-01)."""
from __future__ import annotations

import json
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .. import convenios as convenios_db
from .. import idempotencia, seguridad
from . import comun

router = APIRouter()


class ConvenioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=2, max_length=160)
    tipo: Literal["empresa", "evento", "delegacion"] = "empresa"
    cliente_id: str | None = Field(default=None, max_length=50)
    vigencia_desde: date
    vigencia_hasta: date
    reglas_precio: dict = Field(default_factory=dict)
    requiere_abono_pct: int = Field(default=50, ge=0, le=100)
    notas: str | None = Field(default=None, max_length=400)
    activo: bool = True


class ConvenioEdicionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str | None = Field(default=None, min_length=2, max_length=160)
    tipo: Literal["empresa", "evento", "delegacion"] | None = None
    cliente_id: str | None = Field(default=None, max_length=50)
    vigencia_desde: date | None = None
    vigencia_hasta: date | None = None
    reglas_precio: dict | None = None
    requiere_abono_pct: int | None = Field(default=None, ge=0, le=100)
    notas: str | None = Field(default=None, max_length=400)
    activo: bool | None = None


@router.get("/hotel/convenios")
def listar_convenios(
    solo_vigentes: bool = Query(default=False),
    fecha: date | None = Query(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Lista los convenios tarifarios de la empresa (recepción, caja y administración)."""
    comun.exigir_rol(sesion, convenios_db.ROLES_LECTURA_CONVENIOS)
    items = convenios_db.listar(
        conexion, sesion.empresa_id, solo_vigentes=solo_vigentes, fecha=fecha,
    )
    return {"convenios": items, "total": len(items)}


@router.post("/hotel/convenios")
def crear_convenio(
    datos: ConvenioIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Crea un convenio tarifario por empresa, evento o delegación (solo administración)."""
    comun.exigir_rol(sesion, convenios_db.ROLES_GESTION_CONVENIOS)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "convenio_alta", **json.loads(datos.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            creado = convenios_db.crear(
                conexion,
                sesion.empresa_id,
                nombre=datos.nombre,
                tipo=datos.tipo,
                vigencia_desde=datos.vigencia_desde,
                vigencia_hasta=datos.vigencia_hasta,
                reglas_precio=datos.reglas_precio,
                cliente_id=datos.cliente_id,
                requiere_abono_pct=datos.requiere_abono_pct,
                notas=datos.notas,
                activo=datos.activo,
                actor=sesion.nombre,
            )
        except convenios_db.ConvenioInvalido as error:
            return 422, {"detail": str(error)}
        return 201, creado

    codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)


@router.put("/hotel/convenios/{convenio_id}")
def editar_convenio(
    convenio_id: str,
    datos: ConvenioEdicionIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Actualiza vigencia, reglas de precio o estado de un convenio (solo administración)."""
    comun.exigir_rol(sesion, convenios_db.ROLES_GESTION_CONVENIOS)
    campos_enviados = datos.model_fields_set
    try:
        actualizado = convenios_db.actualizar(
            conexion,
            sesion.empresa_id,
            convenio_id,
            nombre=datos.nombre,
            tipo=datos.tipo,
            vigencia_desde=datos.vigencia_desde,
            vigencia_hasta=datos.vigencia_hasta,
            reglas_precio=datos.reglas_precio,
            cliente_id=datos.cliente_id,
            actualizar_cliente="cliente_id" in campos_enviados,
            requiere_abono_pct=datos.requiere_abono_pct,
            notas=datos.notas,
            actualizar_notas="notas" in campos_enviados,
            activo=datos.activo,
            actor=sesion.nombre,
        )
    except convenios_db.ConvenioInvalido as error:
        conexion.rollback()
        raise HTTPException(status_code=422, detail=str(error))
    conexion.commit()
    return actualizado
