"""SPEC-06 (2026-11-20): al check-in se especifica si ingresan 1 o 2 personas."""
import os
import unittest
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import psycopg
from fastapi.testclient import TestClient

from servicio import hotel_sql, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


class CheckInPersonasTest(unittest.TestCase):
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
                "reservas, tarifas, excepciones_precio, solicitudes, tareas_operativas, sesiones, usuarios, habitaciones "
                "RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES "
                "('HAB-101', 'EST-SINT-001', 'doble', 2)"
            )
            conexion.execute(
                "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) VALUES "
                "('TAR-101', 'HAB-101', '2026-01-01', '2027-12-31', 55000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        r = self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.assertEqual(r.status_code, 200)
        self.csrf = {"X-CSRF": r.cookies.get("csrf", "")}

    def test_checkin_permite_1_o_2_personas_y_persiste(self):
        r_res = self.cliente.post(
            "/hotel/reservas",
            headers={**self.csrf, "Idempotency-Key": f"res-{uuid.uuid4().hex[:8]}"},
            json={
                "habitacion_id": "HAB-101",
                "inicio": HOY.isoformat(),
                "fin": (HOY + timedelta(days=1)).isoformat(),
                "huesped": {"nombre": "María Gómez", "documento": "12345678-5"},
                "personas": 1,
            },
        )
        self.assertEqual(r_res.status_code, 201, r_res.text)
        reserva_id = r_res.json()["reserva_id"]

        orig_ahora = hotel_sql.ahora
        hotel_sql.ahora = lambda: datetime.combine(HOY, time(16, 0))
        try:
            r_in = self.cliente.post(
                f"/hotel/reservas/{reserva_id}/entrada",
                headers={**self.csrf, "Idempotency-Key": f"in-{uuid.uuid4().hex[:8]}"},
                json={"personas": 2},
            )
        finally:
            hotel_sql.ahora = orig_ahora
        self.assertEqual(r_in.status_code, 200, r_in.text)
        self.assertEqual(r_in.json()["personas"], 2)

        with psycopg.connect(URL_TEST) as conn:
            personas_bd = conn.execute("SELECT personas FROM reservas WHERE id = %s", (reserva_id,)).fetchone()[0]
        self.assertEqual(personas_bd, 2)

    def test_checkin_rechaza_3_personas(self):
        r_in = self.cliente.post(
            "/hotel/reservas/RSV-NO-EXISTE/entrada",
            headers={**self.csrf, "Idempotency-Key": f"in-{uuid.uuid4().hex[:8]}"},
            json={"personas": 3},
        )
        self.assertEqual(r_in.status_code, 422)
