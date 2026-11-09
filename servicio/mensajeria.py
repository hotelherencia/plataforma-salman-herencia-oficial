"""Puerto de entrada de WhatsApp (spec 006, #324).

Vive en el servicio, no en el front. Sin las tres variables el proceso deja
el puerto en None y el webhook responde 503 «no configurado». Con el puerto,
la firma y el número se comprueban aquí; el hotel solo recibe una consulta
redactada. Este módulo no llama a Meta.
"""
import hashlib
import hmac
from dataclasses import dataclass

import psycopg

from . import agente
from .modelo_lenguaje import NoConfigurado


class NumeroNoAutorizado(Exception):
    """403: el phone_number_id del aviso no es el del puerto."""


@dataclass(frozen=True)
class PuertoWhatsapp:
    app_secret: str
    verify_token: str
    phone_number_id: str


def firma_valida(cuerpo: bytes, encabezado: str | None, secreto: str) -> bool:
    if not encabezado or not encabezado.startswith("sha256="):
        return False
    esperado = hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
    recibido = encabezado[len("sha256="):].lower()
    if len(recibido) != len(esperado):
        return False
    return hmac.compare_digest(esperado, recibido)


def mensajes_de_texto(payload: dict, phone_number_id: str) -> list[dict]:
    """Texto normalizado. Adjuntos y estados de entrega no entran.

    Si el aviso trae un phone_number_id distinto del autorizado, rechaza el
    aviso entero antes de mirar los mensajes."""
    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        return []
    salida: list[dict] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            meta = (value.get("metadata") or {}).get("phone_number_id")
            if meta != phone_number_id:
                raise NumeroNoAutorizado()
            for mensaje in value.get("messages") or []:
                if mensaje.get("type") != "text":
                    continue
                texto = ((mensaje.get("text") or {}).get("body") or "").strip()
                id_externo = (mensaje.get("id") or "").strip()
                conversacion = (mensaje.get("from") or "").strip()
                if not texto or not id_externo or not conversacion:
                    continue
                salida.append({
                    "id_externo": id_externo,
                    "conversacion": conversacion,
                    "texto": texto,
                })
    return salida


def consulta_de_mensaje(conexion: psycopg.Connection, id_externo: str) -> str | None:
    fila = conexion.execute(
        "SELECT consulta_id FROM mensajes_whatsapp WHERE id_externo = %s",
        (id_externo,),
    ).fetchone()
    return fila[0] if fila else None


def registrar_entrada(
    conexion: psycopg.Connection, empresa_id: str, mensaje: dict, modelo,
) -> str:
    """Persiste la consulta y el id externo. Un id repetido devuelve la
    consulta original. Sin modelo, la consulta queda pendiente."""
    previo = conexion.execute(
        "SELECT c.texto_redactado FROM mensajes_whatsapp m "
        "JOIN consultas_agente c ON c.id = m.consulta_id "
        "WHERE m.empresa_id = %s AND m.conversacion_externa = %s "
        "ORDER BY m.recibido_en DESC, m.id_externo DESC LIMIT 1",
        (empresa_id, mensaje["conversacion"]),
    ).fetchone()
    texto = f"{previo[0]}\n{mensaje['texto']}" if previo else mensaje["texto"]
    try:
        with conexion.transaction():
            consulta = agente.registrar_consulta(
                conexion, empresa_id, "whatsapp", texto, "whatsapp",
            )
            conexion.execute(
                "INSERT INTO mensajes_whatsapp (id_externo, empresa_id, conversacion_externa, consulta_id) "
                "VALUES (%s, %s, %s, %s)",
                (mensaje["id_externo"], empresa_id, mensaje["conversacion"], consulta["consulta_id"]),
            )
    except psycopg.errors.UniqueViolation:
        existente = consulta_de_mensaje(conexion, mensaje["id_externo"])
        if existente is None:
            raise
        return existente
    politica = agente.politica_de(conexion, empresa_id)
    try:
        agente.procesar(
            conexion, consulta, modelo, politica, texto_original=mensaje["texto"], canal=None,
        )
    except NoConfigurado:
        pass
    return consulta["consulta_id"]
