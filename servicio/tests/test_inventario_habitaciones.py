"""Inventario de habitaciones (2026-11-03, spec-api-v1): GET /hotel/habitaciones
expone el estado operativo real que antes solo existía en la base. Orden del
propietario tras la revisión E2E: la pantalla de habitaciones operaba a ciegas.
Ejercita HTTP contra PostgreSQL real (mismo aislamiento que test_h6)."""
import os
import unittest
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
FUTURO = (date.today() + timedelta(days=30)).isoformat()
FUTURO_FIN = (date.today() + timedelta(days=33)).isoformat()


def _semilla(conexion):
    conexion.execute(
        "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
        "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
    )
    seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
    conexion.execute(
        "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
        "VALUES ('HAB-INV-1', 'EST-SINT-001', 'doble', 2)"
    )
    conexion.execute(
        "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, mantenimiento) "
        "VALUES ('HAB-INV-2', 'EST-SINT-001', 'simple', 1, true)"
    )
    conexion.execute(
        "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
        "VALUES ('TAR-INV-1', 'HAB-INV-1', '2026-01-01', '2027-12-31', 45000)"
    )


class InventarioHabitacionesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            _semilla(conexion)

    def _login(self, usuario=ADMIN[0], clave=ADMIN[1]):
        cliente = TestClient(self.app)
        respuesta = cliente.post("/sesion", json={"usuario": usuario, "clave": clave})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return cliente

    def test_exige_sesion(self):
        cliente = TestClient(self.app)
        self.assertEqual(cliente.get("/hotel/habitaciones").status_code, 401)

    def test_lista_estado_operativo_real(self):
        cliente = self._login()
        respuesta = cliente.get("/hotel/habitaciones")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        habitaciones = {h["habitacion_id"]: h for h in respuesta.json()["habitaciones"]}

        self.assertEqual(set(habitaciones), {"HAB-INV-1", "HAB-INV-2"})
        self.assertEqual(habitaciones["HAB-INV-1"]["estado_operativo"], "disponible")
        self.assertEqual(habitaciones["HAB-INV-1"]["estado_preparacion"], "limpia")
        self.assertFalse(habitaciones["HAB-INV-1"]["mantenimiento"])
        self.assertEqual(habitaciones["HAB-INV-1"]["tarifa_noche_clp"], 45000)
        self.assertEqual(habitaciones["HAB-INV-1"]["tareas_pendientes"], 0)

        self.assertTrue(habitaciones["HAB-INV-2"]["mantenimiento"])
        self.assertEqual(habitaciones["HAB-INV-2"]["tarifa_noche_clp"], 0)

    def test_refleja_limpieza_y_estadia(self):
        cliente = self._login()
        reserva = cliente.post(
            "/hotel/reservas",
            json={
                "habitacion_id": "HAB-INV-1",
                "inicio": FUTURO,
                "fin": FUTURO_FIN,
                "huesped": {"nombre": "Inventario E2E", "documento": "12345678"},
            },
            headers={"Idempotency-Key": "inv-res-1"},
        ).json()
        reserva_id = reserva["reserva_id"]
        cliente.post(f"/hotel/reservas/{reserva_id}/entrada", headers={"Idempotency-Key": "inv-ent-1"})

        habitaciones = {h["habitacion_id"]: h for h in cliente.get("/hotel/habitaciones").json()["habitaciones"]}
        self.assertEqual(habitaciones["HAB-INV-1"]["estado_operativo"], "ocupada")
        self.assertEqual(habitaciones["HAB-INV-1"]["estado_preparacion"], "limpia")

        # La salida exige saldo neto en cero: se paga el total aceptado.
        cliente.post(
            f"/hotel/reservas/{reserva_id}/pagos",
            json={"monto_clp": reserva["total_clp"], "clave": "inv-cobro-1", "modo": "manual"},
            headers={"Idempotency-Key": "inv-pag-1"},
        )
        cliente.post("/hotel/reservas/%s/salida" % reserva_id, headers={"Idempotency-Key": "inv-sal-1"})
        habitaciones = {h["habitacion_id"]: h for h in cliente.get("/hotel/habitaciones").json()["habitaciones"]}
        self.assertEqual(habitaciones["HAB-INV-1"]["estado_operativo"], "disponible")
        self.assertEqual(habitaciones["HAB-INV-1"]["estado_preparacion"], "sucia")
        self.assertEqual(habitaciones["HAB-INV-1"]["tareas_pendientes"], 1)

        cliente.post("/hotel/habitaciones/HAB-INV-1/limpieza", headers={"Idempotency-Key": "inv-limp-1"})
        habitaciones = {h["habitacion_id"]: h for h in cliente.get("/hotel/habitaciones").json()["habitaciones"]}
        self.assertEqual(habitaciones["HAB-INV-1"]["estado_preparacion"], "limpia")
        self.assertEqual(habitaciones["HAB-INV-1"]["tareas_pendientes"], 0)

    def test_cualquier_rol_lectura_mantenimiento_solo_admin(self):
        cliente = self._login()
        cliente.post(
            "/usuarios",
            json={"nombre": "recepcion_inv", "rol": "recepcion", "clave": "RecepInv99"},
            headers={"Idempotency-Key": "inv-usr-1"},
        )
        recepcion = self._login("recepcion_inv", "RecepInv99")
        self.assertEqual(recepcion.get("/hotel/habitaciones").status_code, 200)
        respuesta = recepcion.post(
            "/hotel/habitaciones/HAB-INV-1/mantenimiento",
            json={"abierto": True},
            headers={"Idempotency-Key": "inv-mant-1"},
        )
        self.assertEqual(respuesta.status_code, 403, respuesta.text)


if __name__ == "__main__":
    unittest.main()
