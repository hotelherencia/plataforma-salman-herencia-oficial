"""Ruta versionada de exportación de solo lectura hacia PEI CORE (`core.finance.v1.1`).

Seguridad:
- Autenticación servicio-a-servicio por Bearer token dedicado (`CORE_EXPORT_TOKEN`),
  comparación en tiempo constante (`hmac.compare_digest`).
- Fail-closed: si `CORE_EXPORT_TOKEN` no está configurado responde 503.
- Alcance mínimo: solo `GET` con scope `finance:read` y empresa fija del servicio.
- Cero efectos financieros: la exportación corre en `BEGIN TRANSACTION READ ONLY`.
"""
from __future__ import annotations

import hmac
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from .. import exportacion_core, seguridad
from . import comun

router = APIRouter()

REQUIRED_SCOPE = "finance:read"


def _validar_token_core(
    request: Request,
    authorization: str | None = Header(default=None),
    x_core_scope: str | None = Header(default=None),
) -> str:
    config = getattr(request.app.state, "configuracion", None)
    token_esperado = getattr(config, "core_export_token", None) if config else None
    if not token_esperado:
        raise HTTPException(status_code=503, detail="exportación CORE no configurada")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="credencial de servicio requerida")
    token_recibido = authorization[7:].strip()
    if not token_recibido or not hmac.compare_digest(token_recibido.encode("utf-8"), token_esperado.encode("utf-8")):
        raise HTTPException(status_code=401, detail="credencial de servicio inválida")

    if x_core_scope is not None and x_core_scope.strip() != REQUIRED_SCOPE:
        raise HTTPException(status_code=403, detail="alcance de servicio insuficiente")

    return "servicio:pei-core"


@router.get("/integrations/core/v1/finance-export")
def exportar_finanzas_core(
    request: Request,
    resource: str = Query(pattern="^(reservations|payments|bank_movements)$"),
    from_date: date = Query(...),
    to_date: date = Query(...),
    as_of: str | None = Query(default=None),
    updated_since: str | None = Query(default=None),
    page_size: int = Query(default=100, ge=1, le=500),
    cursor: str | None = Query(default=None),
    empresa_id: str | None = Query(default=None),
    actor: str = Depends(_validar_token_core),
    conexion=Depends(comun.conexion),
) -> dict:
    # Ningún llamador puede sobreescribir la empresa del servicio.
    if empresa_id is not None:
        raise HTTPException(status_code=403, detail="la empresa la fija el servicio; parámetro empresa_id prohibido")

    empresa = request.app.state.aplicacion.nucleo.empresa
    config = getattr(request.app.state, "configuracion", None)
    rut = getattr(config, "empresa_rut", None) if config else None

    try:
        resultado = exportacion_core.exportar_pagina(
            conexion,
            empresa=empresa,
            empresa_rut=rut,
            resource=resource,
            from_date=from_date,
            to_date=to_date,
            as_of=as_of,
            updated_since=updated_since,
            page_size=page_size,
            cursor=cursor,
        )
    except exportacion_core.CursorInvalido as err:
        raise HTTPException(status_code=400, detail=str(err))
    except exportacion_core.ExportacionInvalida as err:
        raise HTTPException(status_code=422, detail=str(err))

    # Auditoría de lectura fuera de la transacción READ ONLY (sin tocar tablas financieras).
    try:
        seguridad.auditar(
            conexion,
            actor,
            "core_finance_export",
            f"{resource}:{from_date.isoformat()}..{to_date.isoformat()}",
            f"ok:returned={resultado['pagination']['returned']}",
        )
        conexion.commit()
    except Exception:
        conexion.rollback()

    return resultado
