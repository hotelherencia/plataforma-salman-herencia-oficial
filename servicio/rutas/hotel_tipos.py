"""Rutas de tipos de habitación y alta por lote (entrega 1A, plan modulo-hotel).

Lectura para cualquier rol de la sesión (recepción y caja ven precios y
tipos); toda mutación es solo de administración, con Idempotency-Key y
auditoría, igual que el mantenedor de habitaciones y tarifas.
"""
import json
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Path as RutaParam, Request
from fastapi.responses import JSONResponse

from .. import idempotencia
from .. import inventario_documental
from .. import reservas as reservas_db
from .. import seguridad
from .. import tipos_habitacion as tipos
from . import comun
from .modelos import LoteHabitacionesIn, TipoHabitacionEdicionIn, TipoHabitacionIn

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
    """Tipos con sus habitaciones y el origen del precio de hoy de cada una
    (base del tipo, precio propio o tarifa por fechas). Cualquier rol."""
    filtro = inventario_documental.es_inventario_operativo if _es_titular(request) else None
    return {
        "tipos": tipos.listar(conexion, date.today(), filtro_inventario=filtro),
        "puede_editar": sesion.rol == "administrador",
    }


@router.post("/hotel/tipos")
def crear_tipo(
    tipo: TipoHabitacionIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"operacion": "crear_tipo", **json.loads(tipo.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            creado = tipos.crear(
                conexion, tipo.tipo_id, tipo.nombre, tipo.capacidad_base, tipo.precio_base_clp, tipo.orden
            )
        except tipos.TipoYaExiste as error:
            return 409, {"detail": str(error)}
        precio = f"${tipo.precio_base_clp}/noche" if tipo.precio_base_clp else "sin precio base"
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
    habitaciones del tipo que lo heredan (sin precio propio ni tarifa por
    fechas); las reservas confirmadas conservan su precio congelado."""
    comun.exigir_admin(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    pedidos = {campo: getattr(edicion, campo) for campo in edicion.model_fields_set}
    for campo in ("nombre", "capacidad_base", "orden", "activo"):
        if campo in pedidos and pedidos[campo] is None:
            raise HTTPException(status_code=422, detail=f"{campo} no puede quedar vacío")
    cuerpo = {"operacion": "editar_tipo", "tipo_id": tipo_id, **pedidos}

    def operacion() -> tuple[int, dict]:
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
    comun.exigir_admin(sesion)
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
