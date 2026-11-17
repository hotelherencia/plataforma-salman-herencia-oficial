"""Rutas de las políticas del hotel (entrega 1A.3)."""
from datetime import date, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from .. import canal_publico, iva, politicas, precios, roles, seguridad
from . import comun
from .modelos import PoliticasHotelIn, SimulacionPoliticaIn

router = APIRouter()


@router.get("/publico/politicas")
def politicas_publicas(request: Request, conexion=Depends(comun.conexion)) -> dict:
    freno: canal_publico.FrenoDeSolicitudes = request.app.state.freno_solicitudes
    if not freno.permite(f"ip:{canal_publico.ip_visible(request)}", ambito="politicas"):
        raise HTTPException(
            status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
        )
    empresa_id = request.app.state.aplicacion.nucleo.empresa.id
    return politicas.vista_publica(politicas.de(conexion, empresa_id))


@router.get("/hotel/politicas")
def ver_politicas(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    documento = politicas.de(conexion, sesion.empresa_id)
    vista = politicas.vista_interna(documento)
    vista["puede_editar"] = roles.es_admin_hotel(sesion.rol)
    vista["iva"] = {"porcentaje": iva.como_texto(iva.tasa(conexion))}
    return vista


@router.put("/hotel/politicas")
def guardar_politicas(
    cuerpo: PoliticasHotelIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)

    def operacion() -> tuple[int, dict]:
        try:
            guardada = politicas.guardar(conexion, sesion.empresa_id, cuerpo.cuerpo, sesion.nombre)
        except politicas.PoliticaInvalida as error:
            return 400, {"detail": error.detalle}
        seguridad.auditar(
            conexion, sesion.nombre, "politicas_hotel", sesion.empresa_id,
            f"versión {guardada['version']}",
        )
        vista = politicas.vista_interna(guardada)
        vista["puede_editar"] = True
        vista["iva"] = {"porcentaje": iva.como_texto(iva.tasa(conexion))}
        return 200, vista

    from .. import idempotencia
    codigo, respuesta = idempotencia.ejecutar(
        conexion, sesion.empresa_id, clave, {"operacion": "politicas_hotel"}, operacion,
    )
    conexion.commit()
    return JSONResponse(status_code=codigo, content=respuesta)


@router.post("/hotel/politicas/simulacion")
def simular_cotizacion(
    cuerpo: SimulacionPoliticaIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Calculadora del mantenedor: fechas y horas → total con recargos e IVA."""
    if cuerpo.fin <= cuerpo.inicio:
        raise HTTPException(status_code=400, detail="fin debe ser mayor que inicio")
    documento = politicas.de(conexion, sesion.empresa_id)
    tasa = iva.tasa(conexion)
    extras = cuerpo.extras()
    noches = (cuerpo.fin - cuerpo.inicio).days
    if cuerpo.habitacion_id:
        cotizacion = precios.cotizar(conexion, cuerpo.habitacion_id, cuerpo.inicio, cuerpo.fin)
        if cotizacion.sin_tarifa is not None:
            raise HTTPException(status_code=409, detail="sin tarifa vigente para esas noches")
        item = {
            "habitacion_id": cuerpo.habitacion_id,
            "tarifa_noche_clp": cotizacion.tarifa_primera,
            "total_clp": cotizacion.total,
            "tipo": None,
        }
        item = politicas.enriquecer_item(item, documento["cuerpo"], extras, tasa, noches)
        return {"simulacion": item, "iva": {"porcentaje": iva.como_texto(tasa)}, "noches": noches}
    tarifa = cuerpo.precio_noche_clp
    if not tarifa:
        raise HTTPException(status_code=400, detail="indica una habitación o un precio por noche de ejemplo")
    item = politicas.enriquecer_item(
        {"habitacion_id": None, "tipo": None, "tarifa_noche_clp": tarifa, "total_clp": tarifa * noches},
        documento["cuerpo"], extras, tasa, noches,
    )
    return {"simulacion": item, "iva": {"porcentaje": iva.como_texto(tasa)}, "noches": noches}
