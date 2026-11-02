"""Entrypoint que el preset FastAPI de Vercel (CLI 65) pide en la raíz.

El build falla con FASTAPI_ENTRYPOINT_NOT_FOUND si `pyproject.toml` no
declara `[tool.vercel] entrypoint = "api_vercel:app"`. La aplicación vive
en `servicio/api_vercel.py`; este módulo solo la reexporta.
"""
from servicio.api_vercel import app

__all__ = ["app"]
