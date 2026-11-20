"""Clientes (RUT): consulta y corrección de la ficha. Recepción, caja y administración del hotel."""
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import clientes, seguridad
from . import comun
from .modelos import ClienteEdicionIn

router = APIRouter()


@router.get("/hotel/clientes")
def listar_clientes(
    q: str | None = Query(default=None, max_length=80),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, clientes.ROLES_GESTION)
    return clientes.listar(conexion, q)


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
            direccion=datos.direccion, comuna=datos.comuna, correo=datos.correo, activo=datos.activo,
            actor=sesion.nombre,
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
