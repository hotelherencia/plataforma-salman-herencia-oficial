"""Segundo factor TOTP: vectores RFC 6238 y flujo completo contra la API."""
import os
import unittest

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad, totp
from servicio.tests.aislamiento import exigir_base_libre
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")


def codigo_malo(secreto: str) -> str:
    real = int(totp.codigo(secreto))
    return str((real + 1) % 1_000_000).zfill(6)


class TotpRfcTest(unittest.TestCase):
    def test_vectores_rfc_6238_sha1(self):
        # RFC 6238, apéndice B: secreto ASCII '12345678901234567890' (SHA1).
        secreto = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        casos = [
            (59, "94287082"),
            (1111111109, "07081804"),
            (1111111111, "14050471"),
            (1234567890, "89005924"),
            (2000000000, "69279037"),
            (20000000000, "65353130"),
        ]
        for t, esperado in casos:
            with self.subTest(t=t):
                self.assertEqual(totp.codigo(secreto, t, digitos=8), esperado)


class DosFactoresHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1",
            puerto=0,
            database_url=URL_TEST,
            cookie_segura=False,
            origen_front=None,
            admin_usuario=ADMIN[0],
            admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)
        cls.cliente = TestClient(cls.app)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("TRUNCATE sesiones, usuarios RESTART IDENTITY CASCADE")
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.commit()
        self.cliente.cookies.clear()

    def login(self, **campos):
        cuerpo = {"usuario": ADMIN[0], "clave": ADMIN[1], **campos}
        return self.cliente.post("/sesion", json=cuerpo)

    def test_alta_2fa_exige_sesion(self):
        self.assertEqual(self.cliente.post("/cuenta/2fa").status_code, 401)
        self.assertEqual(self.cliente.post("/cuenta/2fa/activar", json={"codigo": "123456"}).status_code, 401)
        self.assertEqual(self.cliente.delete("/cuenta/2fa").status_code, 401)

    def test_qr_exige_sesion_y_secreto(self):
        self.assertEqual(self.cliente.get("/cuenta/2fa/qr").status_code, 401)
        self.login()
        # sin alta previa no hay secreto que escanear
        self.assertEqual(self.cliente.get("/cuenta/2fa/qr").status_code, 400)

    def test_qr_devuelve_svg_del_secreto_pendiente(self):
        self.login()
        self.cliente.post("/cuenta/2fa")
        r = self.cliente.get("/cuenta/2fa/qr")
        self.assertEqual(r.status_code, 200)
        self.assertIn("image/svg+xml", r.headers["content-type"])
        self.assertIn("<svg", r.text)
        self.assertGreater(len(r.text), 500)

    def test_activar_sin_alta_previa_responde_400(self):
        self.login()
        r = self.cliente.post("/cuenta/2fa/activar", json={"codigo": "123456"})
        self.assertEqual(r.status_code, 400)

    def test_flujo_completo_2fa(self):
        # sin 2FA el acceso sigue siendo el normal
        self.assertEqual(self.login().status_code, 200)

        r = self.cliente.post("/cuenta/2fa")
        self.assertEqual(r.status_code, 200)
        secreto = r.json()["secreto"]
        self.assertEqual(len(secreto), 32)
        self.assertIn("otpauth://totp/Plataforma%20Herencia:admin", r.json()["uri"])
        self.assertIn(f"secret={secreto}", r.json()["uri"])

        # mientras no se confirma, el login no pide código
        self.cliente.cookies.clear()
        self.assertEqual(self.login().status_code, 200)

        r = self.cliente.post("/cuenta/2fa/activar", json={"codigo": codigo_malo(secreto)})
        self.assertEqual(r.status_code, 400)
        r = self.cliente.post("/cuenta/2fa/activar", json={"codigo": totp.codigo(secreto)})
        self.assertEqual(r.status_code, 200)

        self.assertTrue(self.cliente.get("/sesion").json()["totp_activado"])

        # ahora el login exige el código
        self.cliente.cookies.clear()
        r = self.login()
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["detail"], "codigo_totp_requerido")
        self.assertNotIn("sid", r.cookies)

        r = self.login(totp=codigo_malo(secreto))
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["detail"], "código 2FA inválido")

        r = self.login(totp=totp.codigo(secreto))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["totp_activado"])
        self.assertIn("sid=", r.headers["set-cookie"])

    def test_desactivar_vuelve_al_acceso_simple(self):
        self.login()
        secreto = self.cliente.post("/cuenta/2fa").json()["secreto"]
        self.cliente.post("/cuenta/2fa/activar", json={"codigo": totp.codigo(secreto)})
        self.assertEqual(self.cliente.delete("/cuenta/2fa").status_code, 200)
        self.assertFalse(self.cliente.get("/sesion").json()["totp_activado"])
        self.cliente.cookies.clear()
        self.assertEqual(self.login().status_code, 200)
