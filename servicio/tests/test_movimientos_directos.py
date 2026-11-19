"""Movimientos directos sin habitación ni reserva y cuadratura contable (2026-11-19).

Cubre el hallazgo del propietario: un cargo o movimiento no asociado a una
habitación/reserva debe quedar registrado y sumar a la contabilidad aunque la
caja no esté abierta; también verifica consumos extra en conciliación diaria,
descuento/devolución de stock, cobro posterior, reversos inmutables y turnos.
"""
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
from servicio.tests.reloj import a_las

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


class MovimientosDirectosTest(unittest.TestCase):
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
                "caja_movimientos, movimientos_directos, caja_turnos, cierres_diarios, pagos, cargos, reservas, "
                "tarifas, sesiones, usuarios, habitaciones, clientes, movimientos_stock, productos "
                "RESTART IDENTITY CASCADE"
            )
            conexion.execute("DELETE FROM ajustes WHERE empresa_id = %s AND clave = 'caja'", (EMPRESA,))
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                "VALUES ('HAB-D-1', 'EST-SINT-001', 'doble', 2)"
            )
            conexion.execute(
                "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                "VALUES ('TAR-D-1', 'HAB-D-1', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        self.assertEqual(self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)

    def idem(self):
        return {"Idempotency-Key": f"k-{uuid.uuid4().hex[:10]}"}

    def test_cargo_directo_sin_habitacion_ni_caja_abierta_suma_a_contabilidad_y_cierre(self):
        # Sin turno de caja abierto, registramos un cargo directo pendiente de cobro
        r = self.cliente.post(
            "/hotel/contabilidad/movimientos-directos",
            headers=self.idem(),
            json={
                "tipo": "cargo_directo",
                "categoria": "estacionamiento",
                "concepto": "Estacionamiento visitante diario",
                "monto_clp": 11900,
                "estado_cobro": "pendiente",
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        mov = r.json()
        self.assertEqual((mov["monto_clp"], mov["neto_clp"], mov["iva_clp"], mov["estado_cobro"]),
                         (11900, 10000, 1900, "pendiente"))

        # Aparece en el libro contable y suma en el devengado
        libro = self.cliente.get(
            "/hotel/contabilidad/movimientos", params={"desde": str(HOY), "hasta": str(HOY)}
        ).json()
        self.assertEqual(libro["resumen"]["cargos_directos_clp"], 11900)
        self.assertEqual(libro["resumen"]["total_devengado_clp"], 11900)
        self.assertEqual(libro["resumen"]["pendiente_directo_clp"], 11900)
        self.assertEqual(libro["resumen"]["total_cobrado_clp"], 0)

        # Aparece y suma en la conciliación diaria con desglose neto / IVA y alerta de pendiente
        conc = self.cliente.get("/hotel/caja/conciliacion", params={"fecha": str(HOY)}).json()
        self.assertEqual(conc["resumen"]["ingreso_directo_clp"], 11900)
        self.assertEqual(conc["resumen"]["total_ingresos_devengados_clp"], 11900)
        self.assertEqual(conc["resumen"]["total_ingresos_neto_clp"], 10000)
        self.assertEqual(conc["resumen"]["total_iva_debito_clp"], 1900)
        self.assertTrue(any("pendientes de cobro" in a for a in conc["alertas"]))

        # Al abrir turno y cobrarlo en efectivo, entra en caja y turno sin duplicar el devengado
        turno = self.cliente.post("/hotel/caja/turnos", headers=self.idem(), json={"fondo_inicial_clp": 10000})
        self.assertEqual(turno.status_code, 201, turno.text)
        cobro = self.cliente.post(
            f"/hotel/contabilidad/movimientos-directos/{mov['movimiento_directo_id']}/cobrar",
            headers=self.idem(),
            json={"medio": "efectivo", "documento_tipo": "boleta"},
        )
        self.assertEqual(cobro.status_code, 200, cobro.text)
        self.assertEqual(cobro.json()["estado_cobro"], "cobrado")

        caja = self.cliente.get("/hotel/caja", params={"fecha": str(HOY)}).json()
        self.assertEqual(caja["total_clp"], 11900)
        self.assertEqual(caja["por_medio"]["efectivo"], 11900)

        estado = self.cliente.get("/hotel/caja/estado").json()["turno"]
        self.assertEqual(estado["totales"]["efectivo_esperado_clp"], 21900)

        libro2 = self.cliente.get(
            "/hotel/contabilidad/movimientos", params={"desde": str(HOY), "hasta": str(HOY)}
        ).json()
        self.assertEqual(libro2["resumen"]["total_devengado_clp"], 11900)
        self.assertEqual(libro2["resumen"]["total_cobrado_clp"], 11900)
        self.assertEqual(libro2["resumen"]["pendiente_directo_clp"], 0)

    def test_venta_directa_producto_por_transferencia_con_caja_cerrada_entra_al_turno_siguiente_y_descuenta_stock(self):
        prod = self.cliente.post(
            "/hotel/productos",
            headers=self.idem(),
            json={"nombre": "Café grano", "categoria": "cafeteria", "precio_clp": 3500, "controla_stock": True, "stock": 10},
        ).json()
        # Caja cerrada, pago por transferencia
        r = self.cliente.post(
            "/hotel/contabilidad/movimientos-directos",
            headers=self.idem(),
            json={
                "tipo": "cargo_directo",
                "producto_id": prod["producto_id"],
                "cantidad": 2,
                "estado_cobro": "cobrado",
                "medio": "transferencia",
                "documento_tipo": "boleta",
                "comprobante": "TRF-881",
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        mov = r.json()
        self.assertEqual((mov["monto_clp"], mov["categoria"]), (7000, "cafeteria"))

        # Stock bajó de 10 a 8
        lista_prod = self.cliente.get("/hotel/productos").json()["productos"]
        self.assertEqual(lista_prod[0]["stock"], 8)

        # Al abrir el siguiente turno, entra tanto en totales como en detalle.movimientos
        turno = self.cliente.post("/hotel/caja/turnos", headers=self.idem(), json={"fondo_inicial_clp": 0}).json()
        det = self.cliente.get(f"/hotel/caja/turnos/{turno['turno_id']}").json()
        self.assertEqual(det["totales"]["por_medio"]["transferencia"], 7000)
        self.assertEqual(det["totales"]["recibido_sin_turno_clp"], 7000)
        self.assertEqual(len(det["movimientos"]), 1)
        self.assertEqual(det["movimientos"][0]["movimiento_directo_id"], mov["movimiento_directo_id"])

        # Reverso devuelve stock y anula ingresos y cobros
        rev = self.cliente.post(
            f"/hotel/contabilidad/movimientos-directos/{mov['movimiento_directo_id']}/reverso",
            headers=self.idem(),
            json={"motivo": "Error en la cantidad de cafés vendidos"},
        )
        self.assertEqual(rev.status_code, 201, rev.text)
        lista_prod2 = self.cliente.get("/hotel/productos").json()["productos"]
        self.assertEqual(lista_prod2[0]["stock"], 10)
        conc = self.cliente.get("/hotel/caja/conciliacion", params={"fecha": str(HOY)}).json()
        self.assertEqual(conc["resumen"]["ingreso_directo_clp"], 0)
        self.assertEqual(conc["cobros"]["total_clp"], 0)

    def test_efectivo_con_caja_cerrada_rechaza_409_con_guia_clara(self):
        r = self.cliente.post(
            "/hotel/contabilidad/movimientos-directos",
            headers=self.idem(),
            json={
                "tipo": "cargo_directo",
                "concepto": "Café mostrador",
                "monto_clp": 2500,
                "estado_cobro": "cobrado",
                "medio": "efectivo",
                "documento_tipo": "boleta",
            },
        )
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("pendiente de cobro", r.json()["detail"])

    def test_egreso_operacional_descuenta_efectivo_esperado_y_figura_en_cierre(self):
        turno = self.cliente.post("/hotel/caja/turnos", headers=self.idem(), json={"fondo_inicial_clp": 30000}).json()
        egreso = self.cliente.post(
            "/hotel/contabilidad/movimientos-directos",
            headers=self.idem(),
            json={
                "tipo": "egreso_operacional",
                "categoria": "gasto_operacional",
                "concepto": "Compra pan desayuno",
                "monto_clp": 8000,
                "estado_cobro": "cobrado",
                "medio": "efectivo",
                "documento_tipo": "boleta",
            },
        )
        self.assertEqual(egreso.status_code, 201, egreso.text)
        det = self.cliente.get(f"/hotel/caja/turnos/{turno['turno_id']}").json()
        self.assertEqual(det["totales"]["efectivo_esperado_clp"], 22000)
        self.assertEqual(det["totales"]["egresos_caja_clp"], 8000)
        conc = self.cliente.get("/hotel/caja/conciliacion", params={"fecha": str(HOY)}).json()
        self.assertEqual(conc["resumen"]["egresos_operacionales_clp"], 8000)
        self.assertEqual(conc["cobros"]["egresos_caja_clp"], 8000)

    def test_consumos_extra_de_reserva_suman_en_conciliacion_diaria(self):
        rsv = self.cliente.post(
            "/hotel/reservas", headers=self.idem(),
            json={"habitacion_id": "HAB-D-1", "inicio": str(HOY), "fin": str(HOY + timedelta(days=1)),
                  "huesped": {"nombre": "Laura Extra", "documento": "11.111.111-1"}},
        ).json()["reserva_id"]
        with a_las(HOY):
            self.assertEqual(self.cliente.post(f"/hotel/reservas/{rsv}/entrada", json={}, headers=self.idem()).status_code, 200)
        self.assertEqual(
            self.cliente.post(
                f"/hotel/reservas/{rsv}/cargos", headers=self.idem(),
                json={"concepto": "Minibar extra", "monto_clp": 9500},
            ).status_code,
            201,
        )
        conc = self.cliente.get("/hotel/caja/conciliacion", params={"fecha": str(HOY)}).json()
        self.assertEqual(conc["resumen"]["ingreso_alojamiento_clp"], 50000)
        self.assertEqual(conc["resumen"]["ingreso_consumos_reserva_clp"], 9500)
        self.assertEqual(conc["resumen"]["total_ingresos_devengados_clp"], 59500)

    def test_movimientos_directos_inmutables_en_base(self):
        mov_id = self.cliente.post(
            "/hotel/contabilidad/movimientos-directos", headers=self.idem(),
            json={"tipo": "cargo_directo", "concepto": "Lavandería externa", "monto_clp": 6000,
                  "estado_cobro": "cobrado", "medio": "transferencia", "documento_tipo": "boleta"},
        ).json()["movimiento_directo_id"]
        with psycopg.connect(URL_TEST) as c:
            with self.assertRaises(psycopg.errors.CheckViolation):
                c.execute("UPDATE movimientos_directos SET monto_clp = 1 WHERE id = %s", (mov_id,))
            c.rollback()
            with self.assertRaises(psycopg.errors.CheckViolation):
                c.execute("DELETE FROM movimientos_directos WHERE id = %s", (mov_id,))


if __name__ == "__main__":
    unittest.main()
