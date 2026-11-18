"""#352 (2026-11-18): alta de una cuenta administrativa con su correo de
Google, desde «Usuarios», sin pasar por variables de entorno."""
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


class UsuarioGoogleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        ))

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("TRUNCATE auditoria, claves_idempotencia, sesiones, usuarios RESTART IDENTITY CASCADE")
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        self.assertEqual(self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)

    def alta(self, nombre, email, rol="administrador"):
        return self.cliente.post("/usuarios", json={"nombre": nombre, "rol": rol, "clave": "clave-segura-1", "email": email},
                                 headers={"Idempotency-Key": f"k-{uuid.uuid4().hex[:10]}"})

    def email_de(self, usuario_id):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            return conexion.execute("SELECT email FROM usuarios WHERE id = %s", (usuario_id,)).fetchone()[0]

    def test_352_alta_con_correo_google_normalizado_y_listado_sin_correo(self):
        r = self.alta("admin-nominado", "  Persona.Admin@Example.TEST ")
        self.assertEqual(r.status_code, 201, r.text)
        self.assertTrue(r.json()["google_vinculado"])
        self.assertEqual(self.email_de(r.json()["id"]), "persona.admin@example.test")
        lista = self.cliente.get("/usuarios").json()["usuarios"]
        fila = next(u for u in lista if u["nombre"] == "admin-nominado")
        self.assertTrue(fila["google_vinculado"])
        self.assertNotIn("example.test", str(lista))
        with psycopg.connect(URL_TEST) as conexion:
            auditoria = conexion.execute("SELECT accion, resultado FROM auditoria WHERE recurso = %s", (r.json()["id"],)).fetchall()
        self.assertNotIn("example.test", str(auditoria))

    def test_352_correo_unico_e_invalido(self):
        self.assertEqual(self.alta("uno", "misma@example.test").status_code, 201)
        self.assertEqual(self.alta("dos", "MISMA@example.test").status_code, 409)
        self.assertEqual(self.alta("tres", "no-es-correo").status_code, 422)

    def test_352_vincular_y_desvincular(self):
        r = self.cliente.post("/usuarios", json={"nombre": "recep-g", "rol": "recepcion", "clave": "clave-segura-1"},
                              headers={"Idempotency-Key": "u-g-1"})
        uid = r.json()["id"]
        v = self.cliente.post(f"/usuarios/{uid}/email", json={"email": "Recep@Example.test"},
                              headers={"Idempotency-Key": "u-g-2"})
        self.assertEqual((v.status_code, v.json()["google_vinculado"]), (200, True))
        self.assertEqual(self.email_de(uid), "recep@example.test")
        d = self.cliente.post(f"/usuarios/{uid}/email", json={"email": None}, headers={"Idempotency-Key": "u-g-3"})
        self.assertEqual((d.status_code, d.json()["google_vinculado"]), (200, False))
        self.assertIsNone(self.email_de(uid))
        self.assertEqual(self.cliente.post("/usuarios/USR-no-existe/email", json={"email": "x@example.test"},
                                           headers={"Idempotency-Key": "u-g-4"}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
