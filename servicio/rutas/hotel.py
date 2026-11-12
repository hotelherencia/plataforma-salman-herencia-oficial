"""Rutas de la operación del hotel (ARC-A01, #334; extraídas de aplicacion.py).

Mantenedor de habitaciones/tarifas, oferta, reservas, cobro, estadía, caja,
búsqueda, ocupación, indicadores, solicitudes públicas (bandeja) y leads
(bandeja y gestión). Comportamiento idéntico al de las closures originales.
"""
import json
import os
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Path as RutaParam, Query, Request, Response
from fastapi.responses import JSONResponse
from hotel_inventario.servicio import ROLES_DOCUMENTO

from .. import canal_publico
from .. import cobro
from .. import documental
from .. import idempotencia
from .. import inventario_documental
from .. import leads as leads_mod
from .. import recaptcha
from .. import panel
from .. import reservas as reservas_db
from .. import seguridad
from . import comun
from .modelos import (
    CargoIn, DocumentoHuespedIn, GestionLeadIn, HabitacionIn, LeadPublicoIn, MantenimientoIn,
    PagoIn, PATRON_ID_HABITACION, RechazoSolicitudIn, ReservaIn, ServicioIn,
    SolicitudPublicaIn, TarifaIn,
)

router = APIRouter()

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
    comun.exigir_admin(sesion)
    # Titular: no se pueden crear/editar ids fuera de HAB-01..17.
    if (
        not request.app.state.aplicacion.nucleo.empresa.es_sintetico
        and not inventario_documental.es_id_inventario_real(habitacion_id)
    ):
        raise HTTPException(
            status_code=422,
            detail="solo HAB-01..17 forman el inventario real del titular",
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

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

@router.put("/hotel/tarifas")
def definir_tarifa(
    tarifa: TarifaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin(sesion)
    if tarifa.fecha_hasta <= tarifa.fecha_desde:
        raise HTTPException(status_code=400, detail="fecha_hasta debe ser mayor que fecha_desde")
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = json.loads(tarifa.model_dump_json())

    def operacion() -> tuple[int, dict]:
        try:
            tarifa_id = reservas_db.insertar_tarifa(
                conexion, tarifa.habitacion_id, tarifa.fecha_desde, tarifa.fecha_hasta, tarifa.tarifa_noche_clp
            )
        except reservas_db.TarifaSolapadaInutil as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(
            conexion, sesion.nombre, "tarifa", tarifa.habitacion_id,
            f"{tarifa_id} {tarifa.fecha_desde}→{tarifa.fecha_hasta} ${tarifa.tarifa_noche_clp}/noche",
        )
        return 201, {
            "tarifa_id": tarifa_id,
            "habitacion_id": tarifa.habitacion_id,
            "fecha_desde": tarifa.fecha_desde.isoformat(),
            "fecha_hasta": tarifa.fecha_hasta.isoformat(),
            "tarifa_noche_clp": tarifa.tarifa_noche_clp,
        }

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

@router.get("/hotel/oferta")
def consultar_oferta(
    inicio: date,
    fin: date,
    personas: int = Query(gt=0, le=30),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    if fin <= inicio:
        raise HTTPException(status_code=400, detail="fin debe ser mayor que inicio")
    return reservas_db.oferta(conexion, inicio, fin, personas, datetime.now())

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
        habitaciones = [
            h
            for h in habitaciones
            if inventario_documental.es_id_inventario_real(h.get("habitacion_id") or h.get("id") or "")
        ]
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
        ver_documento=sesion.rol in ROLES_DOCUMENTO,
        ver_auditoria=sesion.rol == "administrador",
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
    comun.exigir_admin(sesion)
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

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

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
    """Panel operativo (spec-hotel-operacion-v1 §4); por defecto la noche de hoy.
    D-ROL-01 RATIFICADA 2026-11-06 (#297 opción a): el indicador financiero
    `ingresos_periodo_clp` solo lo recibe el administrador."""
    hoy = date.today()
    desde = desde or hoy
    hasta = hasta or desde + timedelta(days=1)
    solo_reales = not request.app.state.aplicacion.nucleo.empresa.es_sintetico
    return panel.indicadores(
        conexion,
        sesion.empresa_id,
        desde,
        hasta,
        hoy,
        tipo or None,
        incluir_financiero=sesion.rol == "administrador",
        solo_inventario_real=solo_reales,
    )

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
                personas=reserva.personas,
            )
        except reservas_db.SinCupo as error:
            return 409, {"detail": str(error)}
        except (reservas_db.SinTarifaVigente, reservas_db.HabitacionNoVendible) as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "reserva", creada["reserva_id"], "confirmada")
        return 201, creada

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(
            conexion, sesion.empresa_id, idempotency_key, cuerpo, operacion
        )
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

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
                conexion, request.app.state.aplicacion.nucleo, sesion.empresa_id, reserva_id, pago.monto_clp, pago.clave
            )
        except cobro.PagoRechazadoPorNucleo as error:
            seguridad.auditar(conexion, sesion.nombre, "pago", f"{reserva_id}:{pago.clave}", "rechazado-nucleo")
            return 403, {"detail": str(error)}
        except cobro.PagoDuplicadoConDatosDistintos as error:
            seguridad.auditar(conexion, sesion.nombre, "pago", f"{reserva_id}:{pago.clave}", "conflicto-clave-cobro")
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "pago", f"{reserva_id}:{pago.clave}", "confirmado")
        return 201, registrado

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

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
    reserva_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
    cuerpo: DocumentoHuespedIn | None = Body(default=None),
) -> JSONResponse:
    # D-ROL-ENT (DECISIÓN 2026-11-06, #304 opción a): la entrada la registran
    # recepción o administrador («caja cobra, recepción opera la habitación»).
    comun.exigir_rol(sesion, ("recepcion", "administrador"))
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo_idem = {
        "operacion": "entrada",
        "reserva_id": reserva_id,
        "documento": cuerpo.documento if cuerpo else None,
    }

    def operacion() -> tuple[int, dict]:
        try:
            ingreso = cobro.entrada(conexion, sesion.empresa_id, reserva_id,
                                    documento=cuerpo.documento if cuerpo else None)
        except (cobro.HabitacionNoLista, cobro.TransicionInvalida) as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "entrada", reserva_id, "en_estadia")
        return 200, ingreso

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo_idem, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

@router.post("/hotel/reservas/{reserva_id}/salida")
def check_out(
    reserva_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    # D-ROL-ENT (DECISIÓN 2026-11-06, #304 opción a): la salida la registran
    # recepción o administrador, igual que la entrada.
    comun.exigir_rol(sesion, ("recepcion", "administrador"))
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "salida", "reserva_id": reserva_id}

    def operacion() -> tuple[int, dict]:
        try:
            liquidada = cobro.salida(conexion, sesion.empresa_id, reserva_id)
        except (cobro.SaldoPendiente, cobro.TransicionInvalida) as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "salida", reserva_id, "liquidada")
        return 200, liquidada

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

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
        ver_documento=sesion.rol in ROLES_DOCUMENTO,
        desde=desde,
        hasta=hasta,
        habitacion_id=habitacion_id or None,
    )
    return {"reservas": items, "total": len(items)}

@router.get("/hotel/reservas/{reserva_id}")
def detalle_reserva_hotel(
    reserva_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Detalle con cuenta (spec-hotel-operacion-v1 §3.2); ajena → 403."""
    return cobro.detalle_reserva(
        conexion, sesion.empresa_id, reserva_id, ver_documento=sesion.rol in ROLES_DOCUMENTO
    )

@router.post("/hotel/habitaciones/{habitacion_id}/limpieza")
def completar_limpieza_habitacion(
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
            resultado = cobro.completar_limpieza(conexion, habitacion_id)
        except cobro.RecursoAjenoOInexistente as error:
            raise seguridad.ErrorPermiso(str(error)) from error
        seguridad.auditar(conexion, sesion.nombre, "limpieza", habitacion_id, "completada")
        return 200, resultado

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

@router.post("/hotel/habitaciones/{habitacion_id}/mantenimiento")
def fijar_mantenimiento_habitacion(
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
            resultado = cobro.fijar_mantenimiento(conexion, habitacion_id, cuerpo_mantenimiento.abierto)
        except cobro.RecursoAjenoOInexistente as error:
            raise seguridad.ErrorPermiso(str(error)) from error
        seguridad.auditar(
            conexion, sesion.nombre, "mantenimiento", habitacion_id,
            "abierto" if cuerpo_mantenimiento.abierto else "cerrado",
        )
        return 200, resultado

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

@router.post("/hotel/reservas/{reserva_id}/cancelacion")
def cancelar_reserva(
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
            resultado = cobro.cancelar(conexion, sesion.empresa_id, reserva_id, datetime.now())
        except cobro.TransicionInvalida as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "cancelacion", reserva_id, "cancelada")
        return 200, resultado

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

@router.post("/hotel/reservas/{reserva_id}/cargos")
def asentar_cargo_reserva(
    reserva_id: str,
    cargo: CargoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, cobro.ROLES_CARGO)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"reserva_id": reserva_id, **json.loads(cargo.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = cobro.asentar_cargo(
                conexion, sesion.empresa_id, reserva_id, cargo.concepto, cargo.monto_clp
            )
        except cobro.TransicionInvalida as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, "cargo", f"{reserva_id}:{resultado['cargo_id']}", "asentado")
        return 201, resultado

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

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
            raise HTTPException(
                status_code=503, detail="canal público temporalmente no disponible"
            )
        return
    verificador = getattr(request.app.state, "verificar_recaptcha", recaptcha.verificar)
    try:
        verificador(request.headers.get("x-recaptcha-token"), secreto, accion, ip)
    except recaptcha.CaptchaRechazado:
        raise HTTPException(status_code=403, detail="no se pudo verificar el envío")


@router.get("/publico/disponibilidad")
def disponibilidad_publica(
    request: Request,
    inicio: str = Query(min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    fin: str = Query(min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    personas: int = Query(ge=1, le=canal_publico.MAX_PERSONAS),
    conexion=Depends(comun.conexion),
) -> dict:
    _solo_parametros(request, frozenset({"inicio", "fin", "personas"}))
    freno: canal_publico.FrenoDeSolicitudes = request.app.state.freno_solicitudes
    if not freno.permite(f"ip:{canal_publico.ip_visible(request)}"):
        raise HTTPException(
            status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
        )
    return canal_publico.disponibilidad(
        conexion, _fecha_iso(inicio), _fecha_iso(fin), personas, datetime.now()
    )


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
    if not freno.permite(f"ip:{canal_publico.ip_visible(request)}"):
        raise HTTPException(
            status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
        )
    try:
        datos = leads_mod.por_referencia(conexion, token)
    except leads_mod.LeadInvalido as error:
        raise HTTPException(status_code=422, detail=error.detalle)
    if datos is None:
        raise HTTPException(status_code=404, detail="no encontramos esa consulta")
    return datos

@router.post("/publico/solicitudes")
def crear_solicitud_publica(
    request: Request,
    solicitud: SolicitudPublicaIn,
    idempotency_key: str | None = Header(default=None),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    clave = _clave_publica(idempotency_key)
    longitud = request.headers.get("content-length")
    if longitud and int(longitud) > canal_publico.TOPE_CUERPO_BYTES:
        raise HTTPException(status_code=413, detail="el cuerpo supera el tamaño permitido")
    ip = canal_publico.ip_visible(request)
    freno: canal_publico.FrenoDeSolicitudes = request.app.state.freno_solicitudes
    if not freno.permite(f"ip:{ip}", f"contacto:{solicitud.huesped_contacto.strip().lower()}"):
        raise HTTPException(
            status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
        )
    _exigir_captcha(request, "reserva", ip)
    resultado = canal_publico.crear_solicitud(
        conexion, request.app.state.aplicacion.nucleo.empresa.id, solicitud.habitacion_id, solicitud.inicio,
        solicitud.fin, solicitud.personas, solicitud.huesped_nombre,
        solicitud.huesped_contacto, clave,
    )
    codigo = 200 if resultado.get("reintento") else 201
    conexion.commit()
    return JSONResponse(status_code=codigo, content=resultado)

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

    codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

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

    codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

# ------------------------------------------------------------------
# Contacto y leads de la landing (spec-api-v1 «Contacto y leads»)
# ------------------------------------------------------------------

@router.post("/publico/leads")
def crear_lead_publico(
    request: Request,
    lead: LeadPublicoIn,
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
    if not freno.permite(f"ip:{ip}", f"correo:{correo}", f"tel:{telefono}"):
        raise HTTPException(
            status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
        )
    _exigir_captcha(request, "consulta", ip)
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
    return JSONResponse(status_code=codigo, content=resultado)

@router.get("/hotel/leads")
def bandeja_leads(
    estado: str | None = None,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, leads_mod.ROLES_GESTION)
    try:
        return leads_mod.bandeja(conexion, sesion.empresa_id, estado)
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

# ------------------------------------------------------------------
# Agente de reservas N0 (spec 005 / spec-api-v1 «Agente de reservas»)
# ------------------------------------------------------------------
