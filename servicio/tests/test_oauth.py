"""Login con Google (OAuth 2.0 / OIDC): flujo completo con Google mockeado.

El intercambio de `code` y el JWKS se sustituyen con parches; el ID token se
firma de verdad (RS256) con una clave de prueba embebida, así la verificación
criptográfica del servicio queda ejercitada sin llamar a Google.
"""
import base64
import hashlib
import json
import os
import time
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

import psycopg
from fastapi.testclient import TestClient

from servicio import google_oidc, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
EMAIL_ADMIN = "admin@herencia.cl"
CLIENT_ID = "cliente-id-de-prueba"
CLIENT_SECRET = "secreto-de-prueba"
FRONT = "http://localhost:3000"
REDIRECT_URI_ESPERADA = "http://localhost:8080/auth/google/callback"

# Clave RSA de prueba (solo tests; nunca comunica con Google).
N = 136585530483841161549938144051128753564061253337663055522586637208463884019640116907878956151585133373458444840978472297433773589824876194257625163196873155635802260941215775119641954246251051934957827860730276974964886934557923196227422000117141027826407543723080688245901787217268826630022591230758830114877
D = 36734311309766762492625688192092946126922862678023849377315288576474120263823133506542479532597457327014946499947915722638626932789924283992018266422144526433304139953218831408894605042126945940757292514649889393128606404348803034001087561706200651916185359080406119629258941217706938137277988301315065425433
KID = "kid-de-prueba"
_PREFIJO_SHA256 = bytes.fromhex("3031300d060960864801650304020105000420")


def b64u(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


def firmar_rs256(mensaje: bytes) -> bytes:
    k = (N.bit_length() + 7) // 8
    digesto = hashlib.sha256(mensaje).digest()
    relleno = k - len(_PREFIJO_SHA256) - len(digesto) - 3
    em = b"\x00\x01" + b"\xff" * relleno + b"\x00" + _PREFIJO_SHA256 + digesto
    return pow(int.from_bytes(em, "big"), D, N).to_bytes(k, "big")


def jwk_de_prueba(kid: str = KID) -> dict:
    """Una sola JWK (lo que devuelve google_oidc.obtener_jwks)."""
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": b64u(N.to_bytes(128, "big")),
        "e": b64u((65537).to_bytes(3, "big")),
    }


def id_token_de(**claims) -> str:
    cabecera = {"alg": "RS256", "kid": KID, "typ": "JWT"}
    parte = lambda datos: b64u(json.dumps(datos, separators=(",", ":")).encode("utf-8"))
    mensaje = f"{parte(cabecera)}.{parte(claims)}"
    return f"{mensaje}.{b64u(firmar_rs256(mensaje.encode('ascii')))}"


def claims_google(email: str = EMAIL_ADMIN, **sobreescritos) -> dict:
    claims = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "exp": int(time.time()) + 3600,
        "email": email,
        "email_verified": True,
        "sub": "1234567890",
    }
    claims.update(sobreescritos)
    return claims


class GoogleOauthHttpTest(unittest.TestCase):
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
            google_client_id=CLIENT_ID,
            google_client_secret=CLIENT_SECRET,
            admin_email=EMAIL_ADMIN,
            front_url=FRONT,
        )
        cls.app = crear_app(configuracion=cls.config)
        cls.cliente = TestClient(cls.app)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("TRUNCATE sesiones, usuarios, auditoria RESTART IDENTITY CASCADE")
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            seguridad.vincular_email(conexion, ADMIN[0], EMAIL_ADMIN)
            conexion.commit()
        self.cliente.cookies.clear()

    def estado_fresco(self) -> str:
        """Arranca /auth/google y devuelve el state emitido (sin seguir el 302)."""
        r = self.cliente.get("/auth/google", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        return parse_qs(urlparse(r.headers["location"]).query)["state"][0]

    def callback(self, **params):
        with mock.patch.object(google_oidc, "intercambiar_codigo", return_value={"id_token": None}) as cambio, \
             mock.patch.object(google_oidc, "obtener_jwks", return_value=jwk_de_prueba()) as jwks:
            r = self.cliente.get("/auth/google/callback", params=params, follow_redirects=False)
        return r, cambio, jwks

    def test_estado_y_503_cuando_no_configurado(self):
        config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        app = crear_app(configuracion=config)
        cliente = TestClient(app)
        self.assertEqual(cliente.get("/auth/google/estado").json(), {"configurado": False})
        r = cliente.get("/auth/google", follow_redirects=False)
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], "no configurado")
        r = cliente.get("/auth/google/callback", follow_redirects=False)
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], "no configurado")
        # configurado: el front pregunta antes de mostrar el botón
        self.assertEqual(self.cliente.get("/auth/google/estado").json(), {"configurado": True})

    def test_redireccion_a_google_con_state_de_un_solo_uso(self):
        r = self.cliente.get("/auth/google", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        destino = urlparse(r.headers["location"])
        self.assertEqual(destino.scheme, "https")
        self.assertEqual(destino.netloc, "accounts.google.com")
        self.assertEqual(destino.path, "/o/oauth2/v2/auth")
        consulta = parse_qs(destino.query)
        self.assertEqual(consulta["client_id"], [CLIENT_ID])
        self.assertEqual(consulta["redirect_uri"], ["http://localhost:8080/auth/google/callback"])
        self.assertEqual(consulta["scope"], ["openid email profile"])
        self.assertEqual(consulta["response_type"], ["code"])
        estado = consulta["state"][0]
        self.assertTrue(estado)

    def test_redirect_uri_configurable_por_entorno(self):
        config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
            google_client_id=CLIENT_ID, google_client_secret=CLIENT_SECRET,
            google_redirect_uri="https://api.ejemplo.cl/auth/google/callback",
            front_url=FRONT,
        )
        app = crear_app(configuracion=config)
        cliente = TestClient(app)
        r = cliente.get("/auth/google", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        consulta = parse_qs(urlparse(r.headers["location"]).query)
        self.assertEqual(consulta["redirect_uri"], ["https://api.ejemplo.cl/auth/google/callback"])

    def test_flujo_completo_crea_sesion_y_auditoria(self):
        estado = self.estado_fresco()
        token = id_token_de(**claims_google())
        with mock.patch.object(google_oidc, "intercambiar_codigo", return_value={"id_token": token}) as cambio, \
             mock.patch.object(google_oidc, "obtener_jwks", return_value=jwk_de_prueba()):
            r = self.cliente.get(
                "/auth/google/callback",
                params={"state": estado, "code": "codigo-de-prueba"},
                follow_redirects=False,
            )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers["location"], FRONT)
        cambio.assert_called_once_with("codigo-de-prueba", CLIENT_ID, CLIENT_SECRET, REDIRECT_URI_ESPERADA)
        sid = r.cookies.get("sid")
        self.assertTrue(sid)
        # misma maquinaria que POST /sesion: la cookie abre /sesion
        self.assertEqual(self.cliente.get("/sesion").json()["usuario"], ADMIN[0])
        with psycopg.connect(URL_TEST) as conexion:
            filas = conexion.execute(
                "SELECT actor, accion, recurso, resultado FROM auditoria "
                "WHERE accion = 'login' AND recurso = '/auth/google/callback'"
            ).fetchall()
        self.assertEqual(filas, [(ADMIN[0], "login", "/auth/google/callback", "ok")])

    def test_state_de_un_solo_uso_se_rechaza_al_reusar(self):
        estado = self.estado_fresco()
        token = id_token_de(**claims_google())
        with mock.patch.object(google_oidc, "intercambiar_codigo", return_value={"id_token": token}), \
             mock.patch.object(google_oidc, "obtener_jwks", return_value=jwk_de_prueba()):
            primera = self.cliente.get(
                "/auth/google/callback", params={"state": estado, "code": "c1"}, follow_redirects=False
            )
        self.assertEqual(primera.status_code, 302)
        r, cambio, _ = self.callback(state=estado, code="c1")
        self.assertEqual(r.status_code, 400)
        cambio.assert_not_called()

    def test_state_desconocido_o_expirado_se_rechaza(self):
        r, cambio, _ = self.callback(state="state-inventado", code="c1")
        self.assertEqual(r.status_code, 400)
        cambio.assert_not_called()
        estado_vencido = self.app.state.estados_oauth.nuevo(ahora=time.time() - 700)
        r, cambio, _ = self.callback(state=estado_vencido, code="c1")
        self.assertEqual(r.status_code, 400)
        cambio.assert_not_called()

    def test_falta_code_se_rechaza(self):
        estado = self.estado_fresco()
        r, cambio, _ = self.callback(state=estado)
        self.assertEqual(r.status_code, 400)
        cambio.assert_not_called()

    def test_email_sin_vinculo_redirige_al_front(self):
        estado = self.estado_fresco()
        token = id_token_de(**claims_google(email="otro@gmail.com"))
        with mock.patch.object(google_oidc, "intercambiar_codigo", return_value={"id_token": token}), \
             mock.patch.object(google_oidc, "obtener_jwks", return_value=jwk_de_prueba()):
            r = self.cliente.get(
                "/auth/google/callback", params={"state": estado, "code": "c1"}, follow_redirects=False
            )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers["location"], f"{FRONT}/login?error=cuenta_sin_vinculo")
        self.assertIsNone(r.cookies.get("sid"))
        with psycopg.connect(URL_TEST) as conexion:
            (n_sin_vinculo,) = conexion.execute(
                "SELECT count(*) FROM auditoria WHERE resultado = 'sin vinculo'"
            ).fetchone()
            (n_sesiones,) = conexion.execute("SELECT count(*) FROM sesiones").fetchone()
        self.assertEqual(n_sin_vinculo, 1)
        self.assertEqual(n_sesiones, 0)

    def test_access_denied_redirige_al_front(self):
        r = self.cliente.get(
            "/auth/google/callback", params={"error": "access_denied"}, follow_redirects=False
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers["location"], f"{FRONT}/login?error=acceso_denegado")

    def test_claims_invalidos_se_rechazan(self):
        casos = [
            claims_google(aud="otro-cliente"),
            claims_google(iss="https://cuenta.falsa.example"),
            claims_google(exp=int(time.time()) - 10),
            claims_google(email_verified=False),
            claims_google(email=""),
        ]
        for malos in casos:
            with self.subTest(claims=malos):
                estado = self.estado_fresco()
                token = id_token_de(**malos)
                with mock.patch.object(google_oidc, "intercambiar_codigo", return_value={"id_token": token}), \
                     mock.patch.object(google_oidc, "obtener_jwks", return_value=jwk_de_prueba()):
                    r = self.cliente.get(
                        "/auth/google/callback", params={"state": estado, "code": "c1"}, follow_redirects=False
                    )
                self.assertEqual(r.status_code, 502)
                self.assertIsNone(r.cookies.get("sid"))

    def test_firma_invalida_se_rechaza(self):
        estado = self.estado_fresco()
        token = id_token_de(**claims_google())
        cabecera, cuerpo, firma = token.split(".")
        firma_corrupta = ("A" if firma[0] != "A" else "B") + firma[1:]
        with mock.patch.object(google_oidc, "intercambiar_codigo", return_value={"id_token": f"{cabecera}.{cuerpo}.{firma_corrupta}"}), \
             mock.patch.object(google_oidc, "obtener_jwks", return_value=jwk_de_prueba()):
            r = self.cliente.get(
                "/auth/google/callback", params={"state": estado, "code": "c1"}, follow_redirects=False
            )
        self.assertEqual(r.status_code, 502)

    def test_kid_desconocido_se_rechaza(self):
        estado = self.estado_fresco()
        token = id_token_de(**claims_google())
        with mock.patch.object(google_oidc, "intercambiar_codigo", return_value={"id_token": token}), \
             mock.patch.object(
                 google_oidc, "obtener_jwks",
                 side_effect=google_oidc.ErrorGoogleOidc("no hay clave para el kid del token"),
             ):
            r = self.cliente.get(
                "/auth/google/callback", params={"state": estado, "code": "c1"}, follow_redirects=False
            )
        self.assertEqual(r.status_code, 502)

    def test_fallo_del_intercambio_se_rechaza(self):
        estado = self.estado_fresco()
        with mock.patch.object(google_oidc, "intercambiar_codigo", side_effect=google_oidc.ErrorGoogleOidc("x")), \
             mock.patch.object(google_oidc, "obtener_jwks", return_value=jwk_de_prueba()):
            r = self.cliente.get(
                "/auth/google/callback", params={"state": estado, "code": "c1"}, follow_redirects=False
            )
        self.assertEqual(r.status_code, 502)
        self.assertIsNone(r.cookies.get("sid"))

    def test_admin_email_se_vincula_al_arrancar(self):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("TRUNCATE usuarios RESTART IDENTITY CASCADE")
            conexion.commit()
        config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
            google_client_id=CLIENT_ID, google_client_secret=CLIENT_SECRET,
            admin_email="jefe@herencia.cl", front_url=FRONT,
        )
        app = crear_app(configuracion=config)
        with psycopg.connect(URL_TEST) as conexion:
            (email,) = conexion.execute(
                "SELECT email FROM usuarios WHERE nombre = %s", (ADMIN[0],)
            ).fetchone()
        self.assertEqual(email, "jefe@herencia.cl")
        cliente = TestClient(app)
        estado = None
        r = cliente.get("/auth/google", follow_redirects=False)
        estado = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
        token = id_token_de(**claims_google(email="jefe@herencia.cl"))
        with mock.patch.object(google_oidc, "intercambiar_codigo", return_value={"id_token": token}), \
             mock.patch.object(google_oidc, "obtener_jwks", return_value=jwk_de_prueba()):
            r = cliente.get(
                "/auth/google/callback", params={"state": estado, "code": "c1"}, follow_redirects=False
            )
        self.assertEqual(r.status_code, 302)
        self.assertIsNotNone(r.cookies.get("sid"))


if __name__ == "__main__":
    unittest.main()
