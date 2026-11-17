"""Rutas del mantenedor único «Tipos, habitaciones y precios» (1A y 1A.2).

Lectura para cualquier rol de la sesión (recepción y caja ven precios y
tipos). Tipos, precio base, precio propio, excepciones por fecha y alta por
lote: solo administración del hotel. Tasa de IVA: solo administración de
plataforma. Toda mutación con Idempotency-Key y auditoría.
"""
import json
from datetime import date

from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Path as RutaParam, Request
from fastapi.responses import JSONResponse

from .. import idempotencia
from .. import iva
from .. import inventario_documental
from .. import reservas as reservas_db
from .. import roles
from .. import seguridad
from .. import tipos_habitacion as tipos
from . import comun
from .modelos import (
    ExcepcionPrecioIn, LoteHabitacionesIn, PrecioPropioIn, TasaIvaIn, TipoHabitacionEdicionIn, TipoHabitacionIn,
)
from .modelos import PATRON_ID_HABITACION

router = APIRouter()


def _es_titular(request: Request) -> bool:
    return not request.app.state.aplicacion.nucleo.empresa.es_sintetico


def _ejecutar(conexion, sesion, clave: str, cuerpo: dict, operacion) -> JSONResponse:
    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)


@router.get("/hotel/tipos")
def listar_tipos(
    request: Request,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Tipos con sus habitaciones, excepciones por fecha y el origen del
    precio de hoy de cada habitación. Cualquier rol."""
    filtro = inventario_documental.es_inventario_operativo if _es_titular(request) else None
    return {
        "tipos": tipos.listar(conexion, date.today(), filtro_inventario=filtro),
        "iva": _iva(conexion),
        "puede_editar": roles.es_admin_hotel(sesion.rol),
        "puede_editar_iva": roles.es_admin_plataforma(sesion.rol),
    }


def _iva(conexion) -> dict:
    tasa = iva.tasa(conexion)
    return {
        "porcentaje": iva.como_texto(tasa),
        "regla": "precios con IVA incluido; neto = redondeo(precio × 100 / (100 + tasa)); IVA = precio − neto",
    }


def _texto_precio(monto: int | None, tasa: Decimal) -> str:
    if monto is None:
        return "sin precio"
    d = iva.desglose(monto, tasa)

    def pesos(n: int) -> str:
        return "$" + f"{n:,}".replace(",", ".")

    return f"{pesos(monto)} con IVA (neto {pesos(d['neto'])}, IVA {pesos(d['iva'])})"


@router.post("/hotel/tipos")
def crear_tipo(
    tipo: TipoHabitacionIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "crear_tipo", **json.loads(tipo.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        tasa = iva.tasa(conexion)
        precio_base = tipos.monto_con_iva(tipo.precio_base_clp, tipo.precio_en, tasa)
        try:
            creado = tipos.crear(
                conexion, tipo.tipo_id, tipo.nombre, tipo.capacidad_base, precio_base, tipo.orden
            )
        except tipos.TipoYaExiste as error:
            return 409, {"detail": str(error)}
        precio = _texto_precio(precio_base, tasa)
        seguridad.auditar(
            conexion, sesion.nombre, "tipo_habitacion", f"tipo:{tipo.tipo_id}",
            f"creado «{tipo.nombre}» capacidad={tipo.capacidad_base} {precio}",
        )
        return 201, creado

    return _ejecutar(conexion, sesion, clave, cuerpo, operacion)


@router.put("/hotel/tipos/{tipo_id}")
def editar_tipo(
    edicion: TipoHabitacionEdicionIn,
    tipo_id: str = RutaParam(pattern=tipos.PATRON_ID_TIPO_RUTA),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Edita el tipo. Cambiar `precio_base_clp` mueve el precio de todas las
    habitaciones del tipo que lo heredan (sin precio propio ni excepción en
    esa fecha); las reservas confirmadas conservan su precio congelado."""
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    pedidos = {campo: getattr(edicion, campo) for campo in edicion.model_fields_set if campo != "precio_en"}
    for campo in ("nombre", "capacidad_base", "orden", "activo"):
        if campo in pedidos and pedidos[campo] is None:
            raise HTTPException(status_code=422, detail=f"{campo} no puede quedar vacío")
    cuerpo = {"operacion": "editar_tipo", "tipo_id": tipo_id, "precio_en": edicion.precio_en, **pedidos}

    def operacion() -> tuple[int, dict]:
        if "precio_base_clp" in pedidos:
            pedidos["precio_base_clp"] = tipos.monto_con_iva(
                pedidos["precio_base_clp"], edicion.precio_en, iva.tasa(conexion)
            )
        try:
            resultado = tipos.editar(conexion, tipo_id, pedidos)
        except tipos.TipoInexistente as error:
            return 404, {"detail": str(error)}
        texto = (
            "editado " + "; ".join(f"{c}: {a}→{d}" for c, (a, d) in resultado["cambios"].items())
            if resultado["cambios"] else "sin cambios"
        )
        seguridad.auditar(conexion, sesion.nombre, "tipo_habitacion", f"tipo:{tipo_id}", texto)
        return 200, resultado

    return _ejecutar(conexion, sesion, clave, cuerpo, operacion)


@router.post("/hotel/habitaciones/lote")
def crear_lote_habitaciones(
    request: Request,
    lote: LoteHabitacionesIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Alta de N habitaciones de un tipo con numeración `prefijo + número`
    (p. ej. HAB-18..HAB-27). Todo o nada: si alguna ya existe → 409."""
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "lote_habitaciones", **json.loads(lote.model_dump_json())}
    establecimiento = (
        inventario_documental.ESTABLECIMIENTO_HERENCIA if _es_titular(request)
        else reservas_db.ESTABLECIMIENTO_SINTETICO
    )

    def operacion() -> tuple[int, dict]:
        try:
            resultado = tipos.crear_lote(
                conexion, tipo_id=lote.tipo_id, cantidad=lote.cantidad, prefijo=lote.prefijo,
                desde_numero=lote.desde_numero, digitos=lote.digitos, capacidad=lote.capacidad,
                establecimiento_id=establecimiento,
            )
        except tipos.TipoInexistente as error:
            return 422, {"detail": str(error)}
        except tipos.LoteInvalido as error:
            return 422, {"detail": str(error)}
        except (tipos.TipoInactivo, tipos.HabitacionesYaExisten) as error:
            cuerpo_error = {"detail": str(error)}
            if isinstance(error, tipos.HabitacionesYaExisten):
                cuerpo_error["existentes"] = error.ids
            return 409, cuerpo_error
        ids = resultado["habitaciones"]
        for habitacion_id in ids:
            seguridad.auditar(
                conexion, sesion.nombre, "habitacion", habitacion_id,
                f"creada por lote tipo={lote.tipo_id} capacidad={resultado['capacidad']}",
            )
        seguridad.auditar(
            conexion, sesion.nombre, "habitaciones_lote", f"tipo:{lote.tipo_id}",
            f"{len(ids)} creadas: {ids[0]}..{ids[-1]}",
        )
        return 201, resultado

    return _ejecutar(conexion, sesion, clave, cuerpo, operacion)


@router.put("/hotel/habitaciones/{habitacion_id}/precio")
def fijar_precio_propio(
    cuerpo_precio: PrecioPropioIn,
    habitacion_id: str = RutaParam(pattern=PATRON_ID_HABITACION),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Precio propio de la habitación (gana al base de su tipo; las
    excepciones por fecha ganan a ambos). `precio_clp: null` lo quita y la
    habitación vuelve a heredar el precio base del tipo."""
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "precio_propio", "habitacion_id": habitacion_id,
              **json.loads(cuerpo_precio.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        tasa = iva.tasa(conexion)
        precio = tipos.monto_con_iva(cuerpo_precio.precio_clp, cuerpo_precio.precio_en, tasa)
        try:
            resultado = tipos.fijar_precio_propio(conexion, habitacion_id, precio)
        except tipos.HabitacionInexistente as error:
            return 404, {"detail": str(error)}
        seguridad.auditar(
            conexion, sesion.nombre, "precio_habitacion", habitacion_id,
            "precio propio " + (_texto_precio(precio, tasa) if precio else "quitado: hereda el precio base del tipo"),
        )
        return 200, resultado

    return _ejecutar(conexion, sesion, clave, cuerpo, operacion)


@router.post("/hotel/precios/excepciones")
def crear_excepcion(
    excepcion: ExcepcionPrecioIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Excepción por fecha [fecha_desde, fecha_hasta) de un tipo (temporada,
    feriado) o de una habitación; `precio_clp: null` = sin venta. Gana al
    precio propio y al base; la de la habitación gana a la del tipo."""
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "crear_excepcion", **json.loads(excepcion.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        tasa = iva.tasa(conexion)
        precio = tipos.monto_con_iva(excepcion.precio_clp, excepcion.precio_en, tasa)
        try:
            creada = tipos.crear_excepcion(
                conexion, tipo_id=excepcion.tipo_id, habitacion_id=excepcion.habitacion_id,
                fecha_desde=excepcion.fecha_desde, fecha_hasta=excepcion.fecha_hasta,
                precio_clp=precio, motivo=excepcion.motivo, actor=sesion.nombre,
            )
        except tipos.ExcepcionInvalida as error:
            return 422, {"detail": str(error)}
        except (tipos.TipoInexistente, tipos.HabitacionInexistente) as error:
            return 404, {"detail": str(error)}
        except tipos.ExcepcionDuplicada as error:
            return 409, {"detail": str(error)}
        recurso = f"tipo:{excepcion.tipo_id}" if excepcion.tipo_id else excepcion.habitacion_id
        seguridad.auditar(
            conexion, sesion.nombre, "excepcion_precio", recurso,
            f"{creada['excepcion_id']} {excepcion.fecha_desde}→{excepcion.fecha_hasta} "
            + (_texto_precio(precio, tasa) if precio else "sin venta"),
        )
        return 201, creada

    return _ejecutar(conexion, sesion, clave, cuerpo, operacion)


@router.post("/hotel/precios/excepciones/{excepcion_id}/retiro")
def retirar_excepcion(
    excepcion_id: str = RutaParam(pattern=r"^EXC-[A-Za-z0-9-]{1,40}$"),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Retiro lógico: deja de aplicar y queda en el historial (no se borra)."""
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "retirar_excepcion", "excepcion_id": excepcion_id}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = tipos.retirar_excepcion(conexion, excepcion_id, sesion.nombre)
        except tipos.ExcepcionInexistente as error:
            return 404, {"detail": str(error)}
        recurso = f"tipo:{resultado['tipo_id']}" if resultado["tipo_id"] else resultado["habitacion_id"]
        seguridad.auditar(conexion, sesion.nombre, "excepcion_precio", recurso, f"{excepcion_id} retirada")
        return 200, resultado

    return _ejecutar(conexion, sesion, clave, cuerpo, operacion)


@router.get("/plataforma/ajustes")
def ver_ajustes(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """Ajustes del sistema visibles para cualquier sesión (hoy: la tasa de IVA)."""
    return {"iva": _iva(conexion), "puede_editar": roles.es_admin_plataforma(sesion.rol)}


@router.put("/plataforma/ajustes/iva")
def fijar_tasa_iva(
    cuerpo_tasa: TasaIvaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Tasa de IVA (solo administración de plataforma). Los precios guardados
    son con IVA y no cambian: cambia el desglose neto/IVA que se muestra."""
    comun.exigir_admin_plataforma(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "tasa_iva", "iva_porcentaje": str(cuerpo_tasa.iva_porcentaje)}

    def operacion() -> tuple[int, dict]:
        anterior, nueva = iva.fijar_tasa(conexion, cuerpo_tasa.iva_porcentaje, sesion.nombre)
        seguridad.auditar(
            conexion, sesion.nombre, "ajuste_plataforma", iva.CLAVE_TASA,
            f"IVA {iva.como_texto(anterior)}% → {iva.como_texto(nueva)}%",
        )
        return 200, {"iva": _iva(conexion)}

    return _ejecutar(conexion, sesion, clave, cuerpo, operacion)
