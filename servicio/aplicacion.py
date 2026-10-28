"""Fábrica de la aplicación: núcleo y hotel en el mismo proceso, un solo servicio.

Regla de arranque (spec-backend-v1): el hotel entra con la empresa del
núcleo; un establecimiento de otra empresa impide que el proceso arranque.
Con `database_url` configurada, el arranque también aplica migraciones y crea
el administrador inicial desde variables de entorno (spec-api-v1).
"""
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

RAIZ = Path(__file__).resolve().parents[1]
for _ruta in (RAIZ / "core" / "incremento1", RAIZ / "verticales" / "hotel" / "incremento1"):
    if ( _s := str(_ruta) ) not in sys.path:
        sys.path.insert(0, _s)

import psycopg  # noqa: E402
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from hotel_inventario.dominio import EstadoUnidad, Establecimiento, Unidad  # noqa: E402
from hotel_inventario.servicio import ServicioHotelInventario  # noqa: E402
from nucleo.servicio import Nucleo  # noqa: E402

from .configuracion import Configuracion, cargar_desde_entorno  # noqa: E402
from .migracion import aplicar_migraciones  # noqa: E402
from . import seguridad  # noqa: E402
from . import idempotencia  # noqa: E402
from . import reservas as reservas_db  # noqa: E402

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
            reservas_db.sembrar_habitaciones(conexion)
            conexion.commit()
    except RuntimeError as error:
        raise ErrorArranque(str(error))
    except psycopg.OperationalError as error:
        raise ErrorArranque(f"no se pudo conectar a la base de datos: {error}")


class Credenciales(BaseModel):
    usuario: str
    clave: str


class HabitacionIn(BaseModel):
    tipo: str
    capacidad: int


class TarifaIn(BaseModel):
    habitacion_id: str
    fecha_desde: date
    fecha_hasta: date
    tarifa_noche_clp: int


class HuespedIn(BaseModel):
    nombre: str
    documento: str | None = None


class ReservaIn(BaseModel):
    habitacion_id: str
    inicio: date
    fin: date
    huesped: HuespedIn


def crear_app(aplicacion: Aplicacion | None = None, configuracion: Configuracion | None = None) -> FastAPI:
    aplicacion = aplicacion or construir_aplicacion()
    app = FastAPI(title="plataforma-salman-herencia-api", version="0.1.0")
    app.state.aplicacion = aplicacion
    app.state.configuracion = configuracion
    if configuracion is not None and configuracion.database_url:
        _preparar_base_de_datos(configuracion, aplicacion)
        app.state.database_url = configuracion.database_url

    @app.get("/salud")
    def salud() -> dict:
        return {
            "estado": "ok",
            "nucleo": "cargado",
            "hotel": "cargado",
            "empresa": aplicacion.nucleo.empresa.id,
        }

    def _conexion() -> Iterator[psycopg.Connection]:
        with psycopg.connect(app.state.database_url) as conexion:
            yield conexion

    def _fijar_cookie(response: Response, sid: str) -> None:
        config = app.state.configuracion
        response.set_cookie(
            NOMBRE_COOKIE_SESION,
            sid,
            httponly=True,
            secure=config.cookie_segura if config else False,
            samesite="none",
            path="/",
        )

    def _requerir_sesion(request: Request, conexion=Depends(_conexion)) -> seguridad.SesionActiva:
        sid = request.cookies.get(NOMBRE_COOKIE_SESION)
        if not sid:
            raise HTTPException(status_code=401, detail="sin sesión")
        sesion = seguridad.obtener_sesion_activa(conexion, sid)
        if sesion is None:
            raise HTTPException(status_code=401, detail="sesión inválida o vencida")
        return sesion

    @app.post("/sesion")
    def abrir_sesion(credenciales: Credenciales, response: Response, conexion=Depends(_conexion)) -> dict:
        auth = seguridad.autenticar(conexion, credenciales.usuario, credenciales.clave)
        if auth is None:
            raise HTTPException(status_code=401, detail="credenciales inválidas")
        usuario_id, empresa_id, rol = auth
        sid = seguridad.crear_sesion(conexion, usuario_id, empresa_id)
        conexion.commit()
        _fijar_cookie(response, sid)
        return {"usuario": credenciales.usuario, "rol": rol, "empresa_id": empresa_id}

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
        response.set_cookie(NOMBRE_COOKIE_SESION, "", max_age=0, path="/")
        return {"estado": "cerrada"}

    @app.get("/sesion")
    def ver_sesion(sesion: seguridad.SesionActiva = Depends(_requerir_sesion)) -> dict:
        return {"usuario": sesion.nombre, "rol": sesion.rol, "empresa_id": sesion.empresa_id}

    def _exigir_admin(sesion: seguridad.SesionActiva) -> None:
        if sesion.rol != "administrador":
            raise seguridad.ErrorPermiso("solo administrador")

    @app.put("/hotel/habitaciones/{habitacion_id}")
    def definir_habitacion(
        habitacion_id: str,
        habitacion: HabitacionIn,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        _exigir_admin(sesion)
        reservas_db.upsert_habitacion(conexion, habitacion_id, habitacion.tipo, habitacion.capacidad)
        conexion.commit()
        return {"habitacion_id": habitacion_id, "tipo": habitacion.tipo, "capacidad": habitacion.capacidad}

    @app.put("/hotel/tarifas")
    def definir_tarifa(
        tarifa: TarifaIn,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        _exigir_admin(sesion)
        if tarifa.fecha_hasta <= tarifa.fecha_desde:
            raise HTTPException(status_code=400, detail="fecha_hasta debe ser mayor que fecha_desde")
        tarifa_id = reservas_db.insertar_tarifa(
            conexion, tarifa.habitacion_id, tarifa.fecha_desde, tarifa.fecha_hasta, tarifa.tarifa_noche_clp
        )
        conexion.commit()
        return {
            "tarifa_id": tarifa_id,
            "habitacion_id": tarifa.habitacion_id,
            "fecha_desde": tarifa.fecha_desde.isoformat(),
            "fecha_hasta": tarifa.fecha_hasta.isoformat(),
            "tarifa_noche_clp": tarifa.tarifa_noche_clp,
        }

    @app.get("/hotel/oferta")
    def consultar_oferta(
        inicio: date,
        fin: date,
        personas: int,
        sesion: seguridad.SesionActiva = Depends(_requerir_sesion),
        conexion=Depends(_conexion),
    ) -> dict:
        if fin <= inicio:
            raise HTTPException(status_code=400, detail="fin debe ser mayor que inicio")
        return reservas_db.oferta(conexion, inicio, fin, personas, datetime.now())

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
                return 409, {"error": str(error)}
            except reservas_db.SinTarifaVigente as error:
                return 409, {"error": str(error)}
            return 201, creada

        try:
            codigo, cuerpo_respuesta = idempotencia.ejecutar(
                conexion, sesion.empresa_id, idempotency_key, cuerpo, operacion
            )
        except idempotencia.ConflictoIdempotencia as error:
            raise HTTPException(status_code=409, detail=str(error))
        conexion.commit()
        return JSONResponse(status_code=codigo, content=cuerpo_respuesta)

    @app.exception_handler(reservas_db.SinCupo)
    @app.exception_handler(reservas_db.SinTarifaVigente)
    async def manejar_conflictos(_request: Request, exc: Exception) -> Response:
        return Response(content=json.dumps({"error": str(exc)}, ensure_ascii=False), status_code=409, media_type="application/json")

    @app.exception_handler(idempotencia.ConflictoIdempotencia)
    async def manejar_conflicto_idempotencia(_request: Request, exc: idempotencia.ConflictoIdempotencia) -> Response:
        return Response(content=json.dumps({"error": str(exc)}, ensure_ascii=False), status_code=409, media_type="application/json")

    @app.exception_handler(seguridad.ErrorPermiso)
    async def manejar_permiso(_request: Request, _exc: seguridad.ErrorPermiso) -> Response:
        return Response(
            content='{"error":"acceso denegado"}',
            status_code=403,
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
