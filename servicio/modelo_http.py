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
import urllib.error
import urllib.request

from .modelo_lenguaje import ModeloFallo

_INSTRUCCION = (
    "Eres el modelo del agente de reservas del hotel. Responde EXCLUSIVAMENTE "
    "con un objeto JSON de la forma {\"herramienta\": <nombre>, \"argumentos\": "
    "{...}} eligiendo una de las herramientas disponibles. Nada fuera del JSON."
)


class ModeloHttp:
    """Puerto ModeloLenguaje sobre un endpoint /chat/completions.

    `decidir` envía los mensajes con una instrucción que obliga a responder
    JSON, y devuelve {"herramienta", "argumentos"}. Cualquier desviación del
    contrato (HTTP != 200, cuerpo inválido, JSON sin la forma exigida) se
    reporta como ModeloFallo: el orquestador ya sabe reintentar una vez y
    escalar sin efectos (spec 005).
    """

    nombre = "http"

    def __init__(self, base_url: str, api_key: str, modelo: str = "modelo", timeout_seg: int = 30) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._modelo = modelo
        self._timeout = timeout_seg

    def decidir(self, mensajes: list[dict], herramientas: list[str]) -> dict:
        system = {"role": "system", "content": _INSTRUCCION + " Herramientas: " + ", ".join(herramientas)}
        cuerpo = json.dumps({
            "model": self._modelo,
            "messages": [system, *mensajes],
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
            with urllib.request.urlopen(peticion, timeout=self._timeout) as respuesta:
                payload = json.loads(respuesta.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            raise ModeloFallo(f"el modelo no respondió usable: {error}") from error
        try:
            contenido = payload["choices"][0]["message"]["content"]
            decision = json.loads(contenido)
            herramienta = decision["herramienta"]
            argumentos = decision["argumentos"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ModeloFallo(f"respuesta fuera del contrato decidir(): {error}") from error
        if not isinstance(herramienta, str) or not isinstance(argumentos, dict):
            raise ModeloFallo("respuesta fuera del contrato decidir(): tipos inválidos")
        return {"herramienta": herramienta, "argumentos": argumentos}
