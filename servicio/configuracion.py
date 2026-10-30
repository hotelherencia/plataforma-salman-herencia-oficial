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


def cargar_desde_entorno() -> Configuracion:
    _cargar_env()
    return Configuracion(
        host=os.environ.get("SERVICIO_HOST", "127.0.0.1"),
        puerto=int(os.environ.get("SERVICIO_PUERTO") or os.environ.get("PORT") or "8080"),
        database_url=os.environ.get("DATABASE_URL"),
        cookie_segura=os.environ.get("COOKIE_SEGURA", "0") == "1",
        origen_front=os.environ.get("ORIGEN_FRONT"),
        admin_usuario=os.environ.get("ADMIN_USUARIO"),
        admin_clave=os.environ.get("ADMIN_CLAVE"),
        session_horas=int(os.environ.get("SESSION_HORAS", "12")),
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        google_client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        google_redirect_uri=os.environ.get("GOOGLE_REDIRECT_URI") or "http://localhost:8080/auth/google/callback",
        admin_email=os.environ.get("ADMIN_EMAIL"),
        front_url=os.environ.get("FRONT_URL", "http://localhost:3000"),
    )
