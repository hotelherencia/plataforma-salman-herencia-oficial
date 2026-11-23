"""Tarifas públicas por tipo de habitación (GET /publico/tarifas)."""
import os
import unittest
import uuid

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")


class TarifasPublicasTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, origen_landing="https://www.hotelherencia.cl",
            admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "TRUNCATE auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "reservas, tarifas, excepciones_precio, solicitudes, tareas_operativas, sesiones, usuarios, habitaciones, tipos_habitacion "
                "RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.execute(
                "INSERT INTO tipos_habitacion (id, nombre, capacidad_base, precio_base_clp, orden) VALUES "
                "('doble', 'Habitación Doble Pequeña', 2, 55000, 1), "
                "('matrimonial', 'Habitación con Cama Grande', 2, 58000, 2)"
            )
            conexion.commit()
        self.cliente = TestClient(self.app)

    def test_tarifas_publicas_sin_sesion_y_con_cors_landing(self):
        r = self.cliente.get(
            "/publico/tarifas",
            headers={"Origin": "https://www.hotelherencia.cl"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers.get("access-control-allow-origin"), "https://www.hotelherencia.cl")
        datos = r.json()
        self.assertEqual(datos["moneda"], "CLP")
        self.assertTrue(datos["iva_incluido"])
        tipos = {t["tipo"]: t for t in datos["tipos"]}
        self.assertEqual(tipos["doble"]["precio_base_clp"], 55000)
        self.assertEqual(tipos["matrimonial"]["precio_base_clp"], 58000)
        self.assertNotIn("habitaciones", datos["tipos"][0])
