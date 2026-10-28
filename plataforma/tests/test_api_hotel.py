import json
import threading
import unittest
import urllib.error
import urllib.request

from plataforma.servidor import (
    TOKEN_SINTETICO,
    construir_aplicacion,
    construir_hotel,
    servidor,
)
from hotel_inventario.dominio import EstadoUnidad, Establecimiento, Unidad
from nucleo.servicio import AccesoDenegado as AccesoNucleo
from nucleo.servicio import Nucleo

AUTORIZACION = {"Authorization": f"Bearer {TOKEN_SINTETICO}"}


class NucleoEspia(Nucleo):
    """Cuenta los cobros que llegan al núcleo y puede rechazarlos."""

    def __init__(self, rechazar: bool = False) -> None:
        super().__init__()
        self.cobros = []
        self._rechazar = rechazar

    def aplicar_resultado_pago(self, empresa_id, clave, estado, monto_clp):
        self.cobros.append(clave)
        if self._rechazar:
            raise AccesoNucleo("empresa desconocida")
        return super().aplicar_resultado_pago(empresa_id, clave, estado, monto_clp)


class ApiHotelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nucleo = NucleoEspia()
        cls.app = construir_aplicacion(cls.nucleo)
        cls.srv = servidor(cls.app, "127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        cls.hilo = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.hilo.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def pedir(self, metodo, ruta, cuerpo=None, cabeceras=None):
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        req = urllib.request.Request(self.base + ruta, data=datos, method=metodo)
        req.add_header("Content-Type", "application/json")
        for clave, valor in (cabeceras or {}).items():
            req.add_header(clave, valor)
        try:
            with urllib.request.urlopen(req) as respuesta:
                return respuesta.status, json.loads(respuesta.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def reservar(self, unidad="HAB-SINT-101"):
        return self.pedir(
            "POST",
            "/hotel/reservas",
            {
                "unidad_id": unidad,
                "inicio": "2026-11-10",
                "fin": "2026-11-12",
                "huesped": {"nombre": "Huésped Sintético Uno", "documento": "DOC-SINT-0001"},
            },
            AUTORIZACION,
        )

    def test_salud_responde_sin_autenticar(self):
        codigo, cuerpo = self.pedir("GET", "/salud")
        self.assertEqual(codigo, 200)
        self.assertEqual(cuerpo["nucleo"], "cargado")
        self.assertEqual(cuerpo["hotel"], "cargado")

    def test_sin_token_o_con_token_desconocido_responde_401(self):
        self.assertEqual(self.pedir("POST", "/hotel/reservas", {})[0], 401)
        codigo, _ = self.pedir("POST", "/hotel/reservas", {}, {"Authorization": "Bearer otro"})
        self.assertEqual(codigo, 401)

    def test_reserva_se_crea_con_la_empresa_del_token(self):
        codigo, cuerpo = self.reservar()
        self.assertEqual(codigo, 201)
        self.assertEqual(cuerpo["estado"], "confirmada")

    def test_pago_se_registra_en_el_nucleo_y_en_el_hotel(self):
        # Falla si el hotel cobra por su cuenta sin llamar al núcleo.
        _, reserva = self.reservar("HAB-SINT-102")
        antes = len(self.nucleo.cobros)

        codigo, pago = self.pedir(
            "POST", f"/hotel/reservas/{reserva['reserva_id']}/pagos", {"monto_clp": 20_000, "clave": "cob-001"}, AUTORIZACION
        )

        self.assertEqual(codigo, 201)
        self.assertEqual(len(self.nucleo.cobros), antes + 1)
        self.assertEqual(self.nucleo.cobros[-1], f"{reserva['reserva_id']}:cob-001")
        codigo, lista = self.pedir("GET", f"/hotel/reservas/{reserva['reserva_id']}/pagos", None, AUTORIZACION)
        self.assertEqual(codigo, 200)
        self.assertEqual([p["pago_id"] for p in lista["pagos"]], [pago["pago_id"]])

    def test_si_el_nucleo_rechaza_el_cobro_el_hotel_no_lo_guarda(self):
        espia = NucleoEspia(rechazar=True)
        app = construir_aplicacion(espia)
        srv = servidor(app, "127.0.0.1", 0)
        hilo = threading.Thread(target=srv.serve_forever, daemon=True)
        hilo.start()
        try:
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            req = urllib.request.Request(
                base + "/hotel/reservas",
                data=json.dumps(
                    {"unidad_id": "HAB-SINT-101", "inicio": "2026-11-10", "fin": "2026-11-12",
                     "huesped": {"nombre": "Huésped Sintético Uno"}}
                ).encode("utf-8"),
                method="POST",
                headers={**AUTORIZACION, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req) as r:
                reserva = json.loads(r.read())
            req = urllib.request.Request(
                f"{base}/hotel/reservas/{reserva['reserva_id']}/pagos",
                data=json.dumps({"monto_clp": 20_000, "clave": "cob-001"}).encode("utf-8"),
                method="POST",
                headers={**AUTORIZACION, "Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as caso:
                urllib.request.urlopen(req)
            self.assertEqual(caso.exception.code, 403)
            self.assertEqual(espia.cobros, [f"{reserva['reserva_id']}:cob-001"])
            self.assertEqual(app.hotel.pagos(app.nucleo.empresa.id, reserva["reserva_id"]), ())
        finally:
            srv.shutdown()
            srv.server_close()

    def test_ruta_inexistente_responde_404(self):
        self.assertEqual(self.pedir("GET", "/no-existe", None, AUTORIZACION)[0], 404)


class HotelSoloConEmpresaDelNucleoTest(unittest.TestCase):
    def test_establecimiento_de_otra_empresa_no_se_carga(self):
        nucleo = Nucleo()
        ajeno = Establecimiento(id="EST-OTRO-001", empresa_id="EMP-OTRA", nombre="Ajeno")
        unidades = (Unidad("HAB-OTRA-1", ajeno.id, 2, 50_000, EstadoUnidad.LIMPIA),)
        with self.assertRaises(ValueError):
            construir_hotel(nucleo, ajeno, unidades)


if __name__ == "__main__":
    unittest.main()
