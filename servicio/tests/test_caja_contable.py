"""Fase 1 contable (2026-11-19): turnos de caja, medios de pago, retiros para
depósito, arqueo y cuadratura, reverso de pagos, cierre diario con bloqueo del
día, Caja del día en hora de Chile y exportación de contactos por rango.
HTTP contra PostgreSQL real, datos sintéticos."""
import os
import unittest
import uuid
from datetime import timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import contabilidad, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = contabilidad.hoy_chile()


class CajaContableTest(unittest.TestCase):
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
                "habitaciones, leads, contactos RESTART IDENTITY CASCADE"
            )
            conexion.execute("DELETE FROM ajustes WHERE empresa_id = %s AND clave = 'caja'", (EMPRESA,))
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            for hab in ("HAB-CONT-1", "HAB-CONT-2"):
                conexion.execute(
                    "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES (%s, 'EST-SINT-001', 'doble', 2)",
                    (hab,))
                conexion.execute(
                    "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                    "VALUES (%s, %s, '2026-01-01', '2027-12-31', 50000) ON CONFLICT (id) DO NOTHING",
                    (f"TAR-{hab}", hab))
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.admin = TestClient(self.app)
        self.assertEqual(self.admin.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)
        r = self.admin.post("/usuarios", json={"nombre": "caja1", "rol": "caja", "clave": "clave-caja1-x"},
                            headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        self.caja = TestClient(self.app)
        self.assertEqual(self.caja.post("/sesion", json={"usuario": "caja1", "clave": "clave-caja1-x"}).status_code, 200)

    # --- auxiliares ---
    def idem(self):
        return {"Idempotency-Key": f"k-{uuid.uuid4().hex[:12]}"}

    def reservar(self, hab="HAB-CONT-1", inicio=HOY, noches=2, con_cargo=True):
        r = self.admin.post("/hotel/reservas", headers=self.idem(), json={
            "habitacion_id": hab, "inicio": str(inicio), "fin": str(inicio + timedelta(days=noches)),
            "huesped": {"nombre": "Ana Contable", "documento": "11.111.111-1"}})
        self.assertEqual(r.status_code, 201, r.text)
        rid = r.json()["reserva_id"]
        if con_cargo:
            # ADP-4: la cuenta nace vacía (el alojamiento se asienta en la entrada); para probar saldos
            # se asienta aquí el alojamiento como cargo, igual que test_avisos_correo.
            c = self.admin.post(f"/hotel/reservas/{rid}/cargos", headers=self.idem(),
                                json={"concepto": "Alojamiento", "monto_clp": 50000 * noches})
            self.assertEqual(c.status_code, 201, c.text)
        return rid

    def pagar(self, rid, monto, cliente=None, **extra):
        return (cliente or self.caja).post(f"/hotel/reservas/{rid}/pagos", headers=self.idem(), json={
            "monto_clp": monto, "clave": f"c-{uuid.uuid4().hex[:6]}", "modo": "manual", **extra})

    def abrir(self, fondo=20000, cliente=None, **extra):
        return (cliente or self.caja).post("/hotel/caja/turnos", headers=self.idem(),
                                           json={"fondo_inicial_clp": fondo, **extra})

    def cerrar(self, turno_id, arqueo, cliente=None, **extra):
        return (cliente or self.caja).post(f"/hotel/caja/turnos/{turno_id}/cierre", headers=self.idem(),
                                           json={"arqueo": arqueo, **extra})

    # --- turnos ---
    def test_turno_completo_cuadra_por_medio(self):
        r = self.abrir(20000)
        self.assertEqual(r.status_code, 201, r.text)
        turno = r.json()["turno_id"]
        self.assertEqual(self.abrir(0).status_code, 409)  # una sola caja abierta
        rid = self.reservar()
        r = self.pagar(rid, 50000, medio="efectivo", documento_tipo="boleta")
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["turno_id"], turno)
        self.assertEqual(r.json()["fecha_contable"], HOY.isoformat())
        r = self.pagar(rid, 30000, medio="debito", codigo_autorizacion="A1B2C3", tarjeta_ultimos4="4321",
                       tarjeta_marca="Visa")
        self.assertEqual(r.status_code, 201, r.text)
        r = self.caja.post(f"/hotel/caja/turnos/{turno}/retiros", headers=self.idem(),
                           json={"monto_clp": 30000, "comprobante": "DEP-778899", "banco": "BancoEstado"})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["efectivo_en_caja_clp"], 40000)
        r = self.caja.post(f"/hotel/caja/turnos/{turno}/retiros", headers=self.idem(),
                           json={"monto_clp": 999999, "comprobante": "X-1"})
        self.assertEqual(r.status_code, 409)  # más que el efectivo esperado
        estado = self.caja.get("/hotel/caja/estado").json()
        totales = estado["turno"]["totales"]
        self.assertEqual(totales["por_medio"]["efectivo"], 50000)
        self.assertEqual(totales["por_medio"]["debito"], 30000)
        self.assertEqual(totales["efectivo_esperado_clp"], 40000)
        self.assertIn(20000, estado["parametros"]["denominaciones"])
        # Arqueo exacto: 2 × $20.000; débito declarado igual al sistema.
        r = self.cerrar(turno, {"20000": 2}, declarado={"debito": 30000})
        self.assertEqual(r.status_code, 200, r.text)
        cerrado = r.json()
        self.assertEqual(cerrado["estado"], "cerrado")
        self.assertEqual(cerrado["diferencia_clp"], 0)
        self.assertEqual(cerrado["entrega_siguiente_clp"], 40000)
        self.assertEqual(len(cerrado["movimientos"]), 3)
        self.assertEqual(self.cerrar(turno, {"20000": 2}).status_code, 409)  # ya cerrado

    def test_diferencia_exige_justificacion_y_entrega_al_turno_siguiente(self):
        turno = self.abrir(10000).json()["turno_id"]
        r = self.cerrar(turno, {"5000": 1})  # faltan $5.000
        self.assertEqual(r.status_code, 422)
        self.assertIn("justif", r.json()["detail"])
        r = self.cerrar(turno, {"5000": 1}, justificacion="Vuelto mal entregado a un huésped",
                        deposito={"monto_clp": 0})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["diferencia_clp"], -5000)
        self.assertEqual(r.json()["cuadratura"]["efectivo"]["diferencia_clp"], -5000)
        self.assertTrue(r.json()["cuadratura"]["requiere_revision"])
        pendiente = self.caja.get("/hotel/caja/estado").json()["entrega_pendiente"]
        self.assertEqual(pendiente["monto_clp"], 5000)
        self.assertEqual(self.abrir(9000).status_code, 422)  # no coincide y sin nota
        r = self.abrir(9000, nota="Faltaban 1.000 pesos en monedas al recibir")
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["recibido_de_turno_id"], turno)
        self.assertEqual(r.json()["diferencia_recepcion_clp"], 4000)

    def test_denominacion_inexistente_y_cierre_ajeno(self):
        turno = self.abrir(0, cliente=self.admin).json()["turno_id"]
        self.assertEqual(self.cerrar(turno, {"7000": 1}, cliente=self.admin).status_code, 422)
        r = self.cerrar(turno, {}, cliente=self.caja)
        self.assertEqual(r.status_code, 409)  # solo quien abrió o la administración

    # --- pagos ---
    def test_validaciones_del_pago_y_pci(self):
        rid = self.reservar()
        r = self.pagar(rid, 1000, medio="efectivo")
        self.assertEqual(r.status_code, 409)  # efectivo sin turno abierto
        self.assertIn("turno", r.json()["detail"])
        self.assertEqual(self.pagar(rid, 1000, medio="debito").status_code, 422)  # sin código de autorización
        r = self.pagar(rid, 1000, medio="credito", codigo_autorizacion="4111 1111 1111 1111")
        self.assertEqual(r.status_code, 422)
        self.assertIn("número completo", r.json()["detail"])
        self.assertEqual(self.pagar(rid, 1000, medio="credito", codigo_autorizacion="123", cvv="123").status_code, 422)
        self.assertEqual(self.pagar(rid, 1000, medio="transferencia", documento_tipo="factura").status_code, 422)
        r = self.pagar(rid, 1000, medio="transferencia", documento_tipo="factura", comprobante="TRX-55",
                       receptor={"rut": "76.707.504-0", "razon_social": "X", "giro": "Y", "direccion": "Z", "comuna": "Chillán"})
        self.assertEqual(r.status_code, 422)  # dígito verificador
        r = self.pagar(rid, 1000, medio="transferencia", documento_tipo="factura", comprobante="TRX-55",
                       receptor={"rut": "11.111.111-1", "razon_social": "Empresa Ejemplo SpA", "giro": "Servicios",
                                 "direccion": "Calle 1", "comuna": "Chillán"})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["documento_tipo"], "factura")
        self.assertIsNone(r.json()["turno_id"])  # transferencia sin turno: igual queda en el diario
        mov = self.caja.get("/hotel/caja/movimientos").json()["movimientos"]
        self.assertEqual([(m["medio"], m["monto_clp"]) for m in mov], [("transferencia", 1000)])
        # Sin medio (clientes anteriores): no_informado y documento pendiente.
        r = self.pagar(rid, 500)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual((r.json()["medio"], r.json()["documento_tipo"]), ("no_informado", "pendiente"))

    def test_anticipo_y_caja_del_dia_en_hora_de_chile(self):
        futura = self.reservar(inicio=HOY + timedelta(days=10), con_cargo=False)
        # La cuenta nace vacía: un anticipo es un pago sobre saldo 0 y se confirma como tal.
        r = self.pagar(futura, 25000, medio="transferencia", comprobante="TRX-1")
        self.assertEqual(r.status_code, 409, r.text)
        r = self.pagar(futura, 25000, medio="transferencia", comprobante="TRX-1", confirmar_exceso=True)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertTrue(r.json()["es_anticipo"])
        caja = self.caja.get(f"/hotel/caja?fecha={HOY.isoformat()}").json()
        self.assertEqual(caja["total_clp"], 25000)
        self.assertEqual(caja["por_medio"], {"transferencia": 25000})
        self.assertTrue(caja["pagos"][0]["es_anticipo"])
        con = self.caja.get(f"/hotel/caja/conciliacion?fecha={HOY.isoformat()}").json()
        self.assertEqual(con["cobros"]["anticipos_recibidos_clp"], 25000)
        self.assertEqual(con["cobros"]["anticipos_vigentes_clp"], 25000)

    def test_reverso_solo_admin_y_pagos_inmutables(self):
        self.abrir(0)
        rid = self.reservar()
        pago = self.pagar(rid, 40000, medio="efectivo").json()
        url = f"/hotel/reservas/{rid}/pagos/{pago['pago_id']}/reverso"
        self.assertEqual(self.caja.post(url, headers=self.idem(), json={"motivo": "Error de digitación"}).status_code, 403)
        self.assertEqual(self.admin.post(url, headers=self.idem(), json={"motivo": "corto"}).status_code, 422)
        r = self.admin.post(url, headers=self.idem(), json={"motivo": "Monto digitado en la reserva equivocada"})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["saldo_clp"], 100000)
        self.assertEqual(self.admin.post(url, headers=self.idem(), json={"motivo": "Otra vez lo mismo"}).status_code, 409)
        estado = self.caja.get("/hotel/caja/estado").json()
        self.assertEqual(estado["turno"]["totales"]["por_medio"]["efectivo"], 0)
        detalle = self.admin.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual([p["tipo"] for p in detalle["pagos"]], ["pago", "reverso"])
        self.assertTrue(detalle["pagos"][0]["reversado"])
        with psycopg.connect(URL_TEST) as conexion:
            with self.assertRaises(psycopg.errors.CheckViolation):
                conexion.execute("UPDATE pagos SET monto_clp = 1 WHERE id = %s", (pago["pago_id"],))
            conexion.rollback()
            with self.assertRaises(psycopg.errors.CheckViolation):
                conexion.execute("DELETE FROM caja_movimientos")
            conexion.rollback()

    # --- cierre diario ---
    def test_cierre_diario_bloquea_el_dia_y_mueve_lo_nuevo_al_siguiente(self):
        turno = self.abrir(0).json()["turno_id"]
        rid = self.reservar(con_cargo=False)  # la entrada asienta el alojamiento (100.000)
        self.assertEqual(self.admin.post(f"/hotel/reservas/{rid}/entrada", headers=self.idem()).status_code, 200)
        self.pagar(rid, 50000, medio="efectivo", documento_tipo="boleta")
        cuerpo = {"fecha": HOY.isoformat(), "confirmar_alertas": True}
        r = self.caja.post("/hotel/caja/cierres", headers=self.idem(), json=cuerpo)
        self.assertEqual(r.status_code, 409)  # turno abierto
        self.assertEqual(self.cerrar(turno, {"20000": 2, "10000": 1}).status_code, 200)
        con = self.caja.get(f"/hotel/caja/conciliacion?fecha={HOY.isoformat()}").json()
        fila = next(h for h in con["habitaciones"] if h["habitacion_id"] == "HAB-CONT-1")
        self.assertEqual((fila["estado"], fila["pagado_clp"], fila["saldo_clp"]), ("abonada", 50000, 50000))
        self.assertEqual(con["resumen"]["habitaciones_ocupadas"], 1)
        self.assertEqual(con["resumen"]["ocupacion_pct"], 50.0)
        self.assertEqual(con["cobros"]["por_medio"]["efectivo"], 50000)
        self.assertEqual(con["documentos"]["boleta"]["cantidad"], 1)
        r = self.caja.post("/hotel/caja/cierres", headers=self.idem(), json={"fecha": HOY.isoformat()})
        self.assertEqual(r.status_code, 201, r.text)  # sin alertas: no pide confirmar
        manana = (HOY + timedelta(days=1)).isoformat()
        self.assertEqual(r.json()["siguiente_fecha_contable"], manana)
        self.assertEqual(self.caja.post("/hotel/caja/cierres", headers=self.idem(),
                                        json={"fecha": HOY.isoformat()}).status_code, 409)
        # Lo nuevo de hoy cae en el día siguiente; el día cerrado no cambia.
        r = self.pagar(rid, 10000, medio="transferencia", comprobante="TRX-9")
        self.assertEqual(r.json()["fecha_contable"], manana)
        congelada = self.caja.get(f"/hotel/caja/conciliacion?fecha={HOY.isoformat()}").json()
        self.assertTrue(congelada["congelada"])
        self.assertEqual(congelada["cobros"]["total_clp"], 50000)
        self.assertEqual(self.caja.get(f"/hotel/caja?fecha={HOY.isoformat()}").json()["total_clp"], 50000)
        # Futuro: no se cierra. Reapertura: solo administración, con motivo.
        self.assertEqual(self.caja.post("/hotel/caja/cierres", headers=self.idem(),
                                        json={"fecha": (HOY + timedelta(days=3)).isoformat()}).status_code, 409)
        url = f"/hotel/caja/cierres/{HOY.isoformat()}/reapertura"
        self.assertEqual(self.caja.post(url, headers=self.idem(), json={"motivo": "Faltó registrar una boleta"}).status_code, 403)
        r = self.admin.post(url, headers=self.idem(), json={"motivo": "Faltó registrar una boleta"})
        self.assertEqual(r.status_code, 200, r.text)
        cierres = self.caja.get("/hotel/caja/cierres").json()
        self.assertEqual(cierres["cierres"][0]["estado"], "reabierto")
        self.assertEqual(cierres["fecha_contable"], HOY.isoformat())

    def test_cierre_con_alertas_exige_confirmar(self):
        rid = self.reservar(hab="HAB-CONT-2")
        self.assertEqual(self.admin.post(f"/hotel/reservas/{rid}/entrada", headers=self.idem()).status_code, 200)
        r = self.caja.post("/hotel/caja/cierres", headers=self.idem(), json={"fecha": HOY.isoformat()})
        self.assertEqual(r.status_code, 409)
        con = self.caja.get("/hotel/caja/conciliacion").json()
        self.assertTrue(any("sin pagos" in a for a in con["alertas"]))
        r = self.caja.post("/hotel/caja/cierres", headers=self.idem(),
                           json={"fecha": HOY.isoformat(), "confirmar_alertas": True, "nota": "Pagará mañana"})
        self.assertEqual(r.status_code, 201, r.text)

    def test_roles_y_parametros_desde_el_mantenedor(self):
        aseo = TestClient(self.app)
        self.admin.post("/usuarios", json={"nombre": "aseo1", "rol": "aseo", "clave": "clave-aseo1-x"}, headers=self.idem())
        aseo.post("/sesion", json={"usuario": "aseo1", "clave": "clave-aseo1-x"})
        self.assertEqual(aseo.get("/hotel/caja/estado").status_code, 403)
        # La administración apaga el débito y no exige turno para efectivo.
        r = self.admin.put("/hotel/ajustes/caja", headers=self.idem(), json={
            "medios": {"debito": {"activo": False}}, "exigir_turno_efectivo": False, "fondo_fijo_clp": 30000})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.admin.put("/hotel/ajustes/caja", headers=self.idem(),
                                        json={"denominaciones": [1000, 1000]}).status_code, 422)
        rid = self.reservar()
        self.assertEqual(self.pagar(rid, 1000, medio="debito", codigo_autorizacion="X1").status_code, 422)
        self.assertEqual(self.pagar(rid, 1000, medio="efectivo").status_code, 201)
        estado = self.caja.get("/hotel/caja/estado").json()
        self.assertEqual(estado["parametros"]["fondo_fijo_clp"], 30000)
        self.assertNotIn("debito", estado["parametros"]["medios"])

    # --- leads ---
    def test_exportacion_de_contactos_por_rango(self):
        with psycopg.connect(URL_TEST) as conexion:
            for i, dias in enumerate((40, 10, 1)):
                cid = f"CON-T{i}"
                conexion.execute("INSERT INTO contactos (id, empresa_id, nombre, correo) VALUES (%s, %s, %s, %s)",
                                 (cid, EMPRESA, f"Persona {i}", f"p{i}@ejemplo.cl"))
                conexion.execute(
                    "INSERT INTO leads (id, empresa_id, nombre, correo, telefono, contacto_id, creado_en, idempotency_key, cuerpo_hash) "
                    "VALUES (%s, %s, %s, %s, '+56911111111', %s, now() - make_interval(days => %s), %s, 'h')",
                    (f"LEAD-T{i}", EMPRESA, f"Persona {i}", f"p{i}@ejemplo.cl", cid, dias, f"idem-{i}"))
            conexion.commit()
        todos = self.admin.get("/hotel/leads/contactos").json()["contactos"]
        self.assertEqual(len(todos), 3)
        desde = (HOY - timedelta(days=15)).isoformat()
        r = self.admin.get(f"/hotel/leads/contactos?desde={desde}")
        self.assertEqual([c["correo"] for c in r.json()["contactos"]], ["p2@ejemplo.cl", "p1@ejemplo.cl"])
        hasta = (HOY - timedelta(days=5)).isoformat()
        r = self.admin.get(f"/hotel/leads/contactos?desde={desde}&hasta={hasta}")
        self.assertEqual([c["correo"] for c in r.json()["contactos"]], ["p1@ejemplo.cl"])
        self.assertEqual(self.admin.get(f"/hotel/leads/contactos?desde={hasta}&hasta={desde}").status_code, 422)


if __name__ == "__main__":
    unittest.main()
