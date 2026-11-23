"""Rutas del Corte 2 Operativo P1 (#418 parte 2 — ref. Orquestia):
turnos semanales, cambios de turno aprobados, biblioteca por rol,
buzón de sugerencias e inventario de activos con mantenimiento preventivo.
(Comunicados con confirmación de lectura viven en servicio/rutas/operacion.py.)"""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Path as RutaParam, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .. import corte2_operacion, roles, seguridad
from . import comun

router = APIRouter()

ROLES_EQUIPO = roles.con_admin_hotel("recepcion", "caja", roles.ASEO)
ROLES_ADMIN_HOTEL = roles.con_admin_hotel()
ROLES_MANTENCION = roles.con_admin_hotel("recepcion", roles.ASEO)

AreaTurno = Literal["recepcion", "aseo", "desayunos", "mantencion"]
CategoriaBiblioteca = Literal["manual", "instructivo", "politica", "protocolo"]
CategoriaSugerencia = Literal["operacion", "mantencion", "huespedes", "equipo", "otro"]
EstadoSugerencia = Literal["recibida", "en_revision", "implementada", "archivada"]
EstadoActivo = Literal["operativo", "en_mantencion", "fuera_de_servicio", "baja"]
TipoMantencion = Literal["preventiva", "correctiva"]
PATRON_HORA = r"^\d{2}:\d{2}$"
PATRON_ID = r"^[A-Za-z0-9_-]{1,64}$"


class TurnoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    usuario_nombre: str = Field(min_length=2, max_length=80)
    area: AreaTurno
    fecha: date
    hora_inicio: str = Field(pattern=PATRON_HORA)
    hora_fin: str = Field(pattern=PATRON_HORA)
    nota: str = Field(default="", max_length=300)


class CambioTurnoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reemplazo_usuario: str = Field(min_length=2, max_length=80)
    motivo: str = Field(min_length=5, max_length=300)


class DecisionCambioTurnoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["aprobado", "rechazado"]
    nota_revision: str = Field(default="", max_length=300)


class DocumentoBibliotecaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titulo: str = Field(min_length=3, max_length=160)
    categoria: CategoriaBiblioteca = "manual"
    rol_objetivo: str = Field(default="todos", min_length=2, max_length=40)
    contenido: str = Field(min_length=5, max_length=10000)
    version: str = Field(default="1.0", min_length=1, max_length=24)


class SugerenciaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria: CategoriaSugerencia = "operacion"
    mensaje: str = Field(min_length=5, max_length=2000)
    anonimo: bool = False


class EstadoSugerenciaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: EstadoSugerencia
    respuesta_admin: str = Field(default="", max_length=1000)


class ActivoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=2, max_length=140)
    categoria: str = Field(default="equipamiento", min_length=2, max_length=60)
    habitacion_id: str | None = Field(default=None, pattern=PATRON_ID)
    area: str | None = Field(default=None, min_length=2, max_length=60)
    numero_serie: str = Field(default="", max_length=80)
    frecuencia_mantencion_dias: int | None = Field(default=None, ge=1, le=3650)
    ultima_mantencion: date | None = None
    proxima_mantencion: date | None = None
    notas: str = Field(default="", max_length=600)

    @model_validator(mode="after")
    def _ubicacion(self):
        if not self.habitacion_id and not self.area:
            raise ValueError("indica la habitación o el área")
        return self


class MantencionActivoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fecha_realizada: date | None = None
    tipo: TipoMantencion = "preventiva"
    descripcion: str = Field(min_length=3, max_length=1000)
    costo_clp: int = Field(default=0, ge=0, le=100_000_000)
    nuevo_estado: EstadoActivo | None = None


# ----------------------------- Turnos -----------------------------


@router.get("/hotel/equipo/turnos")
def listar_turnos(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    area: str | None = Query(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_EQUIPO)
    return corte2_operacion.listar_turnos_semana(
        conn, sesion.empresa_id, desde=desde, hasta=hasta, area=area
    )


@router.post("/hotel/equipo/turnos", status_code=201)
def crear_turno(
    cuerpo: TurnoIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_ADMIN_HOTEL)
    return corte2_operacion.crear_turno(
        conn,
        sesion.empresa_id,
        usuario_nombre=cuerpo.usuario_nombre,
        area=cuerpo.area,
        fecha=cuerpo.fecha,
        hora_inicio=cuerpo.hora_inicio,
        hora_fin=cuerpo.hora_fin,
        nota=cuerpo.nota,
        actor=sesion.nombre,
    )


@router.post("/hotel/equipo/turnos/{turno_id}/cambios", status_code=201)
def solicitar_cambio(
    cuerpo: CambioTurnoIn,
    turno_id: int = RutaParam(ge=1),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_EQUIPO)
    return corte2_operacion.solicitar_cambio_turno(
        conn,
        sesion.empresa_id,
        turno_id,
        reemplazo_usuario=cuerpo.reemplazo_usuario,
        motivo=cuerpo.motivo,
        actor=sesion.nombre,
    )


@router.post("/hotel/equipo/cambios-turno/{cambio_id}/decision")
def resolver_cambio(
    cuerpo: DecisionCambioTurnoIn,
    cambio_id: int = RutaParam(ge=1),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_ADMIN_HOTEL)
    return corte2_operacion.resolver_cambio_turno(
        conn,
        sesion.empresa_id,
        cambio_id,
        decision=cuerpo.decision,
        nota_revision=cuerpo.nota_revision,
        actor=sesion.nombre,
    )


# ---------------------- Biblioteca y sugerencias ----------------------


@router.get("/hotel/equipo/biblioteca")
def listar_biblioteca(
    categoria: str | None = Query(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_EQUIPO)
    return corte2_operacion.listar_biblioteca(
        conn, sesion.empresa_id, rol_usuario=sesion.rol, categoria=categoria
    )


@router.post("/hotel/equipo/biblioteca", status_code=201)
def crear_documento(
    cuerpo: DocumentoBibliotecaIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_ADMIN_HOTEL)
    return corte2_operacion.crear_documento_biblioteca(
        conn,
        sesion.empresa_id,
        titulo=cuerpo.titulo,
        categoria=cuerpo.categoria,
        rol_objetivo=cuerpo.rol_objetivo,
        contenido=cuerpo.contenido,
        version=cuerpo.version,
        actor=sesion.nombre,
    )


@router.get("/hotel/equipo/sugerencias")
def listar_sugerencias(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_EQUIPO)
    return corte2_operacion.listar_sugerencias(
        conn,
        sesion.empresa_id,
        usuario_nombre=sesion.nombre,
        es_admin=roles.es_admin_hotel(sesion.rol),
    )


@router.post("/hotel/equipo/sugerencias", status_code=201)
def crear_sugerencia(
    cuerpo: SugerenciaIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_EQUIPO)
    return corte2_operacion.crear_sugerencia(
        conn,
        sesion.empresa_id,
        categoria=cuerpo.categoria,
        mensaje=cuerpo.mensaje,
        anonimo=cuerpo.anonimo,
        actor=sesion.nombre,
    )


@router.post("/hotel/equipo/sugerencias/{sugerencia_id}/estado")
def actualizar_sugerencia(
    cuerpo: EstadoSugerenciaIn,
    sugerencia_id: int = RutaParam(ge=1),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_ADMIN_HOTEL)
    return corte2_operacion.actualizar_estado_sugerencia(
        conn,
        sesion.empresa_id,
        sugerencia_id,
        estado=cuerpo.estado,
        respuesta_admin=cuerpo.respuesta_admin,
        actor=sesion.nombre,
    )


# ---------------------- Activos y preventivo ----------------------


@router.get("/hotel/activos")
def listar_activos(
    habitacion_id: str | None = Query(default=None),
    estado: str | None = Query(default=None),
    solo_vencidos: bool = Query(default=False),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_EQUIPO)
    return corte2_operacion.listar_activos(
        conn,
        sesion.empresa_id,
        habitacion_id=habitacion_id,
        estado=estado,
        solo_vencidos=solo_vencidos,
    )


@router.post("/hotel/activos", status_code=201)
def crear_activo(
    cuerpo: ActivoIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_ADMIN_HOTEL)
    return corte2_operacion.crear_activo(
        conn,
        sesion.empresa_id,
        nombre=cuerpo.nombre,
        categoria=cuerpo.categoria,
        habitacion_id=cuerpo.habitacion_id,
        area=cuerpo.area,
        numero_serie=cuerpo.numero_serie,
        frecuencia_mantencion_dias=cuerpo.frecuencia_mantencion_dias,
        ultima_mantencion=cuerpo.ultima_mantencion,
        proxima_mantencion=cuerpo.proxima_mantencion,
        notas=cuerpo.notas,
        actor=sesion.nombre,
    )


@router.post("/hotel/activos/{activo_id}/mantenciones", status_code=201)
def registrar_mantencion(
    cuerpo: MantencionActivoIn,
    activo_id: int = RutaParam(ge=1),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conn=Depends(comun.conexion),
):
    comun.exigir_rol(sesion, ROLES_MANTENCION)
    return corte2_operacion.registrar_mantencion_activo(
        conn,
        sesion.empresa_id,
        activo_id,
        fecha_realizada=cuerpo.fecha_realizada,
        tipo=cuerpo.tipo,
        descripcion=cuerpo.descripcion,
        costo_clp=cuerpo.costo_clp,
        nuevo_estado=cuerpo.nuevo_estado,
        actor=sesion.nombre,
    )
