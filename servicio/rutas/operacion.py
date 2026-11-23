"""Rutas del Corte 1 operativo: incidencias (#415), tareas y checklists (#416).
«Lo que necesita atención» (#417) viaja dentro de GET /hotel/indicadores."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Header, Path as RutaParam, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .. import cobro, operacion, roles, seguridad
from . import comun
from .hotel import _ejecutar_exclusivo

router = APIRouter()

ROLES_OPERACION = roles.con_admin_hotel("recepcion", roles.ASEO)
ROLES_GESTION = roles.con_admin_hotel("recepcion")
ROLES_PLANTILLAS = roles.con_admin_hotel()

Gravedad = Literal["baja", "media", "alta", "critica"]
Area = Literal["limpieza", "banos", "lavanderia", "desayunos", "mantencion", "general"]
Prioridad = Literal["baja", "normal", "alta", "urgente"]
PATRON_ID = r"^[A-Za-z0-9_-]{1,64}$"


class IncidenciaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    habitacion_id: str | None = Field(default=None, pattern=PATRON_ID)
    area: str | None = Field(default=None, min_length=2, max_length=60)
    descripcion: str = Field(min_length=3, max_length=1000)
    gravedad: Gravedad = "media"
    responsable: str | None = Field(default=None, max_length=80)
    plazo: date | None = None
    costo_clp: int | None = Field(default=None, ge=0, le=100_000_000)
    bloquea_disponibilidad: bool = False

    @model_validator(mode="after")
    def _ubicacion(self):
        if not self.habitacion_id and not self.area:
            raise ValueError("indica la habitación o el área")
        if self.bloquea_disponibilidad and not self.habitacion_id:
            raise ValueError("bloquear disponibilidad exige una habitación")
        return self


class IncidenciaCambioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: Literal["abierta", "en_curso", "resuelta"] | None = None
    gravedad: Gravedad | None = None
    responsable: str | None = Field(default=None, max_length=80)
    plazo: date | None = None
    costo_clp: int | None = Field(default=None, ge=0, le=100_000_000)


class IncidenciaCierreIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    costo_clp: int | None = Field(default=None, ge=0, le=100_000_000)
    nota: str | None = Field(default=None, max_length=300)


class EvidenciaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mime: Literal["image/jpeg", "image/png", "image/webp"]
    contenido_base64: str = Field(min_length=8, max_length=245_000)


class SubtareaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texto: str = Field(min_length=2, max_length=200)
    obligatoria: bool = True


class TareaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titulo: str = Field(min_length=2, max_length=160)
    area: Area = "general"
    habitacion_id: str | None = Field(default=None, pattern=PATRON_ID)
    prioridad: Prioridad = "normal"
    vence: date | None = None
    responsable: str | None = Field(default=None, max_length=80)
    observaciones: str | None = Field(default=None, max_length=1000)
    plantilla_id: str | None = Field(default=None, pattern=PATRON_ID)
    subtareas: list[SubtareaIn] = Field(default_factory=list, max_length=40)


class TareaCambioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titulo: str | None = Field(default=None, min_length=2, max_length=160)
    prioridad: Prioridad | None = None
    vence: date | None = None
    responsable: str | None = Field(default=None, max_length=80)
    observaciones: str | None = Field(default=None, max_length=1000)


class MarcadoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hecha: bool


class PlantillaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=2, max_length=120)
    area: Area = "general"
    items: list[SubtareaIn] = Field(min_length=1, max_length=40)


def _cuerpo(operacion_nombre: str, **extra) -> dict:
    return {"operacion": operacion_nombre, **json.loads(json.dumps(extra, default=str))}


def _ejecutar(request, sesion, conexion, idempotency_key, cuerpo, accion, recurso, funcion) -> JSONResponse:
    """Operación idempotente y auditada. `funcion(hotel)` devuelve el cuerpo de la respuesta."""
    clave = comun.clave_idempotencia_o_400(idempotency_key)

    def hacer() -> tuple[int, dict]:
        try:
            resultado = funcion(request.app.state.aplicacion.hotel)
        except operacion.NoEncontrado as error:
            return 404, {"detail": str(error)}
        except (operacion.OperacionInvalida, cobro.RecursoAjenoOInexistente) as error:
            return 409, {"detail": str(error)}
        seguridad.auditar(conexion, sesion.nombre, accion, resultado.get(recurso) or recurso, "ok")
        return 200, resultado

    return _ejecutar_exclusivo(conexion, sesion.empresa_id, clave, cuerpo, hacer)


# --- Incidencias (#415) ---

@router.get("/hotel/incidencias")
def listar_incidencias(
    estado: Literal["abiertas", "abierta", "en_curso", "resuelta", "cerrada"] | None = None,
    habitacion_id: str | None = Query(default=None, pattern=PATRON_ID),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    return operacion.listar_incidencias(conexion, estado, habitacion_id)


@router.post("/hotel/incidencias")
def crear_incidencia(
    request: Request,
    datos: IncidenciaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("incidencia", **datos.model_dump(mode="json")),
        "incidencia_creada", "incidencia_id",
        lambda hotel: operacion.crear_incidencia(conexion, hotel, sesion.empresa_id, sesion.nombre, datos.model_dump()),
    )


@router.get("/hotel/incidencias/{incidencia_id}")
def ver_incidencia(
    incidencia_id: str = RutaParam(pattern=PATRON_ID),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    try:
        return JSONResponse(operacion.obtener_incidencia(conexion, incidencia_id))
    except operacion.NoEncontrado as error:
        return JSONResponse(status_code=404, content={"detail": str(error)})


@router.post("/hotel/incidencias/{incidencia_id}/actualizacion")
def actualizar_incidencia(
    request: Request,
    cambios: IncidenciaCambioIn,
    incidencia_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    return _ejecutar(
        request, sesion, conexion, idempotency_key,
        _cuerpo("incidencia_actualizacion", incidencia_id=incidencia_id, **cambios.model_dump(mode="json")),
        "incidencia_actualizada", "incidencia_id",
        lambda hotel: operacion.actualizar_incidencia(
            conexion, hotel, sesion.empresa_id, sesion.nombre, incidencia_id, cambios.model_dump()),
    )


@router.post("/hotel/incidencias/{incidencia_id}/cierre")
def cerrar_incidencia(
    request: Request,
    cierre: IncidenciaCierreIn,
    incidencia_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_GESTION)
    return _ejecutar(
        request, sesion, conexion, idempotency_key,
        _cuerpo("incidencia_cierre", incidencia_id=incidencia_id, **cierre.model_dump(mode="json")),
        "incidencia_cerrada", "incidencia_id",
        lambda hotel: operacion.cerrar_incidencia(
            conexion, hotel, sesion.empresa_id, sesion.nombre, incidencia_id, cierre.costo_clp, cierre.nota),
    )


@router.post("/hotel/incidencias/{incidencia_id}/evidencias")
def subir_evidencia(
    request: Request,
    evidencia: EvidenciaIn,
    incidencia_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    huella = hashlib.sha256(evidencia.contenido_base64.encode()).hexdigest()
    return _ejecutar(
        request, sesion, conexion, idempotency_key,
        _cuerpo("incidencia_evidencia", incidencia_id=incidencia_id, mime=evidencia.mime, sha256=huella),
        "incidencia_evidencia", "evidencia_id",
        lambda hotel: operacion.agregar_evidencia(
            conexion, sesion.nombre, incidencia_id, evidencia.mime, evidencia.contenido_base64),
    )


@router.get("/hotel/incidencias/{incidencia_id}/evidencias/{evidencia_id}")
def ver_evidencia(
    incidencia_id: str = RutaParam(pattern=PATRON_ID),
    evidencia_id: str = RutaParam(pattern=PATRON_ID),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> Response:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    try:
        mime, contenido = operacion.leer_evidencia(conexion, incidencia_id, evidencia_id)
    except operacion.NoEncontrado as error:
        return JSONResponse(status_code=404, content={"detail": str(error)})
    return Response(content=contenido, media_type=mime, headers={"Cache-Control": "private, max-age=300"})


# --- Tareas generales y checklists (#416) ---

@router.get("/hotel/tareas")
def listar_tareas(
    estado: Literal["pendiente", "completada"] | None = None,
    habitacion_id: str | None = Query(default=None, pattern=PATRON_ID),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    return operacion.listar_tareas(conexion, estado, habitacion_id)


@router.post("/hotel/tareas")
def crear_tarea(
    request: Request,
    datos: TareaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_GESTION)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("tarea", **datos.model_dump(mode="json")),
        "tarea_creada", "tarea_id",
        lambda hotel: operacion.crear_tarea(conexion, sesion.nombre, datos.model_dump()),
    )


@router.post("/hotel/tareas/{tarea_id}/actualizacion")
def actualizar_tarea(
    request: Request,
    cambios: TareaCambioIn,
    tarea_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_GESTION)
    return _ejecutar(
        request, sesion, conexion, idempotency_key,
        _cuerpo("tarea_actualizacion", tarea_id=tarea_id, **cambios.model_dump(mode="json")),
        "tarea_actualizada", "tarea_id",
        lambda hotel: operacion.actualizar_tarea(conexion, tarea_id, cambios.model_dump()),
    )


@router.post("/hotel/tareas/{tarea_id}/subtareas")
def agregar_subtarea(
    request: Request,
    subtarea: SubtareaIn,
    tarea_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_GESTION)
    return _ejecutar(
        request, sesion, conexion, idempotency_key,
        _cuerpo("subtarea_alta", tarea_id=tarea_id, **subtarea.model_dump(mode="json")),
        "subtarea_agregada", "tarea_id",
        lambda hotel: operacion.agregar_subtarea(conexion, tarea_id, subtarea.texto, subtarea.obligatoria),
    )


@router.post("/hotel/tareas/{tarea_id}/subtareas/{subtarea_id}/marcado")
def marcar_subtarea(
    request: Request,
    marcado: MarcadoIn,
    tarea_id: str = RutaParam(pattern=PATRON_ID),
    subtarea_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    return _ejecutar(
        request, sesion, conexion, idempotency_key,
        _cuerpo("subtarea_marcado", tarea_id=tarea_id, subtarea_id=subtarea_id, hecha=marcado.hecha),
        "subtarea_marcada", "tarea_id",
        lambda hotel: operacion.marcar_subtarea(conexion, sesion.nombre, tarea_id, subtarea_id, marcado.hecha),
    )


@router.post("/hotel/tareas/{tarea_id}/cierre")
def cerrar_tarea(
    request: Request,
    tarea_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("tarea_cierre", tarea_id=tarea_id),
        "tarea_cerrada", "tarea_id",
        lambda hotel: operacion.cerrar_tarea(conexion, sesion.nombre, tarea_id),
    )


@router.get("/hotel/checklists/plantillas")
def listar_plantillas(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_OPERACION)
    return operacion.listar_plantillas(conexion)


@router.post("/hotel/checklists/plantillas")
def crear_plantilla(
    request: Request,
    datos: PlantillaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_PLANTILLAS)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("plantilla", **datos.model_dump(mode="json")),
        "plantilla_creada", "plantilla_id",
        lambda hotel: operacion.crear_plantilla(
            conexion, sesion.nombre, datos.nombre, datos.area, [i.model_dump() for i in datos.items]),
    )


@router.post("/hotel/habitaciones/{habitacion_id}/en-limpieza")
def iniciar_limpieza(
    request: Request,
    habitacion_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, cobro.ROLES_LIMPIEZA)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("en_limpieza", habitacion_id=habitacion_id),
        "limpieza_iniciada", "habitacion_id",
        lambda hotel: operacion.iniciar_limpieza(conexion, sesion.nombre, habitacion_id),
    )
