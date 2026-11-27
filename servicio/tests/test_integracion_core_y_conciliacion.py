"""Pruebas de:
1. Contrato de exportación read-only `GET /integrations/core/v1/finance-export`
   (autenticación servicio-a-servicio, denegación 503/401/403, límites 422/400,
   paginación determinista, consistencia `as_of`, minimización de PII y reversos).
2. Regresión aislada de `conciliacion_bancaria.py` (precisión Decimal sin float
   y bloqueo de auto-conciliación solo por monto sin evidencia secundaria).
"""
import os
import unittest
from decimal import Decimal

import psycopg
from fastapi.testclient import TestClient

from servicio import conciliacion_bancaria, migracion, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_core_export",
)
TOKEN_SERVICIO = "tok-core-export-sintetico-verificacion-2026"


class IntegracionCoreYConciliacionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(
            configuracion=Configuracion(
                host="127.0.0.1",
                puerto=0,
                database_url=URL_TEST,
                cookie_segura=False,
                origen_front=None,
                admin_usuario="admin_ce",
                admin_clave="Clave123!",
                core_export_token=TOKEN_SERVICIO,
            )
        )
        cls.app_sin_token = crear_app(
            configuracion=Configuracion(
                host="127.0.0.1",
                puerto=0,
                database_url=URL_TEST,
                cookie_segura=False,
                origen_front=None,
                admin_usuario="admin_ce",
                admin_clave="Clave123!",
                core_export_token=None,
            )
        )
        cls.client = TestClient(cls.app)
        cls.client_sin_token = TestClient(cls.app_sin_token)
        cls._n = 0

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "TRUNCATE conciliaciones_bancarias, cartola_movimientos, cartolas_bancarias, comisiones_medios, "
                "caja_movimientos, caja_turnos, movimientos_directos, imputaciones_pago, reserva_huespedes, huespedes, "
                "pagos, cargos, reserva_noches, liquidaciones, reservas, documentos_proveedor, archivos_documentos, "
                "clientes, tarifas, excepciones_precio, habitaciones, claves_idempotencia, auditoria, sesiones, usuarios CASCADE"
            )
            clave_h = seguridad.hashear_clave("Clave123!")
            c.execute(
                "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                "('USR-CE-ADM', 'admin_ce', %s, 'admin_hotel', 'EMP-SINTETICA-001', true), "
                "('USR-CE-CAJ', 'caja_ce', %s, 'caja', 'EMP-SINTETICA-001', true)",
                (clave_h, clave_h),
            )
            c.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, estado_preparacion, en_inventario) "
                "VALUES ('HAB-CE1', 'EST-1', 'doble', 2, 'disponible', 'limpia', true), "
                "       ('HAB-CE2', 'EST-1', 'doble', 2, 'disponible', 'limpia', true)"
            )
            c.execute(
                "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, motivo, activa) "
                "VALUES ('EXC-CE1', 'HAB-CE1', '2026-10-01', '2026-12-31', 100000, 'base ce', true), "
                "       ('EXC-CE2', 'HAB-CE2', '2026-10-01', '2026-12-31', 120000, 'base ce 2', true)"
            )
            c.commit()

        self.admin = TestClient(self.app)
        r_adm = self.admin.post("/sesion", json={"usuario": "admin_ce", "clave": "Clave123!"})
        self.assertEqual(r_adm.status_code, 200, r_adm.text)

        self.caja = TestClient(self.app)
        r_caj = self.caja.post("/sesion", json={"usuario": "caja_ce", "clave": "Clave123!"})
        self.assertEqual(r_caj.status_code, 200, r_caj.text)

    def _idem(self) -> dict:
        self.__class__._n += 1
        return {"Idempotency-Key": f"ce-{self.__class__._n}"}

    def _auth_core(self, token: str = TOKEN_SERVICIO, scope: str | None = "finance:read") -> dict:
        headers = {"Authorization": f"Bearer {token}"}
        if scope is not None:
            headers["X-Core-Scope"] = scope
        return headers

    def test_regresion_conciliacion_precision_decimal_y_rechazo_solo_monto(self):
        """Reproduce y valida corrección de los dos hallazgos en conciliacion_bancaria.py:
        1) Precision Decimal exacta en comisiones (sin float intermedio).
        2) Transferencia que coincide SOLO en monto (sin referencia ni proveedor tarjeta) NO auto-concilia."""
        # 1. Precisión exacta Decimal (ej. 1.755 % con IVA 19 % sobre $100.000)
        with psycopg.connect(URL_TEST) as c:
            res = conciliacion_bancaria.guardar_comisiones(
                c,
                "EMP-SINTETICA-001",
                [{"medio": "debito", "proveedor": "transbank", "porcentaje_comision": Decimal("1.755"), "iva_comision": True, "dias_habiles_abono": 1}],
                actor="admin_ce",
            )
            self.assertEqual(res["debito"]["porcentaje_comision_exacto"], "1.755")
            abono, com = conciliacion_bancaria.calcular_abono_esperado(100000, res["debito"], Decimal("19"))
            # 100000 * 1.755% = 1755; 1755 * 1.19 = 2088.45 -> ROUND_HALF_UP = 2088
            self.assertEqual(com, 2088)
            self.assertEqual(abono, 97912)
            c.commit()

        # 2. Transferencia sin comprobante + cartola sin referencia (coincide SOLO en monto $120.000)
        r = self.admin.post(
            "/hotel/reservas",
            headers=self._idem(),
            json={
                "habitacion_id": "HAB-CE2",
                "inicio": "2026-11-18",
                "fin": "2026-11-19",
                "personas": 1,
                "huesped": {"nombre": "Cliente Sin Ref", "documento": "11.111.111-1", "documento_tipo": "rut"},
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        rid = r.json()["reserva_id"]

        p = self.caja.post(
            f"/hotel/reservas/{rid}/pagos",
            headers=self._idem(),
            json={"monto_clp": 120000, "clave": "trf-sin-ref", "modo": "manual", "medio": "transferencia", "documento_tipo": "boleta"},
        )
        self.assertEqual(p.status_code, 201, p.text)

        with psycopg.connect(URL_TEST) as c:
            c.execute("ALTER TABLE pagos DISABLE TRIGGER pagos_inmutables")
            c.execute("ALTER TABLE caja_movimientos DISABLE TRIGGER caja_movimientos_inmutables")
            c.execute("UPDATE pagos SET fecha_contable = '2026-11-18'")
            c.execute("UPDATE caja_movimientos SET fecha_contable = '2026-11-18'")
            c.execute("ALTER TABLE pagos ENABLE TRIGGER pagos_inmutables")
            c.execute("ALTER TABLE caja_movimientos ENABLE TRIGGER caja_movimientos_inmutables")
            c.commit()

        csv_solo_monto = (
            "Fecha;Descripcion;Referencia;Monto\n"
            "2026-11-18;ABONO TRANSFERENCIA GENERICA;;120000\n"
        )
        imp = self.caja.post(
            "/hotel/contabilidad/cartolas",
            headers=self._idem(),
            json={"banco": "BancoEstado", "cuenta": "99887766", "periodo": "2026-11", "contenido_csv": csv_solo_monto},
        )
        self.assertEqual(imp.status_code, 201, imp.text)
        # Invariante: coincidir solo en monto JAMÁS auto-concilia
        self.assertEqual(imp.json()["conciliados_automaticamente"], 0)
        self.assertEqual(imp.json()["pendientes"], 1)

    def test_export_core_autenticacion_denegacion_y_limites(self):
        params = {"resource": "reservations", "from_date": "2026-11-01", "to_date": "2026-11-30"}
        # Fail-closed 503 si no hay CORE_EXPORT_TOKEN configurado
        r503 = self.client_sin_token.get("/integrations/core/v1/finance-export", params=params, headers=self._auth_core())
        self.assertEqual(r503.status_code, 503)

        # Sin token o token inválido -> 401
        self.assertEqual(self.client.get("/integrations/core/v1/finance-export", params=params).status_code, 401)
        self.assertEqual(
            self.client.get("/integrations/core/v1/finance-export", params=params, headers=self._auth_core("token-malo")).status_code,
            401,
        )

        # Scope distinto -> 403; intento de inyectar empresa_id -> 403
        self.assertEqual(
            self.client.get("/integrations/core/v1/finance-export", params=params, headers=self._auth_core(scope="finance:write")).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                "/integrations/core/v1/finance-export",
                params={**params, "empresa_id": "EMP-OTRA"},
                headers=self._auth_core(),
            ).status_code,
            403,
        )

        # Límites: > 92 días -> 422; cursor corrupto -> 400
        self.assertEqual(
            self.client.get(
                "/integrations/core/v1/finance-export",
                params={"resource": "payments", "from_date": "2026-01-01", "to_date": "2026-12-31"},
                headers=self._auth_core(),
            ).status_code,
            422,
        )
        self.assertEqual(
            self.client.get(
                "/integrations/core/v1/finance-export",
                params={**params, "cursor": "no-es-un-cursor-valido"},
                headers=self._auth_core(),
            ).status_code,
            400,
        )

    def test_export_core_contrato_paginacion_pii_y_reversos(self):
        # Crear 2 reservas con PII que NO debe aparecer en la exportación
        r1 = self.admin.post(
            "/hotel/reservas",
            headers=self._idem(),
            json={
                "habitacion_id": "HAB-CE1",
                "inicio": "2026-11-10",
                "fin": "2026-11-12",
                "personas": 2,
                "huesped": {"nombre": "Huesped Secreto Uno", "documento": "12.345.678-5", "documento_tipo": "rut"},
            },
        )
        r2 = self.admin.post(
            "/hotel/reservas",
            headers=self._idem(),
            json={
                "habitacion_id": "HAB-CE2",
                "inicio": "2026-11-14",
                "fin": "2026-11-15",
                "personas": 1,
                "huesped": {"nombre": "Huesped Secreto Dos", "documento": "22.222.222-2", "documento_tipo": "rut"},
            },
        )
        self.assertEqual(r1.status_code, 201, r1.text)
        self.assertEqual(r2.status_code, 201, r2.text)
        rid1, rid2 = r1.json()["reserva_id"], r2.json()["reserva_id"]

        # Pago 1 con comprobante y Pago 2 con reverso
        p1 = self.caja.post(
            f"/hotel/reservas/{rid1}/pagos",
            headers=self._idem(),
            json={"monto_clp": 200000, "clave": "p-exp-1", "modo": "manual", "medio": "transferencia", "documento_tipo": "boleta", "comprobante": "TRF-77001"},
        )
        p2 = self.caja.post(
            f"/hotel/reservas/{rid2}/pagos",
            headers=self._idem(),
            json={"monto_clp": 120000, "clave": "p-exp-2", "modo": "manual", "medio": "transferencia", "documento_tipo": "boleta", "comprobante": "TRF-77002"},
        )
        self.assertEqual(p1.status_code, 201, p1.text)
        self.assertEqual(p2.status_code, 201, p2.text)
        pago2_id = p2.json()["pago_id"]

        # Reverso sobre pago 2
        rev = self.admin.post(
            f"/hotel/reservas/{rid2}/pagos/{pago2_id}/reverso",
            headers=self._idem(),
            json={"motivo": "Error de digitación de comprobante bancario"},
        )
        self.assertEqual(rev.status_code, 201, rev.text)

        # Fijar fechas contables dentro de noviembre 2026 y cargar cartola
        with psycopg.connect(URL_TEST) as c:
            c.execute("ALTER TABLE pagos DISABLE TRIGGER pagos_inmutables")
            c.execute("ALTER TABLE caja_movimientos DISABLE TRIGGER caja_movimientos_inmutables")
            c.execute("UPDATE pagos SET fecha_contable = '2026-11-12'")
            c.execute("UPDATE caja_movimientos SET fecha_contable = '2026-11-12'")
            c.execute("ALTER TABLE pagos ENABLE TRIGGER pagos_inmutables")
            c.execute("ALTER TABLE caja_movimientos ENABLE TRIGGER caja_movimientos_inmutables")
            c.commit()

        csv_cartola = (
            "Fecha;Descripcion;Referencia;Monto\n"
            "2026-11-12;TEF cliente;TRF-77001;200000\n"
        )
        self.assertEqual(
            self.caja.post(
                "/hotel/contabilidad/cartolas",
                headers=self._idem(),
                json={"banco": "BancoEstado", "cuenta": "001122334455", "periodo": "2026-11", "contenido_csv": csv_cartola},
            ).status_code,
            201,
        )

        # Exportar reservas con page_size=1 para verificar paginación estable y cero PII
        pg1 = self.client.get(
            "/integrations/core/v1/finance-export",
            params={"resource": "reservations", "from_date": "2026-11-01", "to_date": "2026-11-30", "page_size": 1},
            headers=self._auth_core(),
        )
        self.assertEqual(pg1.status_code, 200, pg1.text)
        b1 = pg1.json()
        self.assertEqual(b1["schema_version"], "1.1")
        self.assertEqual(b1["pagination"]["returned"], 1)
        self.assertTrue(b1["pagination"]["has_more"])
        self.assertIsNotNone(b1["pagination"]["next_cursor"])
        # Minimización PII: ni nombre ni RUT del huésped aparecen en la respuesta
        self.assertNotIn("Huesped Secreto", pg1.text)
        self.assertNotIn("12.345.678-5", pg1.text)

        pg2 = self.client.get(
            "/integrations/core/v1/finance-export",
            params={
                "resource": "reservations",
                "from_date": "2026-11-01",
                "to_date": "2026-11-30",
                "page_size": 1,
                "as_of": b1["as_of"],
                "cursor": b1["pagination"]["next_cursor"],
            },
            headers=self._auth_core(),
        )
        self.assertEqual(pg2.status_code, 200, pg2.text)
        b2 = pg2.json()
        self.assertEqual(b2["pagination"]["returned"], 1)
        self.assertFalse(b2["pagination"]["has_more"])
        self.assertEqual({b1["items"][0]["external_id"], b2["items"][0]["external_id"]}, {rid1, rid2})

        # Exportar pagos: incluye el pago original y su reverso vinculado
        pp = self.client.get(
            "/integrations/core/v1/finance-export",
            params={"resource": "payments", "from_date": "2026-11-01", "to_date": "2026-11-30", "as_of": b1["as_of"]},
            headers=self._auth_core(),
        )
        self.assertEqual(pp.status_code, 200, pp.text)
        pay_items = pp.json()["items"]
        self.assertEqual(len(pay_items), 3)
        reversos = [x for x in pay_items if x["payment_type"] == "reversal"]
        self.assertEqual(len(reversos), 1)
        self.assertEqual(reversos[0]["reverses_payment_external_id"], pago2_id)

        # Exportar movimientos bancarios: cuenta enmascarada (****4455), nunca completa
        pb = self.client.get(
            "/integrations/core/v1/finance-export",
            params={"resource": "bank_movements", "from_date": "2026-11-01", "to_date": "2026-11-30", "as_of": b1["as_of"]},
            headers=self._auth_core(),
        )
        self.assertEqual(pb.status_code, 200, pb.text)
        bm_items = pb.json()["items"]
        self.assertEqual(len(bm_items), 1)
        self.assertEqual(bm_items[0]["account_mask"], "****4455")
        self.assertNotIn("001122334455", pb.text)
