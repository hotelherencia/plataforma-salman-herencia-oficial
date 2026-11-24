"""#467: plantilla de turnos desde la hoja Horario (sin Personal Vigente) y carga idempotente."""
import csv
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

import psycopg

from servicio import migracion, turnos_base
from servicio.tests.test_apertura_excel_468 import _xlsx

URL_TEST = os.environ.get("DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_467")
EMPRESA = "EMP-SINTETICA-001"


def _libro(ruta: Path) -> None:
    _xlsx(ruta, {
        "Horario": [
            ["Turnos Recepción"],
            ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            ["Ana.   (11:00 - 16:00)", "Ana   (08:00 - 16:00)", "", "", "", "", "Eva.   (12:00 - 00:00)"],
            ["Luz  (16:00 - 00:00)", "Luz  (16:00 - 00:00)"],
            ["Beto (00:00 - 08:00)", "Beto (00:00 - 08:00)", "", "", "", "", "Beto (00:00 - 08:00)"],
            ["Turnos Personal de Aseo"],
            ["Lunes", "Martes"],
            ["Ana  (11:00 - 16:00)", "Ana  (08:00 - 16:00)"],
        ],
        "Personal Vigente": [["Nombre", "Rut"], ["No debe leerse", "11.111.111-1"]],
    })


class PlantillaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.xlsx = Path(self.tmp.name) / "h.xlsx"
        _libro(self.xlsx)

    def tearDown(self):
        self.tmp.cleanup()

    def test_parsea_franjas_regla_del_lunes_y_fin_de_contrato(self):
        filas = turnos_base.plantilla(self.xlsx, {"Eva": "2026-12-31"})
        clave = {(f["dia_semana"], f["area"], f["nombre_horario"]): f for f in filas}
        self.assertEqual(clave[(0, "recepcion", "Ana")]["hora_inicio"], "11:00")
        self.assertEqual(clave[(1, "recepcion", "Luz")]["hora_fin"], "23:59")  # 00:00 → 23:59
        self.assertEqual(clave[(0, "recepcion", "Beto")]["hora_fin"], "11:00")  # lunes cubre hasta las 11:00
        self.assertEqual(clave[(1, "recepcion", "Beto")]["hora_fin"], "08:00")
        self.assertEqual(clave[(6, "recepcion", "Eva")]["hasta"], "2026-12-31")
        self.assertIn((1, "aseo", "Ana"), clave)
        self.assertTrue(all(f["usuario"] == "" for f in filas), "la plantilla no asigna personas")
        self.assertNotIn("No debe leerse", str(filas))


class CargaTurnosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            c.execute("TRUNCATE turno_cambios, turnos CASCADE")
            c.execute("DELETE FROM usuarios WHERE nombre LIKE 'tb_%'")
            for nombre in ("tb_ana", "tb_eva"):
                c.execute("INSERT INTO usuarios (id, empresa_id, nombre, rol, clave_hash) VALUES (%s,%s,%s,'recepcion','x')",
                          (f"USR-{nombre}", EMPRESA, nombre))
            c.commit()
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = Path(self.tmp.name) / "t.csv"
        self.xlsx = Path(self.tmp.name) / "h.xlsx"
        _libro(self.xlsx)
        filas = turnos_base.plantilla(self.xlsx, {"Eva": "2026-12-06"})
        for f in filas:
            f["usuario"] = {"Ana": "tb_ana", "Eva": "tb_eva"}.get(f["nombre_horario"], "")
        # Solo se cargan las personas con cuenta; el resto queda para cuando existan.
        turnos_base.escribir_plantilla([f for f in filas if f["usuario"]], self.csv)

    def tearDown(self):
        self.tmp.cleanup()

    def _cargar(self, aplicar):
        with psycopg.connect(URL_TEST) as c:
            acta = turnos_base.cargar_turnos_csv(c, EMPRESA, self.csv, date(2026, 12, 1), 2, aplicar=aplicar)
            c.commit()
        return acta

    def _n(self):
        with psycopg.connect(URL_TEST) as c:
            return c.execute("SELECT count(*) FROM turnos").fetchone()[0]

    def test_dry_run_aplicar_idempotente_y_contrato_a_plazo(self):
        self.assertTrue(self._cargar(False)["aprobado"])
        self.assertEqual(self._n(), 0)
        primera = self._cargar(True)
        self.assertTrue(primera["aprobado"], primera)
        total = self._n()
        self.assertGreater(total, 0)
        self._cargar(True)
        self.assertEqual(self._n(), total, "repetir no duplica")
        with psycopg.connect(URL_TEST) as c:
            domingos_eva = [r[0] for r in c.execute("SELECT fecha FROM turnos WHERE usuario='tb_eva' ORDER BY fecha").fetchall()]
            mia_dup = c.execute("SELECT count(*) FROM turnos WHERE usuario='tb_ana' AND fecha='2026-12-01'").fetchone()[0]
        self.assertEqual(domingos_eva, [date(2026, 12, 6)])  # el domingo 13 ya pasó su fin de contrato
        self.assertEqual(mia_dup, 1, "el mismo bloque en recepción y aseo no se duplica")

    def test_usuario_inexistente_o_vacio_deja_error_y_no_escribe(self):
        filas = list(csv.DictReader(self.csv.open(encoding="utf-8")))
        filas[0]["usuario"] = "no_existe"
        turnos_base.escribir_plantilla(filas, self.csv)
        acta = self._cargar(True)
        self.assertFalse(acta["aprobado"])
        self.assertEqual(self._n(), 0)


if __name__ == "__main__":
    unittest.main()
