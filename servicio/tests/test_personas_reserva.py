"""Personas en la reserva (#298, DECISIÓN 2026-11-06, opción a).

Las personas se persisten en `reservas` y se validan contra la capacidad al
confirmar (hoy solo filtraban la oferta). Opcional: los flujos que no lo
conocen (operación directa) siguen creando reservas sin el dato. La conversión
de solicitudes públicas lo propaga.
"""
import os
import unittest
import uuid
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.tests.aislamiento import exigir_base_libre
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


class PersonasReservaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "TRUNCATE auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "reservas, tarifas, solicitudes, tareas_operativas, sesiones, usuarios, habitaciones "
                "RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES "
                "('HAB-P-2', 'EST-SINT-001', 'doble', 2), ('HAB-P-4', 'EST-SINT-001', 'familiar', 4)"
            )
            conexion.execute(
                "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) VALUES "
                "('TAR-P2', 'HAB-P-2', '2026-01-01', '2027-12-31', 50000), "
                "('TAR-P4', 'HAB-P-4', '2026-01-01', '2027-12-31', 70000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.app.state.freno_solicitudes = __import__(
            "servicio.canal_publico", fromlist=["FrenoDeSolicitudes"]).FrenoDeSolicitudes(max_por_minuto=1000)
        self.cliente = TestClient(self.app)
        self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})

    def clave(self):
        return f"per-{uuid.uuid4().hex[:10]}"

    def reservar(self, habitacion, personas=None, inicio=None, fin=None):
        cuerpo = {"habitacion_id": habitacion, "inicio": str(inicio or HOY + timedelta(days=3)),
                  "fin": str(fin or HOY + timedelta(days=5)),
                  "huesped": {"nombre": "Huésped Personas", "documento": "DOC-PER"}}
        if personas is not None:
            cuerpo["personas"] = personas
        return self.cliente.post("/hotel/reservas", json=cuerpo, headers={"Idempotency-Key": self.clave()})

    def test_personas_se_persisten_y_se_devuelven(self):
        r = self.reservar("HAB-P-4", personas=3)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["personas"], 3)
        with psycopg.connect(URL_TEST) as conexion:
            (guardado,) = conexion.execute(
                "SELECT personas FROM reservas WHERE id = %s", (r.json()["reserva_id"],)
            ).fetchone()
        self.assertEqual(guardado, 3)

    def test_personas_sin_dato_quedan_nulas(self):
        r = self.reservar("HAB-P-4")
        self.assertEqual(r.status_code, 201, r.text)
        self.assertIsNone(r.json()["personas"])

    def test_personas_mayores_a_capacidad_rechazan_sin_efectos(self):
        r = self.reservar("HAB-P-2", personas=4)
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("admite hasta 2 personas", r.json()["detail"])
        with psycopg.connect(URL_TEST) as conexion:
            (n,) = conexion.execute("SELECT count(*) FROM reservas").fetchone()
        self.assertEqual(n, 0)

    def test_conversion_propaga_personas(self):
        s = self.cliente.post("/publico/solicitudes", json={
            "habitacion_id": "HAB-P-4", "inicio": str(HOY + timedelta(days=6)),
            "fin": str(HOY + timedelta(days=8)), "personas": 4,
            "huesped_nombre": "Solicita Personas", "huesped_contacto": "personas@test.cl",
        }, headers={"Idempotency-Key": self.clave()})
        self.assertEqual(s.status_code, 201, s.text)
        sid = s.json()["solicitud_id"]
        conv = self.cliente.post(f"/hotel/solicitudes/{sid}/conversion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(conv.status_code, 201, conv.text)
        rid = conv.json()["reserva_id"]
        with psycopg.connect(URL_TEST) as conexion:
            (guardado,) = conexion.execute("SELECT personas FROM reservas WHERE id = %s", (rid,)).fetchone()
        self.assertEqual(guardado, 4)


if __name__ == "__main__":
    unittest.main()
