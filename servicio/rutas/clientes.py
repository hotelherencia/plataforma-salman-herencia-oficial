"""Clientes (RUT): consulta, alta manual y corrección de la ficha. Recepción, caja y administración del hotel."""
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from .. import clientes, idempotencia, seguridad
from . import comun
from .modelos import ClienteAltaIn, ClienteEdicionIn

router = APIRouter()


@router.get("/hotel/clientes")
def listar_clientes(
    q: str | None = Query(default=None, max_length=80),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, clientes.ROLES_GESTION)
    return clientes.listar(conexion, q)


@router.post("/hotel/clientes", status_code=201)
def crear_cliente(
    datos: ClienteAltaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, clientes.ROLES_GESTION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = json.loads(datos.model_dump_json())

    def operacion() -> tuple[int, dict]:
        try:
            ficha = clientes.crear(
                conexion, rut=datos.rut, nombre=datos.nombre, tipo=datos.tipo, giro=datos.giro,
                direccion=datos.direccion, comuna=datos.comuna, correo=datos.correo,
                telefono=datos.telefono, activo=datos.activo, actor=sesion.nombre,
            )
        except (clientes.RutInvalido, clientes.ClienteInvalido) as error:
            return 422, {"detail": str(error)}
        except clientes.ClienteConflicto as error:
            return 409, {"detail": str(error)}
        return 201, ficha

    try:
        codigo, respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=respuesta)


@router.put("/hotel/clientes/{cliente_id}")
def editar_cliente(
    cliente_id: str,
    datos: ClienteEdicionIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, clientes.ROLES_GESTION)
    try:
        resultado = clientes.editar(
            conexion, cliente_id, rut=datos.rut, nombre=datos.nombre, tipo=datos.tipo, giro=datos.giro,
            direccion=datos.direccion, comuna=datos.comuna, correo=datos.correo, telefono=datos.telefono,
            activo=datos.activo, actor=sesion.nombre,
        )
    except clientes.ClienteInexistente:
        conexion.rollback()
        raise HTTPException(status_code=403, detail="acceso denegado")
    except (clientes.RutInvalido, clientes.ClienteInvalido) as error:
        conexion.rollback()
        raise HTTPException(status_code=422, detail=str(error))
    except clientes.ClienteConflicto as error:
        conexion.rollback()
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return resultado
