"""Webhook del puerto WhatsApp (spec 006, #324). Sin sesión: la firma ocupa
su lugar. Sin puerto configurado responde 503 y no toca la base."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from .. import mensajeria
from . import comun

router = APIRouter()


def _puerto(request: Request) -> mensajeria.PuertoWhatsapp:
    puerto = getattr(request.app.state, "mensajeria", None)
    if puerto is None:
        raise HTTPException(status_code=503, detail="no configurado")
    return puerto


@router.get("/mensajeria/whatsapp/webhook")
def verificar_webhook(
    request: Request,
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
) -> Response:
    puerto = _puerto(request)
    if hub_mode != "subscribe" or hub_verify_token != puerto.verify_token or not hub_challenge:
        raise HTTPException(status_code=403, detail="acceso denegado")
    return Response(content=hub_challenge, media_type="text/plain")


@router.post("/mensajeria/whatsapp/webhook")
async def recibir_webhook(
    request: Request,
    conexion=Depends(comun.conexion),
) -> dict:
    puerto = _puerto(request)
    cuerpo = await request.body()
    if not mensajeria.firma_valida(cuerpo, request.headers.get("x-hub-signature-256"), puerto.app_secret):
        raise HTTPException(status_code=403, detail="acceso denegado")
    try:
        payload = json.loads(cuerpo)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="cuerpo invalido")
    try:
        mensajes = mensajeria.mensajes_de_texto(payload, puerto.phone_number_id)
    except mensajeria.NumeroNoAutorizado:
        raise HTTPException(status_code=403, detail="acceso denegado")
    freno = request.app.state.freno_solicitudes
    empresa_id = request.app.state.aplicacion.nucleo.empresa.id
    modelo = request.app.state.modelo_agente
    consultas: list[str] = []
    for mensaje in mensajes:
        existente = mensajeria.consulta_de_mensaje(conexion, mensaje["id_externo"])
        if existente:
            consultas.append(existente)
            continue
        if not freno.permite(mensaje["conversacion"]):
            raise HTTPException(
                status_code=429,
                detail="demasiados mensajes; espera un minuto e intenta de nuevo",
            )
        consultas.append(mensajeria.registrar_entrada(conexion, empresa_id, mensaje, modelo))
    conexion.commit()
    return {"recibidos": len(consultas), "consultas": consultas}
