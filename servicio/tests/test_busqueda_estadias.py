"""Búsqueda única de estadías (2026-11-19): Salida, Caja y Llegada buscan
por nombre, habitación, documento o código. Permisos por pantalla, texto
mínimo, tope de resultados, sin fuga del documento a caja y solo reservas
de la empresa. HTTP contra PostgreSQL real, datos sintéticos.
"""
import os
import unittest
import uuid
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import busqueda_estadias, seguridad
from servicio.tests.aislamiento import exigir_base_libre
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()
D = lambda n: HOY + timedelta(days=n)

# (id, habitación, inicio, fin, huésped, documento, estado, cargos, pagado)
RESERVAS = [
    ("RSV-SAL-HOY", "HAB-101", D(-2), HOY, "José Pérez Soto", "11.111.111-1", "en_estadia", 100000, 100000),
    ("RSV-SAL-ATR", "HAB-102", D(-3), D(-1), "Ana Muñoz", "22.222.222-2", "en_estadia", 60000, 20000),
    ("RSV-SAL-MAN", "HAB-103", D(-1), D(2), "Pedro Pérez Lagos", "12.345.678-5", "en_estadia", 90000, 0),
    ("RSV-LLE-HOY", "HAB-104", HOY, D(2), "Lucía Pérez", "P1234567", "confirmada", 80000, 0),
    ("RSV-LLE-FUT", "HAB-105", D(10), D(12), "Carla Pérez", None, "confirmada", 80000, 0),
    ("RSV-FIN-OLD", "HAB-106", D(-9), D(-7), "Pérez Finalizado", None, "finalizada", 50000, 50000),
    ("RSV-OTRA-EMP", "HAB-107", D(-1), D(1), "Pérez Ajeno", None, "en_estadia", 10000, 0),
]


class BusquedaEstadiasTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            exigir_base_libre(c)
            c.execute(
                "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
                "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(c, EMPRESA, ADMIN[0], ADMIN[1])
            for rid, hab, ini, fin, nombre, doc, estado, cargos, pagado in RESERVAS:
                c.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES (%s, 'EST-SINT-001', 'doble', 2)",
                          (hab,))
                c.execute(
                    "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, "
                    "tarifa_noche_aceptada_clp, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, 40000, %s)",
                    (rid, "EMP-OTRA" if rid == "RSV-OTRA-EMP" else EMPRESA, hab, ini, fin, nombre, doc, estado),
                )
                c.execute("INSERT INTO cargos (id, reserva_id, concepto, monto_clp) VALUES (%s, %s, 'alojamiento', %s)",
                          (f"CRG-{rid}", rid, cargos))
                if pagado:
                    c.execute("INSERT INTO pagos (id, reserva_id, monto_clp, clave, modo) VALUES (%s, %s, %s, 'k', 'manual')",
                              (f"PAG-{rid}", rid, pagado))
            c.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.admin = TestClient(self.app)
        self.assertEqual(self.admin.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)
        self.cli = {"admin": self.admin}
        for nombre, rol in (("recep1", "recepcion"), ("caja1", "caja"), ("aseo1", "aseo")):
            r = self.admin.post("/usuarios", json={"nombre": nombre, "rol": rol, "clave": f"clave-{nombre}-1"},
                                headers={"Idempotency-Key": uuid.uuid4().hex})
            self.assertEqual(r.status_code, 201, r.text)
            cliente = TestClient(self.app)
            self.assertEqual(cliente.post("/sesion", json={"usuario": nombre, "clave": f"clave-{nombre}-1"}).status_code, 200)
            self.cli[rol] = cliente

    def buscar(self, q=None, alcance="salida", rol="recepcion"):
        params = {"alcance": alcance}
        if q is not None:
            params["q"] = q
        return self.cli[rol].get("/hotel/estadias/busqueda", params=params)

    def ids(self, r):
        self.assertEqual(r.status_code, 200, r.text)
        return [x["reserva_id"] for x in r.json()["resultados"]]

    def test_salida_sin_texto_lista_las_salidas_de_hoy_y_atrasadas(self):
        r = self.buscar()
        self.assertEqual(self.ids(r), ["RSV-SAL-ATR", "RSV-SAL-HOY"])
        datos = r.json()
        self.assertTrue(datos["lista_del_dia"])
        hoy = next(x for x in datos["resultados"] if x["reserva_id"] == "RSV-SAL-HOY")
        self.assertTrue(hoy["sale_hoy"])
        self.assertEqual(hoy["cuenta"]["saldo_clp"], 0)
        atrasada = datos["resultados"][0]
        self.assertTrue(atrasada["salida_atrasada"])
        self.assertEqual(atrasada["cuenta"]["saldo_clp"], 40000)

    def test_salida_por_nombre_sin_tildes_y_con_varias_palabras(self):
        self.assertEqual(self.ids(self.buscar("perez")), ["RSV-SAL-HOY", "RSV-SAL-MAN"])  # sale hoy primero
        self.assertEqual(self.ids(self.buscar("jose perez")), ["RSV-SAL-HOY"])
        self.assertEqual(self.ids(self.buscar("MUÑOZ")), ["RSV-SAL-ATR"])

    def test_salida_por_habitacion_documento_y_codigo(self):
        self.assertEqual(self.ids(self.buscar("103")), ["RSV-SAL-MAN"])
        self.assertEqual(self.ids(self.buscar("hab-101")), ["RSV-SAL-HOY"])
        self.assertEqual(self.ids(self.buscar("12345678")), ["RSV-SAL-MAN"])
        self.assertEqual(self.ids(self.buscar("1234")), ["RSV-SAL-MAN"])  # prefijo para recepción
        self.assertEqual(self.ids(self.buscar("sal-atr")), ["RSV-SAL-ATR"])

    def test_solo_estadias_en_curso_y_de_la_empresa(self):
        encontrados = self.ids(self.buscar("perez"))
        for ajena in ("RSV-LLE-HOY", "RSV-FIN-OLD", "RSV-OTRA-EMP"):
            self.assertNotIn(ajena, encontrados)
        self.assertEqual(self.ids(self.buscar("107")), [])

    def test_llegada_y_pago_tienen_su_propio_alcance(self):
        self.assertEqual(self.ids(self.buscar(alcance="llegada")), ["RSV-LLE-HOY"])
        self.assertEqual(self.ids(self.buscar("perez", alcance="llegada")), ["RSV-LLE-HOY", "RSV-LLE-FUT"])
        # Pago sin texto: estadías en curso con saldo pendiente.
        self.assertEqual(self.ids(self.buscar(alcance="pago", rol="caja")), ["RSV-SAL-ATR", "RSV-SAL-MAN"])
        con_texto = self.ids(self.buscar("perez", alcance="pago", rol="caja"))
        self.assertEqual(con_texto[:2], ["RSV-SAL-MAN", "RSV-SAL-HOY"])  # en casa y con saldo primero
        self.assertIn("RSV-LLE-HOY", con_texto)
        self.assertNotIn("RSV-FIN-OLD", con_texto)

    def test_caja_no_recibe_ni_enumera_documentos(self):
        r = self.buscar("perez", alcance="pago", rol="caja")
        self.assertTrue(all("huesped_documento" not in x for x in r.json()["resultados"]))
        self.assertEqual(self.ids(self.buscar("1234", alcance="pago", rol="caja")), [])  # sin prefijo
        self.assertEqual(self.ids(self.buscar("12.345.678-5", alcance="pago", rol="caja")), ["RSV-SAL-MAN"])  # completo sí
        recep = self.buscar("perez", alcance="pago")
        self.assertTrue(any(x.get("huesped_documento") for x in recep.json()["resultados"]))

    def test_permisos_por_pantalla(self):
        self.assertEqual(self.buscar(rol="caja").status_code, 403)  # Salida: recepción o administración
        self.assertEqual(self.buscar(alcance="llegada", rol="caja").status_code, 403)
        self.assertEqual(self.buscar(alcance="pago", rol="aseo").status_code, 403)
        self.assertEqual(self.buscar(rol="admin").status_code, 200)
        self.assertEqual(TestClient(self.app).get("/hotel/estadias/busqueda").status_code, 401)
        self.assertEqual(self.cli["recepcion"].get("/hotel/estadias/busqueda", params={"alcance": "todo"}).status_code, 422)

    def test_texto_minimo_y_tope(self):
        r = self.buscar("p")
        self.assertEqual(r.status_code, 422)
        self.assertIn("al menos 2", r.json()["detail"])
        self.assertEqual(self.buscar("1").status_code, 200)  # un número de habitación sí
        self.assertEqual(self.cli["recepcion"].get("/hotel/estadias/busqueda", params={"q": "x" * 81}).status_code, 422)
        with psycopg.connect(URL_TEST) as c:
            for i in range(busqueda_estadias.MAX_RESULTADOS + 3):
                hab = f"HAB-9{i:02d}"
                c.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES (%s, 'EST-SINT-001', 'doble', 2)", (hab,))
                c.execute("INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, tarifa_noche_aceptada_clp, "
                          "estado) VALUES (%s, %s, %s, %s, %s, 'Grupo Tope', 1, 'en_estadia')", (f"RSV-T{i}", EMPRESA, hab, D(-1), D(1)))
            c.commit()
        datos = self.buscar("grupo").json()
        self.assertEqual(len(datos["resultados"]), busqueda_estadias.MAX_RESULTADOS)
        self.assertTrue(datos["hay_mas"])

    def test_texto_con_comodines_sql_no_lista_todo(self):
        self.assertEqual(self.ids(self.buscar("%%")), [])
        self.assertEqual(self.ids(self.buscar("__")), [])
        self.assertEqual(self.ids(self.buscar("' OR 1=1 --")), [])


if __name__ == "__main__":
    unittest.main()
