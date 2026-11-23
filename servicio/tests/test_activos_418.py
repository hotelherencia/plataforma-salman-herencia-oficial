"""Activos y mantenimiento preventivo (#418). HTTP contra PostgreSQL real, datos sintéticos."""
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


class ActivosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1]))

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            exigir_base_libre(c)
            c.execute("TRUNCATE auditoria, mantenciones_realizadas, mantenciones_plan, activos, tareas_operativas, observaciones_habitacion, reasignaciones, liquidaciones, efectos_nucleo, pagos, cargos, reservas, tarifas, habitaciones, claves_idempotencia, sesiones, usuarios RESTART IDENTITY CASCADE")
            seguridad.asegurar_admin_inicial(c, EMPRESA, ADMIN[0], ADMIN[1])
            c.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES ('HAB-ACT-1', 'EST-SINT-001', 'doble', 2)")
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


    def _activo(self, cliente=None, **extra):
        cuerpo = {"habitacion_id": "HAB-ACT-1", "nombre": "Split de pared", "categoria": "climatizacion", **extra}
        return (cliente or self.recep).post("/hotel/activos", json=cuerpo, headers=_h())

    def test_inventario_por_habitacion_y_area(self):
        self.assertEqual(self._activo().status_code, 200)
        self.assertEqual(self._activo(habitacion_id=None, area="Lavandería", nombre="Lavadora").status_code, 200)
        self.assertEqual(self._activo(habitacion_id="HAB-NO").status_code, 404)
        self.assertEqual(self._activo(habitacion_id=None).status_code, 422)
        self.assertEqual(self._activo(cliente=self.aseo).status_code, 403)
        self.assertEqual(len(self.aseo.get("/hotel/activos").json()["activos"]), 2)
        self.assertEqual(len(self.aseo.get("/hotel/activos?habitacion_id=HAB-ACT-1").json()["activos"]), 1)

    def test_plan_y_mantencion_realizada_corre_la_proxima(self):
        aid = self._activo().json()["activo_id"]
        hoy = date.today()
        r = self.recep.post(f"/hotel/activos/{aid}/plan", json={"descripcion": "Limpiar filtros", "cada_dias": 90, "proxima": (hoy - timedelta(days=3)).isoformat()}, headers=_h())
        self.assertEqual(r.status_code, 200, r.text)
        pid = r.json()["plan_id"]
        m = self.aseo.get("/hotel/mantenciones").json()["mantenciones"]
        self.assertEqual((m[0]["plan_id"], m[0]["vencida"]), (pid, True))
        ok = self.aseo.post(f"/hotel/mantenciones/{pid}/realizada", json={"nota": "Filtros lavados"}, headers=_h())
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(ok.json()["proxima"], (hoy + timedelta(days=90)).isoformat())
        self.assertEqual(self.aseo.get("/hotel/mantenciones").json()["mantenciones"], [])
        self.assertEqual(len(self.aseo.get("/hotel/mantenciones?dentro_de_dias=120").json()["mantenciones"]), 1)
        # no se registra dos veces el mismo día ni con fecha futura
        self.assertEqual(self.aseo.post(f"/hotel/mantenciones/{pid}/realizada", json={}, headers=_h()).status_code, 409)
        futura = (hoy + timedelta(days=2)).isoformat()
        self.assertEqual(self.aseo.post(f"/hotel/mantenciones/{pid}/realizada", json={"fecha": futura}, headers=_h()).status_code, 409)

    def test_dar_de_baja_desactiva_planes(self):
        aid = self._activo().json()["activo_id"]
        self.recep.post(f"/hotel/activos/{aid}/plan", json={"descripcion": "Revisión general", "cada_dias": 30}, headers=_h())
        self.assertEqual(len(self.recep.get("/hotel/mantenciones?dentro_de_dias=60").json()["mantenciones"]), 1)
        self.assertEqual(self.recep.post(f"/hotel/activos/{aid}/actualizacion", json={"estado": "de_baja"}, headers=_h()).status_code, 200)
        self.assertEqual(self.recep.get("/hotel/mantenciones?dentro_de_dias=60").json()["mantenciones"], [])
        r = self.recep.post(f"/hotel/activos/{aid}/plan", json={"descripcion": "Otra", "cada_dias": 30}, headers=_h())
        self.assertEqual(r.status_code, 409)

    def test_historial_no_se_modifica_y_es_idempotente(self):
        aid = self._activo().json()["activo_id"]
        pid = self.recep.post(f"/hotel/activos/{aid}/plan", json={"descripcion": "Revisión general", "cada_dias": 30}, headers=_h()).json()["plan_id"]
        h = _h()
        a = self.recep.post(f"/hotel/mantenciones/{pid}/realizada", json={}, headers=h)
        b = self.recep.post(f"/hotel/mantenciones/{pid}/realizada", json={}, headers=h)
        self.assertEqual((a.status_code, b.status_code), (200, 200))
        with psycopg.connect(URL_TEST) as c:
            with self.assertRaises(psycopg.errors.RaiseException):
                c.execute("DELETE FROM mantenciones_realizadas")


if __name__ == "__main__":
    unittest.main()
