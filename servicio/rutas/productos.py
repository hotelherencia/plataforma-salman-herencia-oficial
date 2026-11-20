"""Rutas del catálogo de productos y su stock (#357, 2026-11-18)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from .. import idempotencia
from .. import importacion_productos as importacion
from .. import productos as productos_db
from .. import roles
from .. import seguridad
from . import comun
from .modelos import (
    AjusteStockIn,
    ImportacionIn,
    ProductoCambioIn,
    ProductoIn,
    TransferenciaStockCoreIn,
    TransferenciaStockIn,
    VistaPreviaImportacionIn,
)

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
    codigo: str | None = Query(default=None, max_length=60),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Búsqueda incremental por palabra y filtro por categoría (#357)."""
    comun.exigir_rol(sesion, ROLES_LECTURA)
    ver_inactivos = inactivos and roles.es_admin_hotel(sesion.rol)
    return {"productos": productos_db.listar(conexion, texto, categoria, ver_inactivos, codigo=codigo)}


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
                                   producto.controla_stock, producto.stock, sesion.nombre,
                                   codigo=producto.codigo, stock_minimo=producto.stock_minimo),
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
        lambda: productos_db.ajustar_stock(
            conexion, producto_id, ajuste.delta, ajuste.motivo, sesion.nombre,
            bodega_codigo=ajuste.bodega_codigo,
        ),
        200, "stock_ajuste", producto_id,
    )


@router.get("/hotel/productos/bodegas")
@router.get("/core/stock/bodegas")
def listar_bodegas_stock(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Bodegas compartidas del core (#358): bodega_principal, minibar y cafetería."""
    comun.exigir_rol(sesion, ROLES_LECTURA)
    return {"bodegas": productos_db.listar_bodegas(conexion)}


@router.get("/hotel/productos/reposicion")
@router.get("/core/stock/reposicion")
def reporte_stock_reposicion(
    bodega: str | None = Query(default=None, pattern="^(bodega_principal|minibar|cafeteria)$"),
    categoria: str | None = Query(default=None, pattern="^(minibar|cafeteria|servicio|extra)$"),
    solo_alertas: bool = False,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Reporte transversal de stock y sugerencias de reposición (#358)."""
    comun.exigir_rol(sesion, ROLES_MANTENEDOR)
    try:
        return productos_db.reporte_reposicion(conexion, bodega=bodega, categoria=categoria, solo_alertas=solo_alertas)
    except productos_db.ProductoInvalido as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.post("/hotel/productos/{producto_id}/transferencia")
def transferir_stock_producto(
    producto_id: str,
    datos: TransferenciaStockIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Transfiere unidades entre bodegas (ej. bodega_principal → minibar o cafetería)."""
    comun.exigir_rol(sesion, ROLES_MANTENEDOR)
    cuerpo = {"operacion": "stock_transferencia", "producto_id": producto_id, **json.loads(datos.model_dump_json())}
    return _mutar(
        conexion, sesion, idempotency_key, cuerpo,
        lambda: productos_db.transferir_bodega(
            conexion, producto_id, datos.origen, datos.destino, datos.cantidad, datos.motivo, sesion.nombre
        ),
        200, "stock_transferencia", producto_id,
    )


@router.post("/core/stock/transferencias")
def transferir_stock_core(
    datos: TransferenciaStockCoreIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Endpoint core de transferencia entre bodegas compartido por hotel y cafetería (#358)."""
    comun.exigir_rol(sesion, ROLES_MANTENEDOR)
    cuerpo = {"operacion": "stock_transferencia_core", **json.loads(datos.model_dump_json())}
    return _mutar(
        conexion, sesion, idempotency_key, cuerpo,
        lambda: productos_db.transferir_bodega(
            conexion, datos.producto_id, datos.origen, datos.destino, datos.cantidad, datos.motivo, sesion.nombre
        ),
        200, "stock_transferencia", datos.producto_id,
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


# --- Carga amigable: factura XML del SII, planilla o lector (2026-11-19) ---

@router.post("/hotel/productos/importacion/vista-previa")
def vista_previa_importacion(
    entrada: VistaPreviaImportacionIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Lee la fuente y empareja cada línea con el catálogo. No escribe nada."""
    comun.exigir_rol(sesion, ROLES_MANTENEDOR)
    lineas = [l.model_dump() for l in entrada.lineas] if entrada.lineas else None
    try:
        return importacion.vista_previa(conexion, entrada.origen, entrada.xml, lineas)
    except importacion.FacturaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error))
    except importacion.FuenteNoDisponible as error:
        raise HTTPException(status_code=503, detail=str(error))


@router.post("/hotel/productos/importacion")
def confirmar_importacion(
    entrada: ImportacionIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Crea productos y suma stock en una sola transacción. Una factura
    (emisor + tipo + folio, leídos del XML en el servidor) se carga una vez."""
    comun.exigir_rol(sesion, ROLES_MANTENEDOR)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    documento = None
    if entrada.origen == "factura_xml":
        try:
            documento = importacion.leer_factura_xml(entrada.xml or "")["documento"]
        except importacion.FacturaInvalida as error:
            raise HTTPException(status_code=422, detail=str(error))
    lineas = [l.model_dump() for l in entrada.lineas]
    cuerpo = {"operacion": "productos_importacion", "origen": entrada.origen, "documento": documento, "lineas": lineas}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = importacion.confirmar(conexion, entrada.origen, documento, lineas, sesion.nombre)
        except importacion.ImportacionDuplicada as error:
            seguridad.auditar(conexion, sesion.nombre, "productos_importacion",
                              f"{documento['emisor_rut']}:{documento['tipo_dte']}:{documento['folio']}", "duplicada")
            return 409, {"detail": str(error), "ya_importada": error.previa}
        except importacion.ImportacionInvalida as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "productos_importacion", resultado["importacion_id"], "ok")
        return 201, resultado

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)


@router.get("/hotel/productos/importaciones")
def historial_importaciones(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_MANTENEDOR)
    return {"importaciones": importacion.historial(conexion)}
