"""Base compartida de las pruebas de la auditoría de seguridad 2026-11-17.

Misma base de datos y app que test_agente_servicio, sin heredar sus casos
(un TestCase importado en un módulo de pruebas se volvería a ejecutar)."""
import os
import unittest

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.mensajeria import PuertoWhatsapp
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests import test_agente_servicio as _base_agente
from servicio.tests.test_mensajeria_whatsapp import NUMERO, SECRETO, TOKEN

MB = 1024 * 1024
URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")


class BaseWebhook(unittest.TestCase):
    """Misma base de datos y app que test_agente_servicio, sin heredar sus casos."""

    @classmethod
    def setUpClass(cls):
        _base_agente.AgenteServicioBaseTest.setUpClass.__func__(cls)

    def setUp(self):
        _base_agente.AgenteServicioBaseTest.setUp(self)
        self.app.state.mensajeria = None

    def tearDown(self):
        self.app.state.mensajeria = None

    def activar(self):
        self.app.state.mensajeria = PuertoWhatsapp(SECRETO, TOKEN, NUMERO)

    def post(self, cuerpo: bytes, firma: str | None = None):
        headers = {"content-type": "application/json"}
        if firma is not None:
            headers["x-hub-signature-256"] = firma
        return self.cliente.post("/mensajeria/whatsapp/webhook", content=cuerpo, headers=headers)


class BaseSesiones(unittest.TestCase):
    """Base mínima: usuarios, sesiones y claves de idempotencia limpias."""

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
                "TRUNCATE auditoria, claves_idempotencia, sesiones, usuarios RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.admin = self.cliente_como(*ADMIN)

    def cliente_como(self, usuario, clave, codigo=None):
        cliente = TestClient(self.app)
        cuerpo = {"usuario": usuario, "clave": clave}
        if codigo:
            cuerpo["totp"] = codigo
        r = cliente.post("/sesion", json=cuerpo)
        self.assertEqual(r.status_code, 200, r.text)
        return cliente

    def id_de(self, nombre):
        with psycopg.connect(URL_TEST) as conexion:
            (uid,) = conexion.execute("SELECT id FROM usuarios WHERE nombre = %s", (nombre,)).fetchone()
        return uid

    def alta(self, nombre, rol, clave, idem):
        # Un rol privilegiado no se da de alta por la API con la cuenta de arranque (jerarquía y validación
        # de cambios de rol, #338): se crea como cuenta operativa y se fija el rol en la base, como fixture.
        privilegiado = rol in ("administrador", "admin_hotel", "admin_plataforma", "dueno")
        r = self.admin.post("/usuarios", json={"nombre": nombre, "rol": "recepcion" if privilegiado else rol, "clave": clave},
                            headers={"Idempotency-Key": idem})
        self.assertEqual(r.status_code, 201, r.text)
        if privilegiado:
            with psycopg.connect(URL_TEST) as conexion:
                conexion.execute("UPDATE usuarios SET rol = %s WHERE id = %s", (rol, r.json()["id"]))
                conexion.commit()
