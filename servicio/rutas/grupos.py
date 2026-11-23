"""Rutas HTTP de reservas de grupo (PR B / RES-007): titular con varias habitaciones."""
from __future__ import annotations

import json

from fastapi import APIRouter, Body, Depends, Header, Request
from fastapi.responses import JSONResponse

from .. import grupos as grupos_db
from .. import hotel_sql, idempotencia, roles, seguridad
from . import comun
from .modelos import GrupoEntradaIn, GrupoIn, GrupoReservaIn

router = APIRouter()

ROLES_DOCUMENTO_HUESPED = roles.con_admin_hotel("recepcion")


def _ejecutar_exclusivo(conexion, empresa_id, clave, cuerpo, operacion) -> JSONResponse:
    with hotel_sql.EXCLUSIVO:
        hotel_sql.bloquear(conexion)
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, empresa_id, clave, cuerpo, operacion)
        conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)


@router.post("/hotel/grupos")
def crear_grupo(
    request: Request,
    datos: GrupoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Crea un grupo de 1 o más habitaciones bajo un titular en transacción atómica."""
    comun.exigir_rol(sesion, grupos_db.ROLES_GRUPOS)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "grupo_alta", **json.loads(datos.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            creado = grupos_db.crear_grupo(
                conexion,
                request.app.state.aplicacion.hotel,
                empresa_id=sesion.empresa_id,
                titular_nombre=datos.titular.nombre,
                titular_documento=datos.titular.documento,
                titular_documento_tipo=datos.titular.documento_tipo,
                habitaciones=[h.model_dump() for h in datos.habitaciones],
                canal=datos.canal,
                notas=datos.notas,
                actor=sesion.nombre,
            )
        except grupos_db.GrupoInvalido as error:
            return 422, {"detail": str(error)}
        except grupos_db.GrupoConflicto as error:
            return 409, {"detail": str(error)}
        return 201, creado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)


@router.get("/hotel/grupos/{grupo_id}")
def detalle_grupo(
    request: Request,
    grupo_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Detalle del grupo con sus habitaciones, huéspedes y cuenta consolidada sin duplicación."""
    return grupos_db.obtener_grupo(
        conexion,
        request.app.state.aplicacion.hotel,
        sesion.empresa_id,
        grupo_id,
        ver_documento=sesion.rol in ROLES_DOCUMENTO_HUESPED,
    )


@router.post("/hotel/grupos/{grupo_id}/reservas")
def agregar_reserva_grupo(
    request: Request,
    grupo_id: str,
    datos: GrupoReservaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Agrega una nueva habitación (o vincula una reserva existente) al grupo."""
    comun.exigir_rol(sesion, grupos_db.ROLES_GRUPOS)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "grupo_agregar_reserva", "grupo_id": grupo_id, **json.loads(datos.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = grupos_db.agregar_reserva_a_grupo(
                conexion,
                request.app.state.aplicacion.hotel,
                empresa_id=sesion.empresa_id,
                grupo_id=grupo_id,
                datos=datos.model_dump(),
                actor=sesion.nombre,
            )
        except grupos_db.GrupoInvalido as error:
            return 422, {"detail": str(error)}
        except grupos_db.GrupoConflicto as error:
            return 409, {"detail": str(error)}
        return 201, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)


@router.post("/hotel/grupos/{grupo_id}/entrada")
def entrada_grupo(
    request: Request,
    grupo_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
    cuerpo_in: GrupoEntradaIn | None = Body(default=None),
) -> JSONResponse:
    """Llegada en lote atómica de las habitaciones confirmadas del grupo."""
    comun.exigir_rol(sesion, grupos_db.ROLES_GRUPOS)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {
        "operacion": "grupo_entrada",
        "grupo_id": grupo_id,
        **(json.loads(cuerpo_in.model_dump_json()) if cuerpo_in else {}),
    }

    def operacion() -> tuple[int, dict]:
        try:
            resultado = grupos_db.entrada_grupo(
                conexion,
                request.app.state.aplicacion.hotel,
                empresa_id=sesion.empresa_id,
                grupo_id=grupo_id,
                ahora=hotel_sql.ahora(),
                actor=sesion.nombre,
                documento=cuerpo_in.documento if cuerpo_in else None,
                documento_tipo=cuerpo_in.documento_tipo if cuerpo_in else None,
                reserva_ids=cuerpo_in.reserva_ids if cuerpo_in else None,
            )
        except grupos_db.GrupoConflicto as error:
            return 409, {"detail": str(error)}
        return 200, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)
