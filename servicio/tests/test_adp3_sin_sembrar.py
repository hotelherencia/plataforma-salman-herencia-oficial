"""ADP-3: el servicio arranca con `habitaciones` vacía; el inventario es el que crea la API."""
import os
import unittest
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.tests.aislamiento import exigir_base_libre
from servicio.aplicacion import crear_app, construir_aplicacion
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


def vaciar(conexion):
    conexion.execute(
        "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
        "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
    )
    conexion.commit()


def contar(sql):
    with psycopg.connect(URL_TEST) as c:
        return c.execute(sql).fetchone()[0]


class SinSembrarTest(unittest.TestCase):
    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            exigir_base_libre(c)
            vaciar(c)
        config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        self.app = crear_app(configuracion=config)
        self.cliente = TestClient(self.app)
        self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})

    def test_arranque_no_siembra_habitaciones(self):
        self.assertEqual(contar("SELECT count(*) FROM habitaciones"), 0)

    def test_construir_aplicacion_deja_el_hotel_sin_unidades(self):
        self.assertEqual(construir_aplicacion().hotel._unidades, {})

    def test_oferta_vacia_y_sin_hab_sint_101(self):
        r = self.cliente.get(
            "/hotel/oferta",
            params={"inicio": (HOY + timedelta(days=3)).isoformat(),
                    "fin": (HOY + timedelta(days=5)).isoformat(), "personas": 2},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertNotIn("HAB-SINT-101", r.text)
        self.assertEqual(r.json()["oferta"], [])

    def test_put_habitacion_crea_fila_real_y_unidad_del_dominio(self):
        r = self.cliente.put(
            "/hotel/habitaciones/HAB-NUEVA-1", json={"tipo": "doble", "capacidad": 3},
            headers={"Idempotency-Key": "hab-nueva-1"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(
            contar("SELECT count(*) FROM habitaciones WHERE id='HAB-NUEVA-1' AND capacidad=3 AND tipo='doble'"), 1)
        unidad = self.app.state.aplicacion.hotel._unidades.get("HAB-NUEVA-1")
        self.assertIsNotNone(unidad)
        self.assertEqual(unidad.capacidad, 3)

    def test_put_habitacion_edicion_actualiza_capacidad_en_el_dominio(self):
        h = {"Idempotency-Key": "hab-e-1"}
        self.cliente.put("/hotel/habitaciones/HAB-NUEVA-2", json={"tipo": "doble", "capacidad": 2}, headers=h)
        r = self.cliente.put("/hotel/habitaciones/HAB-NUEVA-2", json={"tipo": "doble", "capacidad": 4},
                             headers={"Idempotency-Key": "hab-e-2"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.app.state.aplicacion.hotel._unidades["HAB-NUEVA-2"].capacidad, 4)

    def test_put_habitacion_solo_crear_existente_409_sin_duplicar(self):
        self.cliente.put("/hotel/habitaciones/HAB-NUEVA-3", json={"tipo": "doble", "capacidad": 2},
                         headers={"Idempotency-Key": "hab-3a"})
        r = self.cliente.put("/hotel/habitaciones/HAB-NUEVA-3", json={"tipo": "doble", "capacidad": 2},
                             headers={"Idempotency-Key": "hab-3b", "If-None-Match": "*"})
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(contar("SELECT count(*) FROM habitaciones WHERE id='HAB-NUEVA-3'"), 1)


if __name__ == "__main__":
    unittest.main()
