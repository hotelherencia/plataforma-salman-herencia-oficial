"""Rutas de la biblioteca documental y el buzón de sugerencias (#418, Corte 2)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, Request
from fastapi import Path as RutaParam
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .. import biblioteca, roles, seguridad
from . import comun
from .operacion import PATRON_ID, ROLES_PLANTILLAS, _cuerpo, _ejecutar

router = APIRouter()

Categoria = Literal["manual", "instructivo", "politica", "otro"]


class DocumentoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titulo: str = Field(min_length=3, max_length=120)
    categoria: Categoria
    contenido: str = Field(default="", max_length=20000)
    enlace: str | None = Field(default=None, max_length=500, pattern=r"^https://\S+$")
    roles: list[Literal["administrador", "admin_hotel", "recepcion", "caja", "aseo"]] = Field(default_factory=list, max_length=6)


class SugerenciaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texto: str = Field(min_length=3, max_length=1000)


class AtencionSugerenciaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    respuesta: str | None = Field(default=None, max_length=500)


@router.get("/hotel/biblioteca")
def listar_biblioteca(
    categoria: Categoria | None = None,
    archivados: bool = False,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    incluir = archivados and sesion.rol in roles.ROLES_ADMIN_HOTEL
    return biblioteca.listar(conexion, sesion.rol, categoria=categoria, incluir_archivados=incluir)


@router.post("/hotel/biblioteca")
def publicar_documento(
    request: Request,
    datos: DocumentoIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_PLANTILLAS)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("documento", **datos.model_dump(mode="json")),
        "documento_publicado", "documento_id",
        lambda hotel: biblioteca.publicar(conexion, sesion.nombre, datos.model_dump()),
    )


@router.post("/hotel/biblioteca/{documento_id}/archivo")
def archivar_documento(
    request: Request,
    documento_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_PLANTILLAS)
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("documento_archivo", documento_id=documento_id),
        "documento_archivado", "documento_id",
        lambda hotel: biblioteca.archivar(conexion, documento_id),
    )


@router.post("/hotel/sugerencias")
def enviar_sugerencia(
    request: Request,
    datos: SugerenciaIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    return _ejecutar(
        request, sesion, conexion, idempotency_key, _cuerpo("sugerencia", **datos.model_dump()),
        "sugerencia_enviada", "sugerencia_id",
        lambda hotel: biblioteca.sugerir(conexion, sesion.nombre, datos.texto),
    )


@router.get("/hotel/sugerencias")
def listar_sugerencias(
    estado: Literal["nueva", "atendida"] | None = None,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, ROLES_PLANTILLAS)
    return biblioteca.listar_sugerencias(conexion, estado)


@router.post("/hotel/sugerencias/{sugerencia_id}/atencion")
def atender_sugerencia(
    request: Request,
    datos: AtencionSugerenciaIn,
    sugerencia_id: str = RutaParam(pattern=PATRON_ID),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, ROLES_PLANTILLAS)
    return _ejecutar(
        request, sesion, conexion, idempotency_key,
        _cuerpo("sugerencia_atencion", sugerencia_id=sugerencia_id, **datos.model_dump()),
        "sugerencia_atendida", "sugerencia_id",
        lambda hotel: biblioteca.atender_sugerencia(conexion, sugerencia_id, sesion.nombre, datos.respuesta),
    )
