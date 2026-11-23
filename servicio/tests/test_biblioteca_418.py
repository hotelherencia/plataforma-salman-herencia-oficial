"""Biblioteca documental y buzón de sugerencias (#418). HTTP contra PostgreSQL real, datos sintéticos."""
import os
import unittest
import uuid

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get("DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test")
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")


def _h():
    return {"Idempotency-Key": uuid.uuid4().hex}


class BibliotecaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1]))

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            exigir_base_libre(c)
            c.execute("TRUNCATE auditoria, sugerencias, biblioteca_documentos, claves_idempotencia, sesiones, usuarios RESTART IDENTITY CASCADE")
            seguridad.asegurar_admin_inicial(c, EMPRESA, ADMIN[0], ADMIN[1])
            c.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.admin = TestClient(self.app)
        self.assertEqual(self.admin.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)
        for nombre, rol in (("aseo1", "aseo"), ("recep1", "recepcion")):
            self.assertEqual(self.admin.post("/usuarios", json={"nombre": nombre, "rol": rol, "clave": "clave-sintetica-1"}, headers=_h()).status_code, 201)
        self.aseo = TestClient(self.app)
        self.assertEqual(self.aseo.post("/sesion", json={"usuario": "aseo1", "clave": "clave-sintetica-1"}).status_code, 200)
        self.recep = TestClient(self.app)
        self.assertEqual(self.recep.post("/sesion", json={"usuario": "recep1", "clave": "clave-sintetica-1"}).status_code, 200)


    def _doc(self, **extra):
        cuerpo = {"titulo": "Manual de aseo", "categoria": "manual", "contenido": "1. Ventilar. 2. Cambiar sábanas.", **extra}
        return self.admin.post("/hotel/biblioteca", json=cuerpo, headers=_h())

    def test_publicar_y_leer_segun_rol(self):
        self.assertEqual(self._doc().status_code, 200)
        self.assertEqual(self._doc(titulo="Caja diaria", categoria="instructivo", roles=["recepcion"]).status_code, 200)
        self.assertEqual([d["titulo"] for d in self.aseo.get("/hotel/biblioteca").json()["documentos"]], ["Manual de aseo"])
        self.assertEqual(len(self.recep.get("/hotel/biblioteca").json()["documentos"]), 2)
        self.assertEqual(len(self.recep.get("/hotel/biblioteca?categoria=instructivo").json()["documentos"]), 1)

    def test_validaciones_y_permisos(self):
        self.assertEqual(self.recep.post("/hotel/biblioteca", json={"titulo": "Algo", "categoria": "otro", "contenido": "x y z"}, headers=_h()).status_code, 403)
        self.assertEqual(self._doc(contenido="").status_code, 409)  # ni contenido ni enlace
        self.assertEqual(self._doc(contenido="", enlace="http://inseguro.cl/a").status_code, 422)
        self.assertEqual(self._doc(contenido="", enlace="https://hotelherencia.cl/manual.pdf").status_code, 200)

    def test_archivar_oculta_para_el_personal(self):
        did = self._doc().json()["documento_id"]
        self.assertEqual(self.admin.post(f"/hotel/biblioteca/{did}/archivo", headers=_h()).status_code, 200)
        self.assertEqual(self.aseo.get("/hotel/biblioteca?archivados=true").json()["documentos"], [])
        self.assertEqual(len(self.admin.get("/hotel/biblioteca?archivados=true").json()["documentos"]), 1)

    def test_buzon_de_sugerencias(self):
        r = self.aseo.post("/hotel/sugerencias", json={"texto": "Faltan guantes en bodega"}, headers=_h())
        self.assertEqual(r.status_code, 200, r.text)
        sid = r.json()["sugerencia_id"]
        self.assertEqual(self.aseo.get("/hotel/sugerencias").status_code, 403)
        lista = self.admin.get("/hotel/sugerencias?estado=nueva").json()["sugerencias"]
        self.assertEqual((lista[0]["autor"], lista[0]["estado"]), ("aseo1", "nueva"))
        self.assertEqual(self.recep.post(f"/hotel/sugerencias/{sid}/atencion", json={}, headers=_h()).status_code, 403)
        self.assertEqual(self.admin.post(f"/hotel/sugerencias/{sid}/atencion", json={"respuesta": "Se compran el lunes"}, headers=_h()).status_code, 200)
        self.assertEqual(self.admin.post(f"/hotel/sugerencias/{sid}/atencion", json={}, headers=_h()).status_code, 409)
        self.assertEqual(self.admin.get("/hotel/sugerencias?estado=nueva").json()["sugerencias"], [])

    def test_idempotencia_de_sugerencia(self):
        h = _h()
        a = self.aseo.post("/hotel/sugerencias", json={"texto": "Más toallas"}, headers=h).json()
        b = self.aseo.post("/hotel/sugerencias", json={"texto": "Más toallas"}, headers=h).json()
        self.assertEqual(a["sugerencia_id"], b["sugerencia_id"])


if __name__ == "__main__":
    unittest.main()
