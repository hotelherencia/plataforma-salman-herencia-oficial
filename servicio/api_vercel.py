"""Entrypoint ASGI para Vercel (modo services): expone `app`.

El `vercel.json` raíz enruta `/api/(.*)` a este servicio; el wrapper quita
el prefijo `/api` antes de enrutar, sin tocar ninguna ruta del API (también
funciona si la plataforma entrega la ruta ya sin prefijo). Con `DATABASE_URL`
configurada, la importación aplica migraciones y crea el admin inicial, igual
que el arranque local (`python -m servicio`, ver `docs/arquitectura/h7-despliegue.md`).
"""
from pathlib import Path
import sys

_RAIZ = str(Path(__file__).resolve().parents[1])
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from servicio.aplicacion import crear_app  # noqa: E402
from servicio.configuracion import cargar_desde_entorno  # noqa: E402

_instancia = crear_app(configuracion=cargar_desde_entorno())


class _QuitaPrefijoApi:
    def __init__(self, aplicacion):
        self._aplicacion = aplicacion

    async def __call__(self, scope, receive, send):
        ruta = scope.get("path", "")
        if scope.get("type") == "http" and (ruta == "/api" or ruta.startswith("/api/")):
            scope = dict(scope)
            scope["path"] = ruta[len("/api"):] or "/"
        await self._aplicacion(scope, receive, send)


app = _QuitaPrefijoApi(_instancia)
