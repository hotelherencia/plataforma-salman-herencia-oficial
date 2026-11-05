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


class SECA02MfaReauthTest(BaseAuditoriaTest):
    """SEC-A02 (#327): el secreto pendiente vive aparte del activo (el alta
    nunca desprotege la cuenta) y reemplazar/desactivar el segundo factor
    exige la clave actual (reautenticación)."""

    def admin_con_totp_activo(self):
        with psycopg.connect(URL_TEST) as conexion:
            secreto = seguridad.iniciar_alta_totp(conexion, self.uid_admin())
            seguridad.activar_totp(conexion, self.uid_admin())
            conexion.commit()
        return secreto

    def uid_admin(self):
        with psycopg.connect(URL_TEST) as conexion:
            (uid,) = conexion.execute(
                "SELECT id FROM usuarios WHERE nombre = %s", (ADMIN[0],)
            ).fetchone()
        return uid

    def login_admin(self, codigo=None):
        cuerpo = {"usuario": ADMIN[0], "clave": ADMIN[1]}
        if codigo:
            cuerpo["totp"] = codigo
        return self.cliente.post("/sesion", json=cuerpo)

    def test_primer_alta_sigue_sin_clave(self):
        self.login(*ADMIN)
        r = self.cliente.post("/cuenta/2fa")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len(r.json()["secreto"]), 32)

    def test_reenrolamiento_exige_clave_y_no_desprotege(self):
        self.login(*ADMIN)  # sesión abierta antes de activar el factor
        secreto_viejo = self.admin_con_totp_activo()
        # sin clave y con clave errada: rechazado
        self.assertEqual(self.cliente.post("/cuenta/2fa").status_code, 401)
        r = self.cliente.post("/cuenta/2fa", json={"clave": "mal"})
        self.assertEqual(r.status_code, 401, r.text)
        # con clave: genera secreto pendiente nuevo
        r = self.cliente.post("/cuenta/2fa", json={"clave": ADMIN[1]})
        self.assertEqual(r.status_code, 200, r.text)
        secreto_nuevo = r.json()["secreto"]
        self.assertNotEqual(secreto_nuevo, secreto_viejo)
        # mientras el nuevo está pendiente, el activo sigue siendo el viejo:
        # la cuenta jamás quedó desprotegida (la vulnerabilidad de SEC-A02).
        self.cliente.cookies.clear()
        r = self.login_admin(codigo=totp.codigo(secreto_viejo))
        self.assertEqual(r.status_code, 200, r.text)
        # confirmar el nuevo cambia el activo (la sesión se abre con el viejo,
        # que sigue vigente hasta la activación)
        r = self.login_admin(codigo=totp.codigo(secreto_viejo))
        self.assertEqual(r.status_code, 200, r.text)
        r = self.cliente.post("/cuenta/2fa/activar", json={"codigo": totp.codigo(secreto_nuevo)})
        self.assertEqual(r.status_code, 200, r.text)
        self.cliente.cookies.clear()
        self.assertEqual(self.login_admin(codigo=totp.codigo(secreto_viejo)).status_code, 401)
        self.assertEqual(self.login_admin(codigo=totp.codigo(secreto_nuevo)).status_code, 200)

    def test_qr_solo_del_pendiente(self):
        self.login(*ADMIN)
        self.admin_con_totp_activo()
        # activo sin pendiente: nada que escanear (el activo nunca se expone)
        self.assertEqual(self.cliente.get("/cuenta/2fa/qr").status_code, 400)
        self.cliente.post("/cuenta/2fa", json={"clave": ADMIN[1]})
        r = self.cliente.get("/cuenta/2fa/qr")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("image/svg+xml", r.headers["content-type"])

    def test_desactivar_exige_clave(self):
        self.login(*ADMIN)
        self.admin_con_totp_activo()
        self.assertEqual(self.cliente.delete("/cuenta/2fa").status_code, 401)
        r = self.cliente.request("DELETE", "/cuenta/2fa", json={"clave": "mal"})
        self.assertEqual(r.status_code, 401, r.text)
        r = self.cliente.request("DELETE", "/cuenta/2fa", json={"clave": ADMIN[1]})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertFalse(self.cliente.get("/sesion").json()["totp_activado"])
        self.cliente.cookies.clear()
        self.assertEqual(self.login_admin().status_code, 200)


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


class SECA05StateOAuthTest(BaseAuditoriaTest):
    """SEC-A05 (#330): el state de un solo uso queda vinculado a una cookie
    de transacción HttpOnly de vida corta: un callback con el state de otro
    navegador (sin la cookie que lo originó) se rechaza — cierra el login
    CSRF que la auditoría reprodujo sin cookies."""

    def setUp(self):
        super().setUp()
        with psycopg.connect(URL_TEST) as conexion:
            seguridad.vincular_email(conexion, ADMIN[0], "admin@herencia.cl")
            conexion.commit()

    def callback_con(self, cliente, state, email="admin@herencia.cl"):
        token = id_token_de(**claims_google(email=email))
        with mock.patch.object(google_oidc, "intercambiar_codigo", return_value={"id_token": token}), \
             mock.patch.object(google_oidc, "obtener_jwks", return_value=jwk_de_prueba()):
            return cliente.get(
                "/auth/google/callback", params={"state": state, "code": "c"},
                follow_redirects=False,
            )

    def state_para(self, cliente):
        r = cliente.get("/auth/google", follow_redirects=False)
        self.assertEqual(r.status_code, 302, r.text)
        return r.headers["location"].split("state=")[1]

    def test_state_de_otro_navegador_rechazado(self):
        atacante = TestClient(self.app)
        state = self.state_para(atacante)  # state ligado a la cookie del atacante
        victima = TestClient(self.app)
        victima.cookies.clear()
        r = self.callback_con(victima, state)
        self.assertEqual(r.status_code, 400, r.text)
        # el state se consume igual: no es reutilizable
        r = self.callback_con(atacante, state)
        self.assertEqual(r.status_code, 400, r.text)

    def test_callback_sin_cookie_rechazado(self):
        cliente = TestClient(self.app)
        state = self.state_para(cliente)
        cliente.cookies.clear()
        r = self.callback_con(cliente, state)
        self.assertEqual(r.status_code, 400, r.text)

    def test_flujo_ok_con_la_cookie_de_transaccion(self):
        cliente = TestClient(self.app)
        state = self.state_para(cliente)
        r = self.callback_con(cliente, state)
        self.assertEqual(r.status_code, 302, r.text)
        self.assertTrue(r.headers["location"].startswith(FRONT))
        self.assertIn("sid=", r.headers.get("set-cookie", ""))


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
