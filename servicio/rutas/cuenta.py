"""Contabilidad: saldo por reserva, libro de movimientos (reservas + directos sin habitación),
movimientos directos, cuadratura diaria (2.3), cierre mensual y matriz Ocupación (2.4)
e indicadores ejecutivos reales (2.5 / KPI-002)."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response

from .. import clientes, cobro, contabilidad, contable_avanzado, idempotencia, imputacion, productos, roles, seguridad
from . import comun
from .modelos import (
    CierreMensualIn,
    CobrarMovimientoDirectoIn,
    MovimientoDirectoIn,
    ReaperturaMesIn,
    ReversoPagoIn,
)

router = APIRouter()


@router.get("/hotel/reservas/{reserva_id}/saldo")
def saldo_de_la_reserva(
    reserva_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Total, abonado, pagado y pendiente de la reserva, con el detalle por noche. Ajena o inexistente → 403."""
    cobro._reserva_de_la_empresa(conexion, reserva_id, sesion.empresa_id)
    return imputacion.saldo_reserva(conexion, reserva_id)


@router.get("/hotel/contabilidad/movimientos")
def movimientos_de_la_cuenta(
    desde: date,
    hasta: date,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Cargos, reversos, cobros de reservas y movimientos directos sin habitación del rango (hora de Chile)."""
    comun.exigir_rol(sesion, imputacion.ROLES_MOVIMIENTOS)
    if hasta < desde:
        raise HTTPException(status_code=422, detail="«hasta» no puede ser anterior a «desde»")
    if (hasta - desde).days > 366:
        raise HTTPException(status_code=422, detail="el rango máximo es de un año")
    movs = imputacion.movimientos_cuenta(conexion, sesion.empresa_id, desde, hasta)
    return {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "movimientos": movs,
        "resumen": imputacion.resumen_movimientos_cuenta(movs),
    }


def _operar_directo(conexion, sesion, idempotency_key, cuerpo: dict, funcion, accion: str, recurso: str,
                    codigo_ok: int = 201) -> JSONResponse:
    clave = comun.clave_idempotencia_o_400(idempotency_key)

    def operacion() -> tuple[int, dict]:
        try:
            resultado = funcion()
        except contabilidad.DatosCajaInvalidos as error:
            return 422, {"detail": str(error)}
        except (contabilidad.OperacionCajaInvalida, clientes.ClienteConflicto, productos.ProductoInvalido) as error:
            seguridad.auditar(conexion, sesion.nombre, accion, recurso, "rechazado")
            return 409, {"detail": str(error)}
        except contabilidad.TurnoAjenoOInexistente as error:
            return 404, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, accion, resultado.get("movimiento_directo_id") or recurso, "ok")
        return codigo_ok, resultado

    try:
        codigo, respuesta = idempotencia.ejecutar(
            conexion, sesion.empresa_id, clave, {"accion": accion, "recurso": recurso, **cuerpo}, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=respuesta)


@router.post("/hotel/contabilidad/movimientos-directos")
def crear_movimiento_directo(
    cuerpo: MovimientoDirectoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Asienta un cargo, venta directa o egreso operacional SIN habitación ni reserva.
    Opera con caja abierta o cerrada: siempre queda registrado en la contabilidad."""
    comun.exigir_rol(sesion, contabilidad.ROLES_TURNO)
    if cuerpo.tipo == "egreso_operacional" or not cuerpo.producto_id:
        comun.exigir_rol(sesion, roles.con_admin_hotel("caja"))
    return _operar_directo(
        conexion, sesion, idempotency_key, cuerpo.model_dump(mode="json"),
        lambda: contabilidad.registrar_movimiento_directo(
            conexion, sesion.empresa_id, sesion.nombre,
            tipo=cuerpo.tipo, categoria=cuerpo.categoria, concepto=cuerpo.concepto,
            monto_clp=cuerpo.monto_clp, producto_id=cuerpo.producto_id, cantidad=cuerpo.cantidad,
            estado_cobro=cuerpo.estado_cobro, datos_pago=cuerpo.datos_pago(), nota=cuerpo.nota,
        ),
        "movimiento_directo", "contabilidad", codigo_ok=201,
    )


@router.post("/hotel/contabilidad/movimientos-directos/{movimiento_id}/cobrar")
def cobrar_movimiento_directo(
    movimiento_id: str,
    cuerpo: CobrarMovimientoDirectoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Registra el cobro (o pago) de un movimiento directo asentado previamente como pendiente."""
    comun.exigir_rol(sesion, contabilidad.ROLES_TURNO)
    return _operar_directo(
        conexion, sesion, idempotency_key, cuerpo.model_dump(mode="json"),
        lambda: contabilidad.cobrar_movimiento_directo(
            conexion, sesion.empresa_id, movimiento_id, sesion.nombre, cuerpo.datos_pago(),
        ),
        "movimiento_directo_cobro", movimiento_id, codigo_ok=200,
    )


@router.post("/hotel/contabilidad/movimientos-directos/{movimiento_id}/reverso")
def reversar_movimiento_directo(
    movimiento_id: str,
    cuerpo: ReversoPagoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Reverso inmutable de un movimiento directo (solo administración del hotel)."""
    comun.exigir_rol(sesion, contabilidad.ROLES_REVERSO)
    return _operar_directo(
        conexion, sesion, idempotency_key, cuerpo.model_dump(mode="json"),
        lambda: contabilidad.reversar_movimiento_directo(
            conexion, sesion.empresa_id, movimiento_id, cuerpo.motivo, sesion.nombre,
        ),
        "movimiento_directo_reverso", movimiento_id, codigo_ok=201,
    )


def _solo_reales(request: Request) -> bool:
    return not request.app.state.aplicacion.nucleo.empresa.es_sintetico


@router.get("/hotel/contabilidad/cuadratura-diaria")
def cuadratura_diaria_contable(
    request: Request,
    fecha: date | None = None,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Contabilidad 2.3 (#393): cuadratura diaria de ocupación, noches devengadas y abonos."""
    comun.exigir_rol(sesion, contable_avanzado.ROLES_CUADRATURA)
    dia = fecha or contabilidad.hoy_chile()
    return contable_avanzado.cuadratura_diaria(conexion, sesion.empresa_id, dia, _solo_reales(request))


@router.get("/hotel/contabilidad/cierre-mensual")
def ver_cierre_mensual(
    request: Request,
    anio: int = Query(ge=2020, le=2100),
    mes: int = Query(ge=1, le=12),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Contabilidad 2.4 (#394): cierre mensual (congelado si está cerrado) y matriz habitaciones × días."""
    comun.exigir_rol(sesion, contable_avanzado.ROLES_CUADRATURA)
    return contable_avanzado.obtener_cierre_mensual(conexion, sesion.empresa_id, anio, mes, _solo_reales(request))


@router.get("/hotel/contabilidad/cierre-mensual/exportar.csv")
def exportar_cierre_mensual_csv(
    request: Request,
    anio: int = Query(ge=2020, le=2100),
    mes: int = Query(ge=1, le=12),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> Response:
    """Contabilidad 2.4 (#394): exportación CSV matriz habitaciones × días (equivalente a Ocupación 2026)."""
    comun.exigir_rol(sesion, contable_avanzado.ROLES_CUADRATURA)
    datos = contable_avanzado.obtener_cierre_mensual(conexion, sesion.empresa_id, anio, mes, _solo_reales(request))
    contenido = contable_avanzado.exportar_matriz_mensual_csv(datos)
    nombre = f"ocupacion-{anio:04d}-{mes:02d}.csv"
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/hotel/contabilidad/cierre-mensual")
def cerrar_mes_contable(
    request: Request,
    cuerpo: CierreMensualIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Contabilidad 2.4 (#394): congela el cierre mensual y la matriz habitaciones × días."""
    comun.exigir_rol(sesion, contable_avanzado.ROLES_CUADRATURA)
    recurso = f"{cuerpo.anio:04d}-{cuerpo.mes:02d}"
    return _operar_directo(
        conexion, sesion, idempotency_key, cuerpo.model_dump(mode="json"),
        lambda: contable_avanzado.cerrar_mes(
            conexion, sesion.empresa_id, cuerpo.anio, cuerpo.mes,
            sesion.usuario_id, sesion.nombre, cuerpo.nota, cuerpo.confirmar_alertas,
            _solo_reales(request),
        ),
        "cierre_mensual", recurso, codigo_ok=201,
    )


@router.post("/hotel/contabilidad/cierre-mensual/{anio}/{mes}/reapertura")
def reabrir_mes_contable(
    anio: int,
    mes: int,
    cuerpo: ReaperturaMesIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Contabilidad 2.4 (#394): reapertura auditada de un mes cerrado (solo administración)."""
    comun.exigir_rol(sesion, contable_avanzado.ROLES_REAPERTURA_MENSUAL)
    recurso = f"{anio:04d}-{mes:02d}"
    return _operar_directo(
        conexion, sesion, idempotency_key, cuerpo.model_dump(mode="json"),
        lambda: contable_avanzado.reabrir_mes(
            conexion, sesion.empresa_id, anio, mes, sesion.nombre, cuerpo.motivo,
        ),
        "cierre_mensual_reapertura", recurso, codigo_ok=200,
    )


@router.get("/hotel/contabilidad/indicadores-ejecutivos")
def consultar_indicadores_ejecutivos(
    request: Request,
    desde: date | None = None,
    hasta: date | None = None,
    tipo: str | None = Query(default=None, max_length=50),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Contabilidad 2.5 (#395 / KPI-002): indicadores ejecutivos reales (ocupación, ADR, RevPAR).
    Solo administración del hotel; devuelve null cuando no hay muestra (nunca cero inventado)."""
    comun.exigir_rol(sesion, contable_avanzado.ROLES_EJECUTIVOS)
    hoy = contabilidad.hoy_chile()
    desde = desde or hoy.replace(day=1)
    hasta = hasta or (hoy + timedelta(days=1))
    return contable_avanzado.indicadores_ejecutivos(
        conexion, sesion.empresa_id, desde, hasta, hoy, tipo or None,
        solo_inventario_real=_solo_reales(request),
    )
