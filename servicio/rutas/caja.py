"""Rutas de caja y contabilidad, fase 1 (2026-11-19).

Turnos (apertura, retiros para depósito, cierre con arqueo y cuadratura),
diario de movimientos, reverso de pagos (solo administración), conciliación
diaria y cierre del día (auditoría nocturna) con reapertura auditada.
"""
import contextlib
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from .. import contabilidad, hotel_sql, idempotencia, seguridad
from . import comun
from .modelos import AperturaTurnoIn, CierreDiarioIn, CierreTurnoIn, ReaperturaDiaIn, RetiroCajaIn, ReversoPagoIn

router = APIRouter()

MAX_DIAS_CONSULTA = 92


def _solo_reales(request: Request) -> bool:
    return not request.app.state.aplicacion.nucleo.empresa.es_sintetico


def _rango(desde: date | None, hasta: date | None) -> tuple[date, date]:
    hasta = hasta or contabilidad.hoy_chile()
    desde = desde or hasta
    if desde > hasta:
        raise HTTPException(status_code=422, detail="la fecha «desde» debe ser anterior o igual a «hasta»")
    if (hasta - desde).days > MAX_DIAS_CONSULTA:
        raise HTTPException(status_code=422, detail=f"consulta como máximo {MAX_DIAS_CONSULTA} días")
    return desde, hasta


def _operar(conexion, sesion, idempotency_key, cuerpo: dict, funcion, accion: str, recurso: str,
            codigo_ok: int = 200, exclusivo: bool = False) -> JSONResponse:
    """Operación idempotente y auditada; errores de negocio en castellano."""
    clave = comun.clave_idempotencia_o_400(idempotency_key)

    def operacion() -> tuple[int, dict]:
        try:
            resultado = funcion()
        except contabilidad.DatosCajaInvalidos as error:
            return 422, {"detail": str(error)}
        except contabilidad.OperacionCajaInvalida as error:
            seguridad.auditar(conexion, sesion.nombre, accion, recurso, "rechazado")
            return 409, {"detail": str(error)}
        except contabilidad.TurnoAjenoOInexistente as error:
            return 404, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, accion, resultado.get("turno_id") or recurso, "ok")
        return codigo_ok, resultado

    # Lo que toca la cuenta de una reserva va en la sección crítica del dominio, como las rutas del hotel.
    with hotel_sql.EXCLUSIVO if exclusivo else contextlib.nullcontext():
        if exclusivo:
            hotel_sql.bloquear(conexion)
        try:
            codigo, respuesta = idempotencia.ejecutar(
                conexion, sesion.empresa_id, clave, {"accion": accion, "recurso": recurso, **cuerpo}, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
    return JSONResponse(status_code=codigo, content=respuesta)


@router.get("/hotel/caja/estado")
def estado_caja(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, contabilidad.ROLES_TURNO)
    return contabilidad.estado_caja(conexion, sesion.empresa_id)


@router.post("/hotel/caja/turnos")
def abrir_turno(
    cuerpo: AperturaTurnoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, contabilidad.ROLES_TURNO)
    return _operar(
        conexion, sesion, idempotency_key, cuerpo.model_dump(),
        lambda: contabilidad.abrir_turno(conexion, sesion.empresa_id, sesion.usuario_id, sesion.nombre,
                                         cuerpo.fondo_inicial_clp, cuerpo.nota),
        "caja_turno_apertura", "caja", codigo_ok=201,
    )


@router.get("/hotel/caja/turnos")
def listar_turnos(
    desde: date | None = None,
    hasta: date | None = None,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, contabilidad.ROLES_TURNO)
    desde, hasta = _rango(desde, hasta)
    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(),
            "turnos": contabilidad.listar_turnos(conexion, sesion.empresa_id, desde, hasta)}


@router.get("/hotel/caja/turnos/{turno_id}")
def detalle_turno(
    turno_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, contabilidad.ROLES_TURNO)
    try:
        return contabilidad.detalle_turno(conexion, sesion.empresa_id, turno_id)
    except contabilidad.TurnoAjenoOInexistente:
        raise HTTPException(status_code=404, detail="turno inexistente")


@router.post("/hotel/caja/turnos/{turno_id}/retiros")
def retiro_para_deposito(
    turno_id: str,
    cuerpo: RetiroCajaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, contabilidad.ROLES_TURNO)
    return _operar(
        conexion, sesion, idempotency_key, cuerpo.model_dump(),
        lambda: contabilidad.registrar_retiro(conexion, sesion.empresa_id, turno_id, sesion.nombre, cuerpo.monto_clp,
                                              cuerpo.comprobante, cuerpo.banco, cuerpo.nota),
        "caja_retiro_deposito", turno_id, codigo_ok=201,
    )


@router.post("/hotel/caja/turnos/{turno_id}/cierre")
def cerrar_turno(
    turno_id: str,
    cuerpo: CierreTurnoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, contabilidad.ROLES_TURNO)
    return _operar(
        conexion, sesion, idempotency_key, cuerpo.model_dump(),
        lambda: contabilidad.cerrar_turno(
            conexion, sesion.empresa_id, turno_id, sesion.usuario_id, sesion.rol, sesion.nombre, cuerpo.arqueo,
            cuerpo.declarado, cuerpo.justificacion, cuerpo.deposito.model_dump() if cuerpo.deposito else None),
        "caja_turno_cierre", turno_id,
    )


@router.get("/hotel/caja/movimientos")
def diario_movimientos(
    desde: date | None = None,
    hasta: date | None = None,
    medio: str | None = Query(default=None, pattern="^(efectivo|debito|credito|transferencia|no_informado)$"),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, contabilidad.ROLES_TURNO)
    desde, hasta = _rango(desde, hasta)
    filas = contabilidad.movimientos(conexion, sesion.empresa_id, desde, hasta, medio=medio)
    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "movimientos": filas,
            "total_clp": sum(f["monto_clp"] for f in filas)}


@router.post("/hotel/reservas/{reserva_id}/pagos/{pago_id}/reverso")
def reversar_pago(
    request: Request,
    reserva_id: str,
    pago_id: str,
    cuerpo: ReversoPagoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, contabilidad.ROLES_REVERSO)
    return _operar(
        conexion, sesion, idempotency_key, cuerpo.model_dump(),
        lambda: contabilidad.reversar_pago(conexion, request.app.state.aplicacion.hotel, sesion.empresa_id,
                                           reserva_id, pago_id, cuerpo.motivo, sesion.nombre),
        "pago_reverso", pago_id, codigo_ok=201, exclusivo=True,
    )


@router.get("/hotel/caja/conciliacion")
def conciliacion_diaria(
    request: Request,
    fecha: date | None = None,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Día abierto: conciliación en vivo. Día cerrado: la congelada al cerrar."""
    comun.exigir_rol(sesion, contabilidad.ROLES_CIERRE_DIARIO)
    fecha = fecha or contabilidad.hoy_chile()
    guardado = contabilidad.cierre_guardado(conexion, sesion.empresa_id, fecha)
    if guardado and guardado["cierre"]["estado"] == "cerrado":
        return {**guardado, "congelada": True}
    vivo = contabilidad.conciliacion_diaria(conexion, sesion.empresa_id, fecha, _solo_reales(request))
    return {**vivo, "congelada": False}


@router.get("/hotel/caja/cierres")
def listar_cierres(
    desde: date | None = None,
    hasta: date | None = None,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, contabilidad.ROLES_CIERRE_DIARIO)
    hasta = hasta or contabilidad.hoy_chile()
    desde, hasta = _rango(desde or hasta - timedelta(days=30), hasta)
    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(),
            "fecha_contable": contabilidad.fecha_contable_actual(conexion, sesion.empresa_id).isoformat(),
            "cierres": contabilidad.listar_cierres(conexion, sesion.empresa_id, desde, hasta)}


@router.post("/hotel/caja/cierres")
def cerrar_dia(
    request: Request,
    cuerpo: CierreDiarioIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, contabilidad.ROLES_CIERRE_DIARIO)
    return _operar(
        conexion, sesion, idempotency_key, {**cuerpo.model_dump(mode="json")},
        lambda: contabilidad.cerrar_dia(conexion, sesion.empresa_id, cuerpo.fecha, sesion.usuario_id, sesion.nombre,
                                        cuerpo.nota, cuerpo.confirmar_alertas, _solo_reales(request)),
        "cierre_diario", cuerpo.fecha.isoformat(), codigo_ok=201,
    )


@router.post("/hotel/caja/cierres/{fecha}/reapertura")
def reabrir_dia(
    fecha: date,
    cuerpo: ReaperturaDiaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, contabilidad.ROLES_REAPERTURA)
    return _operar(
        conexion, sesion, idempotency_key, cuerpo.model_dump(),
        lambda: contabilidad.reabrir_dia(conexion, sesion.empresa_id, fecha, sesion.nombre, cuerpo.motivo),
        "cierre_diario_reapertura", fecha.isoformat(),
    )
