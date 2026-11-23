"""Turnos semanales y cambios de turno (#418). HTTP contra PostgreSQL real, datos sintéticos."""
import os
import unittest
import uuid
from datetime import date, timedelta

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


class TurnosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1]))

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            exigir_base_libre(c)
            c.execute("TRUNCATE auditoria, turno_cambios, turnos, claves_idempotencia, sesiones, usuarios RESTART IDENTITY CASCADE")
            seguridad.asegurar_admin_inicial(c, EMPRESA, ADMIN[0], ADMIN[1])
            c.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.admin = TestClient(self.app)
        self.assertEqual(self.admin.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)
        for nombre, rol in (("aseo1", "aseo"), ("aseo2", "aseo"), ("recep1", "recepcion")):
            self.assertEqual(self.admin.post("/usuarios", json={"nombre": nombre, "rol": rol, "clave": "clave-sintetica-1"}, headers=_h()).status_code, 201)
        self.aseo = TestClient(self.app)
        self.assertEqual(self.aseo.post("/sesion", json={"usuario": "aseo1", "clave": "clave-sintetica-1"}).status_code, 200)
        self.recep = TestClient(self.app)
        self.assertEqual(self.recep.post("/sesion", json={"usuario": "recep1", "clave": "clave-sintetica-1"}).status_code, 200)
    def _turno(self, usuario="aseo1", dias=1, area="aseo", ini="08:00", fin="16:00", cliente=None):
        fecha = (date.today() + timedelta(days=dias)).isoformat()
        r = (cliente or self.admin).post("/hotel/turnos", json={"fecha": fecha, "area": area, "usuario": usuario, "hora_inicio": ini, "hora_fin": fin}, headers=_h())
        return r

    def test_armar_y_ver_la_semana_por_dia(self):
        self.assertEqual(self._turno().status_code, 200)
        self.assertEqual(self._turno("recep1", 2, "recepcion").status_code, 200)
        semana = self.aseo.get("/hotel/turnos").json()
        self.assertEqual(len(semana["dias"]), 7)
        con = [d for d in semana["dias"] if d["turnos"]]
        self.assertEqual([t["usuario"] for d in con for t in d["turnos"]], ["aseo1", "recep1"])
        self.assertEqual(len(self.aseo.get("/hotel/turnos?area=aseo").json()["dias"][1]["turnos"]), 1)
        mios = self.aseo.get("/hotel/turnos?solo_mios=true").json()
        self.assertEqual(sum(len(d["turnos"]) for d in mios["dias"]), 1)

    def test_validaciones_y_permisos(self):
        self.assertEqual(self._turno(cliente=self.recep).status_code, 403)
        self.assertEqual(self._turno("fantasma").status_code, 404)
        self.assertEqual(self._turno(ini="16:00", fin="08:00").status_code, 422)
        self.assertEqual(self._turno().status_code, 200)
        self.assertEqual(self._turno().status_code, 409)  # mismo bloque, misma persona
        self.assertEqual(self.aseo.get("/hotel/turnos?desde=2026-01-01&hasta=2026-06-01").status_code, 422)
        self.assertEqual(self.aseo.get("/hotel/turnos/cambios").status_code, 403)

    def test_cambio_de_turno_aprobado_traspasa_el_turno(self):
        tid = self._turno().json()["turno_id"]
        r = self.aseo.post(f"/hotel/turnos/{tid}/cambio", json={"propuesto": "aseo2", "motivo": "Control médico"}, headers=_h())
        self.assertEqual(r.status_code, 200, r.text)
        cid = r.json()["cambio_id"]
        # un solo cambio pendiente por turno
        self.assertEqual(self.aseo.post(f"/hotel/turnos/{tid}/cambio", json={"propuesto": "aseo2", "motivo": "Otra vez"}, headers=_h()).status_code, 409)
        self.assertEqual(self.admin.get("/hotel/turnos/cambios?estado=pendiente").json()["cambios"][0]["id"], cid)
        res = self.admin.post(f"/hotel/turnos/cambios/{cid}/resolucion", json={"aprobar": True}, headers=_h())
        self.assertEqual(res.status_code, 200, res.text)
        dia = [d for d in self.admin.get("/hotel/turnos").json()["dias"] if d["turnos"]][0]
        self.assertEqual(dia["turnos"][0]["usuario"], "aseo2")
        self.assertEqual(self.admin.post(f"/hotel/turnos/cambios/{cid}/resolucion", json={"aprobar": False}, headers=_h()).status_code, 409)

    def test_cambio_rechazado_no_mueve_el_turno_y_solo_el_titular_lo_pide(self):
        tid = self._turno().json()["turno_id"]
        self.assertEqual(self.recep.post(f"/hotel/turnos/{tid}/cambio", json={"propuesto": "aseo2", "motivo": "No es mío"}, headers=_h()).status_code, 409)
        cid = self.aseo.post(f"/hotel/turnos/{tid}/cambio", json={"propuesto": "aseo2", "motivo": "Trámite"}, headers=_h()).json()["cambio_id"]
        self.assertEqual(self.recep.post(f"/hotel/turnos/cambios/{cid}/resolucion", json={"aprobar": True}, headers=_h()).status_code, 403)
        self.assertEqual(self.admin.post(f"/hotel/turnos/cambios/{cid}/resolucion", json={"aprobar": False}, headers=_h()).status_code, 200)
        dia = [d for d in self.admin.get("/hotel/turnos").json()["dias"] if d["turnos"]][0]
        self.assertEqual(dia["turnos"][0]["usuario"], "aseo1")

    def test_no_se_pide_cambio_de_un_turno_pasado(self):
        tid = self._turno(dias=-1).json()["turno_id"]
        r = self.aseo.post(f"/hotel/turnos/{tid}/cambio", json={"propuesto": "aseo2", "motivo": "Ya pasó"}, headers=_h())
        self.assertEqual(r.status_code, 409)


if __name__ == "__main__":
    unittest.main()
