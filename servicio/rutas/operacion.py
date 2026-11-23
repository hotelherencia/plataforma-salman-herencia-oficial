"""Rutas del Corte 1 operativo: incidencias (#415) y tareas/checklists (#416)."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from .. import hotel_sql, idempotencia, incidencias, seguridad, tareas
from . import comun

router = APIRouter()


class IncidenciaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titulo: str = Field(min_length=3, max_length=160)
    descripcion: str = Field(min_length=3, max_length=2000)
    habitacion_id: str | None = Field(default=None, max_length=50)
    area: str = Field(default="habitacion", max_length=40)
    gravedad: Literal["baja", "media", "alta", "critica"] = "media"
    responsable: str | None = Field(default=None, max_length=100)
    plazo: date | None = None
    costo_clp: int | None = Field(default=None, ge=0, le=1_000_000_000)
    bloquea_disponibilidad: bool = False
    evidencia_base64: str | None = None
    evidencia_nombre: str | None = Field(default=None, max_length=120)


class IncidenciaCambioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titulo: str | None = Field(default=None, min_length=3, max_length=160)
    descripcion: str | None = Field(default=None, min_length=3, max_length=2000)
    gravedad: Literal["baja", "media", "alta", "critica"] | None = None
    estado: Literal["abierta", "en_progreso", "resuelta", "cerrada"] | None = None
    responsable: str | None = Field(default=None, max_length=100)
    plazo: date | None = None
    costo_clp: int | None = Field(default=None, ge=0, le=1_000_000_000)
    bloquea_disponibilidad: bool | None = None
    resolucion: str | None = Field(default=None, max_length=1000)


class IncidenciaCierreIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resolucion: str | None = Field(default=None, max_length=1000)
    costo_clp: int | None = Field(default=None, ge=0, le=1_000_000_000)
    estado_final: Literal["resuelta", "cerrada"] = "cerrada"


class IniciarLimpiezaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aplicar_plantilla: bool = True


class SubtareaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descripcion: str = Field(min_length=2, max_length=240)
    obligatoria: bool = True


class SubtareaEstadoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completada: bool


class TareaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo: Literal["limpieza", "mantenimiento", "banos", "lavanderia", "desayunos", "general"] = "general"
    titulo: str = Field(min_length=3, max_length=160)
    habitacion_id: str | None = Field(default=None, max_length=50)
    area: str | None = Field(default=None, max_length=60)
    prioridad: Literal["baja", "media", "alta", "urgente"] = "media"
    responsable: str | None = Field(default=None, max_length=100)
    vence_en: datetime | None = None
    observacion: str | None = Field(default=None, max_length=500)
    subtareas: list[SubtareaIn] | None = None
    aplicar_plantilla: bool = False


class TareaCambioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titulo: str | None = Field(default=None, min_length=3, max_length=160)
    estado: Literal["pendiente", "en_proceso", "completada", "cancelada"] | None = None
    prioridad: Literal["baja", "media", "alta", "urgente"] | None = None
    responsable: str | None = Field(default=None, max_length=100)
    vence_en: datetime | None = None
    observacion: str | None = Field(default=None, max_length=500)


def _ejecutar_exclusivo(conexion, empresa_id: str, clave: str, cuerpo: dict, operacion) -> JSONResponse:
    with hotel_sql.EXCLUSIVO:
        hotel_sql.bloquear(conexion)
        codigo, respuesta = idempotencia.ejecutar(conexion, empresa_id, clave, cuerpo, operacion)
        conexion.commit()
    return JSONResponse(status_code=codigo, content=respuesta)


# ------------------------------------------------------------------
# Incidencias operativas (#415)
# ------------------------------------------------------------------

@router.get("/hotel/incidencias")
def listar_incidencias(
    estado: str | None = Query(default=None),
    gravedad: str | None = Query(default=None),
    habitacion_id: str | None = Query(default=None, max_length=50),
    area: str | None = Query(default=None, max_length=40),
    bloquea_disponibilidad: bool | None = Query(default=None),
    solo_abiertas: bool = Query(default=False),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, incidencias.ROLES_REPORTE)
    try:
        items = incidencias.listar(
            conexion,
            sesion.empresa_id,
            estado=estado,
            gravedad=gravedad,
            habitacion_id=habitacion_id,
            area=area,
            bloquea_disponibilidad=bloquea_disponibilidad,
            solo_abiertas=solo_abiertas,
        )
    except incidencias.IncidenciaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {
        "incidencias": items,
        "total": len(items),
        "abiertas": sum(1 for i in items if i["estado"] in incidencias.ESTADOS_ABIERTOS),
        "bloqueantes": sum(
            1 for i in items if i["estado"] in incidencias.ESTADOS_ABIERTOS and i["bloquea_disponibilidad"]
        ),
    }


@router.post("/hotel/incidencias")
def crear_incidencia(
    request: Request,
    cuerpo_in: IncidenciaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, incidencias.ROLES_REPORTE)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    huella = {
        "operacion": "incidencia_crear",
        "titulo": cuerpo_in.titulo,
        "habitacion_id": cuerpo_in.habitacion_id,
        "area": cuerpo_in.area,
        "gravedad": cuerpo_in.gravedad,
        "bloquea_disponibilidad": cuerpo_in.bloquea_disponibilidad,
    }

    def operacion() -> tuple[int, dict]:
        try:
            creada = incidencias.crear(
                conexion,
                request.app.state.aplicacion.hotel,
                sesion.empresa_id,
                sesion.nombre,
                titulo=cuerpo_in.titulo,
                descripcion=cuerpo_in.descripcion,
                habitacion_id=cuerpo_in.habitacion_id,
                area=cuerpo_in.area,
                gravedad=cuerpo_in.gravedad,
                responsable=cuerpo_in.responsable,
                plazo=cuerpo_in.plazo,
                costo_clp=cuerpo_in.costo_clp,
                bloquea_disponibilidad=cuerpo_in.bloquea_disponibilidad,
                evidencia_base64=cuerpo_in.evidencia_base64,
                evidencia_nombre=cuerpo_in.evidencia_nombre,
            )
        except incidencias.IncidenciaInvalida as error:
            return 422, {"detail": str(error)}
        return 201, creada

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, huella, operacion)


@router.get("/hotel/incidencias/{incidencia_id}")
def detalle_incidencia(
    incidencia_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, incidencias.ROLES_REPORTE)
    try:
        return incidencias.obtener(conexion, sesion.empresa_id, incidencia_id)
    except incidencias.IncidenciaNoEncontrada as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.put("/hotel/incidencias/{incidencia_id}")
def actualizar_incidencia(
    request: Request,
    incidencia_id: str,
    cuerpo_in: IncidenciaCambioIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, incidencias.ROLES_GESTION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cambios = cuerpo_in.model_dump(exclude_unset=True)
    huella = {"operacion": "incidencia_actualizar", "incidencia_id": incidencia_id, **json.loads(cuerpo_in.model_dump_json(exclude_unset=True))}

    def operacion() -> tuple[int, dict]:
        try:
            actualizada = incidencias.actualizar(
                conexion,
                request.app.state.aplicacion.hotel,
                sesion.empresa_id,
                incidencia_id,
                sesion.nombre,
                cambios,
            )
        except incidencias.IncidenciaNoEncontrada:
            return 403, {"detail": "acceso denegado"}
        except incidencias.IncidenciaInvalida as error:
            return 422, {"detail": str(error)}
        return 200, actualizada

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, huella, operacion)


@router.post("/hotel/incidencias/{incidencia_id}/cierre")
def cerrar_incidencia(
    request: Request,
    incidencia_id: str,
    cuerpo_in: IncidenciaCierreIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, incidencias.ROLES_GESTION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    huella = {"operacion": "incidencia_cerrar", "incidencia_id": incidencia_id, **json.loads(cuerpo_in.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            cerrada = incidencias.cerrar(
                conexion,
                request.app.state.aplicacion.hotel,
                sesion.empresa_id,
                incidencia_id,
                sesion.nombre,
                resolucion=cuerpo_in.resolucion,
                costo_clp=cuerpo_in.costo_clp,
                estado_final=cuerpo_in.estado_final,
            )
        except incidencias.IncidenciaNoEncontrada:
            return 403, {"detail": "acceso denegado"}
        except incidencias.TransicionIncidenciaInvalida as error:
            return 409, {"detail": str(error)}
        except incidencias.IncidenciaInvalida as error:
            return 422, {"detail": str(error)}
        return 200, cerrada

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, huella, operacion)


@router.post("/hotel/incidencias/{incidencia_id}/evidencia")
async def subir_evidencia_incidencia(
    request: Request,
    incidencia_id: str,
    x_nombre_archivo: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, incidencias.ROLES_REPORTE)
    datos = await request.body()
    try:
        resultado = incidencias.guardar_evidencia(
            conexion, sesion.empresa_id, incidencia_id, sesion.nombre, datos, nombre=x_nombre_archivo
        )
    except incidencias.IncidenciaNoEncontrada as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except incidencias.IncidenciaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    conexion.commit()
    return resultado


@router.get("/hotel/incidencias/{incidencia_id}/evidencia")
def descargar_evidencia_incidencia(
    incidencia_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> Response:
    comun.exigir_rol(sesion, incidencias.ROLES_REPORTE)
    try:
        datos, mime, nombre = incidencias.leer_evidencia(conexion, sesion.empresa_id, incidencia_id)
    except incidencias.IncidenciaNoEncontrada as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(
        content=datos,
        media_type=mime,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{nombre.replace(chr(34), "")}"',
        },
    )


# ------------------------------------------------------------------
# Tareas operativas, checklists y estado «En limpieza» (#416)
# ------------------------------------------------------------------

@router.post("/hotel/habitaciones/{habitacion_id}/limpieza/iniciar")
def iniciar_limpieza_habitacion(
    habitacion_id: str,
    cuerpo_in: IniciarLimpiezaIn | None = None,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, tareas.ROLES_OPERACION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    aplicar = True if cuerpo_in is None else cuerpo_in.aplicar_plantilla
    huella = {"operacion": "limpieza_iniciar", "habitacion_id": habitacion_id, "aplicar_plantilla": aplicar}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = tareas.iniciar_limpieza(
                conexion, sesion.empresa_id, habitacion_id, sesion.nombre, aplicar_plantilla=aplicar
            )
        except tareas.TareaNoEncontrada:
            return 403, {"detail": "acceso denegado"}
        except tareas.TareaConflicto as error:
            return 409, {"detail": str(error)}
        return 200, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, huella, operacion)


@router.get("/hotel/tareas")
def listar_tareas(
    estado: str | None = Query(default=None),
    tipo: str | None = Query(default=None),
    habitacion_id: str | None = Query(default=None, max_length=50),
    area: str | None = Query(default=None, max_length=60),
    prioridad: str | None = Query(default=None),
    responsable: str | None = Query(default=None, max_length=100),
    solo_abiertas: bool = Query(default=False),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, tareas.ROLES_OPERACION)
    try:
        return tareas.listar_tareas(
            conexion,
            sesion.empresa_id,
            estado=estado,
            tipo=tipo,
            habitacion_id=habitacion_id,
            area=area,
            prioridad=prioridad,
            responsable=responsable,
            solo_abiertas=solo_abiertas,
        )
    except tareas.TareaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/hotel/tareas")
def crear_tarea(
    cuerpo_in: TareaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, tareas.ROLES_OPERACION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    huella = {"operacion": "tarea_crear", **json.loads(cuerpo_in.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            creada = tareas.crear_tarea(
                conexion,
                sesion.empresa_id,
                sesion.nombre,
                tipo=cuerpo_in.tipo,
                titulo=cuerpo_in.titulo,
                habitacion_id=cuerpo_in.habitacion_id,
                area=cuerpo_in.area,
                prioridad=cuerpo_in.prioridad,
                responsable=cuerpo_in.responsable,
                vence_en=cuerpo_in.vence_en,
                observacion=cuerpo_in.observacion,
                subtareas=[s.model_dump() for s in cuerpo_in.subtareas] if cuerpo_in.subtareas else None,
                aplicar_plantilla=cuerpo_in.aplicar_plantilla,
            )
        except tareas.TareaInvalida as error:
            return 422, {"detail": str(error)}
        return 201, creada

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, huella, operacion)


@router.put("/hotel/tareas/{tarea_id}")
def actualizar_tarea(
    request: Request,
    tarea_id: str,
    cuerpo_in: TareaCambioIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, tareas.ROLES_OPERACION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cambios = cuerpo_in.model_dump(exclude_unset=True)
    huella = {"operacion": "tarea_actualizar", "tarea_id": tarea_id, **json.loads(cuerpo_in.model_dump_json(exclude_unset=True))}

    def operacion() -> tuple[int, dict]:
        try:
            actualizada = tareas.actualizar_tarea(
                conexion,
                request.app.state.aplicacion.hotel,
                sesion.empresa_id,
                tarea_id,
                sesion.nombre,
                cambios,
            )
        except tareas.TareaNoEncontrada:
            return 403, {"detail": "acceso denegado"}
        except tareas.TareaConflicto as error:
            return 409, {"detail": str(error)}
        except tareas.TareaInvalida as error:
            return 422, {"detail": str(error)}
        return 200, actualizada

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, huella, operacion)


@router.post("/hotel/tareas/{tarea_id}/subtareas")
def crear_subtarea(
    tarea_id: str,
    cuerpo_in: SubtareaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, tareas.ROLES_OPERACION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    huella = {"operacion": "subtarea_crear", "tarea_id": tarea_id, **json.loads(cuerpo_in.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        try:
            actualizada = tareas.agregar_subtarea(
                conexion,
                sesion.empresa_id,
                tarea_id,
                sesion.nombre,
                descripcion=cuerpo_in.descripcion,
                obligatoria=cuerpo_in.obligatoria,
            )
        except tareas.TareaNoEncontrada:
            return 403, {"detail": "acceso denegado"}
        except tareas.TareaConflicto as error:
            return 409, {"detail": str(error)}
        except tareas.TareaInvalida as error:
            return 422, {"detail": str(error)}
        return 201, actualizada

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, huella, operacion)


@router.post("/hotel/tareas/{tarea_id}/subtareas/{subtarea_id}")
def marcar_subtarea(
    tarea_id: str,
    subtarea_id: str,
    cuerpo_in: SubtareaEstadoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, tareas.ROLES_OPERACION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    huella = {
        "operacion": "subtarea_marcar",
        "tarea_id": tarea_id,
        "subtarea_id": subtarea_id,
        "completada": cuerpo_in.completada,
    }

    def operacion() -> tuple[int, dict]:
        try:
            actualizada = tareas.marcar_subtarea(
                conexion,
                sesion.empresa_id,
                tarea_id,
                subtarea_id,
                sesion.nombre,
                cuerpo_in.completada,
            )
        except tareas.TareaNoEncontrada:
            return 403, {"detail": "acceso denegado"}
        except tareas.TareaConflicto as error:
            return 409, {"detail": str(error)}
        return 200, actualizada

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, huella, operacion)
