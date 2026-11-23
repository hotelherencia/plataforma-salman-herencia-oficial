"""Clientes (RUT): consulta, alta manual y corrección de la ficha. Recepción, caja y administración del hotel."""
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from .. import clientes, credito_clientes, hotel_sql, idempotencia, roles, seguridad
from . import comun
from .modelos import ClienteAltaIn, ClienteCreditoIn, ClienteEdicionIn, SalidaCreditoIn

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


@router.get("/hotel/clientes/{cliente_id}/credito")
def ver_credito_cliente(
    cliente_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Contable 2.2 (#392): política de crédito, cupo, deuda abierta y alertas del cliente."""
    comun.exigir_rol(sesion, clientes.ROLES_GESTION)
    try:
        return credito_clientes.estado_credito_cliente(conexion, sesion.empresa_id, cliente_id)
    except clientes.ClienteInexistente:
        raise HTTPException(status_code=403, detail="acceso denegado")


@router.put("/hotel/clientes/{cliente_id}/credito")
def guardar_credito_cliente(
    cliente_id: str,
    datos: ClienteCreditoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Contable 2.2 (#392): configura política, cupo y plazo de crédito (solo admin_hotel)."""
    comun.exigir_rol(sesion, credito_clientes.ROLES_EDICION_CREDITO)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "cliente_credito", "cliente_id": cliente_id, **datos.model_dump()}

    def operacion() -> tuple[int, dict]:
        try:
            res = credito_clientes.configurar_credito(
                conexion,
                sesion.empresa_id,
                cliente_id,
                politica_credito=datos.politica_credito,
                cupo_credito_clp=datos.cupo_credito_clp,
                plazo_dias=datos.plazo_dias,
                garantia_tarjeta_marca=datos.garantia_tarjeta_marca,
                garantia_tarjeta_ultimos4=datos.garantia_tarjeta_ultimos4,
                actor=sesion.nombre,
            )
        except clientes.ClienteInexistente:
            return 403, {"detail": "acceso denegado"}
        except credito_clientes.CreditoInvalido as error:
            return 422, {"detail": str(error)}
        return 200, res

    try:
        codigo, respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=respuesta)


@router.post("/hotel/reservas/{reserva_id}/salida-credito")
def registrar_salida_credito(
    request: Request,
    reserva_id: str,
    datos: SalidaCreditoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Contable 2.2 (#392 / REC-003): Salida física dejando cuenta por cobrar trazable."""
    comun.exigir_rol(sesion, credito_clientes.ROLES_SALIDA_CREDITO)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "salida_credito", "reserva_id": reserva_id, **datos.model_dump()}

    def operacion() -> tuple[int, dict]:
        try:
            res = credito_clientes.salida_con_credito(
                conexion,
                request.app.state.aplicacion.hotel,
                sesion.empresa_id,
                reserva_id,
                datos.cliente_id,
                actor=sesion.nombre,
                es_admin=roles.es_admin_hotel(sesion.rol),
                confirmar_exceso_cupo=datos.confirmar_exceso_cupo,
                nota=datos.nota,
            )
        except clientes.ClienteInexistente:
            return 403, {"detail": "acceso denegado"}
        except credito_clientes.CreditoConflicto as error:
            cuerpo_err = {"detail": str(error)}
            if error.supera_limite:
                cuerpo_err["supera_limite"] = True
                cuerpo_err["deuda_actual_clp"] = error.deuda_actual_clp
                cuerpo_err["cupo_clp"] = error.cupo_clp
            return 409, cuerpo_err
        return 201, res

    with hotel_sql.EXCLUSIVO:
        hotel_sql.bloquear(conexion)
        try:
            codigo, respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
    return JSONResponse(status_code=codigo, content=respuesta)
