"""Verificación de reCAPTCHA v3 en el servicio.

La clave de sitio vive en el navegador. La secreta solo entra por
RECAPTCHA_SECRET_KEY. Sin esa variable: en desarrollo/suite el canal
público puede omitir la verificación (compatibilidad de tests); en
producción (`COOKIE_SEGURA=1` o `RECAPTCHA_OBLIGATORIO=1`) el servicio
falla cerrado (503) vía `_exigir_captcha` — no se aceptan leads sin
secreto configurado. Con la variable, un token ausente, ajeno, de otra
acción, de otro host o con puntaje bajo se rechaza antes de persistir.
Ni el token ni la secreta se escriben en el log.
"""
import json
import os
import urllib.parse
import urllib.request

UMBRAL = 0.5
# W16-A01 (auditoría 2026-11-16): /reservar también se sirve desde el dominio
# de la plataforma; sin él, toda solicitud pública desde ahí daba 403.
# Hosts adicionales: RECAPTCHA_HOSTNAMES (coma), igual que en la landing.
HOSTS = frozenset({
    "hotelherencia.cl",
    "www.hotelherencia.cl",
    "plataforma.hotelherencia.cl",
    "hotelherencia-landing.vercel.app",
    "plataforma-salman-herencia-oficial.vercel.app",
    "localhost",
    "127.0.0.1",
})


class CaptchaRechazado(Exception):
    """403 genérico: el visitante no distingue la causa."""


def hosts_permitidos() -> frozenset[str]:
    """HOSTS fijos más los de RECAPTCHA_HOSTNAMES (minúsculas, sin espacios)."""
    extra = {
        h.strip().lower()
        for h in (os.environ.get("RECAPTCHA_HOSTNAMES") or "").split(",")
        if h.strip()
    }
    return HOSTS | extra


def juzgar(cuerpo: dict, accion: str, hosts: frozenset[str] | None = None) -> None:
    if not cuerpo.get("success"):
        raise CaptchaRechazado()
    if cuerpo.get("action") != accion:
        raise CaptchaRechazado()
    try:
        puntaje = float(cuerpo.get("score"))
    except (TypeError, ValueError):
        raise CaptchaRechazado()
    if puntaje < UMBRAL:
        raise CaptchaRechazado()
    permitidos = hosts if hosts is not None else hosts_permitidos()
    if (cuerpo.get("hostname") or "").strip().lower() not in permitidos:
        raise CaptchaRechazado()


def verificar(token: str | None, secreto: str, accion: str, ip: str | None = None) -> None:
    if not token or len(token) > 4000:
        raise CaptchaRechazado()
    campos = {"secret": secreto, "response": token}
    if ip:
        campos["remoteip"] = ip
    pedido = urllib.request.Request(
        "https://www.google.com/recaptcha/api/siteverify",
        data=urllib.parse.urlencode(campos).encode(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(pedido, timeout=5) as respuesta:
            cuerpo = json.loads(respuesta.read().decode())
    except Exception:
        raise CaptchaRechazado()
    juzgar(cuerpo, accion)
