"""Contabilidad: saldo por reserva, libro de movimientos (reservas + directos sin habitación) y movimientos directos."""
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

from .. import clientes, cobro, contabilidad, idempotencia, imputacion, productos, roles, seguridad
from . import comun
from .modelos import CobrarMovimientoDirectoIn, MovimientoDirectoIn, ReversoPagoIn

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
