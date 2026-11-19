"""Adaptador HTTP genérico del puerto del modelo (spec 005, avance de #319).

D-AGT-02 (proveedor concreto) sigue pendiente del propietario: este módulo
implementa el contrato `decidir()` contra CUALQUIER endpoint compatible con
la API de chat completions (OpenAI y compatibles), configurado por entorno.
Sin `MODELO_BASE_URL` + `MODELO_API_KEY` el proceso arranca con `SinAdaptador`
(503 «modelo no configurado»): activar un proveedor real = fijar esas
variables, que es la decisión D-AGT-02 en sí. Las pruebas usan un servidor
HTTP local (sin red externa, NFR-A04) y la evaluación de 50 casos (SC-003)
mide a este adaptador igual que al grabado cuando el proveedor se nombre.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from .modelo_lenguaje import ModeloFallo

_ZONA_CL = ZoneInfo("America/Santiago")
_RE_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")


def _mensaje_openai(mensaje: dict) -> dict:
    """El orquestador habla {rol, texto}; el endpoint exige {role, content}.

    Si el mensaje ya viene en la forma del endpoint, se reenvía tal cual.
    """
    if "role" in mensaje and "content" in mensaje:
        return {"role": mensaje["role"], "content": mensaje["content"]}
    rol = mensaje.get("rol") or "user"
    return {"role": rol, "content": mensaje.get("texto", "")}


_INSTRUCCION = (
    "Eres el modelo del agente de reservas del hotel. Responde EXCLUSIVAMENTE "
    "con un objeto JSON de la forma {\"herramienta\": <nombre>, \"argumentos\": "
    "{...}} eligiendo una de las herramientas disponibles. Nada fuera del JSON. "
    "Esquemas: "
    "consultar_disponibilidad={inicio:'YYYY-MM-DD',fin:'YYYY-MM-DD',personas:int}; "
    "consultar_politicas={tema:'general|llegada_salida|cancelacion|estacionamiento|desayuno|mascotas|ninos|pagos|ubicacion'}; "
    "crear_solicitud={inicio:'YYYY-MM-DD',fin:'YYYY-MM-DD',personas:int,tipo:str,nombre:str,contacto:str}; "
    "proponer_borrador={plantilla:'cotizacion|sin_disponibilidad|pedir_dato|informacion|escalar',campos:{...},saludo:str}. "
    "No inventes cifras ni precios en saludo."
)


# SA-MH-01 (auditoría 2026-11-17): la API key viaja en Authorization. urllib
# sigue redirecciones 301/302/303 y reenvía esa cabecera al nuevo host; por
# eso este adaptador no sigue ninguna, exige https salvo loopback y acota la
# respuesta (un endpoint caído o hostil no llena la memoria del proceso).
TOPE_RESPUESTA_BYTES = 1024 * 1024
_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_ABRIDOR = urllib.request.build_opener(_SinRedirecciones)


def _validar_base_url(base_url: str) -> None:
    partes = urllib.parse.urlsplit(base_url)
    if partes.scheme == "https" and partes.hostname:
        return
    if partes.scheme == "http" and partes.hostname in _LOOPBACK:
        return
    raise ValueError("MODELO_BASE_URL debe ser https (http solo en loopback de pruebas)")


class ModeloHttp:
    """Puerto ModeloLenguaje sobre un endpoint /chat/completions.

    `decidir` traduce los mensajes del orquestador ({rol, texto}) al formato
    del endpoint ({role, content}), añade la instrucción que obliga a
    responder JSON, y devuelve {"herramienta", "argumentos"}. Cualquier desviación del
    contrato (HTTP != 200, cuerpo inválido, JSON sin la forma exigida) se
    reporta como ModeloFallo: el orquestador ya sabe reintentar una vez y
    escalar sin efectos (spec 005).
    """

    nombre = "http"

    def __init__(self, base_url: str, api_key: str, modelo: str = "modelo", timeout_seg: int = 30) -> None:
        _validar_base_url(base_url)
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._modelo = modelo
        self._timeout = timeout_seg

    def decidir(self, mensajes: list[dict], herramientas: list[str]) -> dict:
        hoy_cl = datetime.now(_ZONA_CL).date().isoformat()
        system = {
            "role": "system",
            "content": f"{_INSTRUCCION} Fecha actual (Chile): {hoy_cl}. Herramientas: {', '.join(herramientas)}",
        }
        cuerpo = json.dumps({
            "model": self._modelo,
            "messages": [system, *[_mensaje_openai(m) for m in mensajes]],
            "temperature": 0,
        }).encode("utf-8")
        peticion = urllib.request.Request(
            self._url,
            data=cuerpo,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with _ABRIDOR.open(peticion, timeout=self._timeout) as respuesta:
                crudo = respuesta.read(TOPE_RESPUESTA_BYTES + 1)
                if len(crudo) > TOPE_RESPUESTA_BYTES:
                    raise ValueError("respuesta del modelo demasiado grande")
                payload = json.loads(crudo.decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            cerrar = getattr(error, "close", None)
            if cerrar is not None:
                cerrar()
            raise ModeloFallo(f"el modelo no respondió usable: {error}") from error
        try:
            contenido = _RE_FENCE.sub("", str(payload["choices"][0]["message"]["content"]).strip())
            decision = json.loads(contenido)
            herramienta = decision["herramienta"]
            argumentos = decision["argumentos"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ModeloFallo(f"respuesta fuera del contrato decidir(): {error}") from error
        if not isinstance(herramienta, str) or not isinstance(argumentos, dict):
            raise ModeloFallo("respuesta fuera del contrato decidir(): tipos inválidos")
        return {"herramienta": herramienta, "argumentos": argumentos}
