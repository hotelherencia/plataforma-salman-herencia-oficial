"""Pruebas F20 (MIG-002..006): Carga inicial operativa y migración de apertura
con --dry-run (acta de validación) y --aplicar (idempotente, sin duplicados ni PII)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import psycopg

from servicio import aplicacion, carga_apertura, hotel_sql, migracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_paso5",
)
RAIZ = Path(__file__).resolve().parents[2]
DIR_EJEMPLOS = RAIZ / "docs" / "operacion" / "migracion-apertura"
EMPRESA = "EMP-SINTETICA-001"


class CargaAperturaOperativaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app_dom = aplicacion.construir_aplicacion()
        hotel_sql.registrar(cls.app_dom.hotel)

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "TRUNCATE incidencia_eventos, incidencia_evidencias, incidencias, "
                "movimientos_stock, core_stock_bodega, productos, "
                "imputaciones_pago, reserva_huespedes, huespedes, caja_movimientos, "
                "pagos, cargos, reserva_noches, reservas, clientes, tarifas, excepciones_precio, "
                "habitaciones, claves_idempotencia, auditoria CASCADE"
            )
            for num in (1, 2, 3, 10):
                hid = f"HAB-{num:02d}"
                c.execute(
                    "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, estado_preparacion, en_inventario) "
                    "VALUES (%s, 'EST-SINT-001', 'doble', 3, 'disponible', 'limpia', true)",
                    (hid,),
                )
                c.execute(
                    "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, motivo, activa) "
                    "VALUES (%s, %s, '2026-12-01', '2027-03-01', 65000, 'temporada verano', true)",
                    (f"EXC-{hid}", hid),
                )
            c.commit()

    def test_migracion_0063_bodegas_operativas_es_idempotente(self):
        sql = (RAIZ / "servicio/migraciones/0063_bodegas_operativas_apertura.sql").read_text(encoding="utf-8")
        with psycopg.connect(URL_TEST) as c:
            c.execute(sql)
            c.execute(sql)
            c.commit()
            cods = {r[0] for r in c.execute("SELECT codigo FROM core_bodegas").fetchall()}
        self.assertTrue({"lavanderia", "insumos_aseo", "insumos_desayuno", "cocina"}.issubset(cods))

    def test_dry_run_y_aplicar_idempotente_completo(self):
        inv_csv = DIR_EJEMPLOS / "inventario_inicial_ejemplo.csv"
        inc_csv = DIR_EJEMPLOS / "incidencias_iniciales_ejemplo.csv"
        rsv_csv = DIR_EJEMPLOS / "reservas_y_anticipos_corte_2026_12_31_plantilla.csv"

        # 1. --dry-run valida todo sin escribir en BD
        with psycopg.connect(URL_TEST) as c:
            acta_dry = carga_apertura.ejecutar_apertura(
                c, EMPRESA,
                inventarios_csv=inv_csv, incidencias_csv=inc_csv, reservas_csv=rsv_csv,
                aplicar=False, nucleo=self.app_dom.nucleo, hotel=self.app_dom.hotel,
            )
            c.rollback()
            self.assertTrue(acta_dry["aprobado"], acta_dry)
            self.assertEqual(acta_dry["modo"], "dry-run")
            self.assertEqual(acta_dry["secciones"]["inventarios"]["validos"], 12)
            self.assertEqual(acta_dry["secciones"]["incidencias"]["validos"], 4)
            self.assertEqual(acta_dry["secciones"]["reservas"]["validos"], 2)
            self.assertEqual(acta_dry["secciones"]["reservas"]["total_anticipos_validados_clp"], 50000)
            # Nada escrito en BD
            self.assertEqual(c.execute("SELECT COUNT(*) FROM productos").fetchone()[0], 0)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM incidencias").fetchone()[0], 0)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM reservas").fetchone()[0], 0)

        # 2. Primera ejecución con --aplicar
        with psycopg.connect(URL_TEST) as c:
            acta_1 = carga_apertura.ejecutar_apertura(
                c, EMPRESA,
                inventarios_csv=inv_csv, incidencias_csv=inc_csv, reservas_csv=rsv_csv,
                aplicar=True, nucleo=self.app_dom.nucleo, hotel=self.app_dom.hotel,
            )
            c.commit()
            self.assertTrue(acta_1["aprobado"], acta_1)
            self.assertEqual(acta_1["secciones"]["inventarios"]["aplicados"], 12)
            self.assertEqual(acta_1["secciones"]["incidencias"]["aplicados"], 4)
            self.assertEqual(acta_1["secciones"]["reservas"]["aplicados"], 2)

            # Verificar stock en las 4 bodegas operativas (0055)
            por_bodega = dict(
                c.execute("SELECT bodega_codigo, SUM(cantidad) FROM core_stock_bodega GROUP BY bodega_codigo").fetchall()
            )
            self.assertEqual(por_bodega["lavanderia"], 144)
            self.assertEqual(por_bodega["insumos_aseo"], 110)
            self.assertEqual(por_bodega["insumos_desayuno"], 39)
            self.assertEqual(por_bodega["cocina"], 14)

            # Verificar incidencias 0059 (Hb 10, Hb 2, lavandería, mantención)
            inc_rows = c.execute("SELECT habitacion_id, area FROM incidencias ORDER BY id").fetchall()
            self.assertEqual(len(inc_rows), 4)
            self.assertIn(("HAB-10", None), inc_rows)
            self.assertIn(("HAB-02", None), inc_rows)

            # Verificar reservas futuras y anticipo heredado de $50.000
            self.assertEqual(c.execute("SELECT COUNT(*) FROM reservas").fetchone()[0], 2)
            self.assertEqual(
                c.execute("SELECT COALESCE(SUM(monto_clp), 0) FROM pagos WHERE estado = 'confirmado'").fetchone()[0],
                50000,
            )

        # 3. Segunda ejecución con --aplicar -> 100 % idempotente (0 aplicados, todos omitidos, sin duplicar)
        with psycopg.connect(URL_TEST) as c:
            acta_2 = carga_apertura.ejecutar_apertura(
                c, EMPRESA,
                inventarios_csv=inv_csv, incidencias_csv=inc_csv, reservas_csv=rsv_csv,
                aplicar=True, nucleo=self.app_dom.nucleo, hotel=self.app_dom.hotel,
            )
            c.commit()
            self.assertTrue(acta_2["aprobado"])
            self.assertEqual(acta_2["secciones"]["inventarios"]["aplicados"], 0)
            self.assertEqual(acta_2["secciones"]["inventarios"]["omitidos"], 12)
            self.assertEqual(acta_2["secciones"]["incidencias"]["aplicados"], 0)
            self.assertEqual(acta_2["secciones"]["incidencias"]["omitidos"], 4)
            self.assertEqual(acta_2["secciones"]["reservas"]["aplicados"], 0)
            self.assertEqual(acta_2["secciones"]["reservas"]["omitidos"], 2)
            # Totales intactos tras re-ejecución
            self.assertEqual(
                c.execute("SELECT COALESCE(SUM(monto_clp), 0) FROM pagos WHERE estado = 'confirmado'").fetchone()[0],
                50000,
            )
            # Auditoría sin PII
            aud = c.execute("SELECT resultado FROM auditoria WHERE accion LIKE 'apertura_%'").fetchall()
            for (res,) in aud:
                self.assertNotIn("Titular Ejemplo", res)
                self.assertNotIn("11.111.111-1", res)

    def test_rechaza_csv_con_columnas_prohibidas_o_anticipo_sin_medio(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_csv = Path(tmp) / "malo.csv"
            bad_csv.write_text(
                "codigo_externo,habitacion_id,llegada,salida,adultos,titular_nombre,anticipo_clp,anticipo_medio,password\n"
                "R1,HAB-01,2027-01-02,2027-01-04,2,Ana,25000,,secreto\n",
                encoding="utf-8",
            )
            with psycopg.connect(URL_TEST) as c:
                acta = carga_apertura.ejecutar_apertura(c, EMPRESA, reservas_csv=bad_csv, aplicar=False)
                self.assertFalse(acta["aprobado"])
                errs = " | ".join(e["error"] for e in acta["secciones"]["reservas"]["errores"])
                self.assertIn("prohibida", errs)
                self.assertIn("anticipo_medio", errs)

    def test_cli_dry_run_genera_acta_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            acta_path = Path(tmp) / "acta.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(RAIZ / "scripts/cargar_apertura_operativa.py"),
                    "--dry-run",
                    "--database-url", URL_TEST,
                    "--empresa-id", EMPRESA,
                    "--inventarios", str(DIR_EJEMPLOS / "inventario_inicial_ejemplo.csv"),
                    "--incidencias", str(DIR_EJEMPLOS / "incidencias_iniciales_ejemplo.csv"),
                    "--reservas", str(DIR_EJEMPLOS / "reservas_y_anticipos_corte_2026_12_31_plantilla.csv"),
                    "--acta-salida", str(acta_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            acta = json.loads(acta_path.read_text(encoding="utf-8"))
            self.assertTrue(acta["aprobado"])
            self.assertEqual(acta["modo"], "dry-run")


if __name__ == "__main__":
    unittest.main()
