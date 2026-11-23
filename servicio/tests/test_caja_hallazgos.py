"""Hallazgos de caja del propietario (2026-11-18): huésped en el pago (#364),
pago parcial o en exceso (#365), huésped en la caja del día (#366) y reverso
contable de un cargo (#359). HTTP contra PostgreSQL real, datos sintéticos.
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


class CajaHallazgosTest(unittest.TestCase):
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
                "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
                "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                "VALUES ('HAB-CAJA-1', 'EST-SINT-001', 'doble', 2)"
            )
            conexion.execute(
                "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                "VALUES ('TAR-CAJA-1', 'HAB-CAJA-1', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        self.assertEqual(self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)

    def idem(self):
        return {"Idempotency-Key": f"k-{uuid.uuid4().hex[:10]}"}

    def reservar(self, inicio=HOY, noches=2):
        r = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-CAJA-1", "inicio": str(inicio), "fin": str(inicio + timedelta(days=noches)),
                  "huesped": {"nombre": "Marta Caja", "documento": "11.111.111-1"}},
            headers=self.idem(),
        )
        self.assertEqual(r.status_code, 201, r.text)
        rid = r.json()["reserva_id"]
        return rid

    def saldo(self, rid):
        # Saldo contable (2.1): incluye las noches aún no asentadas; la cuenta del dominio nace vacía hasta la Llegada.
        return self.cliente.get(f"/hotel/reservas/{rid}/saldo").json()["pendiente_clp"]

    def pagar(self, rid, monto, **extra):
        return self.cliente.post(
            f"/hotel/reservas/{rid}/pagos",
            json={"monto_clp": monto, "clave": f"c-{uuid.uuid4().hex[:6]}", "modo": "manual", "medio": "transferencia", **extra},
            headers=self.idem(),
        )

    # --- #364 / #365 ---
    def test_364_365_pago_parcial_trae_huesped_y_saldo_pendiente(self):
        rid = self.reservar()
        saldo = self.saldo(rid)
        r = self.pagar(rid, saldo - 30000)
        self.assertEqual(r.status_code, 201, r.text)
        cuerpo = r.json()
        self.assertEqual(cuerpo["huesped_nombre"], "Marta Caja")
        self.assertEqual(cuerpo["habitacion_id"], "HAB-CAJA-1")
        self.assertEqual((cuerpo["tipo"], cuerpo["saldo_antes_clp"], cuerpo["saldo_despues_clp"]),
                         ("parcial", saldo, 30000))
        self.assertEqual(self.saldo(rid), 30000)

    def test_365_pago_total(self):
        rid = self.reservar()
        r = self.pagar(rid, self.saldo(rid))
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual((r.json()["tipo"], r.json()["saldo_despues_clp"]), ("total", 0))

    def test_365_pago_en_exceso_sin_confirmar_409_y_nada_se_registra(self):
        rid = self.reservar()
        saldo = self.saldo(rid)
        r = self.pagar(rid, saldo + 5000)
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual((r.json()["saldo_clp"], r.json()["exceso_clp"]), (saldo, 5000))
        self.assertEqual(self.saldo(rid), saldo)

    def test_365_pago_en_exceso_confirmado(self):
        rid = self.reservar()
        saldo = self.saldo(rid)
        r = self.pagar(rid, saldo + 5000, confirmar_exceso=True)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual((r.json()["tipo"], r.json()["saldo_despues_clp"]), ("exceso", -5000))

    # --- #366 ---
    def test_366_caja_del_dia_muestra_huesped(self):
        rid = self.reservar()
        self.assertEqual(self.pagar(rid, 10000).status_code, 201)
        caja = self.cliente.get("/hotel/caja", params={"fecha": str(date.today())})
        self.assertEqual(caja.status_code, 200, caja.text)
        self.assertEqual([p["huesped_nombre"] for p in caja.json()["pagos"]], ["Marta Caja"])

    # --- #359 ---
    def cargo(self, rid, monto=7000):
        r = self.cliente.post(f"/hotel/reservas/{rid}/cargos", json={"concepto": "minibar", "monto_clp": monto},
                              headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["cargo_id"]

    def reversar(self, rid, cargo_id, motivo="cargo mal ingresado", cliente=None):
        return (cliente or self.cliente).post(
            f"/hotel/reservas/{rid}/cargos/{cargo_id}/reverso", json={"motivo": motivo}, headers=self.idem())

    def test_359_reverso_asienta_movimiento_contrario_y_baja_el_saldo(self):
        rid = self.reservar()
        antes = self.saldo(rid)
        cid = self.cargo(rid)
        self.assertEqual(self.saldo(rid), antes + 7000)
        r = self.reversar(rid, cid)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual((r.json()["tipo"], r.json()["referencia"]), ("reverso", cid))
        self.assertEqual(self.saldo(rid), antes)
        cargos = self.cliente.get(f"/hotel/reservas/{rid}").json()["cargos"]
        original = next(c for c in cargos if c["cargo_id"] == cid)
        self.assertTrue(original["reversado"])
        # nunca se borra: el original sigue en la cuenta
        self.assertEqual(sum(1 for c in cargos if c["tipo"] == "reverso"), 1)

    def test_359_no_se_reversa_dos_veces_ni_un_reverso(self):
        rid = self.reservar()
        cid = self.cargo(rid)
        primero = self.reversar(rid, cid)
        self.assertEqual(primero.status_code, 201)
        self.assertEqual(self.reversar(rid, cid).status_code, 409)
        self.assertEqual(self.reversar(rid, primero.json()["cargo_id"]).status_code, 409)
        self.assertEqual(self.reversar(rid, "CRG-inexistente").status_code, 409)

    def test_359_motivo_obligatorio(self):
        rid = self.reservar()
        cid = self.cargo(rid)
        self.assertEqual(self.reversar(rid, cid, motivo="").status_code, 422)

    def test_359_solo_administracion_del_hotel(self):
        rid = self.reservar()
        cid = self.cargo(rid)
        r = self.cliente.post("/usuarios", json={"nombre": "caja1", "rol": "caja", "clave": "clave-caja-1"},
                              headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        caja = TestClient(self.app)
        self.assertEqual(caja.post("/sesion", json={"usuario": "caja1", "clave": "clave-caja-1"}).status_code, 200)
        self.assertEqual(self.reversar(rid, cid, cliente=caja).status_code, 403)


if __name__ == "__main__":
    unittest.main()
