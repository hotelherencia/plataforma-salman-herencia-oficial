"""Corte 1 operativo (#415 incidencias, #416 tareas y checklists, #417 atención).
HTTP contra PostgreSQL real, datos sintéticos.
"""
import base64
import json
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


class Corte1OperativoTest(unittest.TestCase):
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
                "TRUNCATE auditoria, incidencia_evidencias, incidencias, tarea_subtareas, tareas_generales, checklist_plantillas, tareas_operativas, observaciones_habitacion, reasignaciones, "
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

    def incidencia(self, cliente=None, **extra):
        cuerpo = {"habitacion_id": "HAB-ASEO-1", "descripcion": "Llave del lavamanos gotea", "gravedad": "media", **extra}
        return (cliente or self.aseo).post("/hotel/incidencias", json=cuerpo, headers=self.idem())

    def mantenimiento(self, hid):
        with psycopg.connect(URL_TEST) as c:
            return c.execute("SELECT mantenimiento FROM habitaciones WHERE id = %s", (hid,)).fetchone()[0]

    # --- #415 ---
    def test_415_incidencia_sin_bloqueo_no_toca_disponibilidad(self):
        r = self.incidencia()
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["estado"], "abierta")
        self.assertFalse(self.mantenimiento("HAB-ASEO-1"))
        self.assertIn("HAB-ASEO-1", self.oferta(HOY + timedelta(days=1), HOY + timedelta(days=2)))

    def test_415_bloqueo_saca_la_unidad_del_cupo_y_el_cierre_la_devuelve(self):
        plazo = HOY + timedelta(days=3)
        r = self.incidencia(bloquea_disponibilidad=True, plazo=str(plazo), gravedad="alta")
        self.assertEqual(r.status_code, 200, r.text)
        iid = r.json()["incidencia_id"]
        self.assertTrue(r.json()["bloqueo_activo"])
        self.assertTrue(self.mantenimiento("HAB-ASEO-1"))
        self.assertNotIn("HAB-ASEO-1", self.oferta(HOY + timedelta(days=1), HOY + timedelta(days=2)))
        self.assertIn("HAB-ASEO-1", self.oferta(HOY + timedelta(days=5), HOY + timedelta(days=6)))
        # aseo no puede cerrar; recepción/admin sí
        self.assertEqual(self.aseo.post(f"/hotel/incidencias/{iid}/cierre", json={}, headers=self.idem()).status_code, 403)
        r = self.admin.post(f"/hotel/incidencias/{iid}/cierre", json={"costo_clp": 12000, "nota": "cambio de flexible"},
                            headers=self.idem())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["unidad_liberada"])
        self.assertEqual(r.json()["costo_clp"], 12000)
        self.assertFalse(self.mantenimiento("HAB-ASEO-1"))
        self.assertIn("HAB-ASEO-1", self.oferta(HOY + timedelta(days=1), HOY + timedelta(days=2)))
        acciones = [e["accion"] for e in r.json()["eventos"]]
        self.assertEqual(acciones, ["creada", "bloqueo", "cierre"])
        self.assertEqual(self.admin.post(f"/hotel/incidencias/{iid}/cierre", json={}, headers=self.idem()).status_code, 409)

    def test_415_resolver_libera_solo_si_no_queda_otro_bloqueo(self):
        a = self.incidencia(bloquea_disponibilidad=True).json()["incidencia_id"]
        b = self.incidencia(bloquea_disponibilidad=True, descripcion="Cerradura trabada").json()
        self.assertFalse(b["bloqueo_activo"], "la segunda ve la unidad ya en mantenimiento")
        r = self.admin.post(f"/hotel/incidencias/{a}/actualizacion", json={"estado": "resuelta"}, headers=self.idem())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertFalse(self.mantenimiento("HAB-ASEO-1"))

    def test_415_respeta_mantenimiento_manual_previo(self):
        r = self.admin.post("/hotel/habitaciones/HAB-ASEO-2/mantenimiento", json={"abierto": True}, headers=self.idem())
        self.assertEqual(r.status_code, 200, r.text)
        iid = self.incidencia(habitacion_id="HAB-ASEO-2", bloquea_disponibilidad=True).json()["incidencia_id"]
        self.admin.post(f"/hotel/incidencias/{iid}/cierre", json={}, headers=self.idem())
        self.assertTrue(self.mantenimiento("HAB-ASEO-2"), "el mantenimiento manual no lo cierra una incidencia")

    def test_415_validaciones_y_evidencia(self):
        self.assertEqual(self.incidencia(habitacion_id=None).status_code, 422)
        self.assertEqual(self.incidencia(habitacion_id=None, area="recepcion", bloquea_disponibilidad=True).status_code, 422)
        self.assertEqual(self.incidencia(habitacion_id="HAB-NO-EXISTE").status_code, 404)
        iid = self.incidencia().json()["incidencia_id"]
        foto = base64.b64encode(b"\xff\xd8\xff\xe0fotoliviana").decode()
        r = self.aseo.post(f"/hotel/incidencias/{iid}/evidencias", json={"mime": "image/jpeg", "contenido_base64": foto},
                           headers=self.idem())
        self.assertEqual(r.status_code, 200, r.text)
        r2 = self.aseo.get(f"/hotel/incidencias/{iid}/evidencias/{r.json()['evidencia_id']}")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.headers["content-type"], "image/jpeg")
        self.assertTrue(r2.content.endswith(b"fotoliviana"))
        mediana = base64.b64encode(b"\xff\xd8" + b"y" * 170_000).decode()
        self.assertEqual(self.aseo.post(f"/hotel/incidencias/{iid}/evidencias", json={"mime": "image/jpeg", "contenido_base64": mediana},
                                        headers=self.idem()).status_code, 200)
        grande = base64.b64encode(b"x" * 700_000).decode()
        self.assertIn(self.aseo.post(f"/hotel/incidencias/{iid}/evidencias", json={"mime": "image/png", "contenido_base64": grande},
                                        headers=self.idem()).status_code, (413, 422))
        self.assertEqual(self.aseo.post(f"/hotel/incidencias/{iid}/evidencias", json={"mime": "image/gif", "contenido_base64": foto},
                                        headers=self.idem()).status_code, 422)
        self.assertEqual(self.aseo.get(f"/hotel/incidencias/{iid}").json()["evidencias"], 2)

    def test_415_bitacora_append_only_y_auditoria_sin_texto_libre(self):
        iid = self.incidencia(descripcion="Texto con dato sensible").json()["incidencia_id"]
        with psycopg.connect(URL_TEST) as c:
            with self.assertRaises(psycopg.errors.RaiseException):
                c.execute("DELETE FROM incidencia_eventos WHERE incidencia_id = %s", (iid,))
            c.rollback()
            filas = c.execute("SELECT accion, recurso, resultado FROM auditoria WHERE accion = 'incidencia_creada'").fetchall()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0][1], iid)
        self.assertNotIn("sensible", " ".join(map(str, filas[0])))

    def test_415_idempotencia_no_duplica(self):
        h = self.idem()
        cuerpo = {"habitacion_id": "HAB-ASEO-1", "descripcion": "Ventana no cierra", "gravedad": "baja"}
        a = self.aseo.post("/hotel/incidencias", json=cuerpo, headers=h)
        b = self.aseo.post("/hotel/incidencias", json=cuerpo, headers=h)
        self.assertEqual(a.json()["incidencia_id"], b.json()["incidencia_id"])
        self.assertEqual(len(self.aseo.get("/hotel/incidencias").json()["items"]), 1)

    # --- #416 ---
    def test_416_checklist_no_cierra_sin_obligatorias(self):
        r = self.admin.post("/hotel/tareas", json={
            "titulo": "Baños de recepción", "area": "banos", "prioridad": "alta", "vence": str(HOY),
            "subtareas": [{"texto": "Desinfectar WC"}, {"texto": "Reponer papel"}, {"texto": "Aromatizar", "obligatoria": False}],
        }, headers=self.idem())
        self.assertEqual(r.status_code, 200, r.text)
        tid, subs = r.json()["tarea_id"], r.json()["subtareas"]
        self.assertEqual(r.json()["obligatorias_pendientes"], 2)
        self.assertEqual(self.aseo.post(f"/hotel/tareas/{tid}/cierre", headers=self.idem()).status_code, 409)
        for s in subs[:2]:
            m = self.aseo.post(f"/hotel/tareas/{tid}/subtareas/{s['subtarea_id']}/marcado", json={"hecha": True}, headers=self.idem())
            self.assertEqual(m.status_code, 200, m.text)
        self.assertEqual(m.json()["hecha"] if "hecha" in m.json() else m.json()["obligatorias_pendientes"], 0)
        c = self.aseo.post(f"/hotel/tareas/{tid}/cierre", headers=self.idem())
        self.assertEqual(c.status_code, 200, c.text)
        self.assertEqual(c.json()["estado"], "completada")
        self.assertEqual(c.json()["completada_por"], "aseo1")
        self.assertEqual(self.aseo.post(f"/hotel/tareas/{tid}/cierre", headers=self.idem()).status_code, 409)

    def test_416_plantillas_solo_admin_y_crean_subtareas(self):
        cuerpo = {"nombre": "Desayuno", "area": "desayunos", "items": [{"texto": "Armar buffet"}, {"texto": "Café", "obligatoria": False}]}
        self.assertEqual(self.aseo.post("/hotel/checklists/plantillas", json=cuerpo, headers=self.idem()).status_code, 403)
        p = self.admin.post("/hotel/checklists/plantillas", json=cuerpo, headers=self.idem())
        self.assertEqual(p.status_code, 200, p.text)
        self.assertEqual(self.admin.post("/hotel/checklists/plantillas", json=cuerpo, headers=self.idem()).status_code, 409)
        t = self.admin.post("/hotel/tareas", json={"titulo": "Desayuno lunes", "area": "desayunos",
                                                    "plantilla_id": p.json()["plantilla_id"]}, headers=self.idem())
        self.assertEqual([s["texto"] for s in t.json()["subtareas"]], ["Armar buffet", "Café"])
        self.assertEqual(self.aseo.get("/hotel/checklists/plantillas").status_code, 200)
        self.assertEqual(self.aseo.post("/hotel/tareas", json={"titulo": "No debería"}, headers=self.idem()).status_code, 403)

    def test_416_en_limpieza_solo_desde_sucia_y_se_apaga_al_limpiar(self):
        self.assertEqual(self.aseo.post("/hotel/habitaciones/HAB-ASEO-1/en-limpieza", headers=self.idem()).status_code, 409)
        self.ensuciar("HAB-ASEO-1")
        r = self.aseo.post("/hotel/habitaciones/HAB-ASEO-1/en-limpieza", headers=self.idem())
        self.assertEqual(r.status_code, 200, r.text)
        habitaciones, _ = self.vista()
        self.assertTrue(habitaciones["HAB-ASEO-1"]["en_limpieza"])
        self.assertEqual(habitaciones["HAB-ASEO-1"]["en_limpieza_por"], "aseo1")
        # una operación del dominio (reserva) no pierde el estado
        self.assertEqual(self.admin.get("/hotel/indicadores").status_code, 200)
        habitaciones, _ = self.vista()
        self.assertTrue(habitaciones["HAB-ASEO-1"]["en_limpieza"])
        self.assertEqual(self.limpiar("HAB-ASEO-1").status_code, 200)
        habitaciones, _ = self.vista()
        self.assertFalse(habitaciones["HAB-ASEO-1"]["en_limpieza"])
        self.assertEqual(habitaciones["HAB-ASEO-1"]["estado_preparacion"], "limpia")

    # --- #426 ---
    def test_426_editar_tarea_y_agregar_subtareas(self):
        t = self.admin.post("/hotel/tareas", json={"titulo": "Lavandería", "area": "lavanderia",
                                                    "subtareas": [{"texto": "Lavar sábanas"}]}, headers=self.idem()).json()
        tid = t["tarea_id"]
        r = self.admin.post(f"/hotel/tareas/{tid}/actualizacion",
                            json={"prioridad": "urgente", "responsable": "turno tarde", "vence": str(HOY)}, headers=self.idem())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["prioridad"], r.json()["responsable"]), ("urgente", "turno tarde"))
        self.assertEqual(self.admin.post(f"/hotel/tareas/{tid}/actualizacion", json={}, headers=self.idem()).status_code, 409)
        a = self.admin.post(f"/hotel/tareas/{tid}/subtareas", json={"texto": "Doblar toallas"}, headers=self.idem())
        self.assertEqual(a.status_code, 200, a.text)
        self.assertEqual([s["texto"] for s in a.json()["subtareas"]], ["Lavar sábanas", "Doblar toallas"])
        self.assertEqual(a.json()["obligatorias_pendientes"], 2)
        self.assertEqual(self.aseo.post(f"/hotel/tareas/{tid}/subtareas", json={"texto": "No debería"}, headers=self.idem()).status_code, 403)
        for sub in a.json()["subtareas"]:
            self.admin.post(f"/hotel/tareas/{tid}/subtareas/{sub['subtarea_id']}/marcado", json={"hecha": True}, headers=self.idem())
        self.assertEqual(self.admin.post(f"/hotel/tareas/{tid}/cierre", headers=self.idem()).status_code, 200)
        self.assertEqual(self.admin.post(f"/hotel/tareas/{tid}/subtareas", json={"texto": "Tarde"}, headers=self.idem()).status_code, 409)
        self.assertEqual(self.admin.post(f"/hotel/tareas/{tid}/actualizacion", json={"titulo": "Otra"}, headers=self.idem()).status_code, 409)

    def test_426_indicador_habitaciones_en_limpieza(self):
        self.ensuciar("HAB-ASEO-1")
        self.ensuciar("HAB-ASEO-2")
        hoy = self.admin.get("/hotel/indicadores").json()["hoy"]
        self.assertEqual(hoy["habitaciones_en_limpieza"]["valor"], 0)
        self.aseo.post("/hotel/habitaciones/HAB-ASEO-1/en-limpieza", headers=self.idem())
        hoy = self.admin.get("/hotel/indicadores").json()["hoy"]
        self.assertEqual(hoy["habitaciones_en_limpieza"]["valor"], 1)
        self.assertEqual(hoy["habitaciones_sucias"]["valor"], 2)
        self.limpiar("HAB-ASEO-1")
        self.assertEqual(self.admin.get("/hotel/indicadores").json()["hoy"]["habitaciones_en_limpieza"]["valor"], 0)

    # --- #417 ---
    def test_417_atencion_cruza_areas_con_enlaces(self):
        ayer = HOY - timedelta(days=1)
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, estado, personas, "
                "tarifa_noche_aceptada_clp) VALUES ('RSV-ATR-1', %s, 'HAB-ASEO-2', %s, %s, 'Huesped Privado', "
                "'confirmada', 1, 40000)",
                (EMPRESA, ayer, HOY + timedelta(days=1)),
            )
            c.commit()
        self.ensuciar("HAB-ASEO-1")
        self.limpiar("HAB-ASEO-1")
        self.incidencia(bloquea_disponibilidad=True, gravedad="critica")
        r = self.admin.get("/hotel/indicadores")
        self.assertEqual(r.status_code, 200, r.text)
        a = r.json()["atencion"]
        self.assertEqual([x["id"] for x in a["llegadas_atrasadas"]], ["RSV-ATR-1"])
        self.assertEqual(a["llegadas_atrasadas"][0]["enlace"], "/hotel/reservas/RSV-ATR-1")
        self.assertEqual([x["habitacion_id"] for x in a["limpiezas_por_verificar"]], ["HAB-ASEO-1"])
        self.assertEqual(a["incidencias_abiertas"][0]["gravedad"], "critica")
        self.assertTrue(a["incidencias_abiertas"][0]["bloquea"])
        self.assertEqual(a["bloqueos_por_incidencia"], 1)
        self.assertIsInstance(a["productos_bajo_minimo"], list)
        self.assertGreaterEqual(a["total"], 3)
        self.assertNotIn("Privado", json.dumps(a), "la atención no expone nombres de huéspedes")


if __name__ == "__main__":
    unittest.main()
