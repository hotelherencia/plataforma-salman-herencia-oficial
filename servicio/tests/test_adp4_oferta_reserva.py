"""ADP-4: oferta y confirmación las decide el dominio (`consultar_oferta`, `reservar`).

Piedra de toque (prueba de estupidez): si el método del dominio falla, la ruta
falla; si la ruta decidiera en SQL, el parche no tendría efecto.
"""
import os
import threading
import unittest
from datetime import date, timedelta
from unittest import mock

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre
from hotel_inventario.servicio import ServicioHotelInventario

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


def iso(n):
    return (HOY + timedelta(days=n)).isoformat()


class OfertaReservaDominioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1]))

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            exigir_base_libre(c)
            c.execute(
                "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
                "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE")
            seguridad.asegurar_admin_inicial(c, EMPRESA, ADMIN[0], ADMIN[1])
            for hid, cap, op, mant in (("HAB-A-1", 2, "disponible", False), ("HAB-A-2", 2, "disponible", False),
                                       ("HAB-A-3", 4, "disponible", False), ("HAB-A-4", 2, "bloqueada", False),
                                       ("HAB-A-5", 2, "disponible", True), ("HAB-SIN-TAR", 2, "disponible", False)):
                c.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, mantenimiento) "
                          "VALUES (%s,'EST-SINT-001','doble',%s,%s,%s)", (hid, cap, op, mant))
                if hid != "HAB-SIN-TAR":
                    c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                              "VALUES (%s,%s,%s,%s,40000)", (f"T-{hid}", hid, HOY - timedelta(days=5), HOY + timedelta(days=100)))
            c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                      "VALUES ('T-A1-2',  'HAB-A-2', %s, %s, 70000)", (HOY + timedelta(days=100), HOY + timedelta(days=110)))
        self.cli = TestClient(self.app)
        self.cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.n = 0

    def reservar(self, hab, a=10, b=12, personas=None, cli=None):
        self.n += 1
        cuerpo = {"habitacion_id": hab, "inicio": iso(a), "fin": iso(b),
                  "huesped": {"nombre": "Huésped", "documento": "D-1"}}
        if personas:
            cuerpo["personas"] = personas
        return (cli or self.cli).post("/hotel/reservas", json=cuerpo, headers={"Idempotency-Key": f"k-{self.n}-{threading.get_ident()}"})

    def oferta(self, a=10, b=12, personas=1):
        r = self.cli.get("/hotel/oferta", params={"inicio": iso(a), "fin": iso(b), "personas": personas})
        self.assertEqual(r.status_code, 200, r.text)
        return {i["habitacion_id"]: i for i in r.json()["oferta"]}

    def sql(self, q, *a):
        with psycopg.connect(URL_TEST) as c:
            return c.execute(q, a).fetchall()

    # --- el dominio decide ---
    def test_oferta_falla_si_falla_consultar_oferta(self):
        with mock.patch.object(ServicioHotelInventario, "consultar_oferta", side_effect=RuntimeError("dominio")):
            cli = TestClient(self.app, raise_server_exceptions=False)
            cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
            r = cli.get("/hotel/oferta", params={"inicio": iso(10), "fin": iso(12), "personas": 1})
        self.assertEqual(r.status_code, 500)

    def test_reserva_falla_y_no_deja_fila_si_falla_reservar(self):
        with mock.patch.object(ServicioHotelInventario, "reservar", side_effect=RuntimeError("dominio")):
            cli = TestClient(self.app, raise_server_exceptions=False)
            cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
            r = self.reservar("HAB-A-1", cli=cli)
        self.assertEqual(r.status_code, 500)
        self.assertEqual(self.sql("SELECT count(*) FROM reservas")[0][0], 0)

    def test_el_id_de_la_reserva_nace_en_el_dominio_y_no_colisiona(self):
        a = self.reservar("HAB-A-1"); b = self.reservar("HAB-A-2")
        self.assertEqual((a.status_code, b.status_code), (201, 201), a.text + b.text)
        ids = [a.json()["reserva_id"], b.json()["reserva_id"]]
        self.assertEqual(ids, ["RSV-SINT-0001", "RSV-SINT-0002"])

    # --- oferta ---
    def test_oferta_excluye_no_vendibles_sin_tarifa_y_sobre_capacidad(self):
        o = self.oferta(personas=3)
        self.assertEqual(set(o), {"HAB-A-3"})
        o = self.oferta(personas=1)
        self.assertEqual(set(o), {"HAB-A-1", "HAB-A-2", "HAB-A-3"})  # no A-4 bloqueada, A-5 mant., ni SIN-TAR

    def test_oferta_trae_tipo_politica_y_total_noche_a_noche(self):
        i = self.oferta(99, 102)["HAB-A-2"]  # noches 99 (40000) y 100,101 (70000)
        self.assertEqual(i["tipo"], "doble")
        self.assertEqual(i["tarifa_noche_clp"], 40000)
        self.assertEqual(i["total_clp"], 40000 + 70000 + 70000)
        self.assertIn("48 horas", i["politica_cancelacion"])
        self.assertIn("vigente_hasta", i)

    def test_oferta_no_incluye_unidad_ocupada_en_el_rango(self):
        self.assertEqual(self.reservar("HAB-A-1").status_code, 201)
        self.assertNotIn("HAB-A-1", self.oferta(10, 12))
        self.assertIn("HAB-A-1", self.oferta(12, 14))

    # --- confirmación ---
    def test_reserva_persiste_fila_con_tarifa_aceptada_y_personas(self):
        r = self.reservar("HAB-A-3", personas=3)
        self.assertEqual(r.status_code, 201, r.text)
        j = r.json()
        self.assertEqual((j["estado"], j["tarifa_noche_aceptada_clp"], j["total_clp"], j["personas"]),
                         ("confirmada", 40000, 80000, 3))
        fila = self.sql("SELECT habitacion_id, estado, tarifa_noche_aceptada_clp, personas, huesped_documento "
                        "FROM reservas WHERE id=%s", j["reserva_id"])[0]
        self.assertEqual(fila, ("HAB-A-3", "confirmada", 40000, 3, "D-1"))

    def test_ac3_la_cuenta_nace_vacia_tras_confirmar(self):
        j = self.reservar("HAB-A-1").json()
        self.assertEqual(self.sql("SELECT count(*) FROM cargos WHERE reserva_id=%s", j["reserva_id"])[0][0], 0)

    def test_rechazos_del_dominio_son_409(self):
        self.assertEqual(self.reservar("HAB-A-1").status_code, 201)
        self.assertEqual(self.reservar("HAB-A-1", 11, 13).status_code, 409)       # sin cupo
        self.assertEqual(self.reservar("HAB-A-4").status_code, 409)               # bloqueada
        self.assertEqual(self.reservar("HAB-A-5").status_code, 409)               # mantenimiento
        self.assertEqual(self.reservar("HAB-NO-EXISTE").status_code, 409)         # inexistente
        self.assertEqual(self.reservar("HAB-A-1", 20, 22, personas=3).status_code, 409)  # sobre capacidad
        self.assertEqual(self.reservar("HAB-SIN-TAR").status_code, 409)           # sin tarifa
        self.assertEqual(self.sql("SELECT count(*) FROM reservas")[0][0], 1)       # rechazos no dejan fila

    def test_carrera_por_la_ultima_unidad_deja_una_sola_reserva(self):
        codigos = []
        def intentar():
            cli = TestClient(self.app)
            cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
            codigos.append(self.reservar("HAB-A-1", cli=cli).status_code)
        hilos = [threading.Thread(target=intentar) for _ in range(4)]
        [h.start() for h in hilos]; [h.join() for h in hilos]
        self.assertEqual(sorted(codigos), [201, 409, 409, 409])
        self.assertEqual(self.sql("SELECT count(*) FROM reservas WHERE habitacion_id='HAB-A-1'")[0][0], 1)


if __name__ == "__main__":
    unittest.main()
