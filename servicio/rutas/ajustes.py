"""Ajustes operativos desde Configuración (#348)."""
from fastapi import APIRouter, Body, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

from .. import ajustes, idempotencia, seguridad
from . import comun

router = APIRouter()


@router.get("/hotel/ajustes")
def leer_ajustes(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_admin_hotel(sesion)
    return {"ajustes": ajustes.todos(conexion, sesion.empresa_id)}


@router.put("/hotel/ajustes/{clave_ajuste}")
def guardar_ajuste(
    clave_ajuste: str,
    valor: dict = Body(...),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)

    def operacion() -> tuple[int, dict]:
        try:
            guardado = ajustes.guardar(conexion, sesion.empresa_id, clave_ajuste, valor, sesion.nombre)
        except ajustes.AjusteInvalido as error:
            return 422, {"detail": error.detalle}
        seguridad.auditar(conexion, sesion.nombre, "ajuste", clave_ajuste, "actualizado")
        return 200, {"clave": clave_ajuste, "valor": guardado}

    try:
        codigo, cuerpo = idempotencia.ejecutar(
            conexion, sesion.empresa_id, clave, {"clave": clave_ajuste, "valor": valor}, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo)
