"""Rutas de la bandeja de facturas de proveedores (2026-11-19).

Todo es solo para la administración del hotel. Subir una foto o un XML deja
el documento pendiente; únicamente la confirmación toca el stock.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response

from .. import correo
from .. import facturas_proveedor as facturas
from .. import idempotencia
from .. import importacion_productos as importacion
from .. import roles, seguridad, vision
from . import comun
from .modelos import ConfirmacionDocumentoIn, DocumentoCambioIn, DocumentoXmlIn, EquivalenciaCambioIn

router = APIRouter()
ROLES = roles.con_admin_hotel()
BASE = "/hotel/productos/documentos"


def _error(error: Exception) -> HTTPException:
    if isinstance(error, facturas.DocumentoNoEncontrado):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, facturas.DocumentoEnConflicto):
        return HTTPException(status_code=409, detail=str(error))
    return HTTPException(status_code=422, detail=str(error))


@router.get(BASE)
def listar_documentos(
    estado: str = Query(default="abiertos", pattern=r"^(abiertos|cargada|todos)$"),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Bandeja: facturas por revisar y pedidos en borrador (o el historial)."""
    comun.exigir_rol(sesion, ROLES)
    estados = {"abiertos": facturas.ESTADOS_ABIERTOS, "cargada": ("cargada", "facturado"),
               "todos": ("pendiente", "borrador", "cargada", "facturado", "archivada", "descartada")}[estado]
    hay_buzon = conexion.execute(
        "SELECT count(*) FROM buzones_correo WHERE proposito = 'recepcion_dte' AND activo").fetchone()[0] > 0
    return {"documentos": facturas.listar(conexion, estados), "lectura_automatica": vision.estado(),
            "buzon_recepcion": hay_buzon}


@router.post(f"{BASE}/archivo")
async def subir_archivo(
    request: Request,
    x_nombre_archivo: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Cuerpo binario (foto JPG/PNG/WebP o PDF, máx. 10 MB). El tipo se
    verifica por el contenido. Una misma foto no crea dos documentos."""
    comun.exigir_rol(sesion, ROLES)
    largo = request.headers.get("content-length")
    if largo and largo.isdigit() and int(largo) > facturas.MAX_ARCHIVO:
        raise HTTPException(status_code=413, detail="El archivo es demasiado grande (máximo 10 MB). Reduce la foto o el PDF.")
    contenido = bytearray()
    async for trozo in request.stream():
        contenido += trozo
        if len(contenido) > facturas.MAX_ARCHIVO:
            raise HTTPException(status_code=413, detail="El archivo es demasiado grande (máximo 10 MB). Reduce la foto o el PDF.")
    tipo = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    try:
        resultado = facturas.crear_desde_archivo(conexion, bytes(contenido), tipo, x_nombre_archivo, sesion.nombre)
    except facturas.DocumentoInvalido as error:
        raise HTTPException(status_code=422, detail=str(error))
    seguridad.auditar(conexion, sesion.nombre, "documento_proveedor_archivo", resultado["documento_id"] or "-",
                      "repetido" if resultado["repetido"] else "ok")
    conexion.commit()
    cuerpo = {**facturas.detalle(conexion, resultado["documento_id"]), "repetido": resultado["repetido"]}
    return JSONResponse(status_code=200 if resultado["repetido"] else 201, content=cuerpo)


@router.post(f"{BASE}/xml")
def subir_xml(
    entrada: DocumentoXmlIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """XML del SII subido a mano: igual que si llegara por el correo."""
    comun.exigir_rol(sesion, ROLES)
    try:
        r = facturas.crear_desde_xml(conexion, entrada.xml, "xml", sesion.nombre)
    except importacion.FacturaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error))
    seguridad.auditar(conexion, sesion.nombre, "documento_proveedor_xml",
                      ",".join(c["documento_id"] for c in r["creados"]) or "-", "ok" if r["creados"] else "repetido")
    conexion.commit()
    if r["creados"]:
        return JSONResponse(status_code=201, content={**r, "documento": facturas.detalle(conexion, r["creados"][0]["documento_id"])})
    if r["repetidos"]:
        rep = r["repetidos"][0]
        doc = facturas.detalle(conexion, rep["documento_id"]) if rep["documento_id"] else None
        previa = importacion.importacion_previa(conexion, {**rep, "tipo_dte": (doc or {}).get("tipo_dte") or 33}) if not doc else None
        return JSONResponse(status_code=200, content={**r, "documento": doc, "ya_importada": previa})
    raise HTTPException(status_code=422, detail=(r["ignorados"][0]["motivo"] if r["ignorados"] else "El XML no trae facturas."))


@router.get(f"{BASE}/{{documento_id}}")
def ver_documento(documento_id: str, sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
                  conexion=Depends(comun.conexion)) -> dict:
    comun.exigir_rol(sesion, ROLES)
    try:
        return facturas.detalle(conexion, documento_id)
    except facturas.DocumentoNoEncontrado as error:
        raise _error(error)


@router.get(f"{BASE}/{{documento_id}}/archivo")
def ver_archivo(documento_id: str, sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
                conexion=Depends(comun.conexion)) -> Response:
    """La foto o el PDF original, solo para la administración y sin que el
    navegador lo interprete como otra cosa."""
    comun.exigir_rol(sesion, ROLES)
    try:
        contenido, tipo = facturas.leer_archivo(conexion, documento_id)
    except facturas.DocumentoNoEncontrado as error:
        raise _error(error)
    if tipo == "application/xml":
        tipo = "text/plain; charset=iso-8859-1"
    return Response(content=contenido, media_type=tipo, headers={
        "Content-Disposition": "inline", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox",
        "Cache-Control": "private, no-store",
    })


@router.put(f"{BASE}/{{documento_id}}")
def cambiar_documento(documento_id: str, entrada: DocumentoCambioIn,
                      sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
                      conexion=Depends(comun.conexion)) -> dict:
    comun.exigir_rol(sesion, ROLES)
    cambios = entrada.model_dump(exclude_unset=True)
    if "fecha_emision" in cambios and cambios["fecha_emision"]:
        cambios["fecha_emision"] = cambios["fecha_emision"].isoformat()
    if cambios.get("clase") is None:
        cambios.pop("clase", None)
    try:
        r = facturas.actualizar(conexion, documento_id, cambios, sesion.nombre)
    except (facturas.DocumentoInvalido, facturas.DocumentoNoEncontrado, facturas.DocumentoEnConflicto) as error:
        conexion.rollback()
        raise _error(error)
    seguridad.auditar(conexion, sesion.nombre, "documento_proveedor_edicion", documento_id, "ok")
    conexion.commit()
    return r


@router.post(f"{BASE}/{{documento_id}}/confirmacion")
def confirmar_documento(documento_id: str, entrada: ConfirmacionDocumentoIn,
                        idempotency_key: str | None = Header(default=None),
                        sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
                        conexion=Depends(comun.conexion)) -> JSONResponse:
    """Carga la factura al inventario (una sola vez) y recuerda los envases."""
    comun.exigir_rol(sesion, ROLES)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    lineas = [l.model_dump() for l in entrada.lineas]
    cuerpo = {"operacion": "documento_proveedor_confirmacion", "documento_id": documento_id, "lineas": lineas,
              "pedido_id": entrada.pedido_id}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = facturas.confirmar(conexion, documento_id, lineas, sesion.nombre, entrada.pedido_id)
        except importacion.ImportacionDuplicada as error:
            seguridad.auditar(conexion, sesion.nombre, "documento_proveedor_confirmacion", documento_id, "duplicada")
            return 409, {"detail": str(error), "ya_importada": error.previa}
        except importacion.ImportacionInvalida as error:
            return 409, {"detail": str(error)}
        except facturas.DocumentoNoEncontrado as error:
            return 404, {"detail": str(error)}
        except (facturas.DocumentoEnConflicto, facturas.DocumentoInvalido) as error:
            return (409 if isinstance(error, facturas.DocumentoEnConflicto) else 422), {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "documento_proveedor_confirmacion", documento_id, "ok")
        return 201, resultado

    try:
        codigo, respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=respuesta)


@router.post(f"{BASE}/{{documento_id}}/descarte")
def descartar_documento(documento_id: str, sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
                        conexion=Depends(comun.conexion)) -> dict:
    comun.exigir_rol(sesion, ROLES)
    try:
        r = facturas.descartar(conexion, documento_id, sesion.nombre)
    except (facturas.DocumentoNoEncontrado, facturas.DocumentoEnConflicto) as error:
        raise _error(error)
    seguridad.auditar(conexion, sesion.nombre, "documento_proveedor_descarte", documento_id, r["estado"])
    conexion.commit()
    return r


@router.post("/hotel/productos/recepcion-correo")
def revisar_correo_ahora(sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
                         conexion=Depends(comun.conexion)) -> dict:
    """«Revisar el correo ahora» (sin esperar la revisión periódica)."""
    comun.exigir_rol(sesion, ROLES)
    resultado = correo.revisar_recepcion_dte(conexion, sesion.empresa_id)
    conexion.commit()
    return resultado


@router.get("/hotel/productos/equivalencias")
def listar_equivalencias(sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
                         conexion=Depends(comun.conexion)) -> dict:
    comun.exigir_rol(sesion, ROLES)
    return {"equivalencias": facturas.listar_equivalencias(conexion)}


@router.put("/hotel/productos/equivalencias/{equivalencia_id}")
def cambiar_equivalencia(equivalencia_id: str, entrada: EquivalenciaCambioIn,
                         sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
                         conexion=Depends(comun.conexion)) -> dict:
    comun.exigir_rol(sesion, ROLES)
    try:
        r = facturas.cambiar_equivalencia(conexion, equivalencia_id, entrada.model_dump(exclude_unset=True), sesion.nombre)
    except (facturas.DocumentoNoEncontrado, facturas.DocumentoInvalido) as error:
        raise _error(error)
    seguridad.auditar(conexion, sesion.nombre, "equivalencia_proveedor", equivalencia_id, "ok")
    conexion.commit()
    return r


@router.delete("/hotel/productos/equivalencias/{equivalencia_id}")
def eliminar_equivalencia(equivalencia_id: str, sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
                          conexion=Depends(comun.conexion)) -> dict:
    comun.exigir_rol(sesion, ROLES)
    try:
        facturas.eliminar_equivalencia(conexion, equivalencia_id)
    except facturas.DocumentoNoEncontrado as error:
        raise _error(error)
    seguridad.auditar(conexion, sesion.nombre, "equivalencia_proveedor_eliminada", equivalencia_id, "ok")
    conexion.commit()
    return {"equivalencia_id": equivalencia_id, "eliminada": True}
