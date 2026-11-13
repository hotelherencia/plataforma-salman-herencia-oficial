"""Dependencias y auxiliares compartidos de las rutas HTTP (ARC-A01).

Extraídos de las closures de `aplicacion.py`: las dependencias FastAPI
reciben `Request` y leen el estado de la app desde `request.app.state`, así
los módulos de rutas no necesitan capturar la fábrica.
"""
from __future__ import annotations

import logging
from typing import Iterator

import psycopg
from fastapi import Depends, HTTPException, Request, Response

from .. import seguridad

NOMBRE_COOKIE_SESION = "sid"
# SEC-A05 (#330): transacción OAuth atada al navegador que inició el login.
NOMBRE_COOKIE_OAUTH_TX = "oauth_tx"
NOMBRE_COOKIE_MFA_TX = "mfa_tx"
DETALLE_SESION_EMPRESA_AJENA = "sesion_empresa_ajena"
_log = logging.getLogger("servicio.sesion")


def conexion(request: Request) -> Iterator[psycopg.Connection]:
    # Sin DATABASE_URL en el arranque no hay `app.state.database_url`: se
    # responde 503 «no configurado» (convención de puertos de AGENTS.md) en
    # vez de un 500 por AttributeError (visto en Vercel el 2026-10-30).
    database_url = getattr(request.app.state, "database_url", None)
    if not database_url:
        raise HTTPException(
            status_code=503,
            detail="base de datos no configurada: fija DATABASE_URL en el despliegue",
        )
    with psycopg.connect(database_url) as conn:
        yield conn


def requerir_sesion(
    request: Request,
    response: Response,
    conn=Depends(conexion),
) -> seguridad.SesionActiva:
    sid = request.cookies.get(NOMBRE_COOKIE_SESION)
    if not sid:
        raise HTTPException(status_code=401, detail="sin sesión")
    sesion = seguridad.obtener_sesion_activa(conn, sid)
    if sesion is None:
        raise HTTPException(status_code=401, detail="sesión inválida o vencida")
    # SEC-A04 (#329): en V1 de empresa fija, el límite HTTP niega
    # explícitamente una sesión de otra empresa en lugar de confiar en
    # que la base no puede contenerla (auditoría 2026-11-03). Antes de
    # multiempresa el invariante vive aquí, no en cada consulta.
    # Si el sid quedó de otro núcleo (redeploy / titular↔sintético), se
    # limpia la cookie y se responde un detail ESPECÍFICO (no «sesión
    # inválida» genérico): el front y el log monitor deben poder decir
    # qué falló sin adivinar.
    nucleo_id = request.app.state.aplicacion.nucleo.empresa.id
    if sesion.empresa_id != nucleo_id:
        _log.warning(
            "sesion_empresa_ajena actor=%s sid_empresa=%s nucleo=%s path=%s method=%s",
            sesion.nombre,
            sesion.empresa_id,
            nucleo_id,
            request.url.path,
            request.method,
        )
        seguridad.auditar(
            conn,
            sesion.nombre,
            "sesion",
            request.url.path,
            f"empresa_ajena:{sesion.empresa_id}->{nucleo_id}",
        )
        conn.commit()
        if request.url.path.rstrip("/") == "/sesion" and request.method == "GET":
            # Las cabeceras del `response` inyectado se pierden al lanzar
            # HTTPException: el Set-Cookie de borrado debe viajar en la excepción.
            borrado = Response()
            borrar_cookie_sesion(borrado, request)
            raise HTTPException(
                status_code=401,
                detail=DETALLE_SESION_EMPRESA_AJENA,
                headers={"set-cookie": borrado.headers["set-cookie"]},
            )
        raise seguridad.ErrorPermiso("empresa ajena a la del servicio")
    return sesion


def _cookie_segura(request: Request) -> bool:
    config = request.app.state.configuracion
    return bool(config and config.cookie_segura)


def fijar_cookie_sesion(response: Response, request: Request, sid: str) -> None:
    """spec-api-v1: en producción (Secure) SameSite=None para Vercel↔Railway;
    en local sin Secure el navegador rechaza SameSite=None: se usa Lax."""
    segura = _cookie_segura(request)
    response.set_cookie(
        NOMBRE_COOKIE_SESION,
        sid,
        httponly=True,
        secure=segura,
        samesite="none" if segura else "lax",
        path="/",
    )


def borrar_cookie_sesion(response: Response, request: Request) -> None:
    # El borrado debe repetir los mismos atributos (Secure/SameSite) o el
    # navegador no elimina la cookie cross-site de producción.
    segura = _cookie_segura(request)
    response.set_cookie(
        NOMBRE_COOKIE_SESION,
        "",
        max_age=0,
        httponly=True,
        secure=segura,
        samesite="none" if segura else "lax",
        path="/",
    )


def borrar_cookie_oauth_tx(response: Response, request: Request) -> None:
    """SEC-A05 (#330): la transacción OAuth se consume con el callback;
    su cookie se elimina en los destinos (mismos atributos que al fijarla)."""
    segura = _cookie_segura(request)
    response.set_cookie(
        NOMBRE_COOKIE_OAUTH_TX,
        "",
        max_age=0,
        httponly=True,
        secure=segura,
        samesite="none" if segura else "lax",
        path="/",
    )


def fijar_cookie_mfa_tx(response: Response, request: Request, tx: str, max_age: int) -> None:
    """C-03: transacción Google→TOTP pendiente (mismos atributos que oauth_tx)."""
    segura = _cookie_segura(request)
    response.set_cookie(
        NOMBRE_COOKIE_MFA_TX, tx, max_age=max_age, httponly=True, secure=segura,
        samesite="none" if segura else "lax", path="/",
    )


def borrar_cookie_mfa_tx(response: Response, request: Request) -> None:
    segura = _cookie_segura(request)
    response.set_cookie(
        NOMBRE_COOKIE_MFA_TX, "", max_age=0, httponly=True, secure=segura,
        samesite="none" if segura else "lax", path="/",
    )


def exigir_admin(sesion: seguridad.SesionActiva) -> None:
    if sesion.rol != "administrador":
        raise seguridad.ErrorPermiso("solo administrador")


def exigir_rol(sesion: seguridad.SesionActiva, roles) -> None:
    if sesion.rol not in roles:
        raise seguridad.ErrorPermiso("rol no autorizado")


def clave_idempotencia_o_400(idempotency_key: str | None) -> str:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="falta la cabecera Idempotency-Key")
    return idempotency_key
