"""Contabilidad fase 2.1: saldo por reserva y movimientos de la cuenta (cargos, reversos y pagos), sin depender de la caja."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from .. import cobro, imputacion, seguridad
from . import comun

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
    """Cargos, reversos y pagos del rango (días en hora de Chile) con quién los hizo. Caja y administración."""
    comun.exigir_rol(sesion, imputacion.ROLES_MOVIMIENTOS)
    if hasta < desde:
        raise HTTPException(status_code=422, detail="«hasta» no puede ser anterior a «desde»")
    if (hasta - desde).days > 366:
        raise HTTPException(status_code=422, detail="el rango máximo es de un año")
    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(),
            "movimientos": imputacion.movimientos_cuenta(conexion, sesion.empresa_id, desde, hasta)}
