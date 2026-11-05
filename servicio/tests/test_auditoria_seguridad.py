"""Correcciones de la auditoría de jefatura 2026-11-03 (issues #326–#329, #333).

Lote 1 (seguridad y operación, en verde tras el arreglo):
- SEC-A01 (#326): identidad Google y sesiones vigentes respetan `activo`.
- SEC-A03 (#328): el freno de logins solo se reinicia al completar toda la
  autenticación (antes se reiniciaba con la clave correcta y dejaba el
  segundo factor TOTP sin freno de fuerza bruta).
- SEC-A04 (#329): el límite HTTP deniega explícitamente una sesión cuya
  empresa no es la del núcleo (V1 de empresa fija).
- OPS-A02 (#333): readiness con consulta real a la base de datos y estado
  de migraciones; `/salud` sigue siendo liveness pura.

Pruebas HTTP contra PostgreSQL de test (mismo patrón que test_preh7_seguridad).
"""
import os
import unittest
from unittest import mock

import psycopg
from fastapi.testclient import TestClient

from servicio import google_oidc, seguridad, totp
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests.test_oauth import (
    CLIENT_ID,
    CLIENT_SECRET,
    claims_google,
    id_token_de,
    jwk_de_prueba,
)

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
FRONT = "http://localhost:3000"


def app_de_prueba():
    config = Configuracion(
        host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
        origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        google_client_id=CLIENT_ID, google_client_secret=CLIENT_SECRET,
        front_url=FRONT,
    )
    return crear_app(configuracion=config)


class BaseAuditoriaTest(unittest.TestCase):
    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "TRUNCATE auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.commit()
        self.app = app_de_prueba()
        self.cliente = TestClient(self.app)

    def login(self, usuario, clave, totp_code=None):
        cuerpo = {"usuario": usuario, "clave": clave}
        if totp_code:
            cuerpo["totp"] = totp_code
        return self.cliente.post("/sesion", json=cuerpo)

    def usuario_con_totp(self, nombre="recepcion", clave="clave-recepcion"):
        with psycopg.connect(URL_TEST) as conexion:
            uid = seguridad.crear_usuario(conexion, EMPRESA, nombre, "recepcion", clave)
            secreto = seguridad.iniciar_alta_totp(conexion, uid)
            seguridad.activar_totp(conexion, uid)
            conexion.commit()
        return uid, secreto


class SECA01IdentidadActivaTest(BaseAuditoriaTest):
    def test_google_rechaza_cuenta_dada_de_baja(self):
        email = "baja@herencia.cl"
        with psycopg.connect(URL_TEST) as conexion:
            uid = seguridad.crear_usuario(conexion, EMPRESA, "recepbaja", "recepcion", "clave-x")
            seguridad.vincular_email(conexion, "recepbaja", email)
            seguridad.dar_de_baja(conexion, uid)
            conexion.commit()
        r = self.cliente.get("/auth/google", follow_redirects=False)
        state = r.headers["location"].split("state=")[1]
        token = id_token_de(**claims_google(email=email))
        with mock.patch.object(google_oidc, "intercambiar_codigo", return_value={"id_token": token}), \
             mock.patch.object(google_oidc, "obtener_jwks", return_value=jwk_de_prueba()):
            r = self.cliente.get(
                "/auth/google/callback", params={"state": state, "code": "c"},
                follow_redirects=False,
            )
        self.assertEqual(r.status_code, 302, r.text)
        self.assertIn("cuenta_sin_vinculo", r.headers["location"])
        with psycopg.connect(URL_TEST) as conexion:
            (n_sesiones,) = conexion.execute("SELECT count(*) FROM sesiones").fetchone()
        self.assertEqual(n_sesiones, 0)

    def test_sesion_previa_muere_si_el_usuario_queda_inactivo(self):
        r = self.login(*ADMIN)
        self.assertEqual(r.status_code, 200, r.text)
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("UPDATE usuarios SET activo = false WHERE nombre = %s", (ADMIN[0],))
            conexion.commit()
        r = self.cliente.get("/sesion")
        self.assertEqual(r.status_code, 401, r.text)


class SECA03FrenoTotpTest(BaseAuditoriaTest):
    def test_totps_incorrectos_acumulan_y_bloquean(self):
        self.usuario_con_totp()
        for i in range(5):
            r = self.login("recepcion", "clave-recepcion", totp_code="000000")
            self.assertEqual(r.status_code, 401, f"intento {i + 1}: {r.text}")
        r = self.login("recepcion", "clave-recepcion", totp_code="000000")
        self.assertEqual(r.status_code, 429, r.text)

    def test_login_exitoso_reinicia_el_freno(self):
        _uid, secreto = self.usuario_con_totp()
        for _ in range(4):
            self.login("recepcion", "clave-recepcion", totp_code="000000")
        r = self.login("recepcion", "clave-recepcion", totp_code=totp.codigo(secreto))
        self.assertEqual(r.status_code, 200, r.text)
        r = self.login("recepcion", "clave-recepcion", totp_code="000000")
        self.assertEqual(r.status_code, 401, r.text)

    def test_clave_correcta_sin_codigo_no_borra_el_freno(self):
        """El paso intermedio «falta código» no debe limpiar contadores."""
        self.usuario_con_totp()
        for _ in range(5):
            self.login("recepcion", "clave-recepcion")  # sin totp: 401 codigo_totp_requerido
        r = self.login("recepcion", "clave-recepcion", totp_code="000000")
        self.assertEqual(r.status_code, 401, r.text)


class SECA04EmpresaDelNucleoTest(BaseAuditoriaTest):
    def test_sesion_de_otra_empresa_rechazada_en_el_limite(self):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute(
                "INSERT INTO usuarios (id, empresa_id, nombre, rol, clave_hash, activo) "
                "VALUES ('USR-OTRA', 'EMP-OTRA-001', 'intruso', 'administrador', 'x', true)"
            )
            conexion.execute(
                "INSERT INTO sesiones (id, usuario_id, empresa_id) VALUES ('sid-otra', 'USR-OTRA', 'EMP-OTRA')"
            )
            conexion.commit()
        self.cliente.cookies.set("sid", "sid-otra")
        r = self.cliente.get("/sesion")
        self.assertEqual(r.status_code, 403, r.text)
        r = self.cliente.get("/hotel/habitaciones")
        self.assertEqual(r.status_code, 403, r.text)

    def test_sesion_de_la_empresa_del_nucleo_siguiendo(self):
        r = self.login(*ADMIN)
        self.assertEqual(r.status_code, 200, r.text)
        r = self.cliente.get("/sesion")
        self.assertEqual(r.status_code, 200, r.text)


class OPSA02ReadinessTest(BaseAuditoriaTest):
    def test_readiness_ok_con_base_arriba(self):
        r = self.cliente.get("/readiness")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["estado"], "listo")
        self.assertGreater(r.json()["migraciones"], 0)

    def test_readiness_503_con_base_caida(self):
        self.app.state.database_url = "postgresql://plataforma:plataforma@127.0.0.1:54999/nada"
        r = self.cliente.get("/readiness")
        self.assertEqual(r.status_code, 503, r.text)

    def test_salud_sigue_siendo_liveness(self):
        """Liveness pura: no toca la base (auditoría OPS-A02)."""
        self.app.state.database_url = "postgresql://plataforma:plataforma@127.0.0.1:54999/nada"
        r = self.cliente.get("/salud")
        self.assertEqual(r.status_code, 200, r.text)


if __name__ == "__main__":
    unittest.main()
