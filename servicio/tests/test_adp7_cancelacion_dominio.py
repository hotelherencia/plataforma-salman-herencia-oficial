"""ADP-7: cancelar aplica la política del dominio (24 h antes de las 14:00; si no, la primera
noche). Sin reversos: la cuenta nace vacía (ADP-4/5), no hay cargo de estadía que revertir."""
import os
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


class CancelacionDominioTest(unittest.TestCase):
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
            c.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES ('H1','EST-SINT-001','doble',2)")
            c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                      "VALUES ('T1','H1',%s,%s,45000)", (HOY - timedelta(days=30), HOY + timedelta(days=90)))
        self.cli = TestClient(self.app)
        self.cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.n = 0

    def clave(self):
        self.n += 1
        return {"Idempotency-Key": f"k{self.n}"}

    def reservar(self, a, b):
        r = self.cli.post("/hotel/reservas", json={"habitacion_id": "H1", "inicio": iso(a), "fin": iso(b),
                          "huesped": {"nombre": "H", "documento": "D-1"}}, headers=self.clave())
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["reserva_id"]

    def cancelar(self, rid, cli=None):
        return (cli or self.cli).post(f"/hotel/reservas/{rid}/cancelacion", json={}, headers=self.clave())

    def sql(self, q, *a):
        with psycopg.connect(URL_TEST) as c:
            return c.execute(q, a).fetchall()

    def test_falla_el_dominio_falla_la_cancelacion_y_no_cambia_nada(self):
        rid = self.reservar(5, 7)
        with mock.patch.object(ServicioHotelInventario, "cancelar", side_effect=RuntimeError("dominio")):
            cli = TestClient(self.app, raise_server_exceptions=False)
            cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
            self.assertEqual(self.cancelar(rid, cli).status_code, 500)
        self.assertEqual(self.sql("SELECT estado FROM reservas WHERE id=%s", rid)[0][0], "confirmada")

    def test_con_24_horas_o_mas_no_hay_penalidad_ni_cargos(self):
        rid = self.reservar(5, 7)
        r = self.cancelar(rid)
        self.assertEqual(r.status_code, 200, r.text)
        j = r.json()
        self.assertEqual((j["estado"], j["penalidad_clp"], j["reversos"]), ("cancelada", 0, []))
        self.assertEqual(self.sql("SELECT count(*) FROM cargos WHERE reserva_id=%s", rid)[0][0], 0)
        self.assertEqual(self.sql("SELECT estado FROM reservas WHERE id=%s", rid)[0][0], "cancelada")

    def test_con_menos_de_24_horas_carga_la_primera_noche_sin_reversos(self):
        rid = self.reservar(0, 3)
        j = self.cancelar(rid).json()
        self.assertEqual(j["penalidad_clp"], 45000)
        self.assertEqual(j["reversos"], [])
        filas = self.sql("SELECT concepto, monto_clp, tipo FROM cargos WHERE reserva_id=%s", rid)
        self.assertEqual(filas, [("Cancelación fuera de plazo: primera noche", 45000, "cargo")])

    def test_reintento_409_y_no_duplica_la_penalidad(self):
        rid = self.reservar(0, 3)
        self.assertEqual(self.cancelar(rid).status_code, 200)
        self.assertEqual(self.cancelar(rid).status_code, 409)
        self.assertEqual(self.sql("SELECT count(*) FROM cargos WHERE reserva_id=%s", rid)[0][0], 1)

    def test_un_cargo_suelto_previo_se_reversa_por_el_dominio_y_la_penalidad_no(self):
        rid = self.reservar(0, 3)
        self.assertEqual(self.cli.post(f"/hotel/reservas/{rid}/cargos", json={"concepto": "minibar", "monto_clp": 8000},
                                       headers=self.clave()).status_code, 201)
        j = self.cancelar(rid).json()
        self.assertEqual(j["penalidad_clp"], 45000)
        self.assertEqual([(r["monto_clp"]) for r in j["reversos"]], [8000])
        filas = self.sql("SELECT tipo, monto_clp FROM cargos WHERE reserva_id=%s ORDER BY tipo, monto_clp", rid)
        self.assertEqual(filas, [("cargo", 8000), ("cargo", 45000), ("reverso", 8000)])  # neto = penalidad
        det = self.cli.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(det["cuenta"]["cargos_netos_clp"], 45000)

    def test_cancelada_libera_el_cupo(self):
        rid = self.reservar(5, 7)
        self.cancelar(rid)
        self.reservar(5, 7)

    def test_en_estadia_no_se_cancela(self):
        rid = self.reservar(-2, 1)
        self.assertEqual(self.cli.post(f"/hotel/reservas/{rid}/entrada", json={}, headers=self.clave()).status_code, 200)
        self.assertEqual(self.cancelar(rid).status_code, 409)
        self.assertEqual(self.sql("SELECT estado FROM reservas WHERE id=%s", rid)[0][0], "en_estadia")

    def test_ajena_o_inexistente_403(self):
        self.assertEqual(self.cancelar("RSV-NO-EXISTE").status_code, 403)


if __name__ == "__main__":
    unittest.main()
