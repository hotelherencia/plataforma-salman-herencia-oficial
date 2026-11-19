"""Fábrica de la aplicación: núcleo y hotel en el mismo proceso, un solo servicio.

Regla de arranque (spec-backend-v1): el hotel entra con la empresa del
núcleo; un establecimiento de otra empresa impide que el proceso arranque.
Con `database_url` configurada, el arranque también aplica migraciones y crea
el administrador inicial desde variables de entorno (spec-api-v1).
"""
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for _ruta in (RAIZ / "core" / "incremento1", RAIZ / "verticales" / "hotel" / "incremento1"):
    if ( _s := str(_ruta) ) not in sys.path:
        sys.path.insert(0, _s)

import psycopg  # noqa: E402
from fastapi import FastAPI, HTTPException, Request, Response  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from hotel_inventario.dominio import EstadoUnidad, Establecimiento, Unidad  # noqa: E402
from hotel_inventario.servicio import ServicioHotelInventario  # noqa: E402
from nucleo.servicio import Nucleo  # noqa: E402

from .configuracion import Configuracion, cargar_desde_entorno  # noqa: E402
from .empresa_titular import (  # noqa: E402
    EMPRESA_TITULAR,
    EMPRESA_TITULAR_MARCA,
)
from . import documental  # noqa: E402
from . import inventario_documental  # noqa: E402
from .migracion import aplicar_migraciones, migraciones_pendientes  # noqa: E402
from . import seguridad  # noqa: E402
from . import idempotencia  # noqa: E402
from . import google_oidc  # noqa: E402
from . import reservas as reservas_db  # noqa: E402
from . import cobro  # noqa: E402
from . import panel  # noqa: E402
from . import canal_publico  # noqa: E402
from . import agente  # noqa: E402
from . import hotel_sql  # noqa: E402
from . import observabilidad  # noqa: E402
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
    # ADP-3: el dominio nace vacío; `hotel_sql.recargar` lo llena desde las filas de `habitaciones`.
    return Aplicacion(nucleo=nucleo, hotel=construir_hotel(nucleo, establecimiento, ()))


def _preparar_base_de_datos(config: Configuracion, aplicacion: Aplicacion) -> None:
    """Prepara la base al arrancar, sin operaciones destructivas.

    - Migraciones: solo si `MIGRAR_AL_ARRANCAR` (por defecto sí); se serializan
      con un advisory lock para que dos arranques simultáneos (instancias de
      Vercel en frío, réplicas de Railway) no compitan (NEW-01). Con
      `MIGRAR_AL_ARRANCAR=0` el proceso exige que la base ya esté al día y las
      migraciones se aplican con el comando explícito `python -m servicio.migrar`.
    - Inventario documental (W16-A02): solo inserta HAB-01..17 que falten y las
      el precio base referencial de los tipos sin precio. Nunca borra reservas,
      pagos ni historial y nunca reactiva habitaciones retiradas. En Vercel no
      corre nunca (`VERCEL=1`), aunque la variable esté puesta.
    """
    assert config.database_url is not None
    try:
        if config.migrar_al_arrancar:
            aplicar_migraciones(config.database_url)
        else:
            pendientes = migraciones_pendientes(config.database_url)
            if pendientes:
                raise ErrorArranque(
                    "hay migraciones pendientes y MIGRAR_AL_ARRANCAR=0: "
                    "ejecutar `python -m servicio.migrar` antes de desplegar ("
                    + ", ".join(pendientes) + ")"
                )
        with psycopg.connect(config.database_url) as conexion:
            seguridad.asegurar_admin_inicial(
                conexion,
                empresa_id=aplicacion.nucleo.empresa.id,
                admin_usuario=config.admin_usuario,
                admin_clave=config.admin_clave,
            )
            agente.asegurar_agente_servicio(conexion, aplicacion.nucleo.empresa.id)
            if config.admin_email and config.admin_usuario:
                seguridad.vincular_email(conexion, config.admin_usuario, config.admin_email)
            # ADP-3: el servicio arranca sin habitaciones sembradas; el inventario lo crea la API
            # (PUT /hotel/habitaciones/{id}) y el dominio lo lee de las filas en cada operación.
            if (
                config.inventario_documental
                and not aplicacion.nucleo.empresa.es_sintetico
                and not config.en_vercel
            ):
                # Solo altas idempotentes: ni retiro de ajenas ni reactivación
                # (esas son del comando puntual, ver inventario_documental).
                inventario_documental.sembrar_inventario_documental(
                    conexion,
                    establecimiento_id=inventario_documental.ESTABLECIMIENTO_HERENCIA,
                    retirar_sinteticas=False,
                    activar_reales=False,
                )
                # D3 dueño 2026-11-12: precio base referencial del tipo, solo
                # donde el tipo no tiene precio (no pisa al mantenedor).
                inventario_documental.aplicar_precios_base_referenciales(
                    conexion, solo_sin_precio=True
                )
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
    ServicioIn, SolicitudPublicaIn, UsuarioIn,
)
from .rutas import acceso, hotel  # noqa: E402  (routers incluidos en crear_app)
from .rutas import agente as rutas_agente  # noqa: E402  (alias: `agente` sigue siendo el dominio)
from .rutas import mensajeria as rutas_mensajeria  # noqa: E402
from .rutas import hotel_tipos as rutas_hotel_tipos  # noqa: E402  (entrega 1A)
from .rutas import productos as rutas_productos  # noqa: E402  (#357)
from .rutas import politicas as rutas_politicas  # noqa: E402  (entrega 1A.3)
from .rutas import ajustes as rutas_ajustes  # noqa: E402  (#348)
from .rutas import cuenta as rutas_cuenta  # noqa: E402  (contabilidad fase 2.1)
from .rutas import correo as rutas_correo  # noqa: E402  (#355)
from .rutas import avisos as rutas_avisos  # noqa: E402  (avisos por correo)
from .rutas import facturas_proveedor as rutas_facturas  # noqa: E402  (facturas de proveedores)
from .rutas import caja as rutas_caja  # noqa: E402  (caja y contabilidad, fase 1)


def crear_app(aplicacion: Aplicacion | None = None, configuracion: Configuracion | None = None) -> FastAPI:
    if aplicacion is None:
        aplicacion = construir_aplicacion(nucleo=Nucleo(empresa=empresa_desde_config(configuracion)))
    observabilidad.configurar_logging()
    # En producción (COOKIE_SEGURA=1) se apagan /docs, /redoc y /openapi.json.
    # En desarrollo y en la suite de pruebas (cookie_segura=False o sin config)
    # el contrato OpenAPI sigue disponible para los tests y el trabajo local.
    exponer_docs = not (configuracion and configuracion.cookie_segura)
    app = FastAPI(
        title="plataforma-salman-herencia-api",
        version="1.1.0",
        docs_url="/docs" if exponer_docs else None,
        redoc_url="/redoc" if exponer_docs else None,
        openapi_url="/openapi.json" if exponer_docs else None,
    )
    app.add_middleware(canal_publico.TopeCuerpoPublico)
    app.state.aplicacion = aplicacion
    hotel_sql.registrar(aplicacion.hotel)  # lecturas del canal público, el agente y la evaluación
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
        try:
            app.state.modelo_agente = ModeloHttp(
                base_url=configuracion.modelo_base_url,
                api_key=configuracion.modelo_api_key,
                modelo=configuracion.modelo_nombre or "modelo",
            )
        except ValueError as error:  # SA-MH-01: URL del modelo no https
            raise ErrorArranque(str(error))
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
    # #353: despachador de avisos al administrador (apagado sin canales).
    from .avisos import Despachador, canales_desde_config, destinos_defecto_desde_config
    app.state.avisos = Despachador(canales_desde_config(configuracion),
                                   configuracion.database_url if configuracion else None,
                                   configuracion.front_url if configuracion else "",
                                   empresa_id=aplicacion.nucleo.empresa.id,
                                   destinos_defecto=destinos_defecto_desde_config(configuracion),
                                   resumen_diario=True)
    if configuracion is not None and configuracion.tareas_de_fondo:
        app.state.avisos.iniciar(configuracion.avisos_intervalo_segundos)
    # #355: revisión periódica de enviados para marcar leads contactados.
    from .correo import Revisor
    app.state.revisor_correo = Revisor(configuracion.database_url if configuracion else None)
    if configuracion is not None and configuracion.tareas_de_fondo:
        app.state.revisor_correo.iniciar()
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
        # SA-HDR-01: la API entrega datos de huéspedes, caja y usuarios; ninguna
        # respuesta debe quedar en caché del navegador ni de un proxy/CDN.
        if "cache-control" not in respuesta.headers:
            respuesta.headers["Cache-Control"] = "no-store"
        config = app.state.configuracion
        if config is not None and config.cookie_segura:
            respuesta.headers["Strict-Transport-Security"] = "max-age=31536000"
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
        # Liveness pública: solo el estado. Sin RUT, ids ni datos internos.
        return {"estado": "ok"}

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
        # Estado del canal público sin exponer configuración: "sin_recaptcha"
        # significa que /publico/leads y /publico/solicitudes responden 503
        # (falta RECAPTCHA_SECRET_KEY en producción).
        config = getattr(app.state, "configuracion", None)
        obligatorio = bool(getattr(config, "cookie_segura", False)) or os.environ.get("RECAPTCHA_OBLIGATORIO") == "1"
        tiene_secreto = bool(getattr(config, "recaptcha_secret_key", None))
        canal = "listo" if tiene_secreto else ("sin_recaptcha" if obligatorio else "sin_recaptcha_desarrollo")
        return {"estado": "listo", "migraciones": n_migraciones, "canal_publico": canal}

    app.include_router(acceso.router)
    # Antes que hotel.router: «/hotel/habitaciones/lote» no debe caer en rutas
    # con parámetro de la habitación.
    app.include_router(rutas_hotel_tipos.router)
    app.include_router(rutas_politicas.router)
    app.include_router(rutas_ajustes.router)
    app.include_router(rutas_cuenta.router)
    app.include_router(rutas_correo.router)
    app.include_router(rutas_avisos.router)
    app.include_router(hotel.router)
    app.include_router(rutas_facturas.router)
    app.include_router(rutas_caja.router)
    app.include_router(rutas_productos.router)
    app.include_router(rutas_agente.router)
    app.include_router(rutas_mensajeria.router)

    @app.exception_handler(RequestValidationError)
    async def manejar_validacion(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # 422 sin reflejar el valor recibido: FastAPI incluye `input` (y a veces
        # `ctx`/`url`) con lo que mandó el cliente, p. ej. un <script> o un token.
        # Se conservan tipo, ubicación y mensaje para depurar.
        errores = [
            {"type": e.get("type"), "loc": list(e.get("loc", ())), "msg": e.get("msg")}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errores})

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

    # Último middleware registrado = el más externo: ve todas las respuestas
    # (incluidos los 403 de Origin) y captura cualquier excepción no controlada.
    observabilidad.instalar(app)
    return app


def main(configuracion: Configuracion | None = None) -> None:
    import uvicorn

    configuracion = configuracion or cargar_desde_entorno()
    try:
        app = crear_app(configuracion=configuracion)
    except ErrorArranque as error:
        raise SystemExit(f"el proceso no arranca: {error}")
    uvicorn.run(app, host=configuracion.host, port=configuracion.puerto)
