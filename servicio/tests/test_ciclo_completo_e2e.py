"""Ciclo completo E2E de una reserva (landing → plataforma → cierre diario) y casos borde (2026-11-19).

Recorre de punta a punta el ciclo real contra PostgreSQL:
  Lead web → /publico/referencia → /publico/disponibilidad → /publico/solicitudes →
  conversión en reserva → anticipo con caja cerrada → cambio de tarifa previo →
  Llegada (savepoint ante 409, congelamiento de reserva_noches, aplicación de anticipos) →
  cargos de producto (stock) y movimiento directo sin habitación → apertura de turno →
  pago final con factura (RUT) → Salida y liquidación → Aseo y verificación →
  arqueo, retiro a banco y Cierre diario.
Además ejercita los casos borde críticos verificados en la auditoría E2E.
"""
import os
import unittest
import uuid
from datetime import date, datetime, time, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import contabilidad, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests.reloj import a_las

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")


class CicloCompletoE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        self.hoy = contabilidad.hoy_chile()
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "TRUNCATE auditoria, avisos_envios, avisos_eventos, tareas_operativas, claves_idempotencia, liquidaciones, "
                "efectos_nucleo, caja_movimientos, movimientos_directos, caja_turnos, cierres_diarios, pagos, "
                "cargos, reservas, solicitudes, leads, contactos, tarifas, sesiones, usuarios, habitaciones, "
                "clientes, movimientos_stock, productos RESTART IDENTITY CASCADE"
            )
            conexion.execute("DELETE FROM ajustes WHERE empresa_id = %s AND clave = 'caja'", (EMPRESA,))
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                "VALUES ('HAB-E2E-1', 'EST-SINT-001', 'doble', 2), ('HAB-E2E-2', 'EST-SINT-001', 'doble', 2)"
            )
            conexion.execute(
                "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                "VALUES ('TAR-E2E-1', 'HAB-E2E-1', '2026-01-01', '2027-12-31', 50000), "
                "('TAR-E2E-2', 'HAB-E2E-2', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.app.state.freno_solicitudes.max_por_minuto = 100
        self.publico = TestClient(self.app)
        self.staff = TestClient(self.app)
        self.assertEqual(self.staff.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)

    def idem(self):
        return {"Idempotency-Key": f"e2e-{uuid.uuid4().hex[:10]}"}

    def test_ciclo_completo_landing_hasta_cierre_diario(self):
        inicio = self.hoy
        fin = self.hoy + timedelta(days=2)

        # 1. Lead desde hotelherencia.cl
        r_lead = self.publico.post(
            "/publico/leads",
            headers=self.idem(),
            json={
                "nombre": "Camila Viajera",
                "correo": "camila@ejemplo.cl",
                "telefono": "+56987654321",
                "huespedes": 2,
                "check_in": inicio.isoformat(),
                "check_out": fin.isoformat(),
                "mensaje": "Llegamos en auto, necesitamos estacionamiento.",
            },
        )
        self.assertEqual(r_lead.status_code, 201, r_lead.text)
        ref = r_lead.json()["referencia"]
        self.assertTrue(ref)

        # 2. Continuidad en /reservar?ref=... (solo nombre y correo, sin teléfono ni datos internos)
        r_ref = self.publico.get("/publico/referencia", params={"token": ref})
        self.assertEqual(r_ref.status_code, 200, r_ref.text)
        self.assertEqual(r_ref.json()["nombre"], "Camila Viajera")
        self.assertEqual(r_ref.json()["correo"], "camila@ejemplo.cl")
        self.assertNotIn("telefono", r_ref.json())

        # 3. Disponibilidad pública (por tipo, sin revelar habitacion_id)
        r_disp = self.publico.get(
            "/publico/disponibilidad",
            params={"inicio": inicio.isoformat(), "fin": fin.isoformat(), "personas": 2},
        )
        self.assertEqual(r_disp.status_code, 200, r_disp.text)
        oferta = r_disp.json()["oferta"]
        self.assertEqual(len(oferta), 2)
        self.assertTrue(all("habitacion_id" not in o for o in oferta))
        self.assertEqual(oferta[0]["total_clp"], 100000)

        # 4. Envío de solicitud pública
        r_sol = self.publico.post(
            "/publico/solicitudes",
            headers=self.idem(),
            json={
                "tipo": "doble",
                "inicio": inicio.isoformat(),
                "fin": fin.isoformat(),
                "personas": 2,
                "huesped_nombre": "Camila Viajera",
                "huesped_contacto": "camila@ejemplo.cl",
            },
        )
        self.assertEqual(r_sol.status_code, 201, r_sol.text)
        sol_id = r_sol.json()["solicitud_id"]
        self.assertNotIn("habitacion_id", r_sol.json())

        # 5. Recepción convierte la solicitud en reserva confirmada (cuenta nace vacía, reserva_noches congeladas)
        r_conv = self.staff.post(f"/hotel/solicitudes/{sol_id}/conversion", headers=self.idem(), json={})
        self.assertEqual(r_conv.status_code, 201, r_conv.text)
        rid = r_conv.json()["reserva_id"]
        hab_id = r_conv.json()["habitacion_id"]
        self.assertIn(hab_id, ("HAB-E2E-1", "HAB-E2E-2"))

        # 6. Anticipo pre-Llegada por transferencia con CAJA CERRADA ($40.000)
        r_ant = self.staff.post(
            f"/hotel/reservas/{rid}/pagos",
            headers=self.idem(),
            json={"monto_clp": 40000, "clave": "ant-1", "modo": "manual", "medio": "transferencia", "documento_tipo": "boleta"},
        )
        self.assertEqual(r_ant.status_code, 201, r_ant.text)
        self.assertTrue(r_ant.json()["es_anticipo"])
        saldo_pre = self.staff.get(f"/hotel/reservas/{rid}/saldo").json()
        self.assertEqual((saldo_pre["total_clp"], saldo_pre["abonado_clp"], saldo_pre["pendiente_clp"]), (100000, 40000, 60000))

        # 7. Caso borde: sube la tarifa vigente a $80.000 antes de la Llegada; e intento de Llegada antes de 15:00 con documento
        with psycopg.connect(URL_TEST) as c:
            c.execute("UPDATE excepciones_precio SET precio_clp = 80000 WHERE habitacion_id = %s", (hab_id,))
            c.commit()
        with a_las(inicio, hora=time(11, 0)):
            r_temprano = self.staff.post(
                f"/hotel/reservas/{rid}/entrada",
                headers=self.idem(),
                json={"documento": "12.345.678-5", "documento_tipo": "rut"},
            )
        self.assertEqual(r_temprano.status_code, 409, r_temprano.text)
        # Savepoint: el documento NO debe haber quedado parcialmente guardado tras el 409
        det_post_409 = self.staff.get(f"/hotel/reservas/{rid}").json()
        self.assertIsNone(det_post_409.get("huesped_documento"))

        # 8. Llegada válida (15:30) con documento: congela noches a $50.000 (NO $80.000) y aplica anticipo de $40.000
        with a_las(inicio, hora=time(15, 30)):
            r_ent = self.staff.post(
                f"/hotel/reservas/{rid}/entrada",
                headers=self.idem(),
                json={"documento": "12.345.678-5", "documento_tipo": "rut"},
            )
        self.assertEqual(r_ent.status_code, 200, r_ent.text)
        saldo_post_ent = self.staff.get(f"/hotel/reservas/{rid}/saldo").json()
        self.assertEqual(
            (saldo_post_ent["total_clp"], saldo_post_ent["abonado_clp"], saldo_post_ent["pagado_clp"], saldo_post_ent["pendiente_clp"]),
            (100000, 0, 40000, 60000),
        )
        self.assertEqual([n["precio_clp"] for n in saldo_post_ent["noches"]], [50000, 50000])

        # 9. Cargos en estadía (producto con stock) + movimiento directo sin habitación con caja cerrada
        prod = self.staff.post(
            "/hotel/productos",
            headers=self.idem(),
            json={"nombre": "Agua mineral", "categoria": "minibar", "precio_clp": 2000, "controla_stock": True, "stock": 10},
        ).json()
        r_cargo = self.staff.post(
            f"/hotel/reservas/{rid}/cargos",
            headers=self.idem(),
            json={"producto_id": prod["producto_id"], "cantidad": 2},
        )
        self.assertEqual(r_cargo.status_code, 201, r_cargo.text)
        self.assertEqual(self.staff.get("/hotel/productos").json()["productos"][0]["stock"], 8)

        # Cargo directo sin habitación con caja cerrada (pendiente de cobro)
        r_dir = self.staff.post(
            "/hotel/contabilidad/movimientos-directos",
            headers=self.idem(),
            json={
                "tipo": "cargo_directo",
                "categoria": "estacionamiento",
                "concepto": "Estacionamiento visitante",
                "monto_clp": 6000,
                "estado_cobro": "pendiente",
            },
        )
        self.assertEqual(r_dir.status_code, 201, r_dir.text)
        dir_id = r_dir.json()["movimiento_directo_id"]

        # 10. Apertura de turno de caja: debe absorber el anticipo de $40.000 cobrado sin turno
        r_turno = self.staff.post("/hotel/caja/turnos", headers=self.idem(), json={"fondo_inicial_clp": 20000})
        self.assertEqual(r_turno.status_code, 201, r_turno.text)
        turno_id = r_turno.json()["turno_id"]
        det_turno = self.staff.get(f"/hotel/caja/turnos/{turno_id}").json()
        self.assertEqual(det_turno["totales"]["recibido_sin_turno_clp"], 40000)
        self.assertEqual(len(det_turno["movimientos"]), 1)

        # 11. Salida con saldo pendiente ($64.000) bloquea 409; luego pago en efectivo con factura + cobro directo
        self.assertEqual(self.staff.post(f"/hotel/reservas/{rid}/salida", headers=self.idem(), json={}).status_code, 409)
        r_pago2 = self.staff.post(
            f"/hotel/reservas/{rid}/pagos",
            headers=self.idem(),
            json={
                "monto_clp": 64000, "clave": "fin-1", "modo": "manual", "medio": "efectivo",
                "documento_tipo": "factura",
                "receptor": {"rut": "7.000.013-K", "razon_social": "Empresa Demo SpA", "giro": "Servicios",
                             "direccion": "Calle 1", "comuna": "Chillán"},
            },
        )
        self.assertEqual(r_pago2.status_code, 201, r_pago2.text)
        pago2_id = r_pago2.json()["pago_id"]

        r_cobro_dir = self.staff.post(
            f"/hotel/contabilidad/movimientos-directos/{dir_id}/cobrar",
            headers=self.idem(),
            json={"medio": "efectivo", "documento_tipo": "boleta"},
        )
        self.assertEqual(r_cobro_dir.status_code, 200, r_cobro_dir.text)

        # 12. Salida y liquidación (saldo 0); luego reversar pago post-salida debe bloquear 409
        r_sal = self.staff.post(f"/hotel/reservas/{rid}/salida", headers=self.idem(), json={})
        self.assertEqual(r_sal.status_code, 200, r_sal.text)
        self.assertEqual((r_sal.json()["total_clp"], r_sal.json()["pagado_clp"], r_sal.json()["saldo_clp"]), (104000, 104000, 0))
        r_rev_post = self.staff.post(
            f"/hotel/reservas/{rid}/pagos/{pago2_id}/reverso",
            headers=self.idem(),
            json={"motivo": "Intento de reverso después de liquidar la salida"},
        )
        self.assertEqual(r_rev_post.status_code, 409, r_rev_post.text)

        # 13. Aseo completa limpieza y administración la verifica
        self.assertEqual(self.staff.post(f"/hotel/habitaciones/{hab_id}/limpieza", headers=self.idem(), json={}).status_code, 200)
        aseo = self.staff.get("/hotel/aseo").json()
        hab_aseo = next(h for h in aseo["habitaciones"] if h["habitacion_id"] == hab_id)
        self.assertEqual(hab_aseo["estado_preparacion"], "limpia")
        r_ver = self.staff.post(
            f"/hotel/limpiezas/{hab_aseo['ultima_limpieza']['tarea_id']}/verificacion",
            headers=self.idem(),
            json={"aprobada": True},
        )
        self.assertEqual(r_ver.status_code, 200, r_ver.text)
        self.assertEqual(r_ver.json()["estado_preparacion"], "inspeccionada")

        # 14. Retiro a banco ($50.000), cierre de turno con arqueo exacto ($40.000) y Cierre diario
        # Efectivo esperado: fondo 20.000 + pago2 64.000 + directo 6.000 = 90.000 - retiro 50.000 = 40.000
        r_ret = self.staff.post(
            f"/hotel/caja/turnos/{turno_id}/retiros",
            headers=self.idem(),
            json={"monto_clp": 50000, "comprobante": "DEP-E2E-01"},
        )
        self.assertEqual(r_ret.status_code, 201, r_ret.text)
        self.assertEqual(r_ret.json()["efectivo_en_caja_clp"], 40000)

        r_cierre_t = self.staff.post(
            f"/hotel/caja/turnos/{turno_id}/cierre",
            headers=self.idem(),
            json={"arqueo": {"20000": 2}, "declarado": {"debito": 0, "credito": 0, "transferencia": 40000}},
        )
        self.assertEqual(r_cierre_t.status_code, 200, r_cierre_t.text)
        self.assertEqual(r_cierre_t.json()["diferencia_clp"], 0)

        conc = self.staff.get("/hotel/caja/conciliacion", params={"fecha": self.hoy.isoformat()}).json()
        self.assertEqual(conc["resumen"]["ingreso_alojamiento_clp"], 50000)
        self.assertEqual(conc["resumen"]["ingreso_consumos_reserva_clp"], 4000)
        self.assertEqual(conc["resumen"]["ingreso_directo_clp"], 6000)
        self.assertEqual(conc["resumen"]["total_ingresos_devengados_clp"], 60000)
        self.assertEqual(conc["cobros"]["total_clp"], 110000)
        self.assertEqual(conc["cobros"]["depositos_clp"], 50000)
        self.assertEqual(conc["documentos"]["boleta"]["monto_clp"], 46000)
        self.assertEqual(conc["documentos"]["factura"]["monto_clp"], 64000)

        r_cierre_d = self.staff.post(
            "/hotel/caja/cierres",
            headers=self.idem(),
            json={"fecha": self.hoy.isoformat(), "confirmar_alertas": True},
        )
        self.assertEqual(r_cierre_d.status_code, 201, r_cierre_d.text)
        self.assertGreater(r_cierre_d.json()["siguiente_fecha_contable"], self.hoy.isoformat())

    def test_casos_borde_solicitud_idempotente_y_hora_invalida(self):
        inicio = self.hoy + timedelta(days=5)
        fin = self.hoy + timedelta(days=6)
        # Hora 99:99 no debe provocar HTTP 500
        r_bad = self.publico.get(
            "/publico/disponibilidad",
            params={"inicio": inicio.isoformat(), "fin": fin.isoformat(), "personas": 2, "hora_llegada": "99:99"},
        )
        self.assertEqual(r_bad.status_code, 422, r_bad.text)

        # Solicitud con Idempotency-Key fija; luego se agotan TODAS las habitaciones del tipo; el reintento devuelve 200 reintento=True
        clave_fija = {"Idempotency-Key": "retry-ultima-hab-1"}
        cuerpo = {
            "tipo": "doble", "inicio": inicio.isoformat(), "fin": fin.isoformat(),
            "personas": 2, "huesped_nombre": "Pedro Retry", "huesped_contacto": "pedro@ejemplo.cl",
        }
        r1 = self.publico.post("/publico/solicitudes", headers=clave_fija, json=cuerpo)
        self.assertEqual(r1.status_code, 201, r1.text)
        # Ocupamos ambas habitaciones dobles para agotar el cupo
        for hid in ("HAB-E2E-1", "HAB-E2E-2"):
            self.assertEqual(
                self.staff.post(
                    "/hotel/reservas", headers=self.idem(),
                    json={"habitacion_id": hid, "inicio": inicio.isoformat(), "fin": fin.isoformat(),
                          "huesped": {"nombre": "Otro", "documento": "11.111.111-1"}},
                ).status_code,
                201,
            )
        r2 = self.publico.post("/publico/solicitudes", headers=clave_fija, json=cuerpo)
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertTrue(r2.json()["reintento"])
        self.assertEqual(r2.json()["solicitud_id"], r1.json()["solicitud_id"])

    def test_caso_borde_rechazo_verificacion_limpieza_en_habitacion_ocupada_es_409(self):
        # Huésped A entra hoy→mañana, paga y hace Salida → Aseo limpia (limpia) → Huésped B entra (ocupada)
        # → Admin intenta rechazar la limpieza vieja (debe dar 409 para no marcar sucia una habitación ocupada!)
        r_a = self.staff.post(
            "/hotel/reservas", headers=self.idem(),
            json={"habitacion_id": "HAB-E2E-1", "inicio": self.hoy.isoformat(),
                  "fin": (self.hoy + timedelta(days=1)).isoformat(),
                  "huesped": {"nombre": "Huésped A", "documento": "11.111.111-1"}},
        ).json()["reserva_id"]
        with a_las(self.hoy, hora=time(15, 30)):
            self.assertEqual(self.staff.post(f"/hotel/reservas/{r_a}/entrada", headers=self.idem(), json={}).status_code, 200)
        self.assertEqual(
            self.staff.post(
                f"/hotel/reservas/{r_a}/pagos", headers=self.idem(),
                json={"monto_clp": 50000, "clave": "pa-1", "modo": "manual", "medio": "transferencia", "documento_tipo": "boleta"},
            ).status_code,
            201,
        )
        self.assertEqual(self.staff.post(f"/hotel/reservas/{r_a}/salida", headers=self.idem(), json={}).status_code, 200)
        self.assertEqual(self.staff.post("/hotel/habitaciones/HAB-E2E-1/limpieza", headers=self.idem(), json={}).status_code, 200)
        tarea_id = next(
            h["ultima_limpieza"]["tarea_id"]
            for h in self.staff.get("/hotel/aseo").json()["habitaciones"]
            if h["habitacion_id"] == "HAB-E2E-1"
        )
        manana = self.hoy + timedelta(days=1)
        r_b = self.staff.post(
            "/hotel/reservas", headers=self.idem(),
            json={"habitacion_id": "HAB-E2E-1", "inicio": manana.isoformat(),
                  "fin": (manana + timedelta(days=1)).isoformat(),
                  "huesped": {"nombre": "Huésped B", "documento": "12.345.678-5"}},
        ).json()["reserva_id"]
        with a_las(manana, hora=time(15, 30)):
            self.assertEqual(self.staff.post(f"/hotel/reservas/{r_b}/entrada", headers=self.idem(), json={}).status_code, 200)
        r_rechazo_aseo = self.staff.post(
            f"/hotel/limpiezas/{tarea_id}/verificacion",
            headers=self.idem(),
            json={"aprobada": False, "observacion": "Faltó limpiar baño"},
        )
        self.assertEqual(r_rechazo_aseo.status_code, 409, r_rechazo_aseo.text)
        self.assertIn("ocupada", r_rechazo_aseo.json()["detail"].lower())

    def test_caso_borde_cancelacion_devuelve_stock_de_cargo_producto(self):
        prod = self.staff.post(
            "/hotel/productos", headers=self.idem(),
            json={"nombre": "Vino reserva", "categoria": "minibar", "precio_clp": 15000, "controla_stock": True, "stock": 5},
        ).json()
        inicio = self.hoy + timedelta(days=10)
        rid = self.staff.post(
            "/hotel/reservas", headers=self.idem(),
            json={"habitacion_id": "HAB-E2E-1", "inicio": inicio.isoformat(),
                  "fin": (inicio + timedelta(days=2)).isoformat(),
                  "huesped": {"nombre": "Carlos Cancel", "documento": "11.111.111-1"}},
        ).json()["reserva_id"]
        self.assertEqual(
            self.staff.post(
                f"/hotel/reservas/{rid}/cargos", headers=self.idem(),
                json={"producto_id": prod["producto_id"], "cantidad": 2},
            ).status_code,
            201,
        )
        self.assertEqual(self.staff.get("/hotel/productos").json()["productos"][0]["stock"], 3)
        r_canc = self.staff.post(f"/hotel/reservas/{rid}/cancelacion", headers=self.idem(), json={})
        self.assertEqual(r_canc.status_code, 200, r_canc.text)
        self.assertEqual(self.staff.get("/hotel/productos").json()["productos"][0]["stock"], 5)


if __name__ == "__main__":
    unittest.main()
