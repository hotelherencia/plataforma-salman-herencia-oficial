"""Hallazgos de aseo del propietario (2026-11-18): rol aseo con su lista de
habitaciones por limpiar (#362), verificación y observaciones de la
administración (#363) y mantenimiento con rango de fechas que no quita cupo
fuera de él (#349). HTTP contra PostgreSQL real, datos sintéticos.
"""
import os
import unittest
import uuid
from datetime import date, timedelta

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
HOY = date.today()


class AseoHallazgosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "TRUNCATE auditoria, tareas_operativas, observaciones_habitacion, reasignaciones, "
                "claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, reservas, tarifas, "
                "sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            for hid in ("HAB-ASEO-1", "HAB-ASEO-2"):
                conexion.execute(
                    "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                    "VALUES (%s, 'EST-SINT-001', 'doble', 2)",
                    (hid,),
                )
                conexion.execute(
                    "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                    "VALUES (%s, %s, '2026-01-01', '2027-12-31', 40000)",
                    (f"TAR-{hid}", hid),
                )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.admin = TestClient(self.app)
        self.assertEqual(self.admin.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)
        r = self.admin.post("/usuarios", json={"nombre": "aseo1", "rol": "aseo", "clave": "clave-aseo-1"},
                            headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        self.aseo = TestClient(self.app)
        self.assertEqual(self.aseo.post("/sesion", json={"usuario": "aseo1", "clave": "clave-aseo-1"}).status_code, 200)

    def idem(self):
        return {"Idempotency-Key": f"k-{uuid.uuid4().hex[:10]}"}

    def ensuciar(self, hid):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("UPDATE habitaciones SET estado_preparacion = 'sucia' WHERE id = %s", (hid,))
            conexion.execute(
                "INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado) VALUES (%s, %s, 'limpieza', 'pendiente')",
                (f"TSK-{uuid.uuid4().hex[:8]}", hid),
            )
            conexion.commit()

    def limpiar(self, hid, cliente=None):
        return (cliente or self.aseo).post(f"/hotel/habitaciones/{hid}/limpieza", json={}, headers=self.idem())

    def vista(self, cliente=None):
        r = (cliente or self.aseo).get("/hotel/aseo")
        self.assertEqual(r.status_code, 200, r.text)
        return {h["habitacion_id"]: h for h in r.json()["habitaciones"]}, r.json()

    def oferta(self, inicio, fin):
        r = self.admin.get("/hotel/oferta", params={"inicio": str(inicio), "fin": str(fin), "personas": 1})
        self.assertEqual(r.status_code, 200, r.text)
        return {i["habitacion_id"] for i in r.json()["oferta"]}

    # --- #362 ---
    def test_362_aseo_ve_pendientes_primero_y_completa_con_su_nombre(self):
        self.ensuciar("HAB-ASEO-2")
        habitaciones, cuerpo = self.vista()
        self.assertEqual(cuerpo["pendientes"], 1)
        self.assertEqual(next(iter(habitaciones)), "HAB-ASEO-2")
        self.assertTrue(habitaciones["HAB-ASEO-2"]["limpieza_pendiente"])
        r = self.limpiar("HAB-ASEO-2")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["estado_preparacion"], "limpia")
        habitaciones, cuerpo = self.vista()
        self.assertEqual(cuerpo["pendientes"], 0)
        self.assertEqual(habitaciones["HAB-ASEO-2"]["ultima_limpieza"]["completada_por"], "aseo1")
        self.assertIn("HAB-ASEO-2", cuerpo["por_verificar"])

    def test_362_vista_aseo_sin_datos_del_huesped_ni_precios(self):
        r = self.admin.post("/hotel/reservas", json={
            "habitacion_id": "HAB-ASEO-1", "inicio": str(HOY), "fin": str(HOY + timedelta(days=2)),
            "huesped": {"nombre": "Nombre Privado", "documento": "11.111.111-1"}}, headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        texto = self.aseo.get("/hotel/aseo").text
        self.assertNotIn("Nombre Privado", texto)
        self.assertNotIn("11.111.111-1", texto)
        self.assertNotIn("clp", texto)
        habitaciones, _ = self.vista()
        self.assertEqual(habitaciones["HAB-ASEO-1"]["situacion"], "llega_hoy")

    def test_362_rol_aseo_no_alcanza_otras_operaciones(self):
        for metodo, ruta in (("get", "/hotel/reservas"), ("get", "/hotel/caja"), ("get", "/hotel/oferta"),
                             ("get", "/hotel/indicadores"), ("get", "/hotel/habitaciones"), ("get", "/usuarios")):
            with self.subTest(ruta=ruta):
                self.assertEqual(getattr(self.aseo, metodo)(ruta).status_code, 403)
        self.assertEqual(self.aseo.get("/sesion").status_code, 200)
        self.assertEqual(self.aseo.post("/hotel/limpiezas/TSK-x/verificacion", json={"aprobada": True},
                                        headers=self.idem()).status_code, 403)

    # --- #363 ---
    def tarea_completada(self, hid="HAB-ASEO-1"):
        self.ensuciar(hid)
        self.assertEqual(self.limpiar(hid).status_code, 200)
        habitaciones, _ = self.vista(self.admin)
        return habitaciones[hid]["ultima_limpieza"]["tarea_id"]

    def verificar(self, tarea_id, aprobada, observacion=None):
        return self.admin.post(f"/hotel/limpiezas/{tarea_id}/verificacion",
                               json={"aprobada": aprobada, "observacion": observacion}, headers=self.idem())

    def test_363_verificar_deja_inspeccionada_y_no_dos_veces(self):
        tarea = self.tarea_completada()
        r = self.verificar(tarea, True)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["estado_preparacion"], "inspeccionada")
        self.assertEqual(self.verificar(tarea, True).status_code, 409)
        _, cuerpo = self.vista(self.admin)
        self.assertNotIn("HAB-ASEO-1", cuerpo["por_verificar"])

    def test_363_rechazar_exige_observacion_y_devuelve_a_aseo(self):
        tarea = self.tarea_completada()
        self.assertEqual(self.verificar(tarea, False).status_code, 409)
        r = self.verificar(tarea, False, "falta cambiar toallas")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["estado_preparacion"], "sucia")
        habitaciones, cuerpo = self.vista()
        self.assertTrue(habitaciones["HAB-ASEO-1"]["limpieza_pendiente"])
        self.assertIn("falta cambiar toallas", habitaciones["HAB-ASEO-1"]["observaciones"][0]["texto"])
        self.assertEqual(cuerpo["pendientes"], 1)

    def test_363_observacion_para_aseo_y_atendida(self):
        r = self.admin.post("/hotel/habitaciones/HAB-ASEO-2/observaciones", json={"texto": "revisar cortina"},
                            headers=self.idem())
        self.assertEqual(r.status_code, 200, r.text)
        obs = r.json()["observacion_id"]
        habitaciones, _ = self.vista()
        self.assertEqual(habitaciones["HAB-ASEO-2"]["observaciones"][0]["texto"], "revisar cortina")
        # aseo no crea observaciones, pero sí las marca atendidas
        self.assertEqual(self.aseo.post("/hotel/habitaciones/HAB-ASEO-2/observaciones", json={"texto": "x y"},
                                        headers=self.idem()).status_code, 403)
        atendida = self.aseo.post(f"/hotel/habitaciones/HAB-ASEO-2/observaciones/{obs}/atendida", json={},
                                  headers=self.idem())
        self.assertEqual(atendida.status_code, 200, atendida.text)
        habitaciones, _ = self.vista()
        self.assertEqual(habitaciones["HAB-ASEO-2"]["observaciones"], [])
        self.assertEqual(self.aseo.post(f"/hotel/habitaciones/HAB-ASEO-2/observaciones/{obs}/atendida", json={},
                                        headers=self.idem()).status_code, 409)

    # --- #349 ---
    def mantenimiento(self, hid, **cuerpo):
        return self.admin.post(f"/hotel/habitaciones/{hid}/mantenimiento", json={"abierto": True, **cuerpo},
                               headers=self.idem())

    def test_349_mantenimiento_con_rango_solo_quita_cupo_en_el_rango(self):
        desde, hasta = HOY + timedelta(days=10), HOY + timedelta(days=12)
        self.assertEqual(self.mantenimiento("HAB-ASEO-1", desde=str(desde), hasta=str(hasta)).status_code, 200)
        self.assertNotIn("HAB-ASEO-1", self.oferta(desde, hasta))
        self.assertNotIn("HAB-ASEO-1", self.oferta(HOY + timedelta(days=11), HOY + timedelta(days=14)))
        self.assertIn("HAB-ASEO-1", self.oferta(HOY, HOY + timedelta(days=2)))
        self.assertIn("HAB-ASEO-1", self.oferta(hasta, hasta + timedelta(days=2)))

    def test_349_mantenimiento_sin_fechas_no_quita_cupo_futuro(self):
        self.assertEqual(self.mantenimiento("HAB-ASEO-1").status_code, 200)
        self.assertNotIn("HAB-ASEO-1", self.oferta(HOY, HOY + timedelta(days=1)))
        self.assertIn("HAB-ASEO-1", self.oferta(HOY + timedelta(days=1), HOY + timedelta(days=3)))

    def test_349_limpieza_pendiente_no_quita_cupo(self):
        self.ensuciar("HAB-ASEO-2")
        self.assertIn("HAB-ASEO-2", self.oferta(HOY, HOY + timedelta(days=2)))

    def test_349_rango_invalido_422(self):
        self.assertEqual(self.mantenimiento("HAB-ASEO-1", desde=str(HOY), hasta=str(HOY)).status_code, 422)
        self.assertEqual(self.mantenimiento("HAB-ASEO-1", hasta=str(HOY)).status_code, 422)


if __name__ == "__main__":
    unittest.main()
