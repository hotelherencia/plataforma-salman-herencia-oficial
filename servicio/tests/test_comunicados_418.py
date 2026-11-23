"""Comunicados internos con confirmación de lectura (#418). HTTP contra PostgreSQL real, datos sintéticos."""
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


class ComunicadosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1]))

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            exigir_base_libre(c)
            c.execute("ALTER TABLE comunicado_lecturas DISABLE TRIGGER trg_comunicado_lecturas_solo_agregar")
            c.execute("TRUNCATE auditoria, comunicado_lecturas, comunicados, claves_idempotencia, sesiones, usuarios RESTART IDENTITY CASCADE")
            c.execute("ALTER TABLE comunicado_lecturas ENABLE TRIGGER trg_comunicado_lecturas_solo_agregar")
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

    def _crear(self, **extra):
        r = self.admin.post("/hotel/comunicados", json={"titulo": "Cambio de turno", "cuerpo": "Mañana el aseo entra a las 8.", **extra}, headers=_h())
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["comunicado_id"]

    def test_crear_listar_y_confirmar_lectura_una_sola_vez(self):
        cid = self._crear()
        lista = self.aseo.get("/hotel/comunicados").json()
        self.assertEqual(lista["sin_leer"], 1)
        self.assertFalse(lista["comunicados"][0]["leido"])
        clave = _h()
        self.assertEqual(self.aseo.post(f"/hotel/comunicados/{cid}/lectura", headers=clave).status_code, 200)
        self.assertEqual(self.aseo.post(f"/hotel/comunicados/{cid}/lectura", headers=_h()).status_code, 200)
        lista = self.aseo.get("/hotel/comunicados").json()
        self.assertEqual(lista["sin_leer"], 0)
        self.assertTrue(lista["comunicados"][0]["leido"])
        with psycopg.connect(URL_TEST) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM comunicado_lecturas WHERE comunicado_id = %s", (cid,)).fetchone()[0], 1)

    def test_destinatarios_por_rol(self):
        cid = self._crear(roles=["recepcion"])
        self.assertEqual(self.aseo.get("/hotel/comunicados").json()["comunicados"], [])
        self.assertEqual(self.aseo.post(f"/hotel/comunicados/{cid}/lectura", headers=_h()).status_code, 404)
        self.assertEqual(len(self.recep.get("/hotel/comunicados").json()["comunicados"]), 1)

    def test_quien_leyo_y_quien_falta(self):
        cid = self._crear(roles=["aseo", "recepcion"])
        self.aseo.post(f"/hotel/comunicados/{cid}/lectura", headers=_h())
        r = self.admin.get(f"/hotel/comunicados/{cid}/lecturas").json()
        self.assertEqual([x["usuario"] for x in r["leyeron"]], ["aseo1"])
        self.assertEqual([x["usuario"] for x in r["faltan"]], ["recep1"])

    def test_solo_administracion_publica_y_ve_lecturas(self):
        r = self.recep.post("/hotel/comunicados", json={"titulo": "Aviso", "cuerpo": "Texto"}, headers=_h())
        self.assertEqual(r.status_code, 403)
        cid = self._crear()
        self.assertEqual(self.aseo.get(f"/hotel/comunicados/{cid}/lecturas").status_code, 403)

    def test_idempotencia_al_crear_y_archivo(self):
        h = _h()
        cuerpo = {"titulo": "Aviso", "cuerpo": "Texto del aviso"}
        a = self.admin.post("/hotel/comunicados", json=cuerpo, headers=h).json()
        b = self.admin.post("/hotel/comunicados", json=cuerpo, headers=h).json()
        self.assertEqual(a["comunicado_id"], b["comunicado_id"])
        self.assertEqual(self.admin.post(f"/hotel/comunicados/{a['comunicado_id']}/archivo", headers=_h()).status_code, 200)
        self.assertEqual(self.aseo.get("/hotel/comunicados").json()["comunicados"], [])
        self.assertEqual(len(self.admin.get("/hotel/comunicados?archivados=true").json()["comunicados"]), 1)

    def test_las_lecturas_no_se_modifican_ni_se_borran(self):
        cid = self._crear()
        self.aseo.post(f"/hotel/comunicados/{cid}/lectura", headers=_h())
        with psycopg.connect(URL_TEST) as c:
            with self.assertRaises(psycopg.errors.RaiseException):
                c.execute("DELETE FROM comunicado_lecturas")


if __name__ == "__main__":
    unittest.main()
