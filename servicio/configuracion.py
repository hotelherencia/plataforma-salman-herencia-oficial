"""Configuración del servicio: variables de entorno, nunca un .env en el repo.

El .env local (ignorado por git) se carga si existe, con stdlib y sin
imprimir valores: las variables ya presentes en el entorno del proceso
mandan sobre las del archivo. Los secretos viven ahí o en las variables del
despliegue (Railway/Vercel), jamás en el código.
"""
import os
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _cargar_env(archivo: Path = RAIZ / ".env") -> None:
    """Define en os.environ las claves del .env que aún no existan."""
    if not archivo.is_file():
        return
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        clave = clave.strip()
        valor = valor.strip().strip('"').strip("'")
        if clave and clave not in os.environ:
            os.environ[clave] = valor


@dataclass(frozen=True)
class Configuracion:
    host: str
    puerto: int
    database_url: str | None
    cookie_segura: bool
    origen_front: str | None
    admin_usuario: str | None
    admin_clave: str | None
    session_horas: int = 12
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8080/auth/google/callback"
    admin_email: str | None = None
    front_url: str = "http://localhost:3000"
    origen_landing: str | None = None
    publico_max_por_minuto: int = 6
    agente_guion_json: str | None = None
    # Modelo del agente vía HTTP (spec 005, #319): con ambas variables el
    # proceso arranca con ModeloHttp contra un endpoint OpenAI-compatible;
    # sin ellas sigue SinAdaptador (503). Nombra el proveedor = D-AGT-02.
    modelo_base_url: str | None = None
    modelo_api_key: str | None = None
    modelo_nombre: str | None = None
    # Puerto WhatsApp (spec 006, #324). Las tres juntas encienden el webhook;
    # falta una y el puerto sigue apagado (503, sin persistir).
    whatsapp_app_secret: str | None = None
    whatsapp_verify_token: str | None = None
    whatsapp_phone_number_id: str | None = None


def _normalizar_origenes(valor: str | None) -> str | None:
    """ORIGEN_FRONT sin barras finales ni espacios (una vez por origen).

    La barra final cambia la identidad del origen en CORS y en el middleware
    de mutaciones: «https://front.example/» y «https://front.example» deben
    ser el mismo origen (test_preh7_seguridad; el redirect de Google del
    2026-11-02 falló por exactamente esto)."""
    if not valor:
        return valor
    origenes = [o.strip().rstrip("/") for o in valor.split(",") if o.strip()]
    return ",".join(origenes) if origenes else None


def cargar_desde_entorno() -> Configuracion:
    _cargar_env()
    return Configuracion(
        host=os.environ.get("SERVICIO_HOST", "127.0.0.1"),
        puerto=int(os.environ.get("SERVICIO_PUERTO") or os.environ.get("PORT") or "8080"),
        database_url=os.environ.get("DATABASE_URL"),
        cookie_segura=os.environ.get("COOKIE_SEGURA", "0") == "1",
        origen_front=_normalizar_origenes(os.environ.get("ORIGEN_FRONT")),
        admin_usuario=os.environ.get("ADMIN_USUARIO"),
        admin_clave=os.environ.get("ADMIN_CLAVE"),
        session_horas=int(os.environ.get("SESSION_HORAS", "12")),
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        google_client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        google_redirect_uri=os.environ.get("GOOGLE_REDIRECT_URI") or "http://localhost:8080/auth/google/callback",
        admin_email=os.environ.get("ADMIN_EMAIL"),
        front_url=os.environ.get("FRONT_URL", "http://localhost:3000"),
        origen_landing=_normalizar_origenes(os.environ.get("ORIGEN_LANDING")),
        publico_max_por_minuto=int(os.environ.get("PUBLICO_MAX_POR_MINUTO", "6")),
        agente_guion_json=os.environ.get("AGENTE_GUION_JSON"),
        modelo_base_url=os.environ.get("MODELO_BASE_URL"),
        modelo_api_key=os.environ.get("MODELO_API_KEY"),
        modelo_nombre=os.environ.get("MODELO_NOMBRE"),
        whatsapp_app_secret=os.environ.get("WHATSAPP_APP_SECRET"),
        whatsapp_verify_token=os.environ.get("WHATSAPP_VERIFY_TOKEN"),
        whatsapp_phone_number_id=os.environ.get("WHATSAPP_PHONE_NUMBER_ID"),
    )
