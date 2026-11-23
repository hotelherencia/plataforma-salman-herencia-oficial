"""Pruebas de integración del Corte 1 operativo (#415, #416, #417) contra PostgreSQL real."""
import base64
import os
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient

from servicio import migracion, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()
# PNG mínimo válido de 1x1 px (firma mágica real)
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
JPG_MIN = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


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
                "TRUNCATE auditoria, incidencias, tarea_subtareas, tareas_operativas, "
                "observaciones_habitacion, reasignaciones, claves_idempotencia, liquidaciones, "
                "efectos_nucleo, pagos, cargos, solicitudes, reservas, tarifas, sesiones, usuarios, "
                "habitaciones, productos RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            for hid in ("HAB-OP-1", "HAB-OP-2"):
                conexion.execute(
                    "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                    "VALUES (%s, 'EST-SINT-001', 'doble', 2)",
                    (hid,),
                )
                conexion.execute(
                    "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                    "VALUES (%s, %s, '2026-01-01', '2027-12-31', 50000)",
                    (f"TAR-{hid}", hid),
                )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.admin = TestClient(self.app)
        self.assertEqual(self.admin.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)
        self.assertEqual(
            self.admin.post(
                "/usuarios", json={"nombre": "aseo1", "rol": "aseo", "clave": "clave-aseo-1"}, headers=self.idem()
            ).status_code,
            201,
        )
        self.aseo = TestClient(self.app)
        self.assertEqual(self.aseo.post("/sesion", json={"usuario": "aseo1", "clave": "clave-aseo-1"}).status_code, 200)

    def idem(self):
        return {"Idempotency-Key": f"c1-{uuid.uuid4().hex[:10]}"}

    def oferta_ids(self, inicio, fin):
        r = self.admin.get("/hotel/oferta", params={"inicio": str(inicio), "fin": str(fin), "personas": 1})
        self.assertEqual(r.status_code, 200, r.text)
        return {i["habitacion_id"] for i in r.json()["oferta"]}

    def test_migracion_0059_es_idempotente(self):
        sql = (
            Path(__file__).resolve().parents[1] / "migraciones" / "0059_corte1_incidencias_y_checklists.sql"
        ).read_text(encoding="utf-8")
        with psycopg.connect(URL_TEST) as conn:
            conn.execute(sql)
            conn.commit()
        migracion.aplicar_migraciones(URL_TEST)

    def test_415_incidencias_bloqueo_automatico_evidencia_movil_y_auditoria_sin_pii(self):
        # Antes de la incidencia, HAB-OP-1 aparece en la oferta de hoy
        self.assertIn("HAB-OP-1", self.oferta_ids(HOY, HOY + timedelta(days=2)))

        # Aseo reporta incidencia bloqueante con foto móvil PNG en base64
        b64 = "data:image/png;base64," + base64.b64encode(PNG_1X1).decode()
        r = self.aseo.post(
            "/hotel/incidencias",
            json={
                "habitacion_id": "HAB-OP-1",
                "titulo": "Fuga en llave de ducha",
                "descripcion": "Pierde agua de forma constante; huésped anterior avisó",
                "gravedad": "alta",
                "bloquea_disponibilidad": True,
                "plazo": str(HOY + timedelta(days=3)),
                "evidencia_base64": b64,
                "evidencia_nombre": "ducha.png",
            },
            headers=self.idem(),
        )
        self.assertEqual(r.status_code, 201, r.text)
        inc = r.json()
        inc_id = inc["incidencia_id"]
        self.assertTrue(inc["bloquea_disponibilidad"])
        self.assertTrue(inc["tiene_evidencia"])
        self.assertEqual(inc["evidencia_mime"], "image/png")

        # Bloqueo automático de disponibilidad activo
        self.assertNotIn("HAB-OP-1", self.oferta_ids(HOY, HOY + timedelta(days=2)))

        # Evidencia servida con cabeceras de seguridad
        ev = self.aseo.get(f"/hotel/incidencias/{inc_id}/evidencia")
        self.assertEqual(ev.status_code, 200)
        self.assertEqual(ev.headers["content-type"], "image/png")
        self.assertEqual(ev.headers["x-content-type-options"], "nosniff")
        self.assertEqual(ev.headers["content-security-policy"], "sandbox")
        self.assertEqual(ev.content, PNG_1X1)

        # Rechaza evidencia maliciosa (no imagen)
        bad = self.aseo.post(
            f"/hotel/incidencias/{inc_id}/evidencia",
            content=b"<script>alert(1)</script>",
            headers={"content-type": "image/png"},
        )
        self.assertEqual(bad.status_code, 422)

        # Reemplazo binario válido (JPG)
        ok_jpg = self.aseo.post(
            f"/hotel/incidencias/{inc_id}/evidencia",
            content=JPG_MIN,
            headers={"content-type": "image/jpeg", "x-nombre-archivo": "reparacion.jpg"},
        )
        self.assertEqual(ok_jpg.status_code, 200, ok_jpg.text)
        self.assertEqual(ok_jpg.json()["evidencia_mime"], "image/jpeg")

        # Segunda incidencia bloqueante en la misma habitación: cerrar la primera NO libera todavía
        r2 = self.admin.post(
            "/hotel/incidencias",
            json={
                "habitacion_id": "HAB-OP-1",
                "titulo": "Aire acondicionado sin enfriar",
                "descripcion": "Compresor detenido",
                "gravedad": "critica",
                "bloquea_disponibilidad": True,
            },
            headers=self.idem(),
        )
        self.assertEqual(r2.status_code, 201, r2.text)
        inc2_id = r2.json()["incidencia_id"]

        # Actualizar costo y responsable en la primera
        upd = self.admin.put(
            f"/hotel/incidencias/{inc_id}",
            json={"estado": "en_progreso", "responsable": "gasfiter", "costo_clp": 35000},
            headers=self.idem(),
        )
        self.assertEqual(upd.status_code, 200, upd.text)
        self.assertEqual(upd.json()["costo_clp"], 35000)

        # Cerrar primera incidencia -> sigue bloqueada por inc2
        c1 = self.admin.post(
            f"/hotel/incidencias/{inc_id}/cierre",
            json={"resolucion": "Llave cambiada", "costo_clp": 35000},
            headers=self.idem(),
        )
        self.assertEqual(c1.status_code, 200, c1.text)
        self.assertNotIn("HAB-OP-1", self.oferta_ids(HOY, HOY + timedelta(days=2)))

        # Cerrar segunda incidencia -> habitación vuelve a oferta
        c2 = self.admin.post(
            f"/hotel/incidencias/{inc2_id}/cierre",
            json={"resolucion": "Carga de gas realizada"},
            headers=self.idem(),
        )
        self.assertEqual(c2.status_code, 200, c2.text)
        self.assertIn("HAB-OP-1", self.oferta_ids(HOY, HOY + timedelta(days=2)))

        # Auditoría sin PII ni texto libre de descripción
        with psycopg.connect(URL_TEST) as conn:
            auds = conn.execute(
                "SELECT accion, resultado FROM auditoria WHERE recurso = %s ORDER BY id", (inc_id,)
            ).fetchall()
        acciones = [a[0] for a in auds]
        self.assertIn("incidencia_creada", acciones)
        self.assertIn("incidencia_actualizada", acciones)
        self.assertIn("incidencia_cerrada", acciones)
        for _, res in auds:
            self.assertNotIn("huésped anterior", res)

    def test_416_estado_en_limpieza_checklists_obligatorios_y_tareas_generales(self):
        # Ensuciar HAB-OP-2 y abrir limpieza pendiente
        with psycopg.connect(URL_TEST) as conn:
            conn.execute("UPDATE habitaciones SET estado_preparacion = 'sucia' WHERE id = 'HAB-OP-2'")
            conn.execute(
                "INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado) "
                "VALUES ('TSK-LIMP-1', 'HAB-OP-2', 'limpieza', 'pendiente')"
            )
            conn.commit()

        # Iniciar limpieza -> pasa a en_limpieza y carga subtareas de plantilla
        ini = self.aseo.post(
            "/hotel/habitaciones/HAB-OP-2/limpieza/iniciar",
            json={"aplicar_plantilla": True},
            headers=self.idem(),
        )
        self.assertEqual(ini.status_code, 200, ini.text)
        datos_ini = ini.json()
        self.assertEqual(datos_ini["estado_preparacion"], "en_limpieza")
        self.assertEqual(datos_ini["estado"], "en_proceso")
        self.assertGreaterEqual(len(datos_ini["subtareas"]), 4)
        self.assertGreater(datos_ini["obligatorias_pendientes"], 0)

        # /hotel/aseo muestra estado en_limpieza y subtareas
        vista = self.aseo.get("/hotel/aseo").json()
        hab2 = next(h for h in vista["habitaciones"] if h["habitacion_id"] == "HAB-OP-2")
        self.assertEqual(hab2["estado_preparacion"], "en_limpieza")
        self.assertTrue(hab2["limpieza_en_curso"])
        self.assertEqual(len(hab2["subtareas"]), len(datos_ini["subtareas"]))

        # Intentar cerrar limpieza con obligatorias pendientes -> 409
        bloqueo = self.aseo.post("/hotel/habitaciones/HAB-OP-2/limpieza", json={}, headers=self.idem())
        self.assertEqual(bloqueo.status_code, 409, bloqueo.text)

        # Marcar todas las obligatorias (dejar la opcional sin marcar)
        for sub in datos_ini["subtareas"]:
            if sub["obligatoria"]:
                m = self.aseo.post(
                    f"/hotel/tareas/{datos_ini['tarea_id']}/subtareas/{sub['subtarea_id']}",
                    json={"completada": True},
                    headers=self.idem(),
                )
                self.assertEqual(m.status_code, 200, m.text)

        # Ahora cerrar limpieza -> 200 y habitación limpia
        ok = self.aseo.post("/hotel/habitaciones/HAB-OP-2/limpieza", json={}, headers=self.idem())
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(ok.json()["estado_preparacion"], "limpia")

        # Tarea general de área común (baños) con subtarea adicional
        t_resp = self.admin.post(
            "/hotel/tareas",
            json={
                "tipo": "banos",
                "area": "banos_comunes",
                "titulo": "Revisión baños recepción",
                "prioridad": "alta",
                "responsable": "aseo1",
                "aplicar_plantilla": True,
            },
            headers=self.idem(),
        )
        self.assertEqual(t_resp.status_code, 201, t_resp.text)
        tid = t_resp.json()["tarea_id"]

        # Agregar subtarea obligatoria extra
        s_extra = self.admin.post(
            f"/hotel/tareas/{tid}/subtareas",
            json={"descripcion": "Revisar dispensador de alcohol gel", "obligatoria": True},
            headers=self.idem(),
        )
        self.assertEqual(s_extra.status_code, 201, s_extra.text)
        subs = s_extra.json()["subtareas"]

        # No puede cerrarse antes de marcar las obligatorias
        fail_close = self.aseo.put(
            f"/hotel/tareas/{tid}", json={"estado": "completada"}, headers=self.idem()
        )
        self.assertEqual(fail_close.status_code, 409)

        for sub in subs:
            self.assertEqual(
                self.aseo.post(
                    f"/hotel/tareas/{tid}/subtareas/{sub['subtarea_id']}",
                    json={"completada": True},
                    headers=self.idem(),
                ).status_code,
                200,
            )

        closed = self.aseo.put(
            f"/hotel/tareas/{tid}", json={"estado": "completada"}, headers=self.idem()
        )
        self.assertEqual(closed.status_code, 200, closed.text)
        self.assertEqual(closed.json()["estado"], "completada")

    def test_417_panel_indicadores_devuelve_lo_que_necesita_atencion(self):
        # 1. Llegada atrasada + 2. Salida atrasada + 3. Limpieza por verificar + 4. Producto bajo mínimo
        with psycopg.connect(URL_TEST) as conn:
            conn.execute(
                "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, "
                "tarifa_noche_aceptada_clp, estado) VALUES "
                "('RSV-ATRASO-LLEG', %s, 'HAB-OP-1', %s, %s, 'Marta Atrasada', 50000, 'confirmada'), "
                "('RSV-ATRASO-SAL', %s, 'HAB-OP-2', %s, %s, 'Pedro Salida', 50000, 'en_estadia')",
                (
                    EMPRESA, HOY - timedelta(days=2), HOY + timedelta(days=1),
                    EMPRESA, HOY - timedelta(days=3), HOY - timedelta(days=1),
                ),
            )
            conn.execute(
                "INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado, completada_en, completada_por) "
                "VALUES ('TSK-POR-VERIF', 'HAB-OP-1', 'limpieza', 'completada', now(), 'aseo1')"
            )
            conn.execute(
                "INSERT INTO productos (id, nombre, categoria, precio_clp, controla_stock, stock, stock_minimo, activo) "
                "VALUES ('PRD-BAJO-1', 'Café grano', 'cafeteria', 3000, true, 1, 5, true)"
            )
            conn.commit()

        # 5. Incidencia abierta bloqueante
        r_inc = self.admin.post(
            "/hotel/incidencias",
            json={
                "habitacion_id": "HAB-OP-2",
                "titulo": "Cerradura trabada",
                "descripcion": "No abre con tarjeta",
                "gravedad": "critica",
                "bloquea_disponibilidad": True,
            },
            headers=self.idem(),
        )
        self.assertEqual(r_inc.status_code, 201, r_inc.text)

        ind = self.admin.get("/hotel/indicadores")
        self.assertEqual(ind.status_code, 200, ind.text)
        atencion = ind.json()["atencion"]
        self.assertEqual(atencion["total"], 5)
        self.assertEqual(atencion["llegadas_atrasadas"][0]["reserva_id"], "RSV-ATRASO-LLEG")
        self.assertEqual(atencion["llegadas_atrasadas"][0]["enlace"], "/hotel/reservas/RSV-ATRASO-LLEG")
        self.assertEqual(atencion["salidas_atrasadas"][0]["reserva_id"], "RSV-ATRASO-SAL")
        self.assertEqual(atencion["salidas_atrasadas"][0]["enlace"], "/hotel/reservas/RSV-ATRASO-SAL")
        self.assertEqual(atencion["limpiezas_por_verificar"][0]["habitacion_id"], "HAB-OP-1")
        self.assertEqual(atencion["limpiezas_por_verificar"][0]["enlace"], "/hotel/aseo")
        self.assertEqual(atencion["incidencias_abiertas"][0]["habitacion_id"], "HAB-OP-2")
        self.assertTrue(atencion["incidencias_abiertas"][0]["bloquea_disponibilidad"])
        self.assertEqual(atencion["incidencias_abiertas"][0]["enlace"], "/hotel/habitaciones/HAB-OP-2")
        self.assertEqual(atencion["productos_bajo_stock"][0]["producto_id"], "PRD-BAJO-1")
        self.assertEqual(atencion["productos_bajo_stock"][0]["enlace"], "/hotel/productos")


if __name__ == "__main__":
    unittest.main()
