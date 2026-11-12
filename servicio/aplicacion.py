"""Fábrica de la aplicación: núcleo y hotel en el mismo proceso, un solo servicio.

Regla de arranque (spec-backend-v1): el hotel entra con la empresa del
núcleo; un establecimiento de otra empresa impide que el proceso arranque.
Con `database_url` configurada, el arranque también aplica migraciones y crea
el administrador inicial desde variables de entorno (spec-api-v1).
"""
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for _ruta in (RAIZ / "core" / "incremento1", RAIZ / "verticales" / "hotel" / "incremento1"):
    if ( _s := str(_ruta) ) not in sys.path:
        sys.path.insert(0, _s)

import psycopg  # noqa: E402
from fastapi import FastAPI, HTTPException, Request, Response  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from hotel_inventario.dominio import EstadoUnidad, Establecimiento, Unidad  # noqa: E402
from hotel_inventario.servicio import ServicioHotelInventario  # noqa: E402
from nucleo.servicio import Nucleo  # noqa: E402

from .configuracion import Configuracion, cargar_desde_entorno  # noqa: E402
from .empresa_titular import (  # noqa: E402
    EMPRESA_TITULAR,
    EMPRESA_TITULAR_MARCA,
    EMPRESA_TITULAR_RUT,
)
from . import documental  # noqa: E402
from . import inventario_documental  # noqa: E402
from .migracion import aplicar_migraciones  # noqa: E402
from . import seguridad  # noqa: E402
from . import idempotencia  # noqa: E402
from . import google_oidc  # noqa: E402
from . import reservas as reservas_db  # noqa: E402
from . import cobro  # noqa: E402
from . import panel  # noqa: E402
from . import canal_publico  # noqa: E402
from . import agente  # noqa: E402
from .modelo_lenguaje import ModeloGuionado, NoConfigurado, SinAdaptador  # noqa: E402
from nucleo.empresa import Empresa  # noqa: E402

NOMBRE_COOKIE_SESION = "sid"


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


def empresa_desde_config(config: Configuracion | None) -> Empresa:
    """Resuelve la empresa del núcleo: titular real si el despliegue lo pide;
    si no, el marcador sintético de las pruebas."""
    if config is None:
        return Nucleo().empresa
    if config.empresa_titular or config.empresa_id or config.empresa_nombre:
        if config.empresa_titular and not config.empresa_id and not config.empresa_nombre:
            return EMPRESA_TITULAR
        sintetica = (
            bool(config.empresa_es_sintetica)
            if config.empresa_es_sintetica is not None
            else False
        )
        return Empresa(
            id=(config.empresa_id or EMPRESA_TITULAR.id).strip(),
            nombre=(config.empresa_nombre or EMPRESA_TITULAR.nombre).strip(),
            es_sintetico=sintetica,
        )
    return Nucleo().empresa


def construir_aplicacion(nucleo: Nucleo | None = None) -> Aplicacion:
    nucleo = nucleo or Nucleo()
    if nucleo.empresa.es_sintetico:
        establecimiento = Establecimiento(
            id="EST-SINT-001", empresa_id=nucleo.empresa.id, nombre="Hotel Herencia sintético"
        )
    else:
        establecimiento = Establecimiento(
            id="EST-HERENCIA-001", empresa_id=nucleo.empresa.id, nombre=EMPRESA_TITULAR_MARCA
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
            # HAB-SINT solo en núcleo sintético de pruebas. En titular real
            # el inventario operativo son HAB-01..17 (documental); el resto se retira.
            if aplicacion.nucleo.empresa.es_sintetico:
                reservas_db.sembrar_habitaciones(conexion)
            if config.inventario_documental and not aplicacion.nucleo.empresa.es_sintetico:
                inventario_documental.sembrar_inventario_documental(
                    conexion,
                    establecimiento_id=inventario_documental.ESTABLECIMIENTO_HERENCIA,
                )
                # Re-aplica por si el arranque anterior dejó ajenas en FDS o
                # HAB-01..17 todavía fuera de servicio tras la carga B1.
                inventario_documental.retirar_inventario_ajeno(conexion)
                inventario_documental.activar_inventario_real(conexion)
                # D3 dueño 2026-11-12: precios fijos referenciales todas las fechas.
                inventario_documental.aplicar_tarifas_fijas_referenciales(conexion)
                documental.sembrar_paquete_documental(conexion)
            conexion.commit()
    except RuntimeError as error:
        raise ErrorArranque(str(error))
    except psycopg.OperationalError as error:
        raise ErrorArranque(f"no se pudo conectar a la base de datos: {error}")


# Modelos de entrada HTTP: viven en servicio/rutas/modelos.py (ARC-A01, #334)
# para que los módulos de rutas los importen sin circularidad.
from .rutas.modelos import (  # noqa: E402
    AprobacionBorradorIn, CargoIn, ClaveActualIn, ClaveIn, CodigoTotpIn,
    ConsultaAgenteIn, Credenciales, DescarteBorradorIn, GestionLeadIn,
    HabitacionIn, HuespedIn, LeadPublicoIn, MantenimientoIn, PagoIn,
    PATRON_ID_HABITACION, PoliticaAgenteIn, RechazoSolicitudIn, ReservaIn,
    ServicioIn, SolicitudPublicaIn, TarifaIn, UsuarioIn,
)
from .rutas import acceso, hotel  # noqa: E402  (routers incluidos en crear_app)
from .rutas import agente as rutas_agente  # noqa: E402  (alias: `agente` sigue siendo el dominio)
from .rutas import mensajeria as rutas_mensajeria  # noqa: E402


def crear_app(aplicacion: Aplicacion | None = None, configuracion: Configuracion | None = None) -> FastAPI:
    if aplicacion is None:
        aplicacion = construir_aplicacion(nucleo=Nucleo(empresa=empresa_desde_config(configuracion)))
    app = FastAPI(title="plataforma-salman-herencia-api", version="1.1.0")
    app.add_middleware(canal_publico.TopeCuerpoPublico)
    app.state.aplicacion = aplicacion
    app.state.configuracion = configuracion
    if configuracion is not None and configuracion.database_url:
        _preparar_base_de_datos(configuracion, aplicacion)
        app.state.database_url = configuracion.database_url
    # Traza fija para el log monitor de Railway/Vercel: sin esto, un
    # titular↔sintético mal configurado solo se veía como 401 mudo en el browser.
    logging.getLogger("servicio.sesion").info(
        "nucleo_empresa id=%s nombre=%s sintetica=%s titular_flag=%s",
        aplicacion.nucleo.empresa.id,
        aplicacion.nucleo.empresa.nombre,
        aplicacion.nucleo.empresa.es_sintetico,
        bool(configuracion and configuracion.empresa_titular),
    )
    app.state.freno_logins = seguridad.FrenoDeLogins()
    app.state.freno_solicitudes = canal_publico.FrenoDeSolicitudes(
        max_por_minuto=configuracion.publico_max_por_minuto if configuracion else 6
    )
    if configuracion is not None and configuracion.agente_guion_json:
        app.state.modelo_agente = ModeloGuionado(json.loads(configuracion.agente_guion_json))
    elif configuracion is not None and configuracion.modelo_base_url and configuracion.modelo_api_key:
        # #319: adaptador HTTP genérico (spec 005). Sin guion y con
        # MODELO_BASE_URL + MODELO_API_KEY en el entorno, el agente habla con
        # un endpoint OpenAI-compatible. La ausencia de ambas deja el puerto
        # en SinAdaptador (503 «modelo no configurado», D-AGT-02 pendiente).
        from .modelo_http import ModeloHttp
        app.state.modelo_agente = ModeloHttp(
            base_url=configuracion.modelo_base_url,
            api_key=configuracion.modelo_api_key,
            modelo=configuracion.modelo_nombre or "modelo",
        )
    else:
        app.state.modelo_agente = SinAdaptador()
    from .canal_salida import SinCanal
    from .mensajeria import PuertoWhatsapp
    app.state.canal_agente = SinCanal()
    if (
        configuracion is not None
        and configuracion.whatsapp_app_secret
        and configuracion.whatsapp_verify_token
        and configuracion.whatsapp_phone_number_id
    ):
        app.state.mensajeria = PuertoWhatsapp(
            configuracion.whatsapp_app_secret,
            configuracion.whatsapp_verify_token,
            configuracion.whatsapp_phone_number_id,
        )
    else:
        app.state.mensajeria = None
    app.state.estados_oauth = google_oidc.EstadosOAuth()
    app.state.pendientes_mfa = google_oidc.PendientesMfa()

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
        empresa = aplicacion.nucleo.empresa
        rut = None
        if configuracion is not None and configuracion.empresa_rut:
            rut = configuracion.empresa_rut
        elif not empresa.es_sintetico and empresa.id == EMPRESA_TITULAR.id:
            rut = EMPRESA_TITULAR_RUT
        return {
            "estado": "ok",
            "nucleo": "cargado",
            "hotel": "cargado",
            "empresa": empresa.id,
            "empresa_nombre": empresa.nombre,
            "empresa_rut": rut,
            "es_sintetica": empresa.es_sintetico,
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

    app.include_router(acceso.router)
    app.include_router(hotel.router)
    app.include_router(rutas_agente.router)
    app.include_router(rutas_mensajeria.router)

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
