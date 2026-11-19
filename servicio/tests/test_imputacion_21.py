"""Contabilidad fase 2.1 sobre la fase 1 de caja: clientes con RUT normalizado, imputación de pagos y abonos,
saldo por reserva, registro de movimientos de la cuenta y lo cobrado con la caja cerrada. HTTP contra PostgreSQL real."""
import os
import unittest
import uuid
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import clientes, seguridad
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
RUT_OK = "12.345.678-5"
RECEPTOR = {"rut": RUT_OK, "razon_social": "Empresa Uno SpA", "giro": "Servicios", "direccion": "Calle 1", "comuna": "Chillán"}


class RutTest(unittest.TestCase):
    def test_rut_se_guarda_solo_con_numeros_y_digito_verificador(self):
        for entrada in ("12.345.678-5", "12345678-5", " 12345678 5 ", "123456785"):
            self.assertEqual(clientes.rut_clave(entrada), "123456785")
        self.assertEqual(clientes.rut_clave("7.000.013-k"), "7000013K")

    def test_rut_invalido_se_rechaza(self):
        for malo in ("12.345.678-9", "abc", "", "1-9", "12.345.678-55"):
            with self.subTest(malo=malo), self.assertRaises(clientes.RutInvalido):
                clientes.rut_clave(malo)

    def test_se_muestra_con_puntos_y_guion(self):
        self.assertEqual(clientes.rut_visible("123456785"), "12.345.678-5")
        self.assertIsNone(clientes.rut_visible(None))

    def test_el_nombre_se_compara_sin_tildes_mayusculas_ni_espacios_de_mas(self):
        self.assertEqual(clientes.nombre_clave("  ÁNGEL   Núñez  "), clientes.nombre_clave("angel nunez"))


class Base(unittest.TestCase):
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
                "caja_movimientos, caja_turnos, cierres_diarios, pagos, cargos, reservas, tarifas, sesiones, usuarios, "
                "habitaciones, clientes RESTART IDENTITY CASCADE")
            conexion.execute("DELETE FROM ajustes WHERE empresa_id = %s AND clave = 'caja'", (EMPRESA,))
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                             "VALUES ('HAB-C-1', 'EST-SINT-001', 'doble', 2)")
            conexion.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                             "VALUES ('TAR-C-1', 'HAB-C-1', '2026-01-01', '2027-12-31', 50000)")
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        self.assertEqual(self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)

    def idem(self):
        return {"Idempotency-Key": f"k-{uuid.uuid4().hex[:10]}"}

    def sql(self, consulta, parametros=()):
        with psycopg.connect(URL_TEST) as c:
            return c.execute(consulta, parametros).fetchall()

    def reservar(self, inicio=HOY, noches=2, nombre="Marta Cuenta", documento="11.111.111-1", tipo=None):
        huesped = {"nombre": nombre, "documento": documento}
        if tipo:
            huesped["documento_tipo"] = tipo
        r = self.cliente.post(
            "/hotel/reservas", headers=self.idem(),
            json={"habitacion_id": "HAB-C-1", "inicio": str(inicio), "fin": str(inicio + timedelta(days=noches)),
                  "huesped": huesped})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["reserva_id"]

    def pagar(self, rid, monto, cliente=None, **extra):
        return (cliente or self.cliente).post(
            f"/hotel/reservas/{rid}/pagos", headers=self.idem(),
            json={"monto_clp": monto, "clave": f"c-{uuid.uuid4().hex[:6]}", "modo": "manual", **extra})

    def entrar(self, rid):
        with a_las(HOY):
            r = self.cliente.post(f"/hotel/reservas/{rid}/entrada", json={}, headers=self.idem())
        self.assertEqual(r.status_code, 200, r.text)

    def saldo(self, rid):
        r = self.cliente.get(f"/hotel/reservas/{rid}/saldo")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def factura(self, **cambios):
        return {"documento_tipo": "factura", "receptor": {**RECEPTOR, **cambios}}


class ClientesTest(Base):
    def test_el_rut_queda_en_la_base_solo_con_numeros(self):
        rid = self.reservar()
        r = self.pagar(rid, 10000, medio="transferencia", **self.factura())
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self.sql("SELECT rut, nombre, giro, direccion, comuna FROM clientes"),
                         [("123456785", "Empresa Uno SpA", "Servicios", "Calle 1", "Chillán")])
        self.assertEqual(self.sql("SELECT receptor->>'rut' FROM pagos"), [("123456785",)])

    def test_la_base_rechaza_un_rut_con_simbolos(self):
        with psycopg.connect(URL_TEST) as c, self.assertRaises(psycopg.errors.CheckViolation):
            c.execute("INSERT INTO clientes (id, rut, nombre, nombre_clave, creado_por) "
                      "VALUES ('CLI-X', '12.345.678-5', 'X', 'x', 'a')")

    def test_mismo_rut_otro_nombre_es_409_y_no_se_cobra(self):
        rid = self.reservar()
        self.assertEqual(self.pagar(rid, 10000, medio="transferencia", **self.factura()).status_code, 201)
        otro = self.pagar(rid, 5000, medio="transferencia", **self.factura(rut="12345678-5", razon_social="Otra Razón Ltda"))
        self.assertEqual(otro.status_code, 409, otro.text)
        self.assertIn("Empresa Uno SpA", otro.json()["detail"])
        self.assertEqual(self.sql("SELECT count(*) FROM pagos")[0][0], 1)
        self.assertEqual(self.sql("SELECT count(*) FROM clientes")[0][0], 1)

    def test_el_mismo_nombre_con_otra_escritura_reutiliza_al_cliente(self):
        rid = self.reservar()
        self.pagar(rid, 10000, medio="transferencia", **self.factura())
        r = self.pagar(rid, 5000, medio="transferencia", **self.factura(rut="12345678-5", razon_social="  EMPRESA  UNO spa "))
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self.sql("SELECT count(*) FROM clientes")[0][0], 1)

    def test_una_reserva_con_el_rut_de_un_cliente_y_otro_nombre_es_409(self):
        rid = self.reservar()
        self.pagar(rid, 1000, medio="transferencia", **self.factura(rut="11.111.111-1", razon_social="Marta Cuenta"))
        r = self.cliente.post(
            "/hotel/reservas", headers=self.idem(),
            json={"habitacion_id": "HAB-C-1", "inicio": str(HOY + timedelta(days=9)), "fin": str(HOY + timedelta(days=10)),
                  "huesped": {"nombre": "Pedro Distinto", "documento": "11.111.111-1", "documento_tipo": "rut"}})
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("Marta Cuenta", r.json()["detail"])

    def test_boleta_no_crea_cliente(self):
        rid = self.reservar()
        self.assertEqual(self.pagar(rid, 1000, medio="transferencia", documento_tipo="boleta").status_code, 201)
        self.assertEqual(self.sql("SELECT count(*) FROM clientes")[0][0], 0)


class ImputacionTest(Base):
    def test_el_abono_antes_de_llegar_es_anticipo_y_no_pide_confirmar_exceso(self):
        rid = self.reservar()  # 2 noches x 50.000
        r = self.pagar(rid, 30000)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["tipo"], "parcial")
        s = self.saldo(rid)
        self.assertEqual((s["total_clp"], s["abonado_clp"], s["pagado_clp"], s["pendiente_clp"]), (100000, 30000, 0, 70000))
        self.assertEqual(self.sql("SELECT tipo, noche, monto_clp FROM imputaciones_pago"), [("anticipo", None, 30000)])

    def test_pagar_mas_que_el_total_antes_de_llegar_si_exige_confirmar(self):
        rid = self.reservar()
        self.assertEqual(self.pagar(rid, 130000).status_code, 409)
        self.assertEqual(self.pagar(rid, 130000, confirmar_exceso=True).status_code, 201)

    def test_la_llegada_aplica_el_anticipo_noche_a_noche(self):
        rid = self.reservar()
        self.pagar(rid, 70000)
        self.entrar(rid)
        filas = self.sql("SELECT noche, monto_clp FROM imputaciones_pago WHERE tipo = 'aplicacion_anticipo' ORDER BY noche")
        self.assertEqual(filas, [(HOY, 50000), (HOY + timedelta(days=1), 20000)])
        s = self.saldo(rid)
        self.assertEqual((s["total_clp"], s["abonado_clp"], s["pagado_clp"], s["pendiente_clp"]), (100000, 0, 70000, 30000))
        self.assertEqual([(n["pagado_clp"], n["pendiente_clp"]) for n in s["noches"]], [(50000, 0), (20000, 30000)])

    def test_un_pago_en_estadia_se_imputa_a_las_noches_mas_antiguas(self):
        rid = self.reservar()
        self.entrar(rid)
        self.assertEqual(self.pagar(rid, 60000).status_code, 201)
        s = self.saldo(rid)
        self.assertEqual([(n["pagado_clp"], n["pendiente_clp"]) for n in s["noches"]], [(50000, 0), (10000, 40000)])
        self.assertEqual((s["abonado_clp"], s["pagado_clp"], s["pendiente_clp"]), (0, 60000, 40000))

    def test_el_pago_de_un_consumo_va_al_consumo_y_el_exceso_queda_como_abono(self):
        rid = self.reservar()
        self.entrar(rid)
        self.pagar(rid, 100000)
        self.cliente.post(f"/hotel/reservas/{rid}/cargos", json={"concepto": "Minibar", "monto_clp": 7000}, headers=self.idem())
        self.pagar(rid, 10000, confirmar_exceso=True)
        s = self.saldo(rid)
        self.assertEqual((s["total_clp"], s["pagado_clp"], s["abonado_clp"], s["pendiente_clp"]), (107000, 107000, 3000, -3000))

    def test_abonado_mas_pagado_es_siempre_lo_recibido(self):
        rid = self.reservar()
        for monto in (20000, 45000):
            self.pagar(rid, monto)
        self.entrar(rid)
        self.pagar(rid, 25000)
        s = self.saldo(rid)
        self.assertEqual(s["abonado_clp"] + s["pagado_clp"], 90000)
        self.assertEqual(s["pendiente_clp"], s["total_clp"] - 90000)

    def test_la_imputacion_lleva_habitacion_cliente_y_actor(self):
        rid = self.reservar()
        self.pagar(rid, 11900, medio="transferencia", **self.factura())
        (fila,) = self.sql("SELECT habitacion_id, cliente_id IS NOT NULL, actor FROM imputaciones_pago")
        self.assertEqual(fila, ("HAB-C-1", True, "admin"))

    def test_la_imputacion_es_inmutable(self):
        rid = self.reservar()
        self.pagar(rid, 1000)
        with psycopg.connect(URL_TEST) as c:
            with self.assertRaises(psycopg.errors.CheckViolation):
                c.execute("UPDATE imputaciones_pago SET monto_clp = 1")
            c.rollback()
            with self.assertRaises(psycopg.errors.CheckViolation):
                c.execute("DELETE FROM imputaciones_pago")

    def test_un_reintento_con_la_misma_clave_no_imputa_dos_veces(self):
        rid = self.reservar()
        cuerpo = {"monto_clp": 30000, "clave": "misma", "modo": "manual"}
        for _ in range(2):
            self.cliente.post(f"/hotel/reservas/{rid}/pagos", json=cuerpo, headers=self.idem())
        self.assertEqual(self.sql("SELECT count(*) FROM imputaciones_pago")[0][0], 1)

    def test_la_cancelacion_no_borra_lo_abonado(self):
        rid = self.reservar(inicio=HOY + timedelta(days=30))
        self.pagar(rid, 40000)
        self.assertEqual(self.cliente.post(f"/hotel/reservas/{rid}/cancelacion", headers=self.idem()).status_code, 200)
        self.assertEqual(self.saldo(rid)["abonado_clp"], 40000)  # sigue a la vista para devolverlo o aplicarlo

    def test_el_reverso_de_un_pago_deshace_su_imputacion_y_el_saldo_vuelve(self):
        rid = self.reservar()
        self.pagar(rid, 70000)
        self.entrar(rid)  # aplica el anticipo a las dos noches
        (pago_id,) = [f[0] for f in self.sql("SELECT id FROM pagos WHERE tipo = 'pago'")]
        r = self.cliente.post(f"/hotel/reservas/{rid}/pagos/{pago_id}/reverso", headers=self.idem(),
                              json={"motivo": "cobro duplicado por error"})
        self.assertEqual(r.status_code, 201, r.text)
        s = self.saldo(rid)
        self.assertEqual((s["abonado_clp"], s["pagado_clp"], s["pendiente_clp"], s["recibido_clp"]), (0, 0, 100000, 0))
        self.assertEqual([n["pagado_clp"] for n in s["noches"]], [0, 0])
        # todo es un movimiento contrario: las filas originales siguen ahí
        self.assertGreater(self.sql("SELECT count(*) FROM imputaciones_pago WHERE revierte_id IS NOT NULL")[0][0], 0)
        self.assertEqual(self.sql("SELECT sum(monto_clp) FROM imputaciones_pago")[0][0], 0)

    def test_el_reverso_de_un_anticipo_sin_aplicar_devuelve_el_abono(self):
        rid = self.reservar(inicio=HOY + timedelta(days=30))
        self.pagar(rid, 40000)
        (pago_id,) = [f[0] for f in self.sql("SELECT id FROM pagos WHERE tipo = 'pago'")]
        self.cliente.post(f"/hotel/reservas/{rid}/pagos/{pago_id}/reverso", headers=self.idem(),
                          json={"motivo": "el huésped se arrepintió"})
        s = self.saldo(rid)
        self.assertEqual((s["abonado_clp"], s["recibido_clp"], s["pendiente_clp"]), (0, 0, 100000))


class MovimientosCuentaTest(Base):
    def test_un_cargo_queda_registrado_aunque_no_haya_caja_abierta(self):
        rid = self.reservar()
        self.entrar(rid)
        self.cliente.post(f"/hotel/reservas/{rid}/cargos", json={"concepto": "Minibar", "monto_clp": 7000}, headers=self.idem())
        r = self.cliente.get("/hotel/contabilidad/movimientos", params={"desde": str(HOY), "hasta": str(HOY)})
        self.assertEqual(r.status_code, 200, r.text)
        (m,) = [m for m in r.json()["movimientos"] if m["concepto"] == "Minibar"]
        self.assertEqual((m["tipo"], m["monto_clp"], m["reserva_id"], m["actor"], m["habitacion_id"]),
                         ("cargo", 7000, rid, "admin", "HAB-C-1"))

    def test_los_pagos_y_reversos_tambien_aparecen_con_quien_los_hizo(self):
        rid = self.reservar()
        self.entrar(rid)
        self.pagar(rid, 20000)
        cargo = self.cliente.post(f"/hotel/reservas/{rid}/cargos", json={"concepto": "Cena", "monto_clp": 9000},
                                  headers=self.idem()).json()["cargo_id"]
        self.cliente.post(f"/hotel/reservas/{rid}/cargos/{cargo}/reverso", json={"motivo": "error de digitación"}, headers=self.idem())
        movs = self.cliente.get("/hotel/contabilidad/movimientos", params={"desde": str(HOY), "hasta": str(HOY)}).json()["movimientos"]
        self.assertEqual(sorted({m["tipo"] for m in movs}), ["cargo", "pago", "reverso"])
        self.assertTrue(all(m["actor"] == "admin" for m in movs))

    def test_solo_caja_y_administracion_del_hotel_ven_los_movimientos(self):
        self.cliente.post("/usuarios", json={"nombre": "recep9", "rol": "recepcion", "clave": "clave-recep-9"}, headers=self.idem())
        recep = TestClient(self.app)
        recep.post("/sesion", json={"usuario": "recep9", "clave": "clave-recep-9"})
        r = recep.get("/hotel/contabilidad/movimientos", params={"desde": str(HOY), "hasta": str(HOY)})
        self.assertEqual(r.status_code, 403, r.text)


class CobradoConLaCajaCerradaTest(Base):
    """Lo cobrado sin turno abierto (débito, crédito, transferencia) debe reflejarse al abrir el siguiente turno."""

    def setUp(self):
        super().setUp()
        self.cliente.post("/usuarios", json={"nombre": "caja1", "rol": "caja", "clave": "clave-caja1-x"}, headers=self.idem())
        self.caja = TestClient(self.app)
        self.caja.post("/sesion", json={"usuario": "caja1", "clave": "clave-caja1-x"})

    def test_la_transferencia_sin_turno_entra_en_la_cuadratura_del_turno_que_se_abre_despues(self):
        rid = self.reservar()
        self.assertEqual(self.pagar(rid, 30000, medio="transferencia").status_code, 201)  # caja cerrada
        turno = self.caja.post("/hotel/caja/turnos", headers=self.idem(), json={"fondo_inicial_clp": 20000})
        self.assertEqual(turno.status_code, 201, turno.text)
        estado = self.caja.get("/hotel/caja/estado").json()["turno"]
        self.assertEqual(estado["totales"]["por_medio"]["transferencia"], 30000)
        self.assertEqual(estado["totales"]["recibido_sin_turno_clp"], 30000)

    def test_lo_cobrado_despues_de_cerrar_un_turno_no_se_cuenta_dos_veces(self):
        rid = self.reservar()
        turno1 = self.caja.post("/hotel/caja/turnos", headers=self.idem(), json={"fondo_inicial_clp": 0}).json()["turno_id"]
        self.pagar(rid, 10000, medio="transferencia")
        c = self.caja.post(f"/hotel/caja/turnos/{turno1}/cierre", headers=self.idem(), json={"arqueo": {}})
        self.assertEqual(c.status_code, 200, c.text)
        self.pagar(rid, 5000, medio="transferencia")  # caja cerrada de nuevo
        self.caja.post("/hotel/caja/turnos", headers=self.idem(), json={"fondo_inicial_clp": 0})
        nuevo = self.caja.get("/hotel/caja/estado").json()["turno"]["totales"]
        self.assertEqual(nuevo["por_medio"]["transferencia"], 5000)  # solo lo posterior al cierre del turno 1
        primero = self.caja.get(f"/hotel/caja/turnos/{turno1}").json()["totales"]
        self.assertEqual(primero["por_medio"]["transferencia"], 10000)


if __name__ == "__main__":
    unittest.main()
