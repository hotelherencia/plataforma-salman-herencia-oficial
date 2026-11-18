"""Rutas del catálogo de productos y su stock (#357, 2026-11-18)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from .. import idempotencia
from .. import productos as productos_db
from .. import roles
from .. import seguridad
from . import comun
from .modelos import AjusteStockIn, ProductoCambioIn, ProductoIn

router = APIRouter()

# Quien asienta cargos consulta el catálogo; solo la administración lo mantiene.
ROLES_LECTURA = roles.con_admin_hotel("recepcion", "caja")
ROLES_MANTENEDOR = roles.con_admin_hotel()


def _mutar(conexion, sesion, idempotency_key, cuerpo, funcion, codigo_ok, accion, recurso) -> JSONResponse:
    clave = comun.clave_idempotencia_o_400(idempotency_key)

    def operacion() -> tuple[int, dict]:
        try:
            resultado = funcion()
        except productos_db.ProductoInvalido as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, accion, resultado.get("producto_id", recurso), "ok")
        return codigo_ok, resultado

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)


@router.get("/hotel/productos")
def listar_productos(
    texto: str | None = Query(default=None, max_length=80),
    categoria: str | None = Query(default=None, pattern="^(minibar|cafeteria|servicio|extra)$"),
    inactivos: bool = False,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Búsqueda incremental por palabra y filtro por categoría (#357)."""
    comun.exigir_rol(sesion, ROLES_LECTURA)
    ver_inactivos = inactivos and roles.es_admin_hotel(sesion.rol)
    return {"productos": productos_db.listar(conexion, texto, categoria, ver_inactivos)}


@router.post("/hotel/productos")
def crear_producto(
    producto: ProductoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_MANTENEDOR)
    cuerpo = {"operacion": "producto_alta", **json.loads(producto.model_dump_json())}
    return _mutar(
        conexion, sesion, idempotency_key, cuerpo,
        lambda: productos_db.crear(conexion, producto.nombre, producto.categoria, producto.precio_clp,
                                   producto.controla_stock, producto.stock, sesion.nombre),
        201, "producto_alta", producto.nombre,
    )


@router.put("/hotel/productos/{producto_id}")
def cambiar_producto(
    producto_id: str,
    cambios: ProductoCambioIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Cambia nombre, categoría, precio, activo o control de stock. Los cargos
    ya asentados conservan su precio (#357, criterio 2)."""
    comun.exigir_rol(sesion, ROLES_MANTENEDOR)
    datos = cambios.model_dump(exclude_none=True)
    cuerpo = {"operacion": "producto_cambio", "producto_id": producto_id, **json.loads(cambios.model_dump_json())}
    return _mutar(
        conexion, sesion, idempotency_key, cuerpo,
        lambda: productos_db.actualizar(conexion, producto_id, datos),
        200, "producto_cambio", producto_id,
    )


@router.post("/hotel/productos/{producto_id}/stock")
def ajustar_stock(
    producto_id: str,
    ajuste: AjusteStockIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Reposición (+) o merma (−) con motivo; el stock nunca queda negativo."""
    comun.exigir_rol(sesion, ROLES_MANTENEDOR)
    cuerpo = {"operacion": "stock", "producto_id": producto_id, **json.loads(ajuste.model_dump_json())}
    return _mutar(
        conexion, sesion, idempotency_key, cuerpo,
        lambda: productos_db.ajustar_stock(conexion, producto_id, ajuste.delta, ajuste.motivo, sesion.nombre),
        200, "stock_ajuste", producto_id,
    )


@router.get("/hotel/productos/{producto_id}/movimientos")
def movimientos_stock(
    producto_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_MANTENEDOR)
    try:
        return {"producto_id": producto_id, "movimientos": productos_db.movimientos(conexion, producto_id)}
    except productos_db.ProductoInvalido as error:
        raise HTTPException(status_code=404, detail=str(error))
