import os
import unittest

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.tests.aislamiento import exigir_base_libre
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")


class SesionHttpTest(unittest.TestCase):
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

    def login(self, usuario=ADMIN[0], clave=ADMIN[1]):
        return self.cliente.post("/sesion", json={"usuario": usuario, "clave": clave})

    def test_login_ok_fija_cookie_y_abre_sesion_server_side(self):
        respuesta = self.login()
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["empresa_id"], EMPRESA)
        self.assertEqual(cuerpo["rol"], "administrador")
        cookie = respuesta.headers["set-cookie"]
        self.assertIn("sid=", cookie)
        self.assertIn("HttpOnly", cookie)
        atributos = {parte.strip() for parte in cookie.split(";")}
        self.assertNotIn("Secure", atributos)  # COOKIE_SEGURA=0 en local
        # sin Secure el navegador rechaza SameSite=None: en local es Lax (spec-api-v1)
        self.assertIn("samesite=lax", {a.lower() for a in atributos})
        # el id de sesión vive en PostgreSQL, no en el valor de la cookie firmado por el cliente
        sid = respuesta.cookies.get("sid")
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            fila = conexion.execute(
                "SELECT revocada_en FROM sesiones WHERE id = %s", (sid,)
            ).fetchone()
        self.assertIsNotNone(fila)
        self.assertIsNone(fila[0])

    def test_get_sesion_requiere_cookie(self):
        self.assertEqual(self.cliente.get("/sesion").status_code, 401)
        self.login()
        respuesta = self.cliente.get("/sesion")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["empresa_id"], EMPRESA)

    def test_get_sesion_incluye_id_del_usuario(self):
        # V1-ISSUE-33: el operador necesita su USR-... (p. ej. para cambiar su
        # propia clave vía /cuenta).
        self.login()
        respuesta = self.cliente.get("/sesion")
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        with psycopg.connect(URL_TEST) as conexion:
            (uid,) = conexion.execute(
                "SELECT id FROM usuarios WHERE nombre = %s", (ADMIN[0],)
            ).fetchone()
        self.assertEqual(cuerpo["id"], uid)

    def test_clave_mala_responde_401(self):
        respuesta = self.login(clave="clave-errada")
        self.assertEqual(respuesta.status_code, 401)
        self.assertNotIn("sid", respuesta.cookies)

    def test_logout_revoca_la_sesion_en_el_servidor(self):
        self.login()
        self.assertEqual(self.cliente.delete("/sesion").status_code, 200)
        self.assertEqual(self.cliente.get("/sesion").status_code, 401)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (revocadas,) = conexion.execute("SELECT count(*) FROM sesiones WHERE revocada_en IS NOT NULL").fetchone()
        self.assertEqual(revocadas, 1)

    def test_403_empresa_ajena_sin_consultar_existencia(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            seguridad.crear_usuario(conexion, empresa_id="EMP-OTRA", nombre="ajeno", rol="recepcion", clave="clave-ajena")
            conexion.commit()
        respuesta = self.login(usuario="ajeno", clave="clave-ajena")
        self.assertEqual(respuesta.status_code, 200)
        ajena = seguridad.SesionActiva(
            sid="x", usuario_id="u", empresa_id=respuesta.json()["empresa_id"], rol="recepcion", nombre="ajeno"
        )
        # el mismo 403 con recurso existente o inexistente: la autorización va antes que la existencia
        with self.assertRaises(seguridad.ErrorPermiso) as caso_existente:
            seguridad.exigir_misma_empresa(ajena, EMPRESA)
        with self.assertRaises(seguridad.ErrorPermiso) as caso_inexistente:
            seguridad.exigir_misma_empresa(ajena, "EMP-INEXISTENTE")
        self.assertEqual(str(caso_existente.exception), str(caso_inexistente.exception))

    def test_admin_inicial_se_crea_una_sola_vez_desde_env(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, "otro", "otra-clave")
            (n,) = conexion.execute("SELECT count(*) FROM usuarios").fetchone()
        self.assertEqual(n, 1)  # no duplica ni sobreescribe al primer admin

    def test_arranque_falla_si_falta_admin_con_tabla_vacia(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("TRUNCATE sesiones, usuarios RESTART IDENTITY CASCADE")
            conexion.commit()
        config_sin_admin = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=None, admin_clave=None,
        )
        from servicio.aplicacion import ErrorArranque

        with self.assertRaises(ErrorArranque):
            crear_app(configuracion=config_sin_admin)


if __name__ == "__main__":
    unittest.main()
