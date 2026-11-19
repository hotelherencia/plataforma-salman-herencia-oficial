"""ADP-5: la entrada la decide `check_in` del dominio y asienta las noches (#305: cada
noche con la tarifa vigente de esa noche; la primera la asienta el propio dominio)."""
import os
import unittest
from datetime import date, datetime, time, timedelta
from unittest import mock

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests.reloj import a_las
from hotel_inventario.servicio import ServicioHotelInventario

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


def d(n):
    return HOY + timedelta(days=n)


def iso(n):
    return d(n).isoformat()



class EntradaDominioTest(unittest.TestCase):
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
            for hid in ("H1", "H2", "H3"):
                c.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                          "VALUES (%s,'EST-SINT-001','doble',2)", (hid,))
                c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                          "VALUES (%s,%s,%s,%s,40000)", (f"T-{hid}", hid, d(-30), d(-1)))
                c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                          "VALUES (%s,%s,%s,%s,60000)", (f"U-{hid}", hid, d(-1), d(60)))
        self.cli = TestClient(self.app)
        self.cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.n = 0

    def clave(self):
        self.n += 1
        return {"Idempotency-Key": f"k{self.n}"}

    def reservar(self, hab="H1", a=-3, b=0, documento="D-1"):
        huesped = {"nombre": "Huésped"}
        if documento:
            huesped["documento"] = documento
        r = self.cli.post("/hotel/reservas", json={"habitacion_id": hab, "inicio": iso(a), "fin": iso(b),
                          "huesped": huesped}, headers=self.clave())
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["reserva_id"]

    def entrada(self, rid, cuerpo=None):
        return self.cli.post(f"/hotel/reservas/{rid}/entrada", json=cuerpo or {}, headers=self.clave())

    def sql(self, q, *a):
        with psycopg.connect(URL_TEST) as c:
            return c.execute(q, a).fetchall()

    def test_confirmar_deja_la_cuenta_vacia(self):  # ADP-4 AC-3
        rid = self.reservar()
        self.assertEqual(self.sql("SELECT count(*) FROM cargos WHERE reserva_id=%s", rid)[0][0], 0)

    def test_falla_el_dominio_falla_la_entrada_y_no_cambia_nada(self):
        rid = self.reservar()
        with mock.patch.object(ServicioHotelInventario, "check_in", side_effect=RuntimeError("dominio")):
            cli = TestClient(self.app, raise_server_exceptions=False)
            cli.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
            r = cli.post(f"/hotel/reservas/{rid}/entrada", json={}, headers=self.clave())
        self.assertEqual(r.status_code, 500)
        self.assertEqual(self.sql("SELECT estado FROM reservas WHERE id=%s", rid)[0][0], "confirmada")

    def test_entrada_asienta_cada_noche_con_su_tarifa_vigente(self):
        rid = self.reservar(a=-3, b=0)  # noches -3,-2 (40000) y -1 (60000)
        r = self.entrada(rid)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["estado"], "en_estadia")
        filas = self.sql("SELECT concepto, monto_clp, tipo FROM cargos WHERE reserva_id=%s ORDER BY monto_clp, id", rid)
        self.assertEqual(sorted(f[1] for f in filas), [40000, 40000, 60000])
        self.assertTrue(all(f[2] == "cargo" for f in filas))
        self.assertEqual(self.sql("SELECT count(*) FROM cargos WHERE reserva_id=%s AND referencia='noche:%s'" % ("%s", iso(-3)), rid)[0][0], 1)
        self.assertEqual(self.sql("SELECT estado_operativo FROM habitaciones WHERE id='H1'")[0][0], "ocupada")

    def test_la_cuenta_coincide_con_el_total_ofrecido(self):
        oferta = self.cli.get("/hotel/oferta", params={"inicio": iso(-3), "fin": iso(0), "personas": 1}).json()["oferta"]
        total = next(i for i in oferta if i["habitacion_id"] == "H1")["total_clp"]
        rid = self.reservar(a=-3, b=0)
        self.entrada(rid)
        self.assertEqual(self.sql("SELECT sum(monto_clp) FROM cargos WHERE reserva_id=%s", rid)[0][0], total)

    def test_segunda_entrada_409_y_sin_cargos_duplicados(self):
        rid = self.reservar()
        self.assertEqual(self.entrada(rid).status_code, 200)
        self.assertEqual(self.entrada(rid).status_code, 409)
        self.assertEqual(self.sql("SELECT count(*) FROM cargos WHERE reserva_id=%s", rid)[0][0], 3)

    def test_exige_documento_y_lo_captura(self):
        rid = self.reservar(documento=None)
        self.assertEqual(self.entrada(rid).status_code, 409)
        self.assertEqual(self.sql("SELECT estado FROM reservas WHERE id=%s", rid)[0][0], "confirmada")
        self.assertEqual(self.entrada(rid, {"documento": " 12.345.678-5 "}).status_code, 200)
        self.assertEqual(self.sql("SELECT huesped_documento FROM reservas WHERE id=%s", rid)[0][0], "12.345.678-5")

    def test_antes_de_las_15_del_dia_de_inicio_409_y_a_las_15_pasa(self):
        rid = self.reservar(a=0, b=2)
        with a_las(HOY, time(14, 59)):
            self.assertEqual(self.entrada(rid).status_code, 409)
        with a_las(HOY, time(15, 0)):
            self.assertEqual(self.entrada(rid).status_code, 200)

    def test_futuro_409(self):
        rid = self.reservar(a=3, b=5)
        self.assertEqual(self.entrada(rid).status_code, 409)

    def test_unidad_sucia_bloqueada_o_en_mantenimiento_409(self):
        for hab, col, val in (("H1", "estado_preparacion", "sucia"), ("H2", "estado_operativo", "bloqueada"),
                              ("H3", "mantenimiento", True)):
            rid = self.reservar(hab)
            with psycopg.connect(URL_TEST) as c:
                c.execute(f"UPDATE habitaciones SET {col}=%s WHERE id=%s", (val, hab))
            with self.subTest(hab=hab):
                self.assertEqual(self.entrada(rid).status_code, 409)
                self.assertEqual(self.sql("SELECT count(*) FROM cargos WHERE reserva_id=%s", rid)[0][0], 0)

    def test_turnover_unidad_ocupada_por_otra_estadia_no_solapada_permite_entrada(self):
        a = self.reservar("H1", -6, -3)
        self.assertEqual(self.entrada(a).status_code, 200)   # H1 queda ocupada
        b = self.reservar("H1", -3, 0)
        self.assertEqual(self.entrada(b).status_code, 200)

    def test_reserva_ajena_o_inexistente_403(self):
        self.assertEqual(self.entrada("RSV-NO-EXISTE").status_code, 403)


if __name__ == "__main__":
    unittest.main()
