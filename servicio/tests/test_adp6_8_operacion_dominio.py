"""ADP-6 (pagos y salida) y ADP-8 (cargos, limpieza y mantenimiento): el dominio decide.
Prueba de estupidez: si el método del dominio falla, la ruta falla y no deja estado a medias."""
import os
import unittest
from datetime import date, timedelta
from unittest import mock

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre
from hotel_inventario.servicio import ServicioHotelInventario

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


def iso(n):
    return (HOY + timedelta(days=n)).isoformat()


class OperacionDominioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1]))

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            exigir_base_libre(c)
            c.execute(
                "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
                "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE")
            seguridad.asegurar_admin_inicial(c, EMPRESA, ADMIN[0], ADMIN[1])
            for h in ("H1", "H2"):
                c.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                          "VALUES (%s,'EST-SINT-001','doble',2)", (h,))
                c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                          "VALUES (%s,%s,%s,%s,50000)", (f"T-{h}", h, HOY - timedelta(days=30), HOY + timedelta(days=90)))
        self.cli = TestClient(self.app)
        self.cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.n = 0

    def clave(self):
        self.n += 1
        return {"Idempotency-Key": f"k{self.n}"}

    def post(self, ruta, cuerpo=None, cli=None):
        return (cli or self.cli).post(ruta, json=cuerpo if cuerpo is not None else {}, headers=self.clave())

    def en_estadia(self, hab="H1", a=-2, b=0):
        r = self.post("/hotel/reservas", {"habitacion_id": hab, "inicio": iso(a), "fin": iso(b),
                      "huesped": {"nombre": "H", "documento": "D-1"}})
        rid = r.json()["reserva_id"]
        self.assertEqual(self.post(f"/hotel/reservas/{rid}/entrada").status_code, 200)
        return rid

    def sql(self, q, *a):
        with psycopg.connect(URL_TEST) as c:
            return c.execute(q, a).fetchall()

    def cliente_sin_excepciones(self):
        cli = TestClient(self.app, raise_server_exceptions=False)
        cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        return cli

    # ---- ADP-6 ----
    def test_pago_falla_si_falla_el_dominio_y_no_deja_fila(self):
        rid = self.en_estadia()
        with mock.patch.object(ServicioHotelInventario, "registrar_pago", side_effect=RuntimeError("dominio")):
            r = self.post(f"/hotel/reservas/{rid}/pagos", {"monto_clp": 1000, "clave": "p1", "modo": "manual"},
                          self.cliente_sin_excepciones())
        self.assertEqual(r.status_code, 500)
        self.assertEqual(self.sql("SELECT count(*) FROM pagos")[0][0], 0)

    def test_pago_proyecta_fila_con_efecto_del_nucleo_y_es_idempotente_por_clave(self):
        rid = self.en_estadia()
        r = self.post(f"/hotel/reservas/{rid}/pagos", {"monto_clp": 30000, "clave": "p1", "modo": "manual"})
        self.assertEqual(r.status_code, 201, r.text)
        otra = self.post(f"/hotel/reservas/{rid}/pagos", {"monto_clp": 30000, "clave": "p1", "modo": "manual"})
        self.assertEqual(otra.status_code, 201)
        self.assertTrue(otra.json().get("reintento"))
        filas = self.sql("SELECT monto_clp, modo, estado, efecto_nucleo_id FROM pagos WHERE reserva_id=%s", rid)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0][:3], (30000, "manual", "confirmado"))
        self.assertIsNotNone(filas[0][3])
        self.assertEqual(self.post(f"/hotel/reservas/{rid}/pagos", {"monto_clp": 99, "clave": "p1", "modo": "manual"}).status_code, 409)

    def test_salida_falla_si_falla_check_out(self):
        rid = self.en_estadia()
        self.post(f"/hotel/reservas/{rid}/pagos", {"monto_clp": 100000, "clave": "p1", "modo": "manual"})
        with mock.patch.object(ServicioHotelInventario, "check_out", side_effect=RuntimeError("dominio")):
            r = self.post(f"/hotel/reservas/{rid}/salida", cli=self.cliente_sin_excepciones())
        self.assertEqual(r.status_code, 500)
        self.assertEqual(self.sql("SELECT estado FROM reservas WHERE id=%s", rid)[0][0], "en_estadia")

    def test_salida_con_saldo_409_y_saldada_persiste_liquidacion_del_dominio(self):
        rid = self.en_estadia()  # 2 noches × 50000
        self.assertEqual(self.post(f"/hotel/reservas/{rid}/salida").status_code, 409)
        self.assertEqual(self.sql("SELECT count(*) FROM liquidaciones")[0][0], 0)
        self.post(f"/hotel/reservas/{rid}/pagos", {"monto_clp": 100000, "clave": "p1", "modo": "manual"})
        r = self.post(f"/hotel/reservas/{rid}/salida")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["total_clp"], r.json()["pagado_clp"], r.json()["saldo_clp"]), (100000, 100000, 0))
        self.assertEqual(self.sql("SELECT total_clp, pagado_clp, saldo_clp FROM liquidaciones WHERE reserva_id=%s", rid)[0],
                         (100000, 100000, 0))
        self.assertEqual(self.sql("SELECT estado FROM reservas WHERE id=%s", rid)[0][0], "finalizada")
        self.assertEqual(self.sql("SELECT estado_operativo, estado_preparacion FROM habitaciones WHERE id='H1'")[0],
                         ("disponible", "sucia"))
        self.assertEqual(self.sql("SELECT tipo, estado FROM tareas_operativas WHERE habitacion_id='H1'"), [("limpieza", "pendiente")])

    def test_el_detalle_muestra_la_cuenta_del_dominio(self):
        rid = self.en_estadia()
        self.post(f"/hotel/reservas/{rid}/pagos", {"monto_clp": 30000, "clave": "p1", "modo": "manual"})
        d = self.cli.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(d["cuenta"], {"cargos_netos_clp": 100000, "pagado_clp": 30000, "saldo_clp": 70000})

    # ---- ADP-8 ----
    def test_cargo_falla_si_falla_el_dominio(self):
        rid = self.en_estadia()
        with mock.patch.object(ServicioHotelInventario, "asentar_cargo", side_effect=RuntimeError("dominio")):
            r = self.post(f"/hotel/reservas/{rid}/cargos", {"concepto": "minibar", "monto_clp": 5000},
                          self.cliente_sin_excepciones())
        self.assertEqual(r.status_code, 500)

    def test_cargo_se_asienta_por_el_dominio_y_solo_con_cuenta_abierta(self):
        rid = self.en_estadia()
        r = self.post(f"/hotel/reservas/{rid}/cargos", {"concepto": "minibar", "monto_clp": 5000})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self.sql("SELECT count(*) FROM cargos WHERE reserva_id=%s AND concepto='minibar'", rid)[0][0], 1)
        self.post(f"/hotel/reservas/{rid}/pagos", {"monto_clp": 105000, "clave": "p1", "modo": "manual"})
        self.post(f"/hotel/reservas/{rid}/salida")
        self.assertEqual(self.post(f"/hotel/reservas/{rid}/cargos", {"concepto": "tarde", "monto_clp": 1}).status_code, 409)

    def test_limpieza_falla_si_falla_completar_tarea(self):
        rid = self.en_estadia()
        self.post(f"/hotel/reservas/{rid}/pagos", {"monto_clp": 100000, "clave": "p1", "modo": "manual"})
        self.post(f"/hotel/reservas/{rid}/salida")
        with mock.patch.object(ServicioHotelInventario, "completar_tarea", side_effect=RuntimeError("dominio")):
            r = self.post("/hotel/habitaciones/H1/limpieza", cli=self.cliente_sin_excepciones())
        self.assertEqual(r.status_code, 500)
        self.assertEqual(self.sql("SELECT estado_preparacion FROM habitaciones WHERE id='H1'")[0][0], "sucia")

    def test_limpieza_completa_tarea_y_deja_limpia_la_unidad(self):
        rid = self.en_estadia()
        self.post(f"/hotel/reservas/{rid}/pagos", {"monto_clp": 100000, "clave": "p1", "modo": "manual"})
        self.post(f"/hotel/reservas/{rid}/salida")
        r = self.post("/hotel/habitaciones/H1/limpieza")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["estado_preparacion"], "limpia")
        self.assertEqual(self.sql("SELECT estado FROM tareas_operativas WHERE habitacion_id='H1'"), [("completada",)])
        self.assertEqual(self.sql("SELECT estado_preparacion FROM habitaciones WHERE id='H1'")[0][0], "limpia")

    def test_mantenimiento_lo_decide_el_dominio_y_cierra_cupo_y_entrada(self):
        r = self.post("/hotel/reservas", {"habitacion_id": "H2", "inicio": iso(-1), "fin": iso(1),
                      "huesped": {"nombre": "H", "documento": "D-1"}})
        rid = r.json()["reserva_id"]
        with mock.patch.object(ServicioHotelInventario, "abrir_mantenimiento", side_effect=RuntimeError("dominio")):
            falla = self.post("/hotel/habitaciones/H2/mantenimiento", {"abierto": True}, self.cliente_sin_excepciones())
        self.assertEqual(falla.status_code, 500)
        self.assertEqual(self.sql("SELECT mantenimiento FROM habitaciones WHERE id='H2'")[0][0], False)
        self.assertEqual(self.post("/hotel/habitaciones/H2/mantenimiento", {"abierto": True}).status_code, 200)
        self.assertEqual(self.sql("SELECT tipo, estado FROM tareas_operativas WHERE habitacion_id='H2'"), [("mantenimiento", "pendiente")])
        self.assertEqual(self.post(f"/hotel/reservas/{rid}/entrada").status_code, 409)
        # mismo estado otra vez: no duplica tarea
        self.post("/hotel/habitaciones/H2/mantenimiento", {"abierto": True})
        self.assertEqual(self.sql("SELECT count(*) FROM tareas_operativas WHERE habitacion_id='H2'")[0][0], 1)
        self.assertEqual(self.post("/hotel/habitaciones/H2/mantenimiento", {"abierto": False}).status_code, 200)
        self.assertEqual(self.sql("SELECT estado FROM tareas_operativas WHERE habitacion_id='H2'"), [("completada",)])
        self.assertEqual(self.post(f"/hotel/reservas/{rid}/entrada").status_code, 200)


if __name__ == "__main__":
    unittest.main()
