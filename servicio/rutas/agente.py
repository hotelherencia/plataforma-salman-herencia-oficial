"""Rutas del agente de reservas N0 (ARC-A01, #334; extraídas de aplicacion.py).

El modelo de lenguaje se lee de `request.app.state.modelo_agente` (puerto:
SinAdaptador sin guion → 503). Comportamiento idéntico a las closures
originales.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .. import agente
from .. import idempotencia
from .. import seguridad
from ..modelo_lenguaje import NoConfigurado
from . import comun
from .modelos import (
    AprobacionBorradorIn, ConsultaAgenteIn, DescarteBorradorIn, PoliticaAgenteIn,
)

router = APIRouter()

@router.post("/hotel/agente/consultas")
def registrar_consulta_agente(
    request: Request,
    cuerpo_consulta: ConsultaAgenteIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, agente.ROLES_GESTION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"canal_origen": cuerpo_consulta.canal_origen, "texto": cuerpo_consulta.texto}

    def operacion() -> tuple[int, dict]:
        consulta = agente.registrar_consulta(
            conexion, sesion.empresa_id, cuerpo_consulta.canal_origen,
            cuerpo_consulta.texto, sesion.nombre,
        )
        politica = agente.politica_de(conexion, sesion.empresa_id)
        try:
            resultado = agente.procesar(conexion, consulta, request.app.state.modelo_agente, politica)
        except NoConfigurado:
            return 503, {"detail": "modelo no configurado", "estado": "pendiente", "consulta": consulta}
        detalle = agente.detalle_consulta(conexion, sesion.empresa_id, consulta["consulta_id"])
        if resultado.get("estado") == "escalado":
            return 201, {"consulta": detalle, "motivo": resultado["motivo"]}
        return 201, {"consulta": detalle, "borrador": resultado}

    codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

@router.get("/hotel/agente/consultas")
def bandeja_consultas_agente(
    estado: str | None = None,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, agente.ROLES_GESTION)
    return agente.listar_consultas(conexion, sesion.empresa_id, estado)

@router.get("/hotel/agente/consultas/{consulta_id}")
def detalle_consulta_agente(
    consulta_id: str,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, agente.ROLES_GESTION)
    return agente.detalle_consulta(conexion, sesion.empresa_id, consulta_id)

@router.post("/hotel/agente/borradores/{borrador_id}/aprobacion")
def aprobar_borrador_agente(
    borrador_id: str,
    cuerpo_aprobacion: AprobacionBorradorIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, agente.ROLES_GESTION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"borrador_id": borrador_id, "texto_editado": cuerpo_aprobacion.texto_editado}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = agente.aprobar(
                conexion, sesion.empresa_id, borrador_id, sesion.nombre,
                cuerpo_aprobacion.texto_editado, datetime.now(),
            )
        except agente.ConsultaAjenaOInexistente:
            return 403, {"detail": "acceso denegado"}
        except agente.TransicionInvalida as error:
            return 409, {"detail": str(error)}
        if resultado.get("estado") == "oferta_cambiada":
            return 409, {"detail": resultado["detail"], "borrador": resultado["borrador"]}
        return 200, resultado

    codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

@router.post("/hotel/agente/borradores/{borrador_id}/descarte")
def descartar_borrador_agente(
    borrador_id: str,
    cuerpo_descarte: DescarteBorradorIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, agente.ROLES_GESTION)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"borrador_id": borrador_id, "motivo": cuerpo_descarte.motivo}

    def operacion() -> tuple[int, dict]:
        try:
            resultado = agente.descartar(
                conexion, sesion.empresa_id, borrador_id, cuerpo_descarte.motivo, sesion.nombre
            )
        except agente.ConsultaAjenaOInexistente:
            return 403, {"detail": "acceso denegado"}
        except agente.TransicionInvalida as error:
            return 409, {"detail": str(error)}
        return 200, resultado

    codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

@router.get("/hotel/agente/politica")
def obtener_politica_agente(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_rol(sesion, agente.ROLES_GESTION)
    return {"empresa_id": sesion.empresa_id, **agente.politica_de(conexion, sesion.empresa_id)}

@router.put("/hotel/agente/politica")
def actualizar_politica_agente(
    cuerpo_politica: PoliticaAgenteIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_rol(sesion, {"administrador"})
    try:
        resultado = agente.actualizar_politica(
            conexion, sesion.empresa_id, cuerpo_politica.model_dump(exclude_none=True), sesion.nombre
        )
    except agente.ConsultaInvalida as error:
        return JSONResponse(status_code=400, content={"detail": error.detalle})
    except agente.PoliticaInvalida as error:
        return JSONResponse(status_code=409, content={"detail": error.detalle})
    conexion.commit()
    return JSONResponse(status_code=200, content=resultado)
