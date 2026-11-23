"""Pruebas Contabilidad 2.3, 2.4 y 2.5 (#393, #394, #395 / KPI-002)."""
import os
import unittest
from datetime import date, time, timedelta
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient

from servicio import migracion, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.reloj import a_las

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_paso3",
)
HOY = date(2026, 11, 20)


class ContableAvanzadoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario="admin_c", admin_clave="Clave123!",
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
                "TRUNCATE cierres_mensuales, cierres_diarios, caja_movimientos, caja_turnos, "
                "movimientos_directos, imputaciones_pago, reserva_huespedes, huespedes, "
                "reasignaciones, liquidaciones, pagos, cargos, reserva_noches, reservas, "
                "clientes, tarifas, excepciones_precio, habitaciones, politicas_hotel, "
                "claves_idempotencia, auditoria, sesiones, usuarios CASCADE"
            )
            clave_h = seguridad.hashear_clave("Clave123!")
            c.execute(
                "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                "('USR-C-ADMIN', 'admin_c', %s, 'admin_hotel', 'EMP-SINTETICA-001', true), "
                "('USR-C-CAJA', 'caja_c', %s, 'caja', 'EMP-SINTETICA-001', true), "
                "('USR-C-RECEP', 'recep_c', %s, 'recepcion', 'EMP-SINTETICA-001', true)",
                (clave_h, clave_h, clave_h),
            )
            c.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, estado_preparacion, en_inventario, creado_en) VALUES "
                "('HAB-C1', 'EST-1', 'doble', 2, 'disponible', 'limpia', true, '2026-01-01T00:00:00Z'), "
                "('HAB-C2', 'EST-1', 'matrimonial', 2, 'disponible', 'limpia', true, '2026-01-01T00:00:00Z'), "
                "('HAB-C3', 'EST-1', 'single', 1, 'fuera_de_servicio', 'limpia', true, '2026-01-01T00:00:00Z')"
            )
            for hid, precio in (("HAB-C1", 60000), ("HAB-C2", 80000)):
                c.execute(
                    "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, motivo, activa) "
                    "VALUES (%s, %s, '2026-10-01', '2026-12-31', %s, 'base contable', true)",
                    (f"EXC-{hid}", hid, precio),
                )
            c.commit()

        self.admin = self._login("admin_c")
        self.caja = self._login("caja_c")
        self.recep = self._login("recep_c")

    def _login(self, usuario: str) -> TestClient:
        c = TestClient(self.app)
        r = c.post("/sesion", json={"usuario": usuario, "clave": "Clave123!"})
        self.assertEqual(r.status_code, 200, r.text)
        return c

    def _idem(self) -> dict:
        self.__class__._n += 1
        return {"Idempotency-Key": f"cnt-{self.__class__._n}"}

    def _crear_y_entrar(self, hab: str, inicio: date, fin: date, doc: str, nombre: str, abono: int = 0) -> str:
        r = self.admin.post(
            "/hotel/reservas",
            headers=self._idem(),
            json={
                "habitacion_id": hab,
                "inicio": inicio.isoformat(),
                "fin": fin.isoformat(),
                "personas": 1,
                "huesped": {"nombre": nombre, "documento": doc, "documento_tipo": "rut"},
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        rid = r.json()["reserva_id"]
        if abono > 0:
            rp = self.admin.post(
                f"/hotel/reservas/{rid}/pagos",
                headers=self._idem(),
                json={"monto_clp": abono, "clave": f"ab-{rid}", "modo": "manual", "medio": "transferencia"},
            )
            self.assertEqual(rp.status_code, 201, rp.text)
        with a_las(inicio, hora=time(15, 30)):
            re = self.admin.post(f"/hotel/reservas/{rid}/entrada", headers=self._idem(), json={})
            self.assertEqual(re.status_code, 200, re.text)
        return rid

    def test_migracion_0061_es_idempotente(self):
        sql = Path("servicio/migraciones/0061_cierre_mensual_contable.sql").read_text(encoding="utf-8")
        with psycopg.connect(URL_TEST) as c:
            c.execute(sql)
            c.execute(sql)
            c.commit()

    def test_23_cuadratura_diaria_ocupacion_noches_y_abonos(self):
        # HAB-C1 (60.000/noche) × 2 noches con abono de 120.000 (cubre ambas noches al entrar)
        self._crear_y_entrar("HAB-C1", HOY, HOY + timedelta(days=2), "12.345.678-5", "Ana Cuadra", abono=120000)
        # HAB-C2 confirmada sin Llegada (para verificar alerta/diferencia)
        r2 = self.admin.post(
            "/hotel/reservas",
            headers=self._idem(),
            json={
                "habitacion_id": "HAB-C2",
                "inicio": HOY.isoformat(),
                "fin": (HOY + timedelta(days=1)).isoformat(),
                "personas": 1,
                "huesped": {"nombre": "Luis SinLlegada", "documento": "11.111.111-1", "documento_tipo": "rut"},
            },
        )
        self.assertEqual(r2.status_code, 201, r2.text)

        # Recepción no accede a cuadratura contable -> 403
        self.assertEqual(
            self.recep.get("/hotel/contabilidad/cuadratura-diaria", params={"fecha": HOY.isoformat()}).status_code,
            403,
        )

        # Caja y administración ven la cuadratura exacta
        rc = self.caja.get("/hotel/contabilidad/cuadratura-diaria", params={"fecha": HOY.isoformat()})
        self.assertEqual(rc.status_code, 200, rc.text)
        d = rc.json()
        self.assertEqual(d["ocupacion"]["habitaciones_disponibles"], 2)  # HAB-C3 está fuera de servicio
        self.assertEqual(d["ocupacion"]["noches_ocupadas"], 1)
        self.assertEqual(d["ocupacion"]["confirmadas_sin_llegada"], 1)
        self.assertEqual(d["noches"]["devengado_alojamiento_clp"], 60000)
        self.assertEqual(d["noches"]["imputado_noche_clp"], 60000)
        self.assertEqual(d["noches"]["pendiente_noche_clp"], 0)
        self.assertEqual(d["noches"]["adr_clp"], 60000)
        self.assertEqual(d["noches"]["revpar_clp"], 30000)
        self.assertFalse(d["cuadra"])  # porque HAB-C2 está confirmada sin Llegada
        self.assertTrue(any(dif["tipo"] == "confirmada_sin_llegada" for dif in d["diferencias"]))

    def test_24_cierre_mensual_matriz_ocupacion_y_exportacion_csv(self):
        # Dos estadías en noviembre 2026
        self._crear_y_entrar("HAB-C1", date(2026, 11, 5), date(2026, 11, 7), "12.345.678-5", "Sofía Mes", abono=120000)
        self._crear_y_entrar("HAB-C2", date(2026, 11, 5), date(2026, 11, 6), "11.111.111-1", "Mateo Mes", abono=80000)

        # Vista en vivo del mes 2026-11
        rm = self.caja.get("/hotel/contabilidad/cierre-mensual", params={"anio": 2026, "mes": 11})
        self.assertEqual(rm.status_code, 200, rm.text)
        m = rm.json()
        self.assertFalse(m["congelada"])
        self.assertEqual(m["periodo"], "2026-11")
        self.assertEqual(len(m["dias"]), 30)
        self.assertEqual(m["resumen"]["noches_ocupadas"], 3)
        self.assertEqual(m["resumen"]["ingreso_alojamiento_clp"], 200000)  # 60k*2 + 80k*1
        self.assertEqual(m["resumen"]["adr_clp"], round(200000 / 3))
        self.assertEqual(m["resumen"]["unidades_noche"], 60)  # 2 habitaciones en servicio × 30 días
        self.assertEqual(m["resumen"]["revpar_clp"], round(200000 / 60))

        # Exportación CSV matriz habitaciones × días (Ocupación 2026)
        rcsv = self.caja.get("/hotel/contabilidad/cierre-mensual/exportar.csv", params={"anio": 2026, "mes": 11})
        self.assertEqual(rcsv.status_code, 200, rcsv.text)
        self.assertIn("text/csv", rcsv.headers["content-type"])
        texto_csv = rcsv.content.decode("utf-8-sig")
        self.assertIn("Habitación;Tipo;01;02;", texto_csv)
        self.assertIn("HAB-C1;doble;", texto_csv)
        self.assertIn("TOTAL OCUPADAS", texto_csv)

        # Cierre mensual sin confirmar alertas (días sin cierre diario) -> 409
        r_fail = self.admin.post(
            "/hotel/contabilidad/cierre-mensual",
            headers=self._idem(),
            json={"anio": 2026, "mes": 11, "confirmar_alertas": False},
        )
        self.assertEqual(r_fail.status_code, 409, r_fail.text)

        # Cierre mensual confirmando alertas -> 201 y congela el mes
        r_ok = self.admin.post(
            "/hotel/contabilidad/cierre-mensual",
            headers=self._idem(),
            json={"anio": 2026, "mes": 11, "nota": "Cierre noviembre", "confirmar_alertas": True},
        )
        self.assertEqual(r_ok.status_code, 201, r_ok.text)

        rm_congelado = self.caja.get("/hotel/contabilidad/cierre-mensual", params={"anio": 2026, "mes": 11})
        self.assertTrue(rm_congelado.json()["congelada"])
        self.assertEqual(rm_congelado.json()["cierre"]["estado"], "cerrado")

        # Caja no puede reabrir -> 403; Admin reabre con motivo >= 10 chars -> 200
        self.assertEqual(
            self.caja.post(
                "/hotel/contabilidad/cierre-mensual/2026/11/reapertura",
                headers=self._idem(),
                json={"motivo": "Ajuste contable autorizado"},
            ).status_code,
            403,
        )
        r_reap = self.admin.post(
            "/hotel/contabilidad/cierre-mensual/2026/11/reapertura",
            headers=self._idem(),
            json={"motivo": "Ajuste contable autorizado por gerencia"},
        )
        self.assertEqual(r_reap.status_code, 200, r_reap.text)
        self.assertEqual(r_reap.json()["estado"], "reabierto")

    def test_25_indicadores_ejecutivos_reales_y_sin_muestra_null(self):
        # Periodo sin noches ocupadas -> ADR debe ser None (sin muestra, nunca 0 inventado)
        ayer = date.today() - timedelta(days=2)
        manana = date.today() + timedelta(days=1)
        r_vacio = self.admin.get(
            "/hotel/contabilidad/indicadores-ejecutivos",
            params={"desde": ayer.isoformat(), "hasta": date.today().isoformat()},
        )
        self.assertEqual(r_vacio.status_code, 200, r_vacio.text)
        v = r_vacio.json()
        self.assertEqual(v["noches_ocupadas"], 0)
        self.assertIsNone(v["adr_clp"])  # sin muestra, NUNCA 0 inventado

        # Periodo completamente futuro -> ocupación, ADR y RevPAR TODOS None
        fut_ini = date.today() + timedelta(days=5)
        fut_fin = date.today() + timedelta(days=8)
        r_fut = self.admin.get(
            "/hotel/contabilidad/indicadores-ejecutivos",
            params={"desde": fut_ini.isoformat(), "hasta": fut_fin.isoformat()},
        )
        self.assertEqual(r_fut.status_code, 200, r_fut.text)
        f = r_fut.json()
        self.assertIsNone(f["ocupacion"])
        self.assertIsNone(f["adr_clp"])
        self.assertIsNone(f["revpar_clp"])

        # Con estadías reales hoy: HAB-C1 (60.000) y HAB-C2 (80.000) alojadas hoy
        hoy_real = date.today()
        # Asegurar tarifas vigentes hoy
        with psycopg.connect(URL_TEST) as c:
            for hid, precio in (("HAB-C1", 60000), ("HAB-C2", 80000)):
                c.execute(
                    "UPDATE excepciones_precio SET fecha_desde = %s, fecha_hasta = %s WHERE habitacion_id = %s",
                    (hoy_real - timedelta(days=10), hoy_real + timedelta(days=30), hid),
                )
            c.commit()
        self._crear_y_entrar("HAB-C1", hoy_real, hoy_real + timedelta(days=1), "12.345.678-5", "Elena KPI")
        self._crear_y_entrar("HAB-C2", hoy_real, hoy_real + timedelta(days=1), "11.111.111-1", "Diego KPI")

        # Indicadores ejecutivos dedicados: 2/2 ocupadas, ingreso 140.000, ADR 70.000, RevPAR 70.000
        r_ej = self.admin.get(
            "/hotel/contabilidad/indicadores-ejecutivos",
            params={"desde": hoy_real.isoformat(), "hasta": manana.isoformat()},
        )
        self.assertEqual(r_ej.status_code, 200, r_ej.text)
        ej = r_ej.json()
        self.assertEqual(ej["ocupacion"], 1.0)
        self.assertEqual(ej["ingreso_alojamiento_clp"], 140000)
        self.assertEqual(ej["adr_clp"], 70000)
        self.assertEqual(ej["revpar_clp"], 70000)

        # Panel /hotel/indicadores expone ADR y RevPAR solo a administración, nunca a recepción
        r_panel_adm = self.admin.get(
            "/hotel/indicadores",
            params={"desde": hoy_real.isoformat(), "hasta": manana.isoformat()},
        )
        p_adm = r_panel_adm.json()["periodo_indicadores"]
        self.assertEqual(p_adm["adr_clp"]["valor"], 70000)
        self.assertEqual(p_adm["revpar_clp"]["valor"], 70000)

        r_panel_rec = self.recep.get(
            "/hotel/indicadores",
            params={"desde": hoy_real.isoformat(), "hasta": manana.isoformat()},
        )
        p_rec = r_panel_rec.json()["periodo_indicadores"]
        self.assertNotIn("adr_clp", p_rec)
        self.assertNotIn("revpar_clp", p_rec)

        # Recepción tampoco puede acceder a /hotel/contabilidad/indicadores-ejecutivos -> 403
        self.assertEqual(
            self.recep.get("/hotel/contabilidad/indicadores-ejecutivos").status_code,
            403,
        )


if __name__ == "__main__":
    unittest.main()
