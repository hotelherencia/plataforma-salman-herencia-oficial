"""ADP-10: la conversión de una solicitud pública también la decide el dominio: la reserva nace
como cualquier otra (id del dominio, cuenta vacía) y la entrada asienta las noches una sola vez."""
import os
import unittest
import uuid
from datetime import date, timedelta
from unittest import mock

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.canal_publico import FrenoDeSolicitudes
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests.apoyo_huespedes import registrar_acompanantes
from hotel_inventario.servicio import ServicioHotelInventario

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


class ConversionDominioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1]))

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            exigir_base_libre(c)
            c.execute(
                "TRUNCATE auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "reservas, tarifas, solicitudes, tareas_operativas, sesiones, usuarios, habitaciones "
                "RESTART IDENTITY CASCADE")
            seguridad.asegurar_admin_inicial(c, EMPRESA, ADMIN[0], ADMIN[1])
            c.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                      "VALUES ('H4','EST-SINT-001','doble',4)")
            c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                      "VALUES ('T4','H4',%s,%s,70000)", (HOY - timedelta(days=30), HOY + timedelta(days=90)))
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.app.state.freno_solicitudes = FrenoDeSolicitudes(max_por_minuto=1000)
        self.cli = TestClient(self.app)
        self.cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})

    def clave(self):
        return {"Idempotency-Key": f"c-{uuid.uuid4().hex[:10]}"}

    def sql(self, q, *a):
        with psycopg.connect(URL_TEST) as c:
            return c.execute(q, a).fetchall()

    def solicitud(self):
        r = self.cli.post("/publico/solicitudes", json={
            "habitacion_id": "H4", "inicio": str(HOY + timedelta(days=6)), "fin": str(HOY + timedelta(days=8)),
            "personas": 4, "huesped_nombre": "Solicita", "huesped_contacto": "solicita@test.cl"},
            headers=self.clave())
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["solicitud_id"]

    def test_la_disponibilidad_publica_la_decide_el_dominio(self):
        parametros = {"inicio": str(HOY + timedelta(days=6)), "fin": str(HOY + timedelta(days=8)), "personas": 2}
        ok = self.cli.get("/publico/disponibilidad", params=parametros)
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual([i["tipo"] for i in ok.json()["oferta"]], ["doble"])  # la pública no expone la unidad (#346)
        with mock.patch.object(ServicioHotelInventario, "consultar_oferta", side_effect=RuntimeError("dominio")):
            cli = TestClient(self.app, raise_server_exceptions=False)
            self.assertEqual(cli.get("/publico/disponibilidad", params=parametros).status_code, 500)

    def test_la_solicitud_publica_valida_el_cupo_con_el_dominio(self):
        with mock.patch.object(ServicioHotelInventario, "consultar_oferta", side_effect=RuntimeError("dominio")):
            cli = TestClient(self.app, raise_server_exceptions=False)
            r = cli.post("/publico/solicitudes", json={
                "habitacion_id": "H4", "inicio": str(HOY + timedelta(days=6)), "fin": str(HOY + timedelta(days=8)),
                "personas": 2, "huesped_nombre": "X", "huesped_contacto": "x@test.cl"}, headers=self.clave())
        self.assertEqual(r.status_code, 500)
        self.assertEqual(self.sql("SELECT count(*) FROM solicitudes")[0][0], 0)

    def test_la_conversion_falla_si_falla_reservar_y_la_solicitud_sigue_recibida(self):
        sid = self.solicitud()
        with mock.patch.object(ServicioHotelInventario, "reservar", side_effect=RuntimeError("dominio")):
            cli = TestClient(self.app, raise_server_exceptions=False)
            cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
            r = cli.post(f"/hotel/solicitudes/{sid}/conversion", headers=self.clave())
        self.assertEqual(r.status_code, 500)
        self.assertEqual(self.sql("SELECT estado FROM solicitudes WHERE id=%s", sid)[0][0], "recibida")
        self.assertEqual(self.sql("SELECT count(*) FROM reservas")[0][0], 0)

    def test_la_reserva_convertida_nace_en_el_dominio_con_la_cuenta_vacia(self):
        sid = self.solicitud()
        r = self.cli.post(f"/hotel/solicitudes/{sid}/conversion", headers=self.clave())
        self.assertEqual(r.status_code, 201, r.text)
        rid = r.json()["reserva_id"]
        self.assertTrue(rid.startswith("RSV-SINT-"), rid)
        self.assertEqual(self.sql("SELECT personas, estado FROM reservas WHERE id=%s", rid)[0], (4, "confirmada"))
        self.assertEqual(self.sql("SELECT count(*) FROM cargos WHERE reserva_id=%s", rid)[0][0], 0)

    def test_la_entrada_asienta_las_noches_una_sola_vez(self):
        sid = self.solicitud()
        rid = self.cli.post(f"/hotel/solicitudes/{sid}/conversion", headers=self.clave()).json()["reserva_id"]
        with psycopg.connect(URL_TEST) as c:  # la reserva ya empezó: la entrada no depende de la hora del día
            c.execute("UPDATE reservas SET inicio=%s, fin=%s, huesped_documento='D-1' WHERE id=%s",
                      (HOY - timedelta(days=2), HOY, rid))
        registrar_acompanantes(self.cli, rid, 3, self.clave)  # la solicitud declaró 4 personas
        self.assertEqual(self.cli.post(f"/hotel/reservas/{rid}/entrada", json={}, headers=self.clave()).status_code, 200)
        self.assertEqual(self.sql("SELECT concepto, monto_clp FROM cargos WHERE reserva_id=%s", rid),
                         [("Noche", 70000), ("Noche", 70000)])


if __name__ == "__main__":
    unittest.main()
