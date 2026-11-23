"""Rutas de la operación del hotel (ARC-A01, #334; extraídas de aplicacion.py).

Operación de habitaciones (los precios viven en hotel_tipos), oferta, reservas, cobro, estadía, caja,
búsqueda, ocupación, indicadores, solicitudes públicas (bandeja) y leads
(bandeja y gestión). Comportamiento idéntico al de las closures originales.
"""
import hashlib
import json
import logging
import os
from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, HTTPException, Path as RutaParam, Query, Request, Response
from fastapi.responses import JSONResponse

from .. import roles
from .. import avisos
from .. import busqueda_estadias
from .. import canal_publico
from .. import clientes
from .. import cobro
from .. import contabilidad
from .. import documental
from .. import hotel_sql
from .. import huespedes as huespedes_db
from .. import idempotencia
from .. import inventario_documental
from .. import leads as leads_mod
from .. import observabilidad
from .. import operacion
from .. import politicas
from .. import tipos_habitacion, recaptcha
from .. import panel
from .. import productos as productos_db
from .. import reservas as reservas_db
from .. import seguridad
from . import comun
from .modelos import (
    CargoIn, DevolucionSaldoIn, DocumentoHuespedIn, GestionLeadIn, HabitacionIn, HuespedEdicionIn, LeadEdicionIn,
    LeadPublicoIn, LeadVinculoIn, MantenimientoIn, SolicitudEdicionIn,
    ObservacionIn, OcupacionIn, PagoIn, PATRON_ID_HABITACION, ReasignacionIn, ReservaHuespedEdicionIn, ReservaHuespedIn, VerificacionAseoIn, RechazoSolicitudIn, ReservaIn, ReversoCargoIn, ServicioIn,
    SolicitudPublicaIn,
)

# Documento del huésped: recepción y administración del hotel (no plataforma).
ROLES_DOCUMENTO_HUESPED = roles.con_admin_hotel("recepcion")

router = APIRouter()


def _ejecutar_exclusivo(conexion, empresa_id, clave, cuerpo, operacion) -> JSONResponse:
    """Operación idempotente del hotel: recarga, decide y persiste dentro de la sección crítica del
    dominio (singleton en memoria), que se mantiene hasta el commit."""
    with hotel_sql.EXCLUSIVO:
        hotel_sql.bloquear(conexion)  # entre procesos: la segunda instancia espera y recarga lo ya confirmado
        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

@router.put("/hotel/habitaciones/{habitacion_id}")
def definir_habitacion(
    request: Request,
    habitacion: HabitacionIn,
    habitacion_id: str = RutaParam(pattern=PATRON_ID_HABITACION),
    idempotency_key: str | None = Header(default=None),
    if_none_match: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Alta o edición (spec-hotel-operacion-v1 §2.2–2.3). Con
    `If-None-Match: *` solo crea: una habitación existente responde 409."""
    comun.exigir_admin_hotel(sesion)
    # Titular: no se pueden crear/editar ids fuera de HAB-01..17, salvo las
    # unidades que la administración dio de alta por lote (entrega 1A).
    if (
        not request.app.state.aplicacion.nucleo.empresa.es_sintetico
        and not inventario_documental.es_id_inventario_real(habitacion_id)
        and not reservas_db.en_inventario(conexion, habitacion_id)
    ):
        raise HTTPException(
            status_code=422,
            detail="solo HAB-01..17 y las habitaciones dadas de alta por lote forman el inventario real del titular",
        )
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    solo_crear = (if_none_match or "").strip() == "*"
    cuerpo = {"habitacion_id": habitacion_id, "solo_crear": solo_crear, **json.loads(habitacion.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            guardada = reservas_db.guardar_habitacion(
                conexion, habitacion_id, habitacion.tipo, habitacion.capacidad, solo_crear
            )
        except reservas_db.HabitacionYaExiste as error:
            return 409, {"detail": str(error)}
        # El dominio ve la unidad nueva o editada sin esperar a la próxima operación (ADP-3).
        hotel_sql.recargar(conexion, request.app.state.aplicacion.hotel, sesion.empresa_id)
        if guardada["creada"]:
            resultado = f"creada tipo={habitacion.tipo} capacidad={habitacion.capacidad}"
        elif guardada["cambios"]:
            resultado = "editada " + "; ".join(
                f"{campo}: {antes}→{despues}" for campo, (antes, despues) in guardada["cambios"].items()
            )
        else:
            resultado = "sin cambios"
        seguridad.auditar(conexion, sesion.nombre, "habitacion", habitacion_id, resultado)
        return 200, {
            "habitacion_id": habitacion_id,
            "tipo": habitacion.tipo,
            "capacidad": habitacion.capacidad,
            **guardada,
        }

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)

def _extras_consulta(hora_llegada, hora_salida, cama_adicional, ninos, mascotas) -> dict | None:
    extras = {}
    if hora_llegada:
        extras["hora_llegada"] = hora_llegada
    if hora_salida:
        extras["hora_salida"] = hora_salida
    if cama_adicional:
        extras["cama_adicional"] = True
    if ninos:
        extras["ninos"] = ninos
    if mascotas:
        extras["mascotas"] = True
    return extras or None


@router.get("/hotel/oferta")
def consultar_oferta(
    inicio: date,
    fin: date,
    personas: int = Query(gt=0, le=30),
    hora_llegada: str | None = Query(default=None, pattern=r"^\d{1,2}:\d{2}$"),
    hora_salida: str | None = Query(default=None, pattern=r"^\d{1,2}:\d{2}$"),
    cama_adicional: bool = Query(default=False),
    ninos: int | None = Query(default=None, ge=1, le=30),
    mascotas: bool = Query(default=False),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    if fin <= inicio:
        raise HTTPException(status_code=400, detail="fin debe ser mayor que inicio")
    try:
        return reservas_db.oferta(
            conexion, inicio, fin, personas, datetime.now(),
            empresa_id=sesion.empresa_id,
            extras=_extras_consulta(hora_llegada, hora_salida, cama_adicional, ninos, mascotas),
        )
    except politicas.PoliticaInvalida as error:
        raise HTTPException(status_code=400, detail=error.detalle) from error

@router.get("/hotel/habitaciones")
def listar_habitaciones(
    request: Request,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Inventario operativo (spec-api-v1, 2026-11-03): estado, preparación,
    mantenimiento y tareas pendientes por unidad. Lectura para cualquier
    rol de la sesión; las mutaciones conservan sus reglas de rol.
    En titular solo HAB-01..17 (inventario documental 2026-11-11)."""
    habitaciones = reservas_db.listar_habitaciones(conexion)
    if not request.app.state.aplicacion.nucleo.empresa.es_sintetico:
        habitaciones = [h for h in habitaciones if inventario_documental.es_inventario_operativo(h)]
    return {"habitaciones": habitaciones}

@router.get("/hotel/habitaciones/{habitacion_id}")
def ficha_habitacion(
    habitacion_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Ficha (spec-hotel-operacion-v1 §2.6): cualquier rol; la auditoría
    solo para administrador y el documento según ROLES_DOCUMENTO."""
    return reservas_db.ficha_habitacion(
        conexion,
        habitacion_id,
        sesion.empresa_id,
        ver_documento=sesion.rol in ROLES_DOCUMENTO_HUESPED,
        ver_auditoria=roles.exige_doble_factor(sesion.rol),
    )

@router.post("/hotel/habitaciones/{habitacion_id}/servicio")
def fijar_servicio_habitacion(
    habitacion_id: str,
    cuerpo_servicio: ServicioIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Baja lógica y reincorporación (spec-hotel-operacion-v1 §2.4)."""
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    motivo = (cuerpo_servicio.motivo or "").strip() or None
    if not cuerpo_servicio.en_servicio and (motivo is None or len(motivo) < 3):
        raise HTTPException(status_code=422, detail="retirar de operación exige un motivo (3 a 200 caracteres)")
    cuerpo = {"habitacion_id": habitacion_id, **json.loads(cuerpo_servicio.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = reservas_db.fijar_servicio(conexion, habitacion_id, cuerpo_servicio.en_servicio, motivo)
        except reservas_db.HabitacionInexistente as error:
            raise seguridad.ErrorPermiso(str(error)) from error
        except reservas_db.ReservasVigentes as error:
            return 409, {"detail": str(error), "reservas_vigentes": error.reservas}
        if not resultado["cambio"]:
            texto = "sin cambios"
        elif cuerpo_servicio.en_servicio:
            texto = "reincorporada"
        else:
            texto = f"retirada: {motivo}"
        seguridad.auditar(conexion, sesion.nombre, "habitacion-servicio", habitacion_id, texto)
        return 200, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)

@router.get("/hotel/ocupacion")
def consultar_ocupacion(
    request: Request,
    desde: date | None = None,
    hasta: date | None = None,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Estado por habitación y noche (spec-hotel-operacion-v1 §5); por
    defecto las 14 noches desde hoy (fecha del servidor).
    En titular solo HAB-01..17."""
    hoy = date.today()
    desde = desde or hoy
    hasta = hasta or desde + timedelta(days=14)
    solo_reales = not request.app.state.aplicacion.nucleo.empresa.es_sintetico
    return panel.ocupacion(
        conexion, sesion.empresa_id, desde, hasta, hoy, solo_inventario_real=solo_reales
    )


@router.get("/hotel/documental/resumen")
def documental_resumen(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Paquete documental cargado (ZIP 2026-11-11). No es oferta ni cobro."""
    return documental.resumen(conexion)


@router.get("/hotel/documental/habitaciones")
def documental_habitaciones(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    return {"habitaciones": documental.listar_habitaciones(conexion)}


@router.get("/hotel/documental/tarifas")
def documental_tarifas(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    return {"tarifas": documental.listar_tarifas(conexion), "publicar_activas": False}


@router.get("/hotel/documental/ocupacion")
def documental_ocupacion(
    periodo: str | None = Query(default=None, pattern=r"^2026-(0[1-9]|1[0-2])$"),
    habitacion_id: str | None = Query(default=None, max_length=50),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Histórico reportado del ZIP. `es_kpi` siempre false hasta unidad confirmada."""
    return {
        "ocupacion": documental.listar_ocupacion(conexion, periodo=periodo, habitacion_id=habitacion_id),
        "es_kpi": False,
    }


@router.get("/hotel/documental/control-ocupacion")
def documental_control_ocupacion(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    return {"control": documental.listar_control_ocupacion(conexion), "es_kpi": False}


@router.get("/hotel/documental/ocupacion/serie")
def documental_ocupacion_serie(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Serie mensual del ZIP (ciencia de datos documental, no KPI operativo)."""
    return documental.serie_ocupacion_mensual(conexion)


@router.get("/hotel/documental/tablas/{tabla}")
def documental_tabla(
    tabla: str,
    limite: int = Query(default=500, ge=1, le=2000),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    try:
        return documental.listar_tabla(conexion, tabla, limite=limite)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get("/hotel/indicadores")
def consultar_indicadores(
    request: Request,
    desde: date | None = None,
    hasta: date | None = None,
    tipo: str | None = Query(default=None, max_length=50),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Panel operativo (spec-hotel-operacion-v1 §4); por defecto los próximos 7 días desde hoy (vista semanal).
    D-ROL-01 RATIFICADA 2026-11-06 (#297 opción a): el indicador financiero
    `ingresos_periodo_clp` solo lo recibe el administrador."""
    hoy = date.today()
    desde = desde or hoy
    hasta = hasta or desde + timedelta(days=7)
    solo_reales = not request.app.state.aplicacion.nucleo.empresa.es_sintetico
    resultado = panel.indicadores(
        conexion,
        sesion.empresa_id,
        desde,
        hasta,
        hoy,
        tipo or None,
        incluir_financiero=roles.es_admin_hotel(sesion.rol),
        solo_inventario_real=solo_reales,
    )
    # #417: «Lo que necesita atención», cruzando áreas, con enlace al registro de origen.
    resultado["atencion"] = operacion.atencion(
        conexion, hoy, productos_db.reporte_reposicion(conexion, solo_alertas=True))
    return resultado

@router.post("/hotel/reservas")
def confirmar_reserva(
    reserva: ReservaIn,
    response: Response,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="falta la cabecera Idempotency-Key")
    if reserva.fin <= reserva.inicio:
        raise HTTPException(status_code=400, detail="fin debe ser mayor que inicio")
    if reserva.upgrade_a_single and sesion.rol not in (roles.RECEPCION, *roles.ROLES_ADMIN_HOTEL):
        raise HTTPException(status_code=403, detail="acceso denegado")
    cuerpo = json.loads(reserva.model_dump_json())

    def operacion() -> tuple[int, dict]:
        try:
            creada = reservas_db.crear_reserva(
                conexion,
                empresa_id=sesion.empresa_id,
                habitacion_id=reserva.habitacion_id,
                inicio=reserva.inicio,
                fin=reserva.fin,
                huesped_nombre=reserva.huesped.nombre,
                huesped_documento=reserva.huesped.documento,
                huesped_documento_tipo=reserva.huesped.documento_tipo,
                personas=reserva.personas,
                canal=reserva.canal,
                extras=_extras_consulta(
                    reserva.hora_llegada, reserva.hora_salida,
                    reserva.cama_adicional, reserva.ninos, reserva.mascotas,
                ),
                upgrade_a_single=reserva.upgrade_a_single,
            )
        except reservas_db.SinCupo as error:
            return 409, {"detail": str(error)}
        except (reservas_db.SinTarifaVigente, reservas_db.HabitacionNoVendible,
                clientes.ClienteConflicto) as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "reserva", creada["reserva_id"], "confirmada")
        return 201, creada

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, idempotency_key, cuerpo, operacion)

@router.post("/hotel/reservas/{reserva_id}/pagos")
def registrar_pago(
    request: Request,
    reserva_id: str,
    pago: PagoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"reserva_id": reserva_id, **json.loads(pago.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        if pago.modo == "pasarela":
            return 503, {"detail": "pasarela no configurada", "estado": "pendiente"}
        comun.exigir_rol(sesion, cobro.ROLES_PAGO_MANUAL)
        try:
            registrado = cobro.registrar_pago_manual(
                conexion, request.app.state.aplicacion.nucleo, request.app.state.aplicacion.hotel, sesion.empresa_id, reserva_id, pago.monto_clp, pago.clave,
                confirmar_exceso=pago.confirmar_exceso, datos=pago.datos_contables(), actor=sesion.nombre,
            )
        except contabilidad.DatosCajaInvalidos as error:
            return 422, {"detail": str(error)}
        except (contabilidad.OperacionCajaInvalida, clientes.ClienteConflicto) as error:
            return 409, {"detail": str(error)}
        except cobro.PagoEnExceso as error:
            return 409, {"detail": str(error), "saldo_clp": error.saldo_clp, "exceso_clp": error.exceso_clp}
        except cobro.PagoRechazadoPorNucleo as error:
            seguridad.auditar(conexion, sesion.nombre, "pago", f"{reserva_id}:{pago.clave}", "rechazado-nucleo")
            return 403, {"detail": str(error)}
        except cobro.PagoDuplicadoConDatosDistintos as error:
            seguridad.auditar(conexion, sesion.nombre, "pago", f"{reserva_id}:{pago.clave}", "conflicto-clave-cobro")
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "pago", f"{reserva_id}:{pago.clave}", "confirmado")
        return 201, registrado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)


@router.post("/hotel/reservas/{reserva_id}/devolucion")
def devolver_saldo_reserva(
    request: Request,
    reserva_id: str,
    datos: DevolucionSaldoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Devolución formal de saldo a favor del huésped (#91 / Q-HOT-04)."""
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "devolucion_saldo", "reserva_id": reserva_id, **json.loads(datos.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = contabilidad.devolver_saldo_a_favor(
                conexion, request.app.state.aplicacion.hotel, sesion.empresa_id,
                reserva_id, datos.monto_clp, datos.medio, datos.motivo, sesion.nombre,
            )
        except contabilidad.TurnoAjenoOInexistente as error:
            raise seguridad.ErrorPermiso(str(error)) from error
        except contabilidad.DatosCajaInvalidos as error:
            return 422, {"detail": str(error)}
        except contabilidad.OperacionCajaInvalida as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "devolucion_saldo", reserva_id, f"{datos.monto_clp}:{datos.medio}")
        return 201, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)

@router.get("/hotel/caja")
def ver_caja(
    fecha: date,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, cobro.ROLES_CAJA)
    return cobro.caja_del_dia(conexion, sesion.empresa_id, fecha)

@router.post("/hotel/reservas/{reserva_id}/entrada")
def check_in(
    request: Request,
    reserva_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
    cuerpo: DocumentoHuespedIn | None = Body(default=None),
) -> JSONResponse:
    # D-ROL-ENT (DECISIÓN 2026-11-06, #304 opción a): la entrada la registran
    # recepción o administrador («caja cobra, recepción opera la habitación»).
    comun.exigir_rol(sesion, roles.con_admin_hotel("recepcion"))
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo_idem = {
        "operacion": "entrada",
        "reserva_id": reserva_id,
        "documento": cuerpo.documento if cuerpo else None,
        "documento_tipo": cuerpo.documento_tipo if cuerpo else None,
        "habitacion_id": cuerpo.habitacion_id if cuerpo else None,
        "personas": cuerpo.personas if cuerpo else None,
    }

    def operacion() -> tuple[int, dict]:
        try:
            ingreso = hotel_sql.entrada(conexion, request.app.state.aplicacion.hotel, sesion.empresa_id, reserva_id,
                                        cuerpo.documento if cuerpo else None, hotel_sql.ahora(),
                                        documento_tipo=cuerpo.documento_tipo if cuerpo else None,
                                        habitacion_id=cuerpo.habitacion_id if cuerpo else None,
                                        personas=cuerpo.personas if cuerpo else None,
                                        actor=sesion.nombre)
        except (cobro.HabitacionNoLista, cobro.TransicionInvalida, cobro.ReasignacionInvalida) as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "entrada", reserva_id, "en_estadia")
        return 200, ingreso

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo_idem, operacion)

@router.post("/hotel/reservas/{reserva_id}/habitacion")
def reasignar_habitacion(
    request: Request,
    reserva_id: str,
    reasignacion: ReasignacionIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """#361: mover al huésped a otra habitación (antes de llegar o en estadía)."""
    comun.exigir_rol(sesion, cobro.ROLES_REASIGNACION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "reasignacion", "reserva_id": reserva_id, **json.loads(reasignacion.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            hecho = hotel_sql.reasignar(conexion, request.app.state.aplicacion.hotel, sesion.empresa_id, reserva_id,
                                        reasignacion.habitacion_id, reasignacion.motivo, sesion.nombre)
        except (cobro.TransicionInvalida, cobro.ReasignacionInvalida) as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "reasignacion", reserva_id,
                          f"{hecho['desde_habitacion_id']}->{hecho['hacia_habitacion_id']}")
        return 200, hecho

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)

@router.get("/hotel/aseo")
def ver_aseo(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """#362: habitaciones por limpiar y estado de cada una (rol aseo incluido)."""
    comun.exigir_rol(sesion, cobro.ROLES_VISTA_ASEO)
    return cobro.vista_aseo(conexion, date.today())


def _operacion_aseo(conexion, sesion, idempotency_key, cuerpo, funcion, accion, recurso) -> JSONResponse:
    clave = comun.clave_idempotencia_o_400(idempotency_key)

    def operacion() -> tuple[int, dict]:
        try:
            resultado = funcion()
        except cobro.RecursoAjenoOInexistente as error:
            raise seguridad.ErrorPermiso(str(error)) from error
        except cobro.OperacionAseoInvalida as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, accion, recurso, "ok")
        return 200, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)


@router.post("/hotel/limpiezas/{tarea_id}/verificacion")
def verificar_limpieza(
    tarea_id: str,
    verificacion: VerificacionAseoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """#363: la administración verifica (o rechaza con observación) una limpieza."""
    comun.exigir_rol(sesion, cobro.ROLES_VERIFICACION_ASEO)
    cuerpo = {"operacion": "verificacion", "tarea_id": tarea_id, **json.loads(verificacion.model_dump_json())}
    return _operacion_aseo(
        conexion, sesion, idempotency_key, cuerpo,
        lambda: cobro.verificar_limpieza(conexion, tarea_id, verificacion.aprobada, verificacion.observacion, sesion.nombre),
        "limpieza_verificacion", tarea_id,
    )


@router.post("/hotel/habitaciones/{habitacion_id}/observaciones")
def observar_habitacion(
    habitacion_id: str,
    observacion: ObservacionIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """#363: nota para el personal de aseo en una habitación."""
    comun.exigir_rol(sesion, cobro.ROLES_OBSERVACION)
    cuerpo = {"operacion": "observacion", "habitacion_id": habitacion_id, "texto": observacion.texto}
    return _operacion_aseo(
        conexion, sesion, idempotency_key, cuerpo,
        lambda: cobro.agregar_observacion(conexion, habitacion_id, observacion.texto, sesion.nombre),
        "observacion_aseo", habitacion_id,
    )


@router.post("/hotel/habitaciones/{habitacion_id}/observaciones/{observacion_id}/atendida")
def atender_observacion(
    habitacion_id: str,
    observacion_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, cobro.ROLES_VISTA_ASEO)
    cuerpo = {"operacion": "observacion_atendida", "habitacion_id": habitacion_id, "observacion_id": observacion_id}
    return _operacion_aseo(
        conexion, sesion, idempotency_key, cuerpo,
        lambda: cobro.atender_observacion(conexion, habitacion_id, observacion_id, sesion.nombre),
        "observacion_atendida", observacion_id,
    )


@router.post("/hotel/reservas/{reserva_id}/salida")
def check_out(
    request: Request,
    reserva_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    # D-ROL-ENT (DECISIÓN 2026-11-06, #304 opción a): la salida la registran
    # recepción o administrador, igual que la entrada.
    comun.exigir_rol(sesion, roles.con_admin_hotel("recepcion"))
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "salida", "reserva_id": reserva_id}

    def operacion() -> tuple[int, dict]:
        try:
            liquidada = hotel_sql.salida(conexion, request.app.state.aplicacion.hotel, sesion.empresa_id, reserva_id, hotel_sql.ahora())
        except (cobro.SaldoPendiente, cobro.TransicionInvalida) as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "salida", reserva_id, "liquidada")
        return 200, liquidada

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)

# --- Maduración de la operación (spec-api-v1, 2026-10-30) ---

@router.get("/hotel/reservas")
def buscar_reservas_hotel(
    fecha: date | None = None,
    estado: str | None = None,
    texto: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    habitacion_id: str | None = Query(default=None, max_length=50),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    if estado is not None and estado not in reservas_db.ESTADOS_VALIDOS:
        raise HTTPException(status_code=422, detail="estado inválido")
    if desde is not None and hasta is not None and hasta <= desde:
        raise HTTPException(status_code=422, detail="hasta debe ser mayor que desde")
    items = reservas_db.buscar_reservas(
        conexion,
        empresa_id=sesion.empresa_id,
        fecha=fecha,
        estado=estado,
        texto=texto,
        ver_documento=sesion.rol in ROLES_DOCUMENTO_HUESPED,
        desde=desde,
        hasta=hasta,
        habitacion_id=habitacion_id or None,
    )
    return {"reservas": items, "total": len(items)}

@router.get("/hotel/reservas/{reserva_id}")
def detalle_reserva_hotel(
    request: Request,
    reserva_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Detalle con cuenta (spec-hotel-operacion-v1 §3.2); ajena → 403."""
    return cobro.detalle_reserva(
        conexion, request.app.state.aplicacion.hotel, sesion.empresa_id, reserva_id, ver_documento=sesion.rol in ROLES_DOCUMENTO_HUESPED
    )

@router.post("/hotel/habitaciones/{habitacion_id}/limpieza")
def completar_limpieza_habitacion(
    request: Request,
    habitacion_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, cobro.ROLES_LIMPIEZA)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"habitacion_id": habitacion_id, "operacion": "limpieza"}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = hotel_sql.completar_limpieza(conexion, request.app.state.aplicacion.hotel, sesion.empresa_id, habitacion_id, actor=sesion.nombre)
        except cobro.RecursoAjenoOInexistente as error:
            raise seguridad.ErrorPermiso(str(error)) from error
        except cobro.TransicionInvalida as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "limpieza", habitacion_id, "completada")
        return 200, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)

@router.post("/hotel/habitaciones/{habitacion_id}/mantenimiento")
def fijar_mantenimiento_habitacion(
    request: Request,
    habitacion_id: str,
    cuerpo_mantenimiento: MantenimientoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, cobro.ROLES_MANTENIMIENTO)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"habitacion_id": habitacion_id, **json.loads(cuerpo_mantenimiento.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = hotel_sql.fijar_mantenimiento(conexion, request.app.state.aplicacion.hotel, sesion.empresa_id, habitacion_id,
                                                      cuerpo_mantenimiento.abierto, cuerpo_mantenimiento.desde,
                                                      cuerpo_mantenimiento.hasta)
        except cobro.RecursoAjenoOInexistente as error:
            raise seguridad.ErrorPermiso(str(error)) from error
        seguridad.auditar(
            conexion, sesion.nombre, "mantenimiento", habitacion_id,
            "abierto" if cuerpo_mantenimiento.abierto else "cerrado",
        )
        return 200, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)

@router.post("/hotel/reservas/{reserva_id}/cancelacion")
def cancelar_reserva(
    request: Request,
    reserva_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, cobro.ROLES_CANCELACION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"reserva_id": reserva_id, "operacion": "cancelacion"}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = hotel_sql.cancelar(conexion, request.app.state.aplicacion.hotel, sesion.empresa_id, reserva_id, hotel_sql.ahora())
        except cobro.TransicionInvalida as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "cancelacion", reserva_id, "cancelada")
        return 200, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)

@router.post("/hotel/reservas/{reserva_id}/cargos")
def asentar_cargo_reserva(
    request: Request,
    reserva_id: str,
    cargo: CargoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, cobro.ROLES_CARGO)
    # #357 (criterio 5): el concepto libre queda para la administración del hotel;
    # recepción y caja asientan productos del catálogo.
    if not cargo.producto_id:
        comun.exigir_rol(sesion, cobro.ROLES_CONCEPTO_LIBRE)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    datos = cargo.model_dump(mode="json", exclude_none=True)
    if not cargo.producto_id:
        datos.pop("cantidad", None)  # mismo cuerpo idempotente que antes de #357
    cuerpo = {"reserva_id": reserva_id, **datos}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = hotel_sql.asentar_cargo(
                conexion, request.app.state.aplicacion.hotel, sesion.empresa_id, reserva_id, cargo.concepto, cargo.monto_clp,
                producto_id=cargo.producto_id, cantidad=cargo.cantidad, actor=sesion.nombre,
            )
        except (cobro.TransicionInvalida, productos_db.ProductoInvalido) as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "cargo", f"{reserva_id}:{resultado['cargo_id']}", "asentado")
        return 201, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)

@router.post("/hotel/reservas/{reserva_id}/cargos/{cargo_id}/reverso")
def reversar_cargo_reserva(
    request: Request,
    reserva_id: str,
    cargo_id: str,
    cuerpo_reverso: ReversoCargoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """#359: reverso contable de un cargo (solo administración del hotel)."""
    comun.exigir_rol(sesion, cobro.ROLES_REVERSO)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"reserva_id": reserva_id, "cargo_id": cargo_id, "motivo": cuerpo_reverso.motivo}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = hotel_sql.reversar_cargo(conexion, request.app.state.aplicacion.hotel, sesion.empresa_id, reserva_id, cargo_id,
                                                cuerpo_reverso.motivo, actor=sesion.nombre)
        except (cobro.TransicionInvalida, cobro.CargoNoReversable) as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "cargo_reverso", f"{reserva_id}:{cargo_id}", resultado["cargo_id"])
        return 201, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)

# --- Canal público (spec-api-v1 «Canal público», V1-ISSUE-22/24) ---
def _clave_publica(idempotency_key: str | None) -> str:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(status_code=422, detail="falta la cabecera Idempotency-Key")
    clave = idempotency_key.strip()
    if len(clave) > 128:
        raise HTTPException(status_code=422, detail="Idempotency-Key demasiado larga")
    return clave


def _solo_parametros(request: Request, permitidos: frozenset[str]) -> None:
    if any(clave not in permitidos for clave in request.query_params.keys()):
        raise HTTPException(status_code=422, detail="parámetro no permitido")


def _fecha_iso(valor: str) -> date:
    if len(valor) != 10 or valor[4] != "-" or valor[7] != "-":
        raise HTTPException(status_code=422, detail="fecha inválida")
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise HTTPException(status_code=422, detail="fecha inválida")


MENSAJE_CANAL_NO_DISPONIBLE = (
    "No pudimos recibir tu solicitud en este momento. Escríbenos por WhatsApp al "
    "+56 9 5649 1501 o inténtalo de nuevo más tarde."
)


MENSAJE_CAPTCHA_RECHAZADO = (
    "No pudimos verificar el envío. Recarga la página e inténtalo de nuevo; si "
    "persiste, escríbenos por WhatsApp al +56 9 5649 1501."
)


def _exigir_captcha(request: Request, accion: str, ip: str) -> None:
    """Exige reCAPTCHA en el canal público.

    Sin `RECAPTCHA_SECRET_KEY`: en desarrollo/suite se omite (compatibilidad
    de tests). En producción (`COOKIE_SEGURA=1`) o con
    `RECAPTCHA_OBLIGATORIO=1` se falla cerrado (503) para no aceptar leads
    sin verificación — remediación CE-HH-2026-001 / C-HH-003.
    """
    config = getattr(request.app.state, "configuracion", None)
    secreto = getattr(config, "recaptcha_secret_key", None) if config else None
    if not secreto:
        obligar = bool(getattr(config, "cookie_segura", False)) if config else False
        if os.environ.get("RECAPTCHA_OBLIGATORIO", "0") == "1":
            obligar = True
        if obligar:
            # Falta RECAPTCHA_SECRET_KEY en el entorno que ejecuta el servicio
            # (Railway). Se registra la causa para el operador; el visitante
            # recibe un mensaje útil, sin detalles de configuración.
            observabilidad.evento_seguridad(
                "recaptcha_sin_configurar", nivel=logging.ERROR, accion=accion,
                causa="falta RECAPTCHA_SECRET_KEY con COOKIE_SEGURA=1 o RECAPTCHA_OBLIGATORIO=1",
            )
            raise HTTPException(status_code=503, detail=MENSAJE_CANAL_NO_DISPONIBLE)
        return
    verificador = getattr(request.app.state, "verificar_recaptcha", recaptcha.verificar)
    try:
        verificador(request.headers.get("x-recaptcha-token"), secreto, accion, ip)
    except recaptcha.CaptchaRechazado:
        raise HTTPException(status_code=403, detail=MENSAJE_CAPTCHA_RECHAZADO)


def _es_reintento(conexion, registrada, empresa_id: str, clave: str, accion: str) -> bool:
    """Reintento idempotente: si la clave ya quedó guardada, el envío no crea
    nada nuevo (misma clave y cuerpo → el original con 200; otro cuerpo → 409),
    así que no se vuelve a exigir reCAPTCHA. Sin esto, cuando el primer intento
    sí se guardó pero la respuesta se perdió (Railway desplegando, timeout del
    proxy), el reintento llegaba con el token ya gastado ante Google
    (timeout-or-duplicate) y el huésped veía un 403 aunque su consulta existía."""
    if not registrada(conexion, empresa_id, clave):
        return False
    observabilidad.evento_seguridad("reintento_idempotente", nivel=logging.INFO, accion=accion)
    return True


@router.get("/publico/tarifas")
def listar_tarifas_publicas(
    request: Request,
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Tarifas base públicas vigentes por tipo de habitación (CLP, IVA incluido).
    Sin sesión, solo lectura, sin IDs de habitación ni PII."""
    es_titular = not request.app.state.aplicacion.nucleo.empresa.es_sintetico
    filtro = inventario_documental.es_inventario_operativo if es_titular else None
    lista = tipos_habitacion.listar(conexion, date.today(), filtro_inventario=filtro)
    tipos_publicos = [
        {
            "tipo": t["tipo_id"],
            "nombre": t["nombre"],
            "capacidad": t.get("capacidad_base"),
            "precio_base_clp": t["precio_base_clp"],
        }
        for t in lista
        if t.get("activo", True) and t.get("precio_base_clp") and t["precio_base_clp"] > 0
    ]
    return JSONResponse(
        status_code=200,
        content={"moneda": "CLP", "iva_incluido": True, "tipos": tipos_publicos},
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/publico/disponibilidad")
def disponibilidad_publica(
    request: Request,
    inicio: str = Query(min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    fin: str = Query(min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    personas: int = Query(ge=1, le=canal_publico.MAX_PERSONAS),
    hora_llegada: str | None = Query(default=None, pattern=r"^\d{1,2}:\d{2}$"),
    hora_salida: str | None = Query(default=None, pattern=r"^\d{1,2}:\d{2}$"),
    cama_adicional: bool = Query(default=False),
    ninos: int | None = Query(default=None, ge=1, le=canal_publico.MAX_PERSONAS),
    mascotas: bool = Query(default=False),
    conexion=Depends(comun.conexion),
) -> dict:
    permitidos = {"inicio", "fin", "personas", "hora_llegada", "hora_salida", "cama_adicional", "ninos", "mascotas"}
    _solo_parametros(request, frozenset(permitidos))
    freno: canal_publico.FrenoDeSolicitudes = request.app.state.freno_solicitudes
    if not freno.permite(f"ip:{canal_publico.ip_visible(request)}", ambito="disponibilidad"):
        raise HTTPException(
            status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
        )
    try:
        return canal_publico.disponibilidad(
            conexion, _fecha_iso(inicio), _fecha_iso(fin), personas, datetime.now(),
            empresa_id=request.app.state.aplicacion.nucleo.empresa.id,
            extras=_extras_consulta(hora_llegada, hora_salida, cama_adicional, ninos, mascotas),
        )
    except politicas.PoliticaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get("/publico/referencia")
def leer_referencia_publica(
    request: Request,
    token: str = Query(min_length=20, max_length=128),
    conexion=Depends(comun.conexion),
) -> dict:
    """Recupera nombre, correo y teléfono con la referencia opaca. No acepta
    esos datos por la URL."""
    _solo_parametros(request, frozenset({"token"}))
    freno: canal_publico.FrenoDeSolicitudes = request.app.state.freno_solicitudes
    if not freno.permite(f"ip:{canal_publico.ip_visible(request)}", ambito="referencia"):
        raise HTTPException(
            status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
        )
    # El token nunca va al log: solo un prefijo de su hash para correlacionar.
    huella = hashlib.sha256(token.encode()).hexdigest()[:12]
    try:
        datos = leads_mod.por_referencia(conexion, token)
    except leads_mod.LeadInvalido as error:
        observabilidad.log_http.info("referencia", extra={"evento": "referencia", "ref_hash": huella, "resultado": "formato_invalido"})
        raise HTTPException(status_code=422, detail=error.detalle)
    if datos is None:
        observabilidad.log_http.info("referencia", extra={"evento": "referencia", "ref_hash": huella, "resultado": "no_vigente"})
        raise HTTPException(status_code=404, detail="no encontramos esa consulta")
    observabilidad.log_http.info("referencia", extra={"evento": "referencia", "ref_hash": huella, "resultado": "ok"})
    return datos


@router.get("/hotel/metricas-publicas")
def metricas_publicas(
    request: Request,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
) -> dict:
    """Contadores del canal público de esta instancia (sin PII ni tokens).
    Solo administración; la vista agregada está en los logs JSON."""
    comun.exigir_admin_plataforma(sesion)
    metricas = getattr(request.app.state, "metricas_publicas", None)
    return metricas.resumen() if metricas else {"desde": None, "rutas": {}}

@router.post("/publico/solicitudes")
def crear_solicitud_publica(
    request: Request,
    solicitud: SolicitudPublicaIn,
    tareas: BackgroundTasks,
    idempotency_key: str | None = Header(default=None),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    clave = _clave_publica(idempotency_key)
    longitud = request.headers.get("content-length")
    if longitud and int(longitud) > canal_publico.TOPE_CUERPO_BYTES:
        raise HTTPException(status_code=413, detail="el cuerpo supera el tamaño permitido")
    ip = canal_publico.ip_visible(request)
    freno: canal_publico.FrenoDeSolicitudes = request.app.state.freno_solicitudes
    # C-02: tope barato por IP antes de llamar a Google; las claves de
    # contacto solo se anotan tras el captcha (un bot sin token no puede
    # agotar el cupo del correo/teléfono de un huésped real).
    if not freno.permite(f"ip:{ip}", ambito="solicitudes:pre"):
        raise HTTPException(
            status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
        )
    empresa_id = request.app.state.aplicacion.nucleo.empresa.id
    if not _es_reintento(conexion, canal_publico.clave_registrada, empresa_id, clave, "reserva"):
        _exigir_captcha(request, "reserva", ip)
        if not freno.permite(f"ip:{ip}", f"contacto:{solicitud.huesped_contacto.strip().lower()}", ambito="solicitudes"):
            raise HTTPException(
                status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
            )
    tipo = solicitud.tipo
    if tipo is None:
        tipo = canal_publico.tipo_de_unidad(conexion, solicitud.habitacion_id)
        if tipo is None:
            raise HTTPException(status_code=409, detail="no hay cupo para esa habitación en ese rango")
    resultado = canal_publico.crear_solicitud(
        conexion, request.app.state.aplicacion.nucleo.empresa.id, tipo, solicitud.inicio,
        solicitud.fin, solicitud.personas, solicitud.huesped_nombre,
        solicitud.huesped_contacto, clave,
    )
    if solicitud.referencia:
        leads_mod.consumir_referencia(conexion, empresa_id, solicitud.referencia)
    codigo = 200 if resultado.get("reintento") else 201
    conexion.commit()
    # #353: el aviso sale después de guardar; un fallo de envío no afecta la respuesta.
    despachador = getattr(request.app.state, "avisos", None)
    if codigo == 201 and despachador is not None and despachador.activo:
        tareas.add_task(despachador.despachar_seguro)
    return JSONResponse(status_code=codigo, content=resultado)


@router.get("/hotel/avisos")
def contador_avisos(
    request: Request,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """#353: contador de solicitudes `recibida` para la insignia del menú y
    del panel (el front sondea cada 60 s) y canales de aviso encendidos."""
    comun.exigir_rol(sesion, canal_publico.ROLES_GESTION)
    despachador = getattr(request.app.state, "avisos", None)
    return {
        "solicitudes_recibidas": avisos.solicitudes_recibidas(conexion, sesion.empresa_id),
        "canales_activos": [c.nombre for c in despachador.canales_vigentes(conexion)] if despachador else [],
    }

@router.get("/hotel/solicitudes")
def bandeja_solicitudes(
    estado: str | None = None,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, canal_publico.ROLES_GESTION)
    return canal_publico.bandeja(conexion, sesion.empresa_id, estado)

@router.post("/hotel/solicitudes/{solicitud_id}/conversion")
def convertir_solicitud(
    solicitud_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, canal_publico.ROLES_GESTION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"solicitud_id": solicitud_id, "operacion": "conversion"}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = canal_publico.convertir(
                conexion, sesion.empresa_id, solicitud_id, sesion.nombre
            )
        except canal_publico.SolicitudAjenaOInexistente:
            return 403, {"detail": "acceso denegado"}
        except canal_publico.TransicionInvalida as error:
            return 409, {"detail": str(error)}
        except canal_publico.SinCupoOSinTarifa as error:
            return 409, {"detail": error.detalle}
        return 201, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)

@router.post("/hotel/solicitudes/{solicitud_id}/rechazo")
def rechazar_solicitud(
    solicitud_id: str,
    cuerpo_rechazo: RechazoSolicitudIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, canal_publico.ROLES_GESTION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"solicitud_id": solicitud_id, "motivo": cuerpo_rechazo.motivo}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = canal_publico.rechazar(
                conexion, sesion.empresa_id, solicitud_id, cuerpo_rechazo.motivo, sesion.nombre
            )
        except canal_publico.SolicitudAjenaOInexistente:
            return 403, {"detail": "acceso denegado"}
        except canal_publico.TransicionInvalida as error:
            return 409, {"detail": str(error)}
        return 200, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, operacion)


# ------------------------------------------------------------------
# Contacto y leads de la landing (spec-api-v1 «Contacto y leads»)
# ------------------------------------------------------------------

@router.post("/publico/leads")
def crear_lead_publico(
    request: Request,
    lead: LeadPublicoIn,
    tareas: BackgroundTasks,
    idempotency_key: str | None = Header(default=None),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    clave = _clave_publica(idempotency_key)
    longitud = request.headers.get("content-length")
    if longitud and int(longitud) > canal_publico.TOPE_CUERPO_BYTES:
        raise HTTPException(status_code=413, detail="el cuerpo supera el tamaño permitido")
    ip = canal_publico.ip_visible(request)
    freno: canal_publico.FrenoDeSolicitudes = request.app.state.freno_solicitudes
    correo = (lead.correo or "").strip().lower()
    telefono = "".join(c for c in (lead.telefono or "") if c.isdigit())
    if not freno.permite(f"ip:{ip}", ambito="leads:pre"):
        raise HTTPException(
            status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
        )
    empresa_id = request.app.state.aplicacion.nucleo.empresa.id
    if not _es_reintento(conexion, leads_mod.clave_registrada, empresa_id, clave, "consulta"):
        _exigir_captcha(request, "consulta", ip)
        if not freno.permite(f"ip:{ip}", f"correo:{correo}", f"tel:{telefono}", ambito="leads"):
            raise HTTPException(
                status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
            )
    try:
        resultado = leads_mod.crear_lead(
            conexion, request.app.state.aplicacion.nucleo.empresa.id, lead.nombre, lead.correo, lead.telefono,
            lead.huespedes, lead.check_in, lead.check_out, lead.mensaje,
            clave,
        )
    except leads_mod.LeadInvalido as error:
        raise HTTPException(status_code=422, detail=error.detalle)
    except leads_mod.ClaveEnConflicto as error:
        raise HTTPException(status_code=409, detail=str(error))
    codigo = 200 if resultado.get("reintento") else 201
    conexion.commit()
    # Aviso «consulta recibida»: sale después de guardar, sin afectar la respuesta.
    despachador = getattr(request.app.state, "avisos", None)
    if codigo == 201 and despachador is not None and despachador.activo:
        tareas.add_task(despachador.despachar_seguro)
    return JSONResponse(status_code=codigo, content=resultado)

@router.get("/hotel/leads")
def bandeja_leads(
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    contacto_id: str | None = Query(default=None, max_length=40),
    todos: bool = False,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, leads_mod.ROLES_GESTION)
    try:
        return leads_mod.bandeja(conexion, sesion.empresa_id, estado, desde, hasta, contacto_id, todos)
    except leads_mod.LeadInvalido as error:
        raise HTTPException(status_code=422, detail=error.detalle)


@router.get("/hotel/leads/contactos")
def contactos_leads(
    desde: date | None = None,
    hasta: date | None = None,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """#354: contactos deduplicados para fidelización (un envío por persona);
    `desde`/`hasta` acotan la exportación por fecha del lead."""
    comun.exigir_rol(sesion, leads_mod.ROLES_GESTION)
    try:
        return leads_mod.contactos(conexion, sesion.empresa_id, desde, hasta)
    except leads_mod.LeadInvalido as error:
        raise HTTPException(status_code=422, detail=error.detalle)

@router.post("/hotel/leads/{lead_id}/estado")
def gestionar_lead(
    lead_id: str,
    gestion: GestionLeadIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, leads_mod.ROLES_GESTION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"lead_id": lead_id, "estado": gestion.estado, "nota": gestion.nota}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = leads_mod.gestionar(
                conexion, sesion.empresa_id, lead_id, gestion.estado, gestion.nota,
                sesion.nombre,
            )
        except leads_mod.LeadAjenoOInexistente:
            return 403, {"detail": "acceso denegado"}
        except leads_mod.TransicionInvalida as error:
            return 409, {"detail": str(error)}
        return 200, resultado

    codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

@router.put("/hotel/leads/{lead_id}")
def editar_lead(
    lead_id: str,
    datos: LeadEdicionIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Corrige los datos del lead en cualquier estado. PUT es idempotente: repetirlo no cambia nada."""
    comun.exigir_rol(sesion, leads_mod.ROLES_GESTION)
    try:
        resultado = leads_mod.editar(
            conexion, sesion.empresa_id, lead_id, datos.nombre, datos.correo, datos.telefono,
            datos.huespedes, datos.check_in, datos.check_out, datos.mensaje, datos.nota, sesion.nombre,
        )
    except leads_mod.LeadAjenoOInexistente:
        conexion.rollback()
        raise HTTPException(status_code=403, detail="acceso denegado")
    except leads_mod.LeadInvalido as error:
        conexion.rollback()
        raise HTTPException(status_code=422, detail=error.detalle)
    conexion.commit()
    return resultado


@router.get("/hotel/leads/{lead_id}/historial")
def historial_lead(
    lead_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Historial auditable del lead (nombres de campo y transiciones, nunca valores personales)."""
    comun.exigir_rol(sesion, leads_mod.ROLES_GESTION)
    try:
        return leads_mod.historial(conexion, sesion.empresa_id, lead_id)
    except leads_mod.LeadAjenoOInexistente:
        raise HTTPException(status_code=403, detail="acceso denegado")


@router.put("/hotel/leads/{lead_id}/vinculo")
def vincular_lead(
    lead_id: str,
    datos: LeadVinculoIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Vincula (o desvincula) un lead con un cliente y/o una solicitud de la misma empresa."""
    comun.exigir_rol(sesion, leads_mod.ROLES_GESTION)
    try:
        resultado = leads_mod.vincular(
            conexion, sesion.empresa_id, lead_id, datos.cliente_id, datos.solicitud_id, sesion.nombre
        )
    except leads_mod.LeadAjenoOInexistente:
        conexion.rollback()
        raise HTTPException(status_code=403, detail="acceso denegado")
    except leads_mod.LeadInvalido as error:
        conexion.rollback()
        raise HTTPException(status_code=422, detail=error.detalle)
    conexion.commit()
    return resultado


@router.put("/hotel/solicitudes/{solicitud_id}")
def editar_solicitud(
    solicitud_id: str,
    datos: SolicitudEdicionIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, canal_publico.ROLES_GESTION)
    try:
        resultado = canal_publico.editar(
            conexion, sesion.empresa_id, solicitud_id, datos.huesped_nombre, datos.huesped_contacto,
            datos.personas, sesion.nombre,
        )
    except canal_publico.SolicitudAjenaOInexistente:
        conexion.rollback()
        raise HTTPException(status_code=403, detail="acceso denegado")
    except canal_publico.SolicitudInvalida as error:
        conexion.rollback()
        raise HTTPException(status_code=422, detail=error.detalle)
    except canal_publico.TransicionInvalida as error:
        conexion.rollback()
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return resultado


@router.put("/hotel/reservas/{reserva_id}/huesped")
def editar_huesped_reserva(
    reserva_id: str,
    datos: HuespedEdicionIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Corrige nombre y documento del huésped (recepción o admin del hotel; el documento es dato sensible)."""
    comun.exigir_rol(sesion, ROLES_DOCUMENTO_HUESPED)
    with hotel_sql.EXCLUSIVO:  # el dominio recarga reservas desde la base en cada operación
        hotel_sql.bloquear(conexion)
        try:
            resultado = cobro.editar_huesped(
                conexion, sesion.empresa_id, reserva_id, datos.nombre, datos.documento,
                datos.documento_tipo, sesion.nombre,
            )
        except cobro.RecursoAjenoOInexistente:
            conexion.rollback()
            raise HTTPException(status_code=403, detail="acceso denegado")
        except cobro.HuespedInvalido as error:
            conexion.rollback()
            raise HTTPException(status_code=422, detail=str(error))
        except clientes.ClienteConflicto as error:
            conexion.rollback()
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
    return resultado

# ------------------------------------------------------------------
# Agente de reservas N0 (spec 005 / spec-api-v1 «Agente de reservas»)
# ------------------------------------------------------------------


# --- Búsqueda única de estadías (2026-11-19): Llegada, Salida y Caja ---

@router.get("/hotel/estadias/busqueda")
def buscar_estadias(
    q: str | None = Query(default=None, max_length=80),
    alcance: str = Query(default="salida", pattern="^(salida|llegada|pago)$"),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Busca por nombre del huésped, habitación, documento o código. Sin
    texto devuelve la lista del día de esa pantalla. Tope de resultados."""
    comun.exigir_rol(sesion, busqueda_estadias.ROLES_POR_ALCANCE[alcance])
    try:
        return busqueda_estadias.buscar(
            conexion, sesion.empresa_id, q, alcance, ver_documento=sesion.rol in ROLES_DOCUMENTO_HUESPED,
        )
    except busqueda_estadias.BusquedaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get("/hotel/huespedes/busqueda")
def buscar_huespedes(
    documento: str = Query(min_length=1, max_length=50),
    documento_tipo: str | None = Query(default=None, pattern="^(rut|pasaporte)$"),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Búsqueda de huéspedes registrados por documento (solo recepción y admin_hotel/administrador)."""
    comun.exigir_rol(sesion, ROLES_DOCUMENTO_HUESPED)
    try:
        items = huespedes_db.buscar(conexion, sesion.empresa_id, documento, documento_tipo)
    except huespedes_db.HuespedInvalido as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"huespedes": items, "total": len(items)}


@router.get("/hotel/reservas/{reserva_id}/huespedes")
def listar_huespedes_reserva(
    reserva_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    try:
        return huespedes_db.obtener_huespedes_reserva(
            conexion, sesion.empresa_id, reserva_id,
            ver_documento=sesion.rol in ROLES_DOCUMENTO_HUESPED,
        )
    except cobro.RecursoAjenoOInexistente:
        raise HTTPException(status_code=403, detail="acceso denegado")


@router.put("/hotel/reservas/{reserva_id}/ocupacion")
def actualizar_ocupacion_reserva(
    request: Request,
    reserva_id: str,
    datos: OcupacionIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_DOCUMENTO_HUESPED)
    with hotel_sql.EXCLUSIVO:
        hotel_sql.bloquear(conexion)
        try:
            resultado = huespedes_db.actualizar_ocupacion(
                conexion, request.app.state.aplicacion.hotel, sesion.empresa_id,
                reserva_id, datos.adultos, datos.ninos, sesion.nombre,
            )
        except cobro.RecursoAjenoOInexistente:
            conexion.rollback()
            raise HTTPException(status_code=403, detail="acceso denegado")
        except (cobro.TransicionInvalida, huespedes_db.OcupacionInvalida) as error:
            conexion.rollback()
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
    return resultado


@router.post("/hotel/reservas/{reserva_id}/huespedes", status_code=201)
def agregar_huesped_reserva(
    reserva_id: str,
    datos: ReservaHuespedIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_DOCUMENTO_HUESPED)
    try:
        resultado = huespedes_db.agregar_huesped(
            conexion, sesion.empresa_id, reserva_id, datos.model_dump(), sesion.nombre,
        )
    except cobro.RecursoAjenoOInexistente:
        conexion.rollback()
        raise HTTPException(status_code=403, detail="acceso denegado")
    except huespedes_db.HuespedInvalido as error:
        conexion.rollback()
        raise HTTPException(status_code=422, detail=str(error))
    except (cobro.TransicionInvalida, huespedes_db.HuespedConflicto) as error:
        conexion.rollback()
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return resultado


@router.put("/hotel/reservas/{reserva_id}/huespedes/{huesped_id}")
def editar_huesped_vinculado(
    reserva_id: str,
    huesped_id: str,
    datos: ReservaHuespedEdicionIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_DOCUMENTO_HUESPED)
    try:
        resultado = huespedes_db.editar_huesped_en_reserva(
            conexion, sesion.empresa_id, reserva_id, huesped_id,
            datos.model_dump(exclude_unset=True), sesion.nombre,
        )
    except cobro.RecursoAjenoOInexistente:
        conexion.rollback()
        raise HTTPException(status_code=403, detail="acceso denegado")
    except huespedes_db.HuespedInvalido as error:
        conexion.rollback()
        raise HTTPException(status_code=422, detail=str(error))
    except huespedes_db.HuespedConflicto as error:
        conexion.rollback()
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return resultado


@router.delete("/hotel/reservas/{reserva_id}/huespedes/{huesped_id}")
def quitar_huesped_vinculado(
    reserva_id: str,
    huesped_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_DOCUMENTO_HUESPED)
    try:
        resultado = huespedes_db.quitar_huesped_de_reserva(
            conexion, sesion.empresa_id, reserva_id, huesped_id, sesion.nombre,
        )
    except cobro.RecursoAjenoOInexistente:
        conexion.rollback()
        raise HTTPException(status_code=403, detail="acceso denegado")
    except (cobro.TransicionInvalida, huespedes_db.HuespedConflicto) as error:
        conexion.rollback()
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return resultado
