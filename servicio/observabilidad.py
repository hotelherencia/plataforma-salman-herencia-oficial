"""Observabilidad del servicio: logs JSON, correlación por petición y
detección temprana de intentos de vulneración.

Antes de este módulo no había configuración de `logging`: el logger
`servicio.*` heredaba el nivel WARNING del root, así la traza INFO
`nucleo_empresa` nunca salía, y un 500 solo dejaba el traceback de uvicorn
sin método, ruta ni identificador para cruzarlo con la tabla `auditoria`.

Reglas:
- Una línea JSON por evento en stdout (Railway/Vercel la indexan tal cual).
- Jamás se registran cuerpos, cookies, cabeceras de autorización ni query
  string (el callback OAuth lleva `code`/`state` en la query).
- Cada respuesta lleva `X-Request-ID`; el 500 lo devuelve en el cuerpo para
  que el operador busque el traceback exacto.
- El detector cuenta respuestas de rechazo (401/403/404/405/429) y rutas
  sonda por IP en una ventana deslizante; al superar el umbral emite una
  alerta `posible_ataque` una vez por ventana. El bloqueo es opcional
  (BLOQUEO_IP_SOSPECHOSA=1) porque, sin proxy de confianza, la IP vista
  puede ser la del borde y bloquear a todos.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import time
import traceback
import uuid
from contextvars import ContextVar

from fastapi.responses import JSONResponse

_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_PATRON_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_CAMPOS_ESTANDAR = set(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}

log_http = logging.getLogger("servicio.http")
log_seguridad = logging.getLogger("servicio.seguridad")

# Rutas que solo pide un escáner automático: nunca existen en este API.
_RUTAS_SONDA = re.compile(
    r"(\.env|\.git/|wp-admin|wp-login|xmlrpc\.php|phpmyadmin|\.php$|/cgi-bin/|"
    r"/actuator|/\.aws|/server-status|/etc/passwd|\.\./|%2e%2e)",
    re.IGNORECASE,
)
_ESTADOS_RECHAZO = {401, 403, 404, 405, 429}
_RUTAS_SIN_LOG = {"/salud"}  # healthcheck de Railway cada pocos segundos


def request_id_actual() -> str:
    return _request_id.get()


class FormatoJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        datos = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "nivel": record.levelname,
            "logger": record.name,
            "mensaje": record.getMessage(),
            "request_id": _request_id.get(),
        }
        for clave, valor in vars(record).items():
            if clave not in _CAMPOS_ESTANDAR and not clave.startswith("_"):
                datos[clave] = valor
        if record.exc_info:
            datos["traza"] = "".join(traceback.format_exception(*record.exc_info))
        return json.dumps(datos, ensure_ascii=False, default=str)


def configurar_logging() -> None:
    """Idempotente: un solo handler JSON en el logger `servicio`."""
    raiz = logging.getLogger("servicio")
    nivel = os.environ.get("LOG_NIVEL", "INFO").upper()
    raiz.setLevel(getattr(logging, nivel, logging.INFO))
    if not any(getattr(h, "_servicio_json", False) for h in raiz.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(FormatoJson())
        handler._servicio_json = True  # type: ignore[attr-defined]
        raiz.addHandler(handler)


def evento_seguridad(tipo: str, nivel: int = logging.WARNING, **campos) -> None:
    log_seguridad.log(nivel, tipo, extra={"evento": tipo, **campos})


class DetectorAmenazas:
    """Ventana deslizante en memoria por proceso (igual que FrenoDeLogins).

    No sustituye a un WAF: es la señal temprana que queda en los logs aunque
    el atacante rote usuarios (el freno de logins es por usuario)."""

    def __init__(self, umbral: int = 20, ventana_segundos: int = 300, bloquear: bool = False) -> None:
        self.umbral = umbral
        self.ventana = ventana_segundos
        self.bloquear = bloquear
        self._marcas: dict[str, list[float]] = {}
        self._alertado_hasta: dict[str, float] = {}
        self._cerrojo = threading.Lock()

    def _limpiar(self, ahora: float) -> None:
        if len(self._marcas) > 4096:
            self._marcas = {
                ip: [t for t in m if ahora - t < self.ventana]
                for ip, m in self._marcas.items()
            }
            self._marcas = {ip: m for ip, m in self._marcas.items() if m}
            self._alertado_hasta = {ip: t for ip, t in self._alertado_hasta.items() if t > ahora}

    def registrar(self, ip: str, peso: int = 1, ahora: float | None = None) -> bool:
        """Anota un rechazo; True si esta anotación cruza el umbral (alertar)."""
        ahora = time.monotonic() if ahora is None else ahora
        with self._cerrojo:
            self._limpiar(ahora)
            marcas = [t for t in self._marcas.get(ip, []) if ahora - t < self.ventana]
            marcas.extend([ahora] * peso)
            self._marcas[ip] = marcas
            if len(marcas) >= self.umbral and self._alertado_hasta.get(ip, 0) <= ahora:
                self._alertado_hasta[ip] = ahora + self.ventana
                return True
            return False

    def sospechosa(self, ip: str, ahora: float | None = None) -> bool:
        ahora = time.monotonic() if ahora is None else ahora
        with self._cerrojo:
            marcas = [t for t in self._marcas.get(ip, []) if ahora - t < self.ventana]
            return len(marcas) >= self.umbral


def detector_desde_entorno() -> DetectorAmenazas:
    return DetectorAmenazas(
        umbral=int(os.environ.get("ALERTA_RECHAZOS_UMBRAL") or "20"),
        ventana_segundos=int(os.environ.get("ALERTA_RECHAZOS_VENTANA") or "300"),
        bloquear=os.environ.get("BLOQUEO_IP_SOSPECHOSA") == "1",
    )


def instalar(app) -> None:
    """Registra el middleware externo de observabilidad. Llamar al final de
    `crear_app` para que envuelva a los demás middlewares."""
    from .canal_publico import ip_visible

    configurar_logging()
    app.state.detector_amenazas = detector_desde_entorno()

    @app.middleware("http")
    async def observar(request, call_next):
        entrante = request.headers.get("x-request-id", "")
        rid = entrante if _PATRON_REQUEST_ID.match(entrante) else uuid.uuid4().hex[:16]
        token = _request_id.set(rid)
        inicio = time.perf_counter()
        ruta = request.url.path
        ip = ip_visible(request)
        detector: DetectorAmenazas = app.state.detector_amenazas
        try:
            if detector.bloquear and ruta not in ("/salud", "/readiness") and detector.sospechosa(ip):
                evento_seguridad("ip_bloqueada", ip=ip, metodo=request.method, ruta=ruta)
                respuesta = JSONResponse(status_code=429, content={"detail": "demasiadas solicitudes"})
            else:
                try:
                    respuesta = await call_next(request)
                except Exception:
                    log_http.error(
                        "error_no_controlado",
                        exc_info=True,
                        extra={"metodo": request.method, "ruta": ruta, "ip": ip},
                    )
                    respuesta = JSONResponse(
                        status_code=500,
                        content={"detail": "error interno", "request_id": rid},
                    )
            estado = respuesta.status_code
            ms = round((time.perf_counter() - inicio) * 1000, 1)
            respuesta.headers["X-Request-ID"] = rid

            sonda = bool(_RUTAS_SONDA.search(ruta))
            if sonda:
                evento_seguridad("ruta_sonda", ip=ip, metodo=request.method, ruta=ruta[:200])
            if sonda or estado in _ESTADOS_RECHAZO:
                if detector.registrar(ip, peso=5 if sonda else 1):
                    evento_seguridad(
                        "posible_ataque",
                        nivel=logging.ERROR,
                        ip=ip,
                        umbral=detector.umbral,
                        ventana_s=detector.ventana,
                        ultima_ruta=ruta[:200],
                        ultimo_estado=estado,
                    )

            if ruta not in _RUTAS_SIN_LOG or estado >= 400:
                nivel = (
                    logging.ERROR if estado >= 500
                    else logging.WARNING if estado in (401, 403, 429)
                    else logging.INFO
                )
                log_http.log(
                    nivel,
                    "peticion",
                    extra={
                        "metodo": request.method,
                        "ruta": ruta[:200],
                        "estado": estado,
                        "ms": ms,
                        "ip": ip,
                        "agente": (request.headers.get("user-agent") or "")[:120],
                    },
                )
            return respuesta
        finally:
            _request_id.reset(token)
