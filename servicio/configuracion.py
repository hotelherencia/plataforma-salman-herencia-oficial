"""Configuración del servicio: solo variables de entorno, nunca un .env en el repo."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Configuracion:
    host: str
    puerto: int
    database_url: str | None
    cookie_segura: bool
    origen_front: str | None
    admin_usuario: str | None
    admin_clave: str | None


def cargar_desde_entorno() -> Configuracion:
    return Configuracion(
        host=os.environ.get("SERVICIO_HOST", "127.0.0.1"),
        puerto=int(os.environ.get("SERVICIO_PUERTO", "8080")),
        database_url=os.environ.get("DATABASE_URL"),
        cookie_segura=os.environ.get("COOKIE_SEGURA", "0") == "1",
        origen_front=os.environ.get("ORIGEN_FRONT"),
        admin_usuario=os.environ.get("ADMIN_USUARIO"),
        admin_clave=os.environ.get("ADMIN_CLAVE"),
    )
