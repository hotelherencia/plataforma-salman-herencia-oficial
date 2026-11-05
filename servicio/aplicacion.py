"""Fábrica de la aplicación: núcleo y hotel en el mismo proceso, un solo servicio.

Regla de arranque (spec-backend-v1): el hotel entra con la empresa del
núcleo; un establecimiento de otra empresa impide que el proceso arranque.
Con `database_url` configurada, el arranque también aplica migraciones y crea
el administrador inicial desde variables de entorno (spec-api-v1).
"""
import json
import secrets
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator

RAIZ = Path(__file__).resolve().parents[1]
for _ruta in (RAIZ / "core" / "incremento1", RAIZ / "verticales" / "hotel" / "incremento1"):
    if ( _s := str(_ruta) ) not in sys.path:
        sys.path.insert(0, _s)

import psycopg  # noqa: E402
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Path as RutaParam, Query, Request, Response  # noqa: E402
from fastapi.responses import JSONResponse, RedirectResponse  # noqa: E402
from pydantic import BaseModel, Field, field_validator  # noqa: E402

from hotel_inventario.dominio import EstadoUnidad, Establecimiento, Unidad  # noqa: E402
from hotel_inventario.servicio import ROLES_DOCUMENTO, ServicioHotelInventario  # noqa: E402
from nucleo.servicio import Nucleo  # noqa: E402

from .configuracion import Configuracion, cargar_desde_entorno  # noqa: E402
from .migracion import aplicar_migraciones  # noqa: E402
from . import seguridad  # noqa: E402
from . import idempotencia  # noqa: E402
from . import google_oidc  # noqa: E402
from . import reservas as reservas_db  # noqa: E402
from . import cobro  # noqa: E402
from . import panel  # noqa: E402
from . import canal_publico  # noqa: E402
from . import leads as leads_mod  # noqa: E402
from . import agente  # noqa: E402
from .modelo_lenguaje import ModeloGuionado, NoConfigurado, SinAdaptador  # noqa: E402
from . import totp  # noqa: E402
from . import totp_qr  # noqa: E402

NOMBRE_COOKIE_SESION = "sid"
# SEC-A05 (#330): transacción OAuth atada al navegador que inició el login.
NOMBRE_COOKIE_OAUTH_TX = "oauth_tx"


class ErrorArranque(Exception):
    """El proceso no arranca (regla de plataforma incumplida)."""


@dataclass
class Aplicacion:
    nucleo: Nucleo
    hotel: ServicioHotelInventario


def construir_hotel(nucleo: Nucleo, establecimiento: Establecimiento, unidades: tuple[Unidad, ...]) -> ServicioHotelInventario:
    if establecimiento.empresa_id != nucleo.empresa.id:
        raise ErrorArranque("el establecimiento no pertenece a la empresa del núcleo")
    return ServicioHotelInventario(establecimiento, unidades, empresa=nucleo.empresa)


def construir_aplicacion(nucleo: Nucleo | None = None) -> Aplicacion:
    nucleo = nucleo or Nucleo()
    establecimiento = Establecimiento(
        id="EST-SINT-001", empresa_id=nucleo.empresa.id, nombre="Hotel Herencia sintético"
    )
    unidades = tuple(
        Unidad(f"HAB-SINT-10{n}", establecimiento.id, 2, 50_000, EstadoUnidad.LIMPIA) for n in range(1, 4)
    )
    return Aplicacion(nucleo=nucleo, hotel=construir_hotel(nucleo, establecimiento, unidades))


def _preparar_base_de_datos(config: Configuracion, aplicacion: Aplicacion) -> None:
    assert config.database_url is not None
    try:
        with psycopg.connect(config.database_url) as conexion:
            aplicar_migraciones(config.database_url)
            seguridad.asegurar_admin_inicial(
                conexion,
                empresa_id=aplicacion.nucleo.empresa.id,
                admin_usuario=config.admin_usuario,
                admin_clave=config.admin_clave,
            )
            agente.asegurar_agente_servicio(conexion, aplicacion.nucleo.empresa.id)
            if config.admin_email and config.admin_usuario:
                seguridad.vincular_email(conexion, config.admin_usuario, config.admin_email)
            reservas_db.sembrar_habitaciones(conexion)
            conexion.commit()
    except RuntimeError as error:
        raise ErrorArranque(str(error))
    except psycopg.OperationalError as error:
        raise ErrorArranque(f"no se pudo conectar a la base de datos: {error}")


class Credenciales(BaseModel):
    usuario: str
    clave: str
    totp: str | None = Field(default=None, min_length=6, max_length=10)


class CodigoTotpIn(BaseModel):
    codigo: str = Field(min_length=6, max_length=10)


class ClaveActualIn(BaseModel):
    """SEC-A02 (#327): clave actual para reautenticar operaciones sensibles
    del segundo factor (reemplazar el autenticador o desactivarlo). Cualquier
    largo no vacío: la validación de la clave la hace `reautenticar_clave`
    (401), no el esquema — un 422 aquí filtraría el chequeo de autorización."""
    clave: str = Field(min_length=1)


class HabitacionIn(BaseModel):
    tipo: str = Field(min_length=1, max_length=50)
    capacidad: int = Field(gt=0, le=30)

    @field_validator("tipo")
    @classmethod
    def _tipo_sin_bordes(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("el tipo no puede quedar vacío")
        return valor


# spec-hotel-operacion-v1 §2.2: id estable y apto para URL (clave primaria).
PATRON_ID_HABITACION = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$"


class ServicioIn(BaseModel):
    en_servicio: bool
    motivo: str | None = Field(default=None, max_length=200)


class TarifaIn(BaseModel):
    habitacion_id: str = Field(min_length=1, max_length=50)
    fecha_desde: date
    fecha_hasta: date
    tarifa_noche_clp: int = Field(gt=0, le=100_000_000)


class HuespedIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    documento: str | None = Field(default=None, max_length=50)


class ReservaIn(BaseModel):
    habitacion_id: str = Field(min_length=1, max_length=50)
    inicio: date
    fin: date
    huesped: HuespedIn


class PagoIn(BaseModel):
    monto_clp: int = Field(gt=0, le=1_000_000_000)
    clave: str = Field(min_length=1, max_length=100)
    modo: str = Field(pattern="^(manual|pasarela)$")


class UsuarioIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    rol: str = Field(pattern="^(administrador|recepcion|caja)$")
    clave: str = Field(min_length=6, max_length=200)


class ClaveIn(BaseModel):
    clave: str = Field(min_length=6, max_length=200)


class MantenimientoIn(BaseModel):
    abierto: bool


class CargoIn(BaseModel):
    concepto: str = Field(min_length=1, max_length=200)
    monto_clp: int = Field(gt=0, le=1_000_000_000)


class SolicitudPublicaIn(BaseModel):
    habitacion_id: str = Field(min_length=1, max_length=50)
    inicio: date
    fin: date
    personas: int = Field(gt=0, le=canal_publico.MAX_PERSONAS)
    huesped_nombre: str = Field(min_length=1, max_length=120)
    huesped_contacto: str = Field(min_length=1, max_length=120)


class RechazoSolicitudIn(BaseModel):
    motivo: str = Field(min_length=1, max_length=300)


class LeadPublicoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=leads_mod.MAX_NOMBRE)
    correo: str = Field(min_length=1, max_length=leads_mod.MAX_CORREO)
    telefono: str = Field(min_length=1, max_length=leads_mod.MAX_TELEFONO)
    huespedes: int | None = Field(default=None, ge=1, le=leads_mod.MAX_PERSONAS)
    check_in: date | None = None
    check_out: date | None = None
    mensaje: str | None = Field(default=None, max_length=leads_mod.MAX_MENSAJE)


class GestionLeadIn(BaseModel):
    estado: str = Field(min_length=1, max_length=20)
    nota: str | None = Field(default=None, max_length=500)


class ConsultaAgenteIn(BaseModel):
    canal_origen: str = Field(min_length=1, max_length=20)
    texto: str = Field(min_length=1, max_length=agente.MAX_TEXTO_CONSULTA)


class AprobacionBorradorIn(BaseModel):
    texto_editado: str | None = Field(default=None, max_length=4000)


class DescarteBorradorIn(BaseModel):
    motivo: str = Field(min_length=1, max_length=300)


class PoliticaAgenteIn(BaseModel):
    nivel: str | None = Field(default=None, pattern=r"^N[012]$")
    horario: str | None = Field(default=None, max_length=100)
    max_noches: int | None = Field(default=None, ge=1, le=30)
    max_personas: int | None = Field(default=None, ge=1, le=30)
    tope_mensual_clp: int | None = Field(default=None, ge=0)
    evaluacion_ref: str | None = Field(default=None, max_length=200)


def crear_app(aplicacion: Aplicacion | None = None, configuracion: Configuracion | None = None) -> FastAPI:
    aplicacion = aplicacion or construir_aplicacion()
    app = FastAPI(title="plataforma-salman-herencia-api", version="0.1.0")
    app.state.aplicacion = aplicacion
    app.state.configuracion = configuracion
    if configuracion is not None and configuracion.database_url:
        _preparar_base_de_datos(configuracion, aplicacion)
        app.state.database_url = configuracion.database_url
    app.state.freno_logins = seguridad.FrenoDeLogins()
    app.state.freno_solicitudes = canal_publico.FrenoDeSolicitudes(
        max_por_minuto=configuracion.publico_max_por_minuto if configuracion else 6
    )
    if configuracion is not None and configuracion.agente_guion_json:
        app.state.modelo_agente = ModeloGuionado(json.loads(configuracion.agente_guion_json))
    else:
        app.state.modelo_agente = SinAdaptador()
    app.state.estados_oauth = google_oidc.EstadosOAuth()

    if configuracion is not None and configuracion.origen_front:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=configuracion.origen_front.split(","),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # spec-api-v1 / test_preh7_seguridad: si el front es de otro sitio
    # (CORS con credenciales), la cookie debe ser Secure+SameSite=None o el
    # navegador la rechaza. Se exige COOKIE_SEGURA salvo orígenes locales de
    # desarrollo (127.0.0.1 / localhost), donde la cookie es Lax sin Secure.
    _LOCALES = ("127.0.0.1", "localhost", "::1")
    if configuracion is not None and configuracion.origen_front and not configuracion.cookie_segura:
        _origenes = [o.strip() for o in configuracion.origen_front.split(",") if o.strip()]
        if any(not any(local in origen for local in _LOCALES) for origen in _origenes):
            raise ErrorArranque(
                "ORIGEN_FRONT ajeno exige COOKIE_SEGURA=1 (cookie SameSite=None requiere Secure)"
            )

    @app.middleware("http")
    async def origin_de_mutaciones(request, call_next):
        # Con orígenes configurados, una mutación con Origin ajeno se rechaza
        # aunque traiga sesión (defensa en profundidad junto al CORS). Sin
        # cabecera Origin (curl, server-to-server) la mutación sigue.
        config = app.state.configuracion
        if (
            config is not None
            and config.origen_front
            and request.method in ("POST", "PUT", "PATCH", "DELETE")
        ):
            permitidos = {o.strip() for o in config.origen_front.split(",") if o.strip()}
            origin = request.headers.get("origin")
            if origin and origin not in permitidos:
                # V1-ISSUE-22: el origen de la landing entra solo a /publico/*
                # (CORS sin credenciales en cors_canal_publico); lo interno sigue 403.
                es_publico_del_landing = (
                    request.url.path.startswith("/publico/")
                    and getattr(config, "origen_landing", None)
                    and origin in {o.strip() for o in config.origen_landing.split(",") if o.strip()}
                )
                if not es_publico_del_landing:
                    return JSONResponse(status_code=403, content={"detail": "acceso denegado"})
        return await call_next(request)

    @app.middleware("http")
    async def cabeceras_seguras(request, call_next):
        respuesta = await call_next(request)
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        respuesta.headers["Referrer-Policy"] = "no-referrer"
        return respuesta

    @app.middleware("http")
    async def cors_canal_publico(request, call_next):
        # V1-ISSUE-22 (spec-api-v1 «Canal público»): el origen de la landing
        # tiene CORS sin credenciales y solo sobre /publico/*. Sin ORIGEN_LANDING
        # configurado, estas rutas se usan same-origin (front y pruebas).
        config = app.state.configuracion
        if not (config and getattr(config, "origen_landing", None) and request.url.path.startswith("/publico/")):
            return await call_next(request)
        origin = request.headers.get("origin")
        permitidos = {o.strip() for o in config.origen_landing.split(",") if o.strip()}
        if not origin or origin not in permitidos:
            return await call_next(request)
        if request.method == "OPTIONS":
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": request.headers.get(
                        "access-control-request-headers", "Content-Type, Idempotency-Key"
                    ),
                    "Vary": "Origin",
                },
            )
        respuesta = await call_next(request)
        respuesta.headers["Access-Control-Allow-Origin"] = origin
        respuesta.headers["Vary"] = "Origin"
        # El CORSMiddleware global añade Allow-Credentials a toda respuesta con
        # Origin; aquí no hay credenciales (spec-api-v1 «Canal público»).
        if "access-control-allow-credentials" in respuesta.headers:
            del respuesta.headers["access-control-allow-credentials"]
        return respuesta

    @app.get("/salud")
    def salud() -> dict:
        return {
            "estado": "ok",
            "nucleo": "cargado",
            "hotel": "cargado",
            "empresa": aplicacion.nucleo.empresa.id,
        }

    @app.get("/readiness")
    def readiness() -> dict:
        """Readiness (OPS-A02, #333): consulta real a la base y estado de
        migraciones; 503 si no responde. `/salud` sigue siendo liveness pura
        (no toca la base) — Railway puede seguir usando /salud para el
        healthcheck del proceso y /readiness para el enrutado."""
        database_url = getattr(app.state, "database_url", None)
        if not database_url:
            raise HTTPException(status_code=503, detail="base de datos no configurada")
        try:
            with psycopg.connect(database_url, connect_timeout=5) as conexion:
                conexion.execute("SELECT 1")
                (n_migraciones,) = conexion.execute(
                    "SELECT count(*) FROM schema_migrations"
                ).fetchone()
        except psycopg.Error:
            raise HTTPException(status_code=503, detail="la base de datos no responde")
        return {"estado": "listo", "migraciones": n_migraciones}

    def _conexion() -> Iterator[psycopg.Connection]:
        # Sin DATABASE_URL en el arranque no hay `app.state.database_url`: se
        # responde 503 «no configurado» (convención de puertos de AGENTS.md) en
        # vez de un 500 por AttributeError (visto en Vercel el 2026-10-30).
        database_url = getattr(app.state, "database_url", None)
        if not database_url:
            raise HTTPException(
                status_code=503,
                detail="base de datos no configurada: fija DATABASE_URL en el despliegue",
            )
        with psycopg.connect(database_url) as conexion:
            yield conexion

    def _fijar_cookie(response: Response, sid: str) -> None:
        config = app.state.configuracion
        segura = config.cookie_segura if config else False
        # spec-api-v1: en producción (Secure) SameSite=None para Vercel↔Railway;
        # en local sin Secure el navegador rechaza SameSite=None: se usa Lax.
        response.set_cookie(
            NOMBRE_COOKIE_SESION,
            sid,
            httponly=True,
            secure=segura,
            samesite="none" if segura else "lax",
            path="/",
        )

    def _borrar_cookie(response: Response) -> None:
        # El borrado debe repetir los mismos atributos (Secure/SameSite) o el
        # navegador no elimina la cookie cross-site de producción.
        config = app.state.configuracion
        segura = config.cookie_segura if config else False
        response.set_cookie(
            NOMBRE_COOKIE_SESION,
            "",
            max_age=0,
            httponly=True,
            secure=segura,
            samesite="none" if segura else "lax",
            path="/",
        )

    def _borrar_cookie_oauth_tx(response: Response) -> None:
        """SEC-A05 (#330): la transacción OAuth se consume con el callback;
        su cookie se elimina en los destinos (mismos atributos que al fijarla)."""
        config = app.state.configuracion
        segura = config.cookie_segura if config else False
        response.set_cookie(
            NOMBRE_COOKIE_OAUTH_TX,
            "",
            max_age=0,
            httponly=True,
            secure=segura,
            samesite="none" if segura else "lax",
            path="/auth",
        )

    def _requerir_sesion(request: Request, conexion=Depends(_conexion)) -> seguridad.SesionActiva:
        sid = request.cookies.get(NOMBRE_COOKIE_SESION)
        if not sid:
            raise HTTPException(status_code=401, detail="sin sesión")
        sesion = seguridad.obtener_sesion_activa(conexion, sid)
        if sesion is None:
            raise HTTPException(status_code=401, detail="sesión inválida o vencida")
        # SEC-A04 (#329): en V1 de empresa fija, el límite HTTP niega
        # explícitamente una sesión de otra empresa en lugar de confiar en
        # que la base no puede contenerla (auditoría 2026-11-03). Antes de
        # multiempresa el invariante vive aquí, no en cada consulta.
        if sesion.empresa_id != app.state.aplicacion.nucleo.empresa.id:
            raise seguridad.ErrorPermiso("empresa ajena a la del servicio")
        return sesion

    @app.post("/sesion")
    def abrir_sesion(
        credenciales: Credenciales,
        response: Response,
        request: Request,
        conexion=Depends(_conexion),
    ) -> dict:
        ip = request.client.host if request.client else "desconocida"
        freno: seguridad.FrenoDeLogins = app.state.freno_logins
        if freno.bloqueado(ip, credenciales.usuario, time.time()) or \
                freno.bloqueado_usuario(credenciales.usuario, time.time()):
            raise HTTPException(status_code=429, detail="demasiados intentos; espera unos minutos")
        auth = seguridad.autenticar(conexion, credenciales.usuario, credenciales.clave)
        if auth is None:
            freno.registrar_fallo(ip, credenciales.usuario, time.time())
            freno.registrar_fallo_usuario(credenciales.usuario, time.time())
            seguridad.auditar(conexion, credenciales.usuario, "login", "/sesion", "rechazado")
            conexion.commit()
            raise HTTPException(status_code=401, detail="credenciales inválidas")
        usuario_id, empresa_id, rol, totp_activado = auth
        config = app.state.configuracion
        if totp_activado:
            secreto = seguridad.secreto_totp(conexion, usuario_id)
            if not credenciales.totp:
                seguridad.auditar(conexion, credenciales.usuario, "login", "/sesion", "falta codigo 2fa")
                conexion.commit()
                raise HTTPException(status_code=401, detail="codigo_totp_requerido")
            if secreto is None or not totp.verificar(secreto, credenciales.totp):
                freno.registrar_fallo(ip, credenciales.usuario, time.time())
                freno.registrar_fallo_usuario(credenciales.usuario, time.time())
                seguridad.auditar(conexion, credenciales.usuario, "login", "/sesion", "2fa rechazado")
                conexion.commit()
                raise HTTPException(status_code=401, detail="código 2FA inválido")
        # SEC-A03 (#328): los contadores se reinician solo al completar TODA
        # la autenticación. Hacerlo con la clave correcta (antes del TOTP)
        # borraba los fallos en cada intento y dejaba el segundo factor sin
        # freno de fuerza bruta (auditoría de jefatura 2026-11-03, SEC-A03).
        freno.reiniciar(ip, credenciales.usuario)
        freno.reiniciar_usuario(credenciales.usuario)
        sid = seguridad.crear_sesion(
            conexion, usuario_id, empresa_id,
            horas_vigencia=config.session_horas if config else 12,
        )
        seguridad.auditar(conexion, credenciales.usuario, "login", "/sesion", "ok")
        conexion.commit()
        _fijar_cookie(response, sid)
        return {
            "usuario": credenciales.usuario,
            "rol": rol,
            "empresa_id": empresa_id,
            "totp_activado": totp_activado,
        }

    @app.delete("/sesion")
    def cerrar_sesion(request: Request, response: Response, conexion=Depends(_conexion)) -> dict:
        sid = request.cookies.get(NOMBRE_COOKIE_SESION)
        if not sid:
            raise HTTPException(status_code=401, detail="sin sesión")
        sesion = seguridad.obtener_sesion_activa(conexion, sid)
        if sesion is None:
            raise HTTPException(status_code=401, detail="sesión inválida o vencida")
        seguridad.revocar_sesion(conexion, sid)
        conexion.commit()
        _borrar_cookie(response)
        return {"estado": "cerrada"}

    @app.get("/sesion")
    def ver_sesion(sesion: seguridad.SesionActiva = Depends(_requerir_sesion), conexion=Depends(_conexion)) -> dict:
        (totp_activado,) = conexion.execute(
            "SELECT totp_activado FROM usuarios WHERE id = %s", (sesion.usuario_id,)
        ).fetchone()
        return {
            "id": sesion.usuario_id,
            "usuario": sesion.nombre,
            "rol": sesion.rol,
            "empresa_id": sesion.empresa_id,
            "totp_activado": totp_activado,
        }

    # --- Login con Google (OAuth 2.0 / OIDC): adaptador opcional (spec-api-v1).
    # DECISIÓN 2026-10-29: sustituye al par usuario/clave + TOTP para la
    # identidad vinculada; no lleva freno de fuerza bruta ni aprovisionamiento.

    @app.get("/auth/google/estado")
    def estado_login_google() -> dict:
        return {"configurado": google_oidc.configurado(app.state.configuracion)}

    @app.get("/auth/google")
    def iniciar_login_google() -> Response:
        config = app.state.configuracion
        if not google_oidc.configurado(config):
            raise HTTPException(status_code=503, detail="no configurado")
        # SEC-A05 (#330): la transacción queda atada a una cookie HttpOnly de
        # vida corta; el callback exige que la cookie coincida con el state.
        tx = secrets.token_urlsafe(16)
        estado = app.state.estados_oauth.nuevo(tx=tx)
        url = google_oidc.url_de_consentimiento(config.google_client_id, estado, config.google_redirect_uri)
        respuesta = RedirectResponse(url, status_code=302)
        segura = config.cookie_segura if config else False
        respuesta.set_cookie(
            NOMBRE_COOKIE_OAUTH_TX,
            tx,
            max_age=google_oidc.VIDA_ESTADO_SEG,
            httponly=True,
            secure=segura,
            samesite="none" if segura else "lax",
            path="/auth",
        )
        return respuesta

    @app.get("/auth/google/callback")
    def callback_login_google(
        request: Request,
        state: str | None = None,
        code: str | None = None,
        error: str | None = None,
        conexion=Depends(_conexion),
    ) -> Response:
        config = app.state.configuracion
        if not google_oidc.configurado(config):
            raise HTTPException(status_code=503, detail="no configurado")
        front = config.front_url
        if error is not None:
            destino = RedirectResponse(f"{front}/login?error=acceso_denegado", status_code=302)
            _borrar_cookie_oauth_tx(destino)
            return destino
        # El state se consume en todo intento (tomar lo extrae siempre): un
        # rechazo por cookie ausente o distinta no deja el state reutilizable.
        tx = request.cookies.get(NOMBRE_COOKIE_OAUTH_TX)
        if state is None or not app.state.estados_oauth.tomar(state, tx=tx):
            raise HTTPException(status_code=400, detail="state inválido o expirado")
        if code is None:
            raise HTTPException(status_code=400, detail="falta el código de autorización")
        try:
            tokens = google_oidc.intercambiar_codigo(
                code, config.google_client_id, config.google_client_secret, config.google_redirect_uri
            )
            claims = google_oidc.verificar_id_token(tokens["id_token"], config.google_client_id)
        except (google_oidc.ErrorGoogleOidc, KeyError) as fallo:
            raise HTTPException(status_code=502, detail="fallo al validar la identidad con Google") from fallo
        email = claims["email"]
        usuario = seguridad.buscar_usuario_por_email(conexion, email)
        if usuario is None:
            seguridad.auditar(conexion, email, "login", "/auth/google/callback", "sin vinculo")
            conexion.commit()
            destino = RedirectResponse(f"{front}/login?error=cuenta_sin_vinculo", status_code=302)
            _borrar_cookie_oauth_tx(destino)
            return destino
        usuario_id, empresa_id, _rol, nombre = usuario
        sid = seguridad.crear_sesion(
            conexion, usuario_id, empresa_id,
            horas_vigencia=config.session_horas,
        )
        seguridad.auditar(conexion, nombre, "login", "/auth/google/callback", "ok")
        conexion.commit()
        destino = RedirectResponse(front, status_code=302)
        _fijar_cookie(destino, sid)
        _borrar_cookie_oauth_tx(destino)
        return destino

    @app.post("/cuenta/2fa")
    def iniciar_2fa(
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
        cuerpo: ClaveActualIn | None = Body(default=None),
    ) -> dict:
        """Genera el secreto TOTP pendiente: el factor activo queda intacto
        hasta confirmar. SEC-A02 (#327): con 2FA ya activo (reenrolamiento)
        exige la clave actual — una sesión capturada no puede reemplazar el
        autenticador."""
        (activo,) = conexion.execute(
            "SELECT totp_activado FROM usuarios WHERE id = %s", (sesion.usuario_id,)
        ).fetchone()
        if activo:
            if cuerpo is None or not seguridad.reautenticar_clave(conexion, sesion.usuario_id, cuerpo.clave):
                seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa", "reauth rechazada")
                conexion.commit()
                raise HTTPException(status_code=401, detail="se requiere la clave actual para reemplazar el autenticador")
        secreto = seguridad.iniciar_alta_totp(conexion, sesion.usuario_id)
        seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa", "alta iniciada")
        conexion.commit()
        return {
            "secreto": secreto,
            "uri": totp.uri_de_alta(secreto, sesion.nombre),
        }

    @app.post("/cuenta/2fa/activar")
    def activar_2fa(
        cuerpo: CodigoTotpIn,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        secreto = seguridad.secreto_totp_pendiente(conexion, sesion.usuario_id)
        if secreto is None:
            raise HTTPException(status_code=400, detail="no hay alta de 2FA en curso")
        if not totp.verificar(secreto, cuerpo.codigo):
            seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa/activar", "rechazado")
            conexion.commit()
            raise HTTPException(status_code=400, detail="código 2FA inválido")
        seguridad.activar_totp(conexion, sesion.usuario_id)
        seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa/activar", "activado")
        conexion.commit()
        return {"estado": "activado"}

    @app.get("/cuenta/2fa/qr")
    def qr_2fa(
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> Response:
        """QR (SVG) del secreto PENDIENTE: escaneable por Google Authenticator.

        SEC-A02 (#327): el secreto activo nunca se expone; el QR sirve solo
        durante el alta en curso."""
        secreto = seguridad.secreto_totp_pendiente(conexion, sesion.usuario_id)
        if secreto is None:
            raise HTTPException(status_code=400, detail="no hay alta de 2FA en curso; iníciala con POST /cuenta/2fa")
        svg = totp_qr.uri_a_svg(totp.uri_de_alta(secreto, sesion.nombre))
        return Response(content=svg, media_type="image/svg+xml")

    @app.delete("/cuenta/2fa")
    def desactivar_2fa(
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
        cuerpo: ClaveActualIn | None = Body(default=None),
    ) -> dict:
        """SEC-A02 (#327): desactivar exige la clave actual (reautenticación):
        una sesión capturada no puede eliminar el segundo factor."""
        if cuerpo is None or not seguridad.reautenticar_clave(conexion, sesion.usuario_id, cuerpo.clave):
            seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa", "reauth rechazada")
            conexion.commit()
            raise HTTPException(status_code=401, detail="clave de confirmación inválida")
        seguridad.desactivar_totp(conexion, sesion.usuario_id)
        seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa", "desactivado")
        conexion.commit()
        return {"estado": "desactivado"}

    def _exigir_admin(sesion: seguridad.SesionActiva) -> None:
        if sesion.rol != "administrador":
            raise seguridad.ErrorPermiso("solo administrador")

    def _clave_idempotencia_o_400(idempotency_key: str | None) -> str:
        if not idempotency_key:
            raise HTTPException(status_code=400, detail="falta la cabecera Idempotency-Key")
        return idempotency_key

    @app.put("/hotel/habitaciones/{habitacion_id}")
    def definir_habitacion(
        habitacion: HabitacionIn,
        habitacion_id: str = RutaParam(pattern=PATRON_ID_HABITACION),
        idempotency_key: str | None = Header(default=None),
        if_none_match: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        """Alta o edición (spec-hotel-operacion-v1 §2.2–2.3). Con
        `If-None-Match: *` solo crea: una habitación existente responde 409."""
        _exigir_admin(sesion)
        clave = _clave_idempotencia_o_400(idempotency_key)
        solo_crear = (if_none_match or "").strip() == "*"
        cuerpo = {"habitacion_id": habitacion_id, "solo_crear": solo_crear, **json.loads(habitacion.model_dump_json())}

        def operacion() -> tuple[int, dict]:
            try:
                guardada = reservas_db.guardar_habitacion(
                    conexion, habitacion_id, habitacion.tipo, habitacion.capacidad, solo_crear
                )
            except reservas_db.HabitacionYaExiste as error:
                return 409, {"detail": str(error)}
            if guardada["creada"]:
                resultado = f"creada tipo={habitacion.tipo} capacidad={habitacion.capacidad}"
            elif guardada["cambios"]:
                resultado = "editada " + "; ".join(
                    f"{campo}: {antes}→{despues}" for campo, (antes, despues) in guardada["cambios"].items()
                )
            else:
                resultado = "sin cambios"
            seguridad.auditar(conexion, sesion.nombre, "habitacion", habitacion_id, resultado)
            return 200, {
                "habitacion_id": habitacion_id,
                "tipo": habitacion.tipo,
                "capacidad": habitacion.capacidad,
                **guardada,
            }

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.put("/hotel/tarifas")
    def definir_tarifa(
        tarifa: TarifaIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_admin(sesion)
        if tarifa.fecha_hasta <= tarifa.fecha_desde:
            raise HTTPException(status_code=400, detail="fecha_hasta debe ser mayor que fecha_desde")
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = json.loads(tarifa.model_dump_json())

        def operacion() -> tuple[int, dict]:
            tarifa_id = reservas_db.insertar_tarifa(
                conexion, tarifa.habitacion_id, tarifa.fecha_desde, tarifa.fecha_hasta, tarifa.tarifa_noche_clp
            )
            seguridad.auditar(
                conexion, sesion.nombre, "tarifa", tarifa.habitacion_id,
                f"{tarifa_id} {tarifa.fecha_desde}→{tarifa.fecha_hasta} ${tarifa.tarifa_noche_clp}/noche",
            )
            return 201, {
                "tarifa_id": tarifa_id,
                "habitacion_id": tarifa.habitacion_id,
                "fecha_desde": tarifa.fecha_desde.isoformat(),
                "fecha_hasta": tarifa.fecha_hasta.isoformat(),
                "tarifa_noche_clp": tarifa.tarifa_noche_clp,
            }

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.get("/hotel/oferta")
    def consultar_oferta(
        inicio: date,
        fin: date,
        personas: int = Query(gt=0, le=30),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        if fin <= inicio:
            raise HTTPException(status_code=400, detail="fin debe ser mayor que inicio")
        return reservas_db.oferta(conexion, inicio, fin, personas, datetime.now())

    @app.get("/hotel/habitaciones")
    def listar_habitaciones(
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        """Inventario operativo (spec-api-v1, 2026-11-03): estado, preparación,
        mantenimiento y tareas pendientes por unidad. Lectura para cualquier
        rol de la sesión; las mutaciones conservan sus reglas de rol."""
        return {"habitaciones": reservas_db.listar_habitaciones(conexion)}

    @app.get("/hotel/habitaciones/{habitacion_id}")
    def ficha_habitacion(
        habitacion_id: str,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        """Ficha (spec-hotel-operacion-v1 §2.6): cualquier rol; la auditoría
        solo para administrador y el documento según ROLES_DOCUMENTO."""
        return reservas_db.ficha_habitacion(
            conexion,
            habitacion_id,
            sesion.empresa_id,
            ver_documento=sesion.rol in ROLES_DOCUMENTO,
            ver_auditoria=sesion.rol == "administrador",
        )

    @app.post("/hotel/habitaciones/{habitacion_id}/servicio")
    def fijar_servicio_habitacion(
        habitacion_id: str,
        cuerpo_servicio: ServicioIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        """Baja lógica y reincorporación (spec-hotel-operacion-v1 §2.4)."""
        _exigir_admin(sesion)
        clave = _clave_idempotencia_o_400(idempotency_key)
        motivo = (cuerpo_servicio.motivo or "").strip() or None
        if not cuerpo_servicio.en_servicio and (motivo is None or len(motivo) < 3):
            raise HTTPException(status_code=422, detail="retirar de operación exige un motivo (3 a 200 caracteres)")
        cuerpo = {"habitacion_id": habitacion_id, **json.loads(cuerpo_servicio.model_dump_json())}

        def operacion() -> tuple[int, dict]:
            try:
                resultado = reservas_db.fijar_servicio(conexion, habitacion_id, cuerpo_servicio.en_servicio, motivo)
            except reservas_db.HabitacionInexistente as error:
                raise seguridad.ErrorPermiso(str(error)) from error
            except reservas_db.ReservasVigentes as error:
                return 409, {"detail": str(error), "reservas_vigentes": error.reservas}
            if not resultado["cambio"]:
                texto = "sin cambios"
            elif cuerpo_servicio.en_servicio:
                texto = "reincorporada"
            else:
                texto = f"retirada: {motivo}"
            seguridad.auditar(conexion, sesion.nombre, "habitacion-servicio", habitacion_id, texto)
            return 200, resultado

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.get("/hotel/ocupacion")
    def consultar_ocupacion(
        desde: date | None = None,
        hasta: date | None = None,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        """Estado por habitación y noche (spec-hotel-operacion-v1 §5); por
        defecto las 14 noches desde hoy (fecha del servidor)."""
        hoy = date.today()
        desde = desde or hoy
        hasta = hasta or desde + timedelta(days=14)
        return panel.ocupacion(conexion, sesion.empresa_id, desde, hasta, hoy)

    @app.get("/hotel/indicadores")
    def consultar_indicadores(
        desde: date | None = None,
        hasta: date | None = None,
        tipo: str | None = Query(default=None, max_length=50),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        """Panel operativo (spec-hotel-operacion-v1 §4); por defecto la noche de hoy."""
        hoy = date.today()
        desde = desde or hoy
        hasta = hasta or desde + timedelta(days=1)
        return panel.indicadores(conexion, sesion.empresa_id, desde, hasta, hoy, tipo or None)

    @app.post("/hotel/reservas")
    def confirmar_reserva(
        reserva: ReservaIn,
        response: Response,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        if not idempotency_key:
            raise HTTPException(status_code=400, detail="falta la cabecera Idempotency-Key")
        if reserva.fin <= reserva.inicio:
            raise HTTPException(status_code=400, detail="fin debe ser mayor que inicio")
        cuerpo = json.loads(reserva.model_dump_json())

        def operacion() -> tuple[int, dict]:
            try:
                creada = reservas_db.crear_reserva(
                    conexion,
                    empresa_id=sesion.empresa_id,
                    habitacion_id=reserva.habitacion_id,
                    inicio=reserva.inicio,
                    fin=reserva.fin,
                    huesped_nombre=reserva.huesped.nombre,
                    huesped_documento=reserva.huesped.documento,
                )
            except reservas_db.SinCupo as error:
                return 409, {"detail": str(error)}
            except (reservas_db.SinTarifaVigente, reservas_db.HabitacionNoVendible) as error:
                return 409, {"detail": str(error)}
            seguridad.auditar(conexion, sesion.nombre, "reserva", creada["reserva_id"], "confirmada")
            return 201, creada

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(
                conexion, sesion.empresa_id, idempotency_key, cuerpo, operacion
            )
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    def _exigir_rol(sesion: seguridad.SesionActiva, roles) -> None:
        if sesion.rol not in roles:
            raise seguridad.ErrorPermiso("rol no autorizado")

    @app.post("/hotel/reservas/{reserva_id}/pagos")
    def registrar_pago(
        reserva_id: str,
        pago: PagoIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"reserva_id": reserva_id, **json.loads(pago.model_dump_json())}

        def operacion() -> tuple[int, dict]:
            if pago.modo == "pasarela":
                return 503, {"detail": "pasarela no configurada", "estado": "pendiente"}
            _exigir_rol(sesion, cobro.ROLES_PAGO_MANUAL)
            try:
                registrado = cobro.registrar_pago_manual(
                    conexion, aplicacion.nucleo, sesion.empresa_id, reserva_id, pago.monto_clp, pago.clave
                )
            except cobro.PagoRechazadoPorNucleo as error:
                seguridad.auditar(conexion, sesion.nombre, "pago", f"{reserva_id}:{pago.clave}", "rechazado-nucleo")
                return 403, {"detail": str(error)}
            except cobro.PagoDuplicadoConDatosDistintos as error:
                seguridad.auditar(conexion, sesion.nombre, "pago", f"{reserva_id}:{pago.clave}", "conflicto-clave-cobro")
                return 409, {"detail": str(error)}
            seguridad.auditar(conexion, sesion.nombre, "pago", f"{reserva_id}:{pago.clave}", "confirmado")
            return 201, registrado

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.get("/hotel/caja")
    def ver_caja(
        fecha: date,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        _exigir_rol(sesion, cobro.ROLES_CAJA)
        return cobro.caja_del_dia(conexion, sesion.empresa_id, fecha)

    @app.post("/hotel/reservas/{reserva_id}/entrada")
    def check_in(
        reserva_id: str,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"reserva_id": reserva_id}

        def operacion() -> tuple[int, dict]:
            try:
                ingreso = cobro.entrada(conexion, sesion.empresa_id, reserva_id)
            except (cobro.HabitacionNoLista, cobro.TransicionInvalida) as error:
                return 409, {"detail": str(error)}
            seguridad.auditar(conexion, sesion.nombre, "entrada", reserva_id, "en_estadia")
            return 200, ingreso

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.post("/hotel/reservas/{reserva_id}/salida")
    def check_out(
        reserva_id: str,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"reserva_id": reserva_id}

        def operacion() -> tuple[int, dict]:
            try:
                liquidada = cobro.salida(conexion, sesion.empresa_id, reserva_id)
            except (cobro.SaldoPendiente, cobro.TransicionInvalida) as error:
                return 409, {"detail": str(error)}
            seguridad.auditar(conexion, sesion.nombre, "salida", reserva_id, "liquidada")
            return 200, liquidada

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    # --- Maduración de la operación (spec-api-v1, 2026-10-30) ---

    @app.get("/hotel/reservas")
    def buscar_reservas_hotel(
        fecha: date | None = None,
        estado: str | None = None,
        texto: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        habitacion_id: str | None = Query(default=None, max_length=50),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        if estado is not None and estado not in reservas_db.ESTADOS_VALIDOS:
            raise HTTPException(status_code=422, detail="estado inválido")
        if desde is not None and hasta is not None and hasta <= desde:
            raise HTTPException(status_code=422, detail="hasta debe ser mayor que desde")
        items = reservas_db.buscar_reservas(
            conexion,
            empresa_id=sesion.empresa_id,
            fecha=fecha,
            estado=estado,
            texto=texto,
            ver_documento=sesion.rol in ROLES_DOCUMENTO,
            desde=desde,
            hasta=hasta,
            habitacion_id=habitacion_id or None,
        )
        return {"reservas": items, "total": len(items)}

    @app.get("/hotel/reservas/{reserva_id}")
    def detalle_reserva_hotel(
        reserva_id: str,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        """Detalle con cuenta (spec-hotel-operacion-v1 §3.2); ajena → 403."""
        return cobro.detalle_reserva(
            conexion, sesion.empresa_id, reserva_id, ver_documento=sesion.rol in ROLES_DOCUMENTO
        )

    @app.get("/usuarios")
    def listar_usuarios(
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        _exigir_admin(sesion)
        return {"usuarios": seguridad.listar_usuarios(conexion, sesion.empresa_id)}

    @app.post("/usuarios")
    def alta_usuario(
        usuario: UsuarioIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_admin(sesion)
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = json.loads(usuario.model_dump_json())

        def operacion() -> tuple[int, dict]:
            existe = conexion.execute(
                "SELECT 1 FROM usuarios WHERE empresa_id = %s AND nombre = %s",
                (sesion.empresa_id, usuario.nombre),
            ).fetchone()
            if existe is not None:
                return 409, {"detail": "nombre de usuario ya existe en la empresa"}
            usuario_id = seguridad.crear_usuario(
                conexion, sesion.empresa_id, usuario.nombre, usuario.rol, usuario.clave
            )
            seguridad.auditar(conexion, sesion.nombre, "usuario", usuario_id, "creado")
            return 201, {"id": usuario_id, "nombre": usuario.nombre, "rol": usuario.rol, "activo": True}

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.post("/usuarios/{usuario_id}/clave")
    def cambiar_clave_usuario(
        usuario_id: str,
        cuerpo_clave: ClaveIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        if sesion.rol != "administrador" and sesion.usuario_id != usuario_id:
            raise HTTPException(status_code=403, detail="acceso denegado")
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"usuario_id": usuario_id, **json.loads(cuerpo_clave.model_dump_json())}

        def operacion() -> tuple[int, dict]:
            seguridad.buscar_usuario_en_empresa(conexion, sesion.empresa_id, usuario_id)
            seguridad.cambiar_clave(conexion, usuario_id, cuerpo_clave.clave)
            seguridad.auditar(conexion, sesion.nombre, "usuario-clave", usuario_id, "cambiada")
            return 200, {"id": usuario_id, "estado": "clave actualizada"}

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.post("/usuarios/{usuario_id}/revocacion")
    def revocar_usuario(
        usuario_id: str,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_admin(sesion)
        if usuario_id == sesion.usuario_id:
            raise HTTPException(status_code=409, detail="para cerrar tu sesión usa DELETE /sesion")
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"usuario_id": usuario_id, "operacion": "revocacion"}

        def operacion() -> tuple[int, dict]:
            seguridad.buscar_usuario_en_empresa(conexion, sesion.empresa_id, usuario_id)
            revocadas = seguridad.revocar_sesiones_de_usuario(conexion, usuario_id)
            seguridad.auditar(conexion, sesion.nombre, "usuario-revocacion", usuario_id, f"{revocadas} sesiones")
            return 200, {"id": usuario_id, "sesiones_revocadas": revocadas}

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.post("/usuarios/{usuario_id}/baja")
    def baja_usuario(
        usuario_id: str,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_admin(sesion)
        if usuario_id == sesion.usuario_id:
            raise HTTPException(status_code=409, detail="no puedes darte de baja a ti mismo")
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"usuario_id": usuario_id, "operacion": "baja"}

        def operacion() -> tuple[int, dict]:
            _id, _nombre, rol, activo = seguridad.buscar_usuario_en_empresa(
                conexion, sesion.empresa_id, usuario_id
            )
            if not activo:
                return 409, {"detail": "el usuario ya está de baja"}
            if rol == "administrador" and seguridad.contar_administradores_activos(
                conexion, sesion.empresa_id
            ) <= 1:
                return 409, {"detail": "no se puede dar de baja al último administrador activo"}
            seguridad.dar_de_baja(conexion, usuario_id)
            seguridad.auditar(conexion, sesion.nombre, "usuario-baja", usuario_id, "de baja")
            return 200, {"id": usuario_id, "activo": False}

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.post("/hotel/habitaciones/{habitacion_id}/limpieza")
    def completar_limpieza_habitacion(
        habitacion_id: str,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_rol(sesion, cobro.ROLES_LIMPIEZA)
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"habitacion_id": habitacion_id, "operacion": "limpieza"}

        def operacion() -> tuple[int, dict]:
            try:
                resultado = cobro.completar_limpieza(conexion, habitacion_id)
            except cobro.RecursoAjenoOInexistente as error:
                raise seguridad.ErrorPermiso(str(error)) from error
            seguridad.auditar(conexion, sesion.nombre, "limpieza", habitacion_id, "completada")
            return 200, resultado

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.post("/hotel/habitaciones/{habitacion_id}/mantenimiento")
    def fijar_mantenimiento_habitacion(
        habitacion_id: str,
        cuerpo_mantenimiento: MantenimientoIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_rol(sesion, cobro.ROLES_MANTENIMIENTO)
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"habitacion_id": habitacion_id, **json.loads(cuerpo_mantenimiento.model_dump_json())}

        def operacion() -> tuple[int, dict]:
            try:
                resultado = cobro.fijar_mantenimiento(conexion, habitacion_id, cuerpo_mantenimiento.abierto)
            except cobro.RecursoAjenoOInexistente as error:
                raise seguridad.ErrorPermiso(str(error)) from error
            seguridad.auditar(
                conexion, sesion.nombre, "mantenimiento", habitacion_id,
                "abierto" if cuerpo_mantenimiento.abierto else "cerrado",
            )
            return 200, resultado

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.post("/hotel/reservas/{reserva_id}/cancelacion")
    def cancelar_reserva(
        reserva_id: str,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_rol(sesion, cobro.ROLES_CANCELACION)
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"reserva_id": reserva_id, "operacion": "cancelacion"}

        def operacion() -> tuple[int, dict]:
            try:
                resultado = cobro.cancelar(conexion, sesion.empresa_id, reserva_id, datetime.now())
            except cobro.TransicionInvalida as error:
                return 409, {"detail": str(error)}
            seguridad.auditar(conexion, sesion.nombre, "cancelacion", reserva_id, "cancelada")
            return 200, resultado

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.post("/hotel/reservas/{reserva_id}/cargos")
    def asentar_cargo_reserva(
        reserva_id: str,
        cargo: CargoIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_rol(sesion, cobro.ROLES_CARGO)
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"reserva_id": reserva_id, **json.loads(cargo.model_dump_json())}

        def operacion() -> tuple[int, dict]:
            try:
                resultado = cobro.asentar_cargo(
                    conexion, sesion.empresa_id, reserva_id, cargo.concepto, cargo.monto_clp
                )
            except cobro.TransicionInvalida as error:
                return 409, {"detail": str(error)}
            seguridad.auditar(conexion, sesion.nombre, "cargo", f"{reserva_id}:{resultado['cargo_id']}", "asentado")
            return 201, resultado

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    # --- Canal público (spec-api-v1 «Canal público», V1-ISSUE-22/24) ---

    @app.get("/publico/disponibilidad")
    def disponibilidad_publica(
        inicio: date,
        fin: date,
        personas: int = Query(gt=0, le=canal_publico.MAX_PERSONAS),
        conexion=Depends(_conexion),
    ) -> dict:
        return canal_publico.disponibilidad(conexion, inicio, fin, personas, datetime.now())

    @app.post("/publico/solicitudes")
    def crear_solicitud_publica(
        solicitud: SolicitudPublicaIn,
        request: Request,
        idempotency_key: str | None = Header(default=None),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        if not idempotency_key or not idempotency_key.strip():
            raise HTTPException(status_code=422, detail="falta la cabecera Idempotency-Key")
        longitud = request.headers.get("content-length")
        if longitud and int(longitud) > canal_publico.TOPE_CUERPO_BYTES:
            raise HTTPException(status_code=413, detail="el cuerpo supera el tamaño permitido")
        ip = request.client.host if request.client else "desconocida"
        freno: canal_publico.FrenoDeSolicitudes = app.state.freno_solicitudes
        if not freno.permite(ip):
            raise HTTPException(
                status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
            )
        resultado = canal_publico.crear_solicitud(
            conexion, aplicacion.nucleo.empresa.id, solicitud.habitacion_id, solicitud.inicio,
            solicitud.fin, solicitud.personas, solicitud.huesped_nombre,
            solicitud.huesped_contacto, idempotency_key.strip(),
        )
        codigo = 200 if resultado.get("reintento") else 201
        conexion.commit()
        return JSONResponse(status_code=codigo, content=resultado)

    @app.get("/hotel/solicitudes")
    def bandeja_solicitudes(
        estado: str | None = None,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        _exigir_rol(sesion, canal_publico.ROLES_GESTION)
        return canal_publico.bandeja(conexion, sesion.empresa_id, estado)

    @app.post("/hotel/solicitudes/{solicitud_id}/conversion")
    def convertir_solicitud(
        solicitud_id: str,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_rol(sesion, canal_publico.ROLES_GESTION)
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"solicitud_id": solicitud_id, "operacion": "conversion"}

        def operacion() -> tuple[int, dict]:
            try:
                resultado = canal_publico.convertir(
                    conexion, sesion.empresa_id, solicitud_id, sesion.nombre
                )
            except canal_publico.SolicitudAjenaOInexistente:
                return 403, {"detail": "acceso denegado"}
            except canal_publico.TransicionInvalida as error:
                return 409, {"detail": str(error)}
            except canal_publico.SinCupoOSinTarifa as error:
                return 409, {"detail": error.detalle}
            return 201, resultado

        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.post("/hotel/solicitudes/{solicitud_id}/rechazo")
    def rechazar_solicitud(
        solicitud_id: str,
        cuerpo_rechazo: RechazoSolicitudIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_rol(sesion, canal_publico.ROLES_GESTION)
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"solicitud_id": solicitud_id, "motivo": cuerpo_rechazo.motivo}

        def operacion() -> tuple[int, dict]:
            try:
                resultado = canal_publico.rechazar(
                    conexion, sesion.empresa_id, solicitud_id, cuerpo_rechazo.motivo, sesion.nombre
                )
            except canal_publico.SolicitudAjenaOInexistente:
                return 403, {"detail": "acceso denegado"}
            except canal_publico.TransicionInvalida as error:
                return 409, {"detail": str(error)}
            return 200, resultado

        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    # ------------------------------------------------------------------
    # Contacto y leads de la landing (spec-api-v1 «Contacto y leads»)
    # ------------------------------------------------------------------

    @app.post("/publico/leads")
    def crear_lead_publico(
        lead: LeadPublicoIn,
        request: Request,
        idempotency_key: str | None = Header(default=None),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        if not idempotency_key or not idempotency_key.strip():
            raise HTTPException(status_code=422, detail="falta la cabecera Idempotency-Key")
        longitud = request.headers.get("content-length")
        if longitud and int(longitud) > canal_publico.TOPE_CUERPO_BYTES:
            raise HTTPException(status_code=413, detail="el cuerpo supera el tamaño permitido")
        ip = request.client.host if request.client else "desconocida"
        freno: canal_publico.FrenoDeSolicitudes = app.state.freno_solicitudes
        if not freno.permite(ip):
            raise HTTPException(
                status_code=429, detail="demasiadas solicitudes; espera un minuto e intenta de nuevo"
            )
        try:
            resultado = leads_mod.crear_lead(
                conexion, aplicacion.nucleo.empresa.id, lead.nombre, lead.correo, lead.telefono,
                lead.huespedes, lead.check_in, lead.check_out, lead.mensaje,
                idempotency_key.strip(),
            )
        except leads_mod.LeadInvalido as error:
            raise HTTPException(status_code=422, detail=error.detalle)
        except leads_mod.ClaveEnConflicto as error:
            raise HTTPException(status_code=409, detail=str(error))
        codigo = 200 if resultado.get("reintento") else 201
        conexion.commit()
        return JSONResponse(status_code=codigo, content=resultado)

    @app.get("/hotel/leads")
    def bandeja_leads(
        estado: str | None = None,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        _exigir_rol(sesion, leads_mod.ROLES_GESTION)
        try:
            return leads_mod.bandeja(conexion, sesion.empresa_id, estado)
        except leads_mod.LeadInvalido as error:
            raise HTTPException(status_code=422, detail=error.detalle)

    @app.post("/hotel/leads/{lead_id}/estado")
    def gestionar_lead(
        lead_id: str,
        gestion: GestionLeadIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_rol(sesion, leads_mod.ROLES_GESTION)
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"lead_id": lead_id, "estado": gestion.estado, "nota": gestion.nota}

        def operacion() -> tuple[int, dict]:
            try:
                resultado = leads_mod.gestionar(
                    conexion, sesion.empresa_id, lead_id, gestion.estado, gestion.nota,
                    sesion.nombre,
                )
            except leads_mod.LeadAjenoOInexistente:
                return 403, {"detail": "acceso denegado"}
            except leads_mod.TransicionInvalida as error:
                return 409, {"detail": str(error)}
            return 200, resultado

        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    # ------------------------------------------------------------------
    # Agente de reservas N0 (spec 005 / spec-api-v1 «Agente de reservas»)
    # ------------------------------------------------------------------

    @app.post("/hotel/agente/consultas")
    def registrar_consulta_agente(
        cuerpo_consulta: ConsultaAgenteIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_rol(sesion, agente.ROLES_GESTION)
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"canal_origen": cuerpo_consulta.canal_origen, "texto": cuerpo_consulta.texto}

        def operacion() -> tuple[int, dict]:
            consulta = agente.registrar_consulta(
                conexion, sesion.empresa_id, cuerpo_consulta.canal_origen,
                cuerpo_consulta.texto, sesion.nombre,
            )
            politica = agente.politica_de(conexion, sesion.empresa_id)
            try:
                resultado = agente.procesar(conexion, consulta, app.state.modelo_agente, politica)
            except NoConfigurado:
                return 503, {"detail": "modelo no configurado", "estado": "pendiente", "consulta": consulta}
            detalle = agente.detalle_consulta(conexion, sesion.empresa_id, consulta["consulta_id"])
            if resultado.get("estado") == "escalado":
                return 201, {"consulta": detalle, "motivo": resultado["motivo"]}
            return 201, {"consulta": detalle, "borrador": resultado}

        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.get("/hotel/agente/consultas")
    def bandeja_consultas_agente(
        estado: str | None = None,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        _exigir_rol(sesion, agente.ROLES_GESTION)
        return agente.listar_consultas(conexion, sesion.empresa_id, estado)

    @app.get("/hotel/agente/consultas/{consulta_id}")
    def detalle_consulta_agente(
        consulta_id: str,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        _exigir_rol(sesion, agente.ROLES_GESTION)
        return agente.detalle_consulta(conexion, sesion.empresa_id, consulta_id)

    @app.post("/hotel/agente/borradores/{borrador_id}/aprobacion")
    def aprobar_borrador_agente(
        borrador_id: str,
        cuerpo_aprobacion: AprobacionBorradorIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_rol(sesion, agente.ROLES_GESTION)
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"borrador_id": borrador_id, "texto_editado": cuerpo_aprobacion.texto_editado}

        def operacion() -> tuple[int, dict]:
            try:
                resultado = agente.aprobar(
                    conexion, sesion.empresa_id, borrador_id, sesion.nombre,
                    cuerpo_aprobacion.texto_editado, datetime.now(),
                )
            except agente.ConsultaAjenaOInexistente:
                return 403, {"detail": "acceso denegado"}
            except agente.TransicionInvalida as error:
                return 409, {"detail": str(error)}
            if resultado.get("estado") == "oferta_cambiada":
                return 409, {"detail": resultado["detail"], "borrador": resultado["borrador"]}
            return 200, resultado

        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.post("/hotel/agente/borradores/{borrador_id}/descarte")
    def descartar_borrador_agente(
        borrador_id: str,
        cuerpo_descarte: DescarteBorradorIn,
        idempotency_key: str | None = Header(default=None),
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_rol(sesion, agente.ROLES_GESTION)
        clave = _clave_idempotencia_o_400(idempotency_key)
        cuerpo = {"borrador_id": borrador_id, "motivo": cuerpo_descarte.motivo}

        def operacion() -> tuple[int, dict]:
            try:
                resultado = agente.descartar(
                    conexion, sesion.empresa_id, borrador_id, cuerpo_descarte.motivo, sesion.nombre
                )
            except agente.ConsultaAjenaOInexistente:
                return 403, {"detail": "acceso denegado"}
            except agente.TransicionInvalida as error:
                return 409, {"detail": str(error)}
            return 200, resultado

        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.get("/hotel/agente/politica")
    def obtener_politica_agente(
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        _exigir_rol(sesion, agente.ROLES_GESTION)
        return {"empresa_id": sesion.empresa_id, **agente.politica_de(conexion, sesion.empresa_id)}

    @app.put("/hotel/agente/politica")
    def actualizar_politica_agente(
        cuerpo_politica: PoliticaAgenteIn,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> JSONResponse:
        _exigir_rol(sesion, {"administrador"})
        try:
            resultado = agente.actualizar_politica(
                conexion, sesion.empresa_id, cuerpo_politica.model_dump(exclude_none=True), sesion.nombre
            )
        except agente.ConsultaInvalida as error:
            return JSONResponse(status_code=400, content={"detail": error.detalle})
        except agente.PoliticaInvalida as error:
            return JSONResponse(status_code=409, content={"detail": error.detalle})
        conexion.commit()
        return JSONResponse(status_code=200, content=resultado)

    @app.exception_handler(cobro.RecursoAjenoOInexistente)
    @app.exception_handler(cobro.PagoRechazadoPorNucleo)
    async def manejar_acceso(_request: Request, _exc: Exception) -> Response:
        return Response(content='{"detail":"acceso denegado"}', status_code=403, media_type="application/json")

    @app.exception_handler(reservas_db.HabitacionInexistente)
    async def manejar_habitacion_inexistente(_request: Request, _exc: Exception) -> Response:
        return Response(content='{"detail":"acceso denegado"}', status_code=403, media_type="application/json")

    @app.exception_handler(panel.PeriodoInvalido)
    async def manejar_periodo(_request: Request, exc: panel.PeriodoInvalido) -> Response:
        return Response(content=json.dumps({"detail": str(exc)}, ensure_ascii=False), status_code=422, media_type="application/json")

    @app.exception_handler(psycopg.IntegrityError)
    async def manejar_integridad(_request: Request, _exc: psycopg.IntegrityError) -> Response:
        return Response(content='{"detail":"conflicto de integridad"}', status_code=409, media_type="application/json")

    @app.exception_handler(reservas_db.SinCupo)
    @app.exception_handler(reservas_db.SinTarifaVigente)
    async def manejar_conflictos(_request: Request, exc: Exception) -> Response:
        return Response(content=json.dumps({"detail": str(exc)}, ensure_ascii=False), status_code=409, media_type="application/json")

    @app.exception_handler(idempotencia.ConflictoIdempotencia)
    async def manejar_conflicto_idempotencia(_request: Request, exc: idempotencia.ConflictoIdempotencia) -> Response:
        return Response(content=json.dumps({"detail": str(exc)}, ensure_ascii=False), status_code=409, media_type="application/json")

    @app.exception_handler(seguridad.ErrorPermiso)
    async def manejar_permiso(_request: Request, _exc: seguridad.ErrorPermiso) -> Response:
        return Response(
            content='{"detail":"acceso denegado"}',
            status_code=403,
            media_type="application/json",
        )

    @app.exception_handler(canal_publico.SolicitudAjenaOInexistente)
    async def manejar_solicitud_ajena(_request: Request, _exc: canal_publico.SolicitudAjenaOInexistente) -> Response:
        return Response(content='{"detail":"acceso denegado"}', status_code=403, media_type="application/json")

    @app.exception_handler(canal_publico.SolicitudInvalida)
    async def manejar_solicitud_invalida(_request: Request, exc: canal_publico.SolicitudInvalida) -> Response:
        return Response(
            content=json.dumps({"detail": exc.detalle}, ensure_ascii=False),
            status_code=422,
            media_type="application/json",
        )

    @app.exception_handler(canal_publico.SinCupoOSinTarifa)
    async def manejar_sin_cupo_publico(_request: Request, exc: canal_publico.SinCupoOSinTarifa) -> Response:
        return Response(
            content=json.dumps({"detail": exc.detalle}, ensure_ascii=False),
            status_code=409,
            media_type="application/json",
        )

    @app.exception_handler(canal_publico.ClaveEnConflicto)
    async def manejar_clave_publica(_request: Request, exc: canal_publico.ClaveEnConflicto) -> Response:
        return Response(
            content=json.dumps({"detail": str(exc)}, ensure_ascii=False),
            status_code=409,
            media_type="application/json",
        )

    @app.exception_handler(canal_publico.TransicionInvalida)
    async def manejar_transicion_solicitud(_request: Request, exc: canal_publico.TransicionInvalida) -> Response:
        return Response(
            content=json.dumps({"detail": str(exc)}, ensure_ascii=False),
            status_code=409,
            media_type="application/json",
        )

    @app.exception_handler(agente.ConsultaInvalida)
    async def manejar_consulta_agente_invalida(_request: Request, exc: agente.ConsultaInvalida) -> Response:
        return Response(
            content=json.dumps({"detail": exc.detalle}, ensure_ascii=False),
            status_code=400,
            media_type="application/json",
        )

    @app.exception_handler(agente.ConsultaAjenaOInexistente)
    async def manejar_consulta_agente_ajena(_request: Request, _exc: agente.ConsultaAjenaOInexistente) -> Response:
        return Response(content='{"detail":"acceso denegado"}', status_code=403, media_type="application/json")

    @app.exception_handler(agente.TransicionInvalida)
    async def manejar_transicion_borrador(_request: Request, exc: agente.TransicionInvalida) -> Response:
        return Response(
            content=json.dumps({"detail": str(exc)}, ensure_ascii=False),
            status_code=409,
            media_type="application/json",
        )

    @app.exception_handler(agente.PoliticaInvalida)
    async def manejar_politica_invalida(_request: Request, exc: agente.PoliticaInvalida) -> Response:
        return Response(
            content=json.dumps({"detail": exc.detalle}, ensure_ascii=False),
            status_code=409,
            media_type="application/json",
        )

    return app


def main(configuracion: Configuracion | None = None) -> None:
    import uvicorn

    configuracion = configuracion or cargar_desde_entorno()
    try:
        app = crear_app(configuracion=configuracion)
    except ErrorArranque as error:
        raise SystemExit(f"el proceso no arranca: {error}")
    uvicorn.run(app, host=configuracion.host, port=configuracion.puerto)
