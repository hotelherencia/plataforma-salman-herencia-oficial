"""Reproducción forense del caso RSV-374cbd57abf6 con datos PRUEBA G."""
import os
import unittest
import uuid
from datetime import date, datetime, time, timedelta

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


class ForensePruebaGTest(unittest.TestCase):
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
                "caja_movimientos, caja_turnos, cierres_diarios, reservas, tarifas, excepciones_precio, "
                "solicitudes, tareas_operativas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES "
                "('HAB-G', 'EST-SINT-001', 'matrimonial', 2)"
            )
            conexion.execute(
                "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) VALUES "
                "('TAR-G', 'HAB-G', '2026-01-01', '2027-12-31', 55000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        r = self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.assertEqual(r.status_code, 200)
        self.csrf = {"X-CSRF": r.cookies.get("csrf", "")}

    def test_reproduce_aritmetica_prueba_g_y_reverso_sin_devolucion(self):
        r_res = self.cliente.post(
            "/hotel/reservas",
            headers={**self.csrf, "Idempotency-Key": f"res-{uuid.uuid4().hex[:8]}"},
            json={
                "habitacion_id": "HAB-G",
                "inicio": HOY.isoformat(),
                "fin": (HOY + timedelta(days=1)).isoformat(),
                "huesped": {"nombre": "PRUEBA G", "documento": "DOC-PRUEBA-G"},
            },
        )
        self.assertEqual(r_res.status_code, 201, r_res.text)
        rid = r_res.json()["reserva_id"]

        orig_ahora = hotel_sql.ahora
        hotel_sql.ahora = lambda: datetime.combine(HOY, time(16, 0))
        try:
            r_in = self.cliente.post(
                f"/hotel/reservas/{rid}/entrada",
                headers={**self.csrf, "Idempotency-Key": f"in-{uuid.uuid4().hex[:8]}"},
                json={},
            )
            self.assertEqual(r_in.status_code, 200, r_in.text)
        finally:
            hotel_sql.ahora = orig_ahora

        # Cargos minibar: 100k x 3 + 50k = 350k (+ 55k alojamiento = 405k)
        cids = []
        for monto in (100000, 100000, 100000, 50000):
            rc = self.cliente.post(
                f"/hotel/reservas/{rid}/cargos",
                headers={**self.csrf, "Idempotency-Key": f"c-{uuid.uuid4().hex[:8]}"},
                json={"concepto": "minibar", "monto_clp": monto},
            )
            self.assertEqual(rc.status_code, 201, rc.text)
            cids.append(rc.json()["cargo_id"])

        # 3 pagos: 100k, 405k (con exceso), 100k (con exceso) = 605k
        for idx, (monto, exc) in enumerate([(100000, False), (405000, True), (100000, True)]):
            rp = self.cliente.post(
                f"/hotel/reservas/{rid}/pagos",
                headers={**self.csrf, "Idempotency-Key": f"p-{uuid.uuid4().hex[:8]}"},
                json={"monto_clp": monto, "clave": f"pago-g-{idx}", "modo": "manual", "confirmar_exceso": exc},
            )
            self.assertEqual(rp.status_code, 201, rp.text)

        # 2 reversos de 100k cada uno
        for cid in cids[1:3]:
            rr = self.cliente.post(
                f"/hotel/reservas/{rid}/cargos/{cid}/reverso",
                headers={**self.csrf, "Idempotency-Key": f"rev-{uuid.uuid4().hex[:8]}"},
                json={"motivo": "Pago extra, no necesario se regresa al cliente."},
            )
            self.assertEqual(rr.status_code, 201, rr.text)

        # Cargo Alfajores 500
        ra = self.cliente.post(
            f"/hotel/reservas/{rid}/cargos",
            headers={**self.csrf, "Idempotency-Key": f"alf-{uuid.uuid4().hex[:8]}"},
            json={"concepto": "Alfajores", "monto_clp": 500},
        )
        self.assertEqual(ra.status_code, 201, ra.text)

        det = self.cliente.get(f"/hotel/reservas/{rid}").json()["cuenta"]
        self.assertEqual(det["cargos_netos_clp"], 205500)
        self.assertEqual(det["pagado_clp"], 605000)
        self.assertEqual(det["saldo_clp"], -399500)
