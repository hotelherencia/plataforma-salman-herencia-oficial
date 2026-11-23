"""Pruebas Contable 2.6 (#396) y 2.7 (#397):
- Comisiones y desfase de abono configurables por medio (sin hardcoding).
- Importación CSV con vista previa, hash anti-duplicado y filas rechazadas.
- Cruce automático exacto (transferencia + tarjeta con comisión y desfase),
  pendiente/parcial y conciliación manual muchos-a-muchos con justificación auditada.
- Ventas de fin de mes en tránsito (suman al IVA del mes de la venta y figuran
  en tránsito para conciliación bancaria del mes siguiente).
- Resumen tributario F29 con notas de crédito (reversos) y sin integración SII."""
import os
import unittest
from datetime import date, timedelta
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient

from servicio import migracion, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_396_397",
)


class ConciliacionBancariaYTributariaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario="admin_bt", admin_clave="Clave123!",
        ))
        cls.client_cm = TestClient(cls.app)
        cls.client = cls.client_cm.__enter__()
        cls._n = 0

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "TRUNCATE conciliaciones_bancarias, cartola_movimientos, cartolas_bancarias, comisiones_medios, "
                "caja_movimientos, caja_turnos, movimientos_directos, imputaciones_pago, reserva_huespedes, huespedes, "
                "pagos, cargos, reserva_noches, reservas, documentos_proveedor, archivos_documentos, "
                "clientes, tarifas, excepciones_precio, habitaciones, claves_idempotencia, auditoria, sesiones, usuarios CASCADE"
            )
            clave_h = seguridad.hashear_clave("Clave123!")
            c.execute(
                "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                "('USR-BT-ADM', 'admin_bt', %s, 'admin_hotel', 'EMP-SINTETICA-001', true), "
                "('USR-BT-CAJ', 'caja_bt', %s, 'caja', 'EMP-SINTETICA-001', true), "
                "('USR-BT-REC', 'recep_bt', %s, 'recepcion', 'EMP-SINTETICA-001', true)",
                (clave_h, clave_h, clave_h),
            )
            c.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, estado_preparacion, en_inventario) "
                "VALUES ('HAB-BT1', 'EST-1', 'doble', 2, 'disponible', 'limpia', true)"
            )
            c.execute(
                "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, motivo, activa) "
                "VALUES ('EXC-BT1', 'HAB-BT1', '2026-10-01', '2026-12-31', 100000, 'base bt', true)"
            )
            c.commit()

        self.admin = self._login("admin_bt")
        self.caja = self._login("caja_bt")
        self.recep = self._login("recep_bt")

    def _login(self, usuario: str) -> TestClient:
        c = TestClient(self.app)
        r = c.post("/sesion", json={"usuario": usuario, "clave": "Clave123!"})
        self.assertEqual(r.status_code, 200, r.text)
        return c

    def _idem(self) -> dict:
        self.__class__._n += 1
        return {"Idempotency-Key": f"bt-{self.__class__._n}"}

    def _crear_reserva(self, inicio="2026-11-10", fin="2026-11-12", rut="12.345.678-5", nombre="Camila Banco"):
        r = self.admin.post(
            "/hotel/reservas",
            headers=self._idem(),
            json={
                "habitacion_id": "HAB-BT1", "inicio": inicio, "fin": fin, "personas": 1,
                "huesped": {"nombre": nombre, "documento": rut, "documento_tipo": "rut"},
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["reserva_id"]

    def test_migracion_0065_idempotente_y_comisiones_solo_admin(self):
        sql = Path("servicio/migraciones/0065_conciliacion_bancaria_tributaria.sql").read_text(encoding="utf-8")
        with psycopg.connect(URL_TEST) as c:
            c.execute(sql)
            c.execute(sql)
            c.commit()

        # Recepción -> 403; Caja no puede editar comisiones -> 403
        self.assertEqual(self.recep.get("/hotel/contabilidad/comisiones-medios").status_code, 403)
        self.assertEqual(
            self.caja.put(
                "/hotel/contabilidad/comisiones-medios",
                headers=self._idem(),
                json={"medios": [{"medio": "credito", "porcentaje_comision": 2.0, "iva_comision": False, "dias_habiles_abono": 2}]},
            ).status_code,
            403,
        )
        r = self.admin.put(
            "/hotel/contabilidad/comisiones-medios",
            headers=self._idem(),
            json={"medios": [
                {"medio": "credito", "proveedor": "transbank", "porcentaje_comision": 2.0, "iva_comision": False, "dias_habiles_abono": 2},
                {"medio": "debito", "proveedor": "transbank", "porcentaje_comision": 1.0, "iva_comision": False, "dias_habiles_abono": 1},
            ]},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["comisiones"]["credito"]["porcentaje_comision"], 2.0)

    def test_26_conciliacion_bancaria_automatica_parcial_manual_y_transito(self):
        # Configurar comisión crédito = 2% (sin IVA comisión) y 2 días hábiles de abono
        self.admin.put(
            "/hotel/contabilidad/comisiones-medios",
            headers=self._idem(),
            json={"medios": [
                {"medio": "credito", "proveedor": "transbank", "porcentaje_comision": 2.0, "iva_comision": False, "dias_habiles_abono": 2},
            ]},
        )
        rid = self._crear_reserva()
        # Pago 1: transferencia $100.000 el día 2026-11-10
        p1 = self.caja.post(
            f"/hotel/reservas/{rid}/pagos",
            headers=self._idem(),
            json={"monto_clp": 100000, "clave": "trf-1", "modo": "manual", "medio": "transferencia",
                  "documento_tipo": "boleta", "comprobante": "TRF-8811"},
        )
        self.assertEqual(p1.status_code, 201, p1.text)
        # Pago 2: crédito $100.000 (abono esperado = $98.000 tras 2% comisión, +2 días hábiles -> 2026-11-12)
        p2 = self.caja.post(
            f"/hotel/reservas/{rid}/pagos",
            headers=self._idem(),
            json={"monto_clp": 100000, "clave": "crd-1", "modo": "manual", "medio": "credito",
                  "documento_tipo": "boleta", "codigo_autorizacion": "AUT991"},
        )
        self.assertEqual(p2.status_code, 201, p2.text)

        # Ajustar fecha_contable de ambos pagos y movimientos de caja a 2026-11-10 para prueba determinística
        with psycopg.connect(URL_TEST) as c:
            c.execute("ALTER TABLE pagos DISABLE TRIGGER pagos_inmutables")
            c.execute("ALTER TABLE caja_movimientos DISABLE TRIGGER caja_movimientos_inmutables")
            c.execute("UPDATE pagos SET fecha_contable = '2026-11-10'")
            c.execute("UPDATE caja_movimientos SET fecha_contable = '2026-11-10'")
            c.execute("ALTER TABLE pagos ENABLE TRIGGER pagos_inmutables")
            c.execute("ALTER TABLE caja_movimientos ENABLE TRIGGER caja_movimientos_inmutables")
            c.commit()

        # Cartola CSV con: 1 transferencia exacta, 1 liquidación tarjeta exacta ($98.000), 1 parcial/sin calce, 1 fila inválida
        csv_cartola = (
            "Fecha;Descripcion;Referencia;Monto\n"
            "2026-11-10;TEF recibida Camila;TRF-8811;100000\n"
            "2026-11-12;Abono Transbank Credito;TBK-001;98000\n"
            "2026-11-15;Abono parcial sin calce;PARC-01;50000\n"
            "fecha-mala;Fila corrupta;ERR;abc\n"
        )
        prev = self.caja.post("/hotel/contabilidad/cartolas/vista-previa", json={"contenido_csv": csv_cartola})
        self.assertEqual(prev.status_code, 200, prev.text)
        self.assertEqual(prev.json()["filas_validas"], 3)
        self.assertEqual(prev.json()["filas_rechazadas"], 1)
        self.assertFalse(prev.json()["duplicada"])

        imp = self.caja.post(
            "/hotel/contabilidad/cartolas",
            headers=self._idem(),
            json={"banco": "BancoEstado", "cuenta": "12345678", "periodo": "2026-11", "contenido_csv": csv_cartola},
        )
        self.assertEqual(imp.status_code, 201, imp.text)
        self.assertEqual(imp.json()["conciliados_automaticamente"], 2)
        self.assertEqual(imp.json()["pendientes"], 1)

        # Misma cartola (SHA-256) no se duplica -> 409
        dup = self.caja.post(
            "/hotel/contabilidad/cartolas",
            headers=self._idem(),
            json={"banco": "BancoEstado", "cuenta": "12345678", "periodo": "2026-11", "contenido_csv": csv_cartola},
        )
        self.assertEqual(dup.status_code, 409)

        # Crear otro pago de transferencia $80.000 para conciliar manualmente (parcial) contra el abono de $50.000
        p3 = self.caja.post(
            f"/hotel/reservas/{rid}/pagos",
            headers=self._idem(),
            json={"monto_clp": 80000, "clave": "trf-parcial", "modo": "manual", "medio": "transferencia",
                  "documento_tipo": "boleta", "confirmar_exceso": True},
        )
        self.assertEqual(p3.status_code, 201, p3.text)

        est = self.caja.get("/hotel/contabilidad/cartolas", params={"periodo": "2026-11"}).json()
        mov_pend = next(m for m in est["movimientos_cartola"] if m["estado"] == "pendiente")
        int_pend = est["internos_pendientes"][0]

        # Sin justificación suficiente -> 422
        r_mal = self.caja.post(
            "/hotel/contabilidad/conciliacion-bancaria/emparejar",
            headers=self._idem(),
            json={
                "cartola_movimiento_id": mov_pend["cartola_movimiento_id"],
                "caja_movimiento_id": int_pend["caja_movimiento_id"],
                "monto_asignado_clp": 30000,
                "justificacion": "corto",
            },
        )
        self.assertEqual(r_mal.status_code, 422)

        # Emparejamiento parcial manual válido ($30.000 de $50.000) -> estado 'parcial'
        r_ok = self.caja.post(
            "/hotel/contabilidad/conciliacion-bancaria/emparejar",
            headers=self._idem(),
            json={
                "cartola_movimiento_id": mov_pend["cartola_movimiento_id"],
                "caja_movimiento_id": int_pend["caja_movimiento_id"],
                "monto_asignado_clp": 30000,
                "justificacion": "Emparejamiento parcial verificado contra comprobante bancario",
            },
        )
        self.assertEqual(r_ok.status_code, 201, r_ok.text)
        self.assertEqual(r_ok.json()["estado_cartola_movimiento"], "parcial")

        # Superar el saldo restante ($25.000 > $20.000 disponibles en cartola) -> 409
        r_exc = self.caja.post(
            "/hotel/contabilidad/conciliacion-bancaria/emparejar",
            headers=self._idem(),
            json={
                "cartola_movimiento_id": mov_pend["cartola_movimiento_id"],
                "caja_movimiento_id": int_pend["caja_movimiento_id"],
                "monto_asignado_clp": 25000,
                "justificacion": "Intento que excede disponible del movimiento bancario",
            },
        )
        self.assertEqual(r_exc.status_code, 409)

    def test_27_tributario_f29_iva_mes_transito_y_nota_credito(self):
        # Configurar desfase crédito = 2 días hábiles
        self.admin.put(
            "/hotel/contabilidad/comisiones-medios",
            headers=self._idem(),
            json={"medios": [
                {"medio": "credito", "proveedor": "transbank", "porcentaje_comision": 2.0, "iva_comision": True, "dias_habiles_abono": 2},
            ]},
        )
        rid = self._crear_reserva(inicio="2026-11-29", fin="2026-12-01")
        # Venta con boleta por $119.000 con tarjeta crédito el último día de noviembre (30-11-2026 -> abona en diciembre!)
        p_bol = self.caja.post(
            f"/hotel/reservas/{rid}/pagos",
            headers=self._idem(),
            json={"monto_clp": 119000, "clave": "bol-finmes", "modo": "manual", "medio": "credito",
                  "documento_tipo": "boleta", "codigo_autorizacion": "AUT777"},
        )
        self.assertEqual(p_bol.status_code, 201, p_bol.text)
        # Venta con boleta por $59.500 y luego reverso (nota de crédito) dentro del mismo mes
        p_rev = self.caja.post(
            f"/hotel/reservas/{rid}/pagos",
            headers=self._idem(),
            json={"monto_clp": 59500, "clave": "bol-rev", "modo": "manual", "medio": "transferencia",
                  "documento_tipo": "boleta"},
        )
        self.assertEqual(p_rev.status_code, 201, p_rev.text)
        pago_rev_id = p_rev.json()["pago_id"]
        rr = self.admin.post(
            f"/hotel/reservas/{rid}/pagos/{pago_rev_id}/reverso",
            headers=self._idem(),
            json={"motivo": "Nota de crédito por cobro duplicado en recepción"},
        )
        self.assertEqual(rr.status_code, 201, rr.text)

        # Fijar fecha_contable al 2026-11-30 para probar tránsito hacia diciembre y mes calendario exacto
        with psycopg.connect(URL_TEST) as c:
            c.execute("ALTER TABLE pagos DISABLE TRIGGER pagos_inmutables")
            c.execute("ALTER TABLE caja_movimientos DISABLE TRIGGER caja_movimientos_inmutables")
            c.execute("UPDATE pagos SET fecha_contable = '2026-11-30'")
            c.execute("UPDATE caja_movimientos SET fecha_contable = '2026-11-30'")
            c.execute("ALTER TABLE pagos ENABLE TRIGGER pagos_inmutables")
            c.execute("ALTER TABLE caja_movimientos ENABLE TRIGGER caja_movimientos_inmutables")
            c.commit()

        # Consultar resumen tributario 2026-11
        rt = self.caja.get("/hotel/contabilidad/tributario", params={"anio": 2026, "mes": 11})
        self.assertEqual(rt.status_code, 200, rt.text)
        d = rt.json()
        self.assertFalse(d["integracion_sii"])
        # Boletas: 119.000 + 59.500 = 178.500; Nota de crédito (reverso): -59.500 -> Neto final 100.000 + IVA 19.000 = 119.000
        self.assertEqual(d["por_documento"]["boleta"]["total_clp"], 178500)
        self.assertEqual(d["por_documento"]["nota_credito"]["total_clp"], -59500)
        self.assertEqual(d["borrador_f29"]["ventas_tributarias_total_clp"], 119000)
        self.assertEqual(d["borrador_f29"]["ventas_tributarias_neto_clp"], 100000)
        self.assertEqual(d["borrador_f29"]["debito_fiscal_clp"], 19000)
        # La venta con crédito del 30-11 suma al IVA de noviembre Y aparece en tránsito (abono diciembre)
        self.assertEqual(len(d["ventas_en_transito"]), 1)
        self.assertEqual(d["ventas_en_transito"][0]["total_clp"], 119000)
        self.assertTrue(d["ventas_en_transito"][0]["fecha_abono_estimada"].startswith("2026-12-"))

        # Exportar CSV F29
        rcsv = self.caja.get("/hotel/contabilidad/tributario/exportar.csv", params={"anio": 2026, "mes": 11})
        self.assertEqual(rcsv.status_code, 200)
        self.assertIn("Débito fiscal", rcsv.content.decode("utf-8-sig"))

        # Recepción no accede -> 403
        self.assertEqual(self.recep.get("/hotel/contabilidad/tributario", params={"anio": 2026, "mes": 11}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
