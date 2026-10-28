"""Proceso backend de la plataforma: núcleo y hotel en el mismo servicio HTTP.

Biblioteca estándar únicamente. Datos sintéticos, en memoria, sin red saliente.
Arranque desde la raíz del repositorio:

    python3 -m plataforma.servidor --puerto 8080
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "core" / "incremento1"), str(RAIZ / "verticales" / "hotel" / "incremento1")]

from hotel_inventario.dominio import EstadoUnidad, Establecimiento, Huesped, Unidad  # noqa: E402
from hotel_inventario.servicio import AccesoDenegado as AccesoHotel  # noqa: E402
from hotel_inventario.servicio import ServicioHotelInventario  # noqa: E402
from nucleo.servicio import AccesoDenegado as AccesoNucleo  # noqa: E402
from nucleo.servicio import Nucleo  # noqa: E402

# Token sintético: resuelve la empresa del request. Sustituible por la identidad del núcleo
# cuando exista (FR-001 de specs/000-core, todavía sin implementar).
TOKEN_SINTETICO = "tok-sintetico-herencia"

RE_RESERVA_PAGOS = re.compile(r"^/hotel/reservas/([^/]+)/pagos$")


@dataclass
class Aplicacion:
    nucleo: Nucleo
    hotel: ServicioHotelInventario
    tokens: dict[str, str]


def construir_hotel(nucleo: Nucleo, establecimiento: Establecimiento, unidades: tuple[Unidad, ...]) -> ServicioHotelInventario:
    """El hotel entra con la empresa del núcleo; un establecimiento de otra empresa no se carga."""
    if establecimiento.empresa_id != nucleo.empresa.id:
        raise ValueError("el establecimiento no pertenece a la empresa del núcleo")
    return ServicioHotelInventario(establecimiento, unidades, empresa=nucleo.empresa, cobros=nucleo)


def construir_aplicacion(nucleo: Nucleo | None = None) -> Aplicacion:
    nucleo = nucleo or Nucleo()
    establecimiento = Establecimiento(id="EST-SINT-001", empresa_id=nucleo.empresa.id, nombre="Hotel Herencia sintético")
    unidades = tuple(
        Unidad(f"HAB-SINT-10{n}", establecimiento.id, 2, 50_000, EstadoUnidad.LIMPIA) for n in range(1, 4)
    )
    hotel = construir_hotel(nucleo, establecimiento, unidades)
    return Aplicacion(nucleo=nucleo, hotel=hotel, tokens={TOKEN_SINTETICO: nucleo.empresa.id})


def _reserva_a_json(reserva) -> dict:
    return {
        "reserva_id": reserva.id,
        "unidad_id": reserva.unidad_id,
        "inicio": reserva.inicio.isoformat(),
        "fin": reserva.fin.isoformat(),
        "estado": reserva.estado.value,
    }


def _pago_a_json(pago) -> dict:
    return {"pago_id": pago.id, "reserva_id": pago.reserva_id, "monto_clp": pago.monto_clp, "clave": pago.clave}


def manejador(app: Aplicacion):
    class Manejador(BaseHTTPRequestHandler):
        server_version = "plataforma-herencia/0.1"

        def log_message(self, formato, *args):  # silencia el registro por defecto en pruebas
            return

        def _responder(self, codigo: int, cuerpo) -> None:
            datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def _empresa(self) -> str | None:
            cabecera = self.headers.get("Authorization", "")
            if not cabecera.startswith("Bearer "):
                return None
            return app.tokens.get(cabecera[len("Bearer "):].strip())

        def _cuerpo(self) -> dict:
            largo = int(self.headers.get("Content-Length", "0") or 0)
            crudo = self.rfile.read(largo) if largo else b""
            return json.loads(crudo.decode("utf-8")) if crudo else {}

        def do_GET(self):
            if self.path == "/salud":
                return self._responder(200, {"estado": "ok", "nucleo": "cargado", "hotel": "cargado"})
            empresa = self._empresa()
            if empresa is None:
                return self._responder(401, {"error": "no autenticado"})
            coincidencia = RE_RESERVA_PAGOS.match(self.path)
            if coincidencia:
                try:
                    pagos = app.hotel.pagos(empresa, coincidencia.group(1))
                except AccesoHotel:
                    return self._responder(403, {"error": "acceso denegado"})
                return self._responder(200, {"pagos": [_pago_a_json(p) for p in pagos]})
            return self._responder(404, {"error": "ruta no existe"})

        def do_POST(self):
            empresa = self._empresa()
            if empresa is None:
                return self._responder(401, {"error": "no autenticado"})
            try:
                cuerpo = self._cuerpo()
            except (ValueError, UnicodeDecodeError):
                return self._responder(400, {"error": "cuerpo JSON inválido"})
            try:
                if self.path == "/hotel/reservas":
                    h = cuerpo["huesped"]
                    resultado = app.hotel.reservar(
                        empresa,
                        cuerpo["unidad_id"],
                        date.fromisoformat(cuerpo["inicio"]),
                        date.fromisoformat(cuerpo["fin"]),
                        Huesped(nombre=h["nombre"], documento=h.get("documento")),
                    )
                    codigo = 201 if resultado.confirmada else 409
                    return self._responder(codigo, _reserva_a_json(resultado.reserva))
                coincidencia = RE_RESERVA_PAGOS.match(self.path)
                if coincidencia:
                    pago = app.hotel.registrar_pago(
                        empresa, coincidencia.group(1), int(cuerpo["monto_clp"]), cuerpo.get("clave")
                    )
                    return self._responder(201, _pago_a_json(pago))
                return self._responder(404, {"error": "ruta no existe"})
            except (AccesoHotel, AccesoNucleo):
                return self._responder(403, {"error": "acceso denegado"})
            except (KeyError, ValueError, TypeError) as error:
                return self._responder(400, {"error": f"solicitud inválida: {error}"})

    return Manejador


def servidor(app: Aplicacion, host: str, puerto: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, puerto), manejador(app))


def main() -> None:
    parser = argparse.ArgumentParser(description="Proceso backend sintético de la plataforma.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=8080)
    args = parser.parse_args()
    srv = servidor(construir_aplicacion(), args.host, args.puerto)
    print(f"plataforma escuchando en http://{args.host}:{srv.server_address[1]}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
