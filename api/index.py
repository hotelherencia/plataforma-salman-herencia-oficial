"""Entrypoint FastAPI en ruta convencional para el build de Vercel.

El build de Vercel exige el `app` en una ruta estándar (`api/index.py`,
`main.py`, `app.py`, …) o en `tool.vercel.entrypoint` de `pyproject.toml`;
sin eso falla con `FASTAPI_ENTRYPOINT_NOT_FOUND` aunque `vercel.json`
declare un entrypoint dentro de `services`. Aquí se cubren ambas vías.
La aplicación real se arma en `servicio/api_vercel.py` (H7/T4b).
"""
from servicio.api_vercel import app

__all__ = ["app"]
