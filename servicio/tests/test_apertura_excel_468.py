"""#468: el conversor del Excel de levantamiento y la carga idempotente de activos e insumos."""
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import psycopg

from servicio import apertura_excel, carga_apertura, migracion

URL_TEST = os.environ.get("DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_468")


def _xlsx(ruta: Path, hojas: dict[str, list[list[str]]]) -> None:
    """XLSX mínimo con cadenas en línea (sin estilos), suficiente para el lector."""
    columnas = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("xl/workbook.xml",
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(hojas, 1))
                   + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i}" Target="worksheets/s{i}.xml"/>' for i in range(1, len(hojas) + 1))
                   + "</Relationships>")
        for i, filas in enumerate(hojas.values(), 1):
            cuerpo = ""
            for r, fila in enumerate(filas, 1):
                celdas = "".join(
                    f'<c r="{columnas[c]}{r}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
                    for c, v in enumerate(fila) if v != ""
                )
                cuerpo += f'<row r="{r}">{celdas}</row>'
            z.writestr(f"xl/worksheets/s{i}.xml",
                       f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{cuerpo}</sheetData></worksheet>')


def _libro(ruta: Path) -> None:
    cab_hab = ["Habitación", "Tipo"] + [""] * 26
    def hab(n, **kw):
        f = [""] * 28
        f[0], f[1] = str(n), "Matrimonial"
        for col, v in kw.items():
            f["ABCDEFGHIJKLMNOPQRSTUVWXYZ".index(col) if len(col) == 1 else 26] = v
        return f
    _xlsx(ruta, {
        "Detalle de habitaciones": [cab_hab, hab(1, D="Cambiar", O="Suelta", P="Pendiente mantención anual"),
                                    hab(10, P="Por reparar", Z="SUELTA"), ["10", "", "", "", "", "", "", "", "", "", "", "OK"]],
        "Inventario Lavanderia": [["Inventario ropa"], ["", "En habitaciones", "Disponible"],
                                  ["Sabanas de 1/2", "14", "10", "", "Secadora Grande", "1", "Ok"]],
        "Inventario Cocina": [["", "Cantidad", "Observación"], ["Encimera", "1", "Reparar enchufe (esta suelto)"],
                              ["Tazas blancas", "15", "Buen estado"]],
        "Insumos Desayuno": [["Insumos", "Proveedor", "Marca", "Precio", "Medida", "Bodega"],
                             ["Pan Hallulla", "Ganga", "—", "1132", "1 kg", "—"],
                             ["Leche Blanca", "Colún", "Colún", "1222", "1 litro", "8"]],
        "Insumos Aseo": [["Insumos", "Proveedor", "Marca", "Precio", "Medida", "Bodega"],
                         ["Shampoo", "Liquimax", "H&S", "3016", "24 sachet", "5 paquetes"]],
        "Otras observaciones": [["Sugerencias", "Observación"], ["Motor de Agua", "No para hasta desenchufarlo"],
                                ["Techo patio lavanderia", "Goteras"], ["Hb 2", "Revisar Filtración ducha"],
                                ["Sugerencias de Cambio"]],
        "Redes": [["Servicio", "Clave"], ["Gmail", "no-leer-nunca"]],
    })


class ConversorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.xlsx = self.dir / "libro.xlsx"
        _libro(self.xlsx)

    def tearDown(self):
        self.tmp.cleanup()

    def test_nunca_lee_la_hoja_redes(self):
        with self.assertRaises(apertura_excel.HojaProhibida):
            apertura_excel.leer_hojas(self.xlsx, ("Redes",))
        hojas = apertura_excel.leer_hojas(self.xlsx)
        self.assertNotIn("Redes", hojas)
        salida = self.dir / "out"
        apertura_excel.generar(self.xlsx, salida)
        for csv_ in salida.glob("*.csv"):
            self.assertNotIn("no-leer-nunca", csv_.read_text(encoding="utf-8"))

    def test_inventario_parsea_stock_y_costo_y_manda_equipos_a_activos(self):
        filas = apertura_excel.filas_inventario(apertura_excel.leer_hojas(self.xlsx))
        por_codigo = {f["codigo"]: f for f in filas}
        self.assertEqual(por_codigo["DES-PAN-HALLULLA"]["stock_inicial"], 0)  # «—» → 0
        self.assertEqual(por_codigo["DES-PAN-HALLULLA"]["costo_clp"], 1132)
        self.assertEqual(por_codigo["ASE-SHAMPOO"]["stock_inicial"], 5)  # «5 paquetes»
        self.assertEqual(por_codigo["LAV-SABANAS-DE-1-2"]["stock_inicial"], 24)  # habitaciones + lavandería
        self.assertIn("COC-TAZAS-BLANCAS", por_codigo)
        self.assertNotIn("COC-ENCIMERA", por_codigo)
        self.assertTrue(all(f["activo"] == "false" for f in filas))

    def test_incidencias_sin_duplicar_y_con_gravedad(self):
        filas = apertura_excel.filas_incidencias(apertura_excel.leer_hojas(self.xlsx))
        cods = [f["codigo_externo"] for f in filas]
        self.assertEqual(len(cods), len(set(cods)))
        gravedad = {f["codigo_externo"]: f["gravedad"] for f in filas}
        self.assertEqual(gravedad["XL-H10-AIRE"], "critica")
        self.assertEqual(gravedad["XL-COMUN-MOTOR-AGUA"], "critica")
        self.assertEqual(gravedad["XL-COMUN-GOTERAS"], "critica")
        self.assertEqual(gravedad["XL-H01-CERRADURA"], "alta")
        self.assertIn("XL-H01-COLCHON", gravedad)
        self.assertNotIn("XL-H10-COLCHON", gravedad)

    def test_activos_marcan_en_reparacion_y_plan_anual(self):
        filas = {f["codigo_externo"]: f for f in apertura_excel.filas_activos(apertura_excel.leer_hojas(self.xlsx), "2026-12-15")}
        self.assertEqual(filas["XL-ACT-H10-AIRE"]["estado"], "en_reparacion")
        self.assertEqual(filas["XL-ACT-H01-AIRE"]["estado"], "operativo")
        self.assertEqual(filas["XL-ACT-H01-AIRE"]["mantencion_cada_dias"], "365")
        self.assertEqual(filas["XL-ACT-COC-ENCIMERA"]["estado"], "en_reparacion")
        self.assertIn("XL-ACT-LAV-SECADORA-GRANDE", filas)


class CargaActivosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            c.execute("TRUNCATE mantenciones_realizadas, mantenciones_plan, activos, incidencia_eventos, "
                      "incidencia_evidencias, incidencias, movimientos_stock, core_stock_bodega, productos, "
                      "auditoria, excepciones_precio, habitaciones CASCADE")
            for n in (1, 2, 10):
                c.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, "
                          "estado_preparacion, en_inventario) VALUES (%s, 'EST-SINT-001', 'doble', 3, 'disponible', "
                          "'limpia', true) ON CONFLICT (id) DO NOTHING", (f"HAB-{n:02d}",))
            c.commit()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        _libro(self.dir / "libro.xlsx")
        apertura_excel.generar(self.dir / "libro.xlsx", self.dir / "out")

    def tearDown(self):
        self.tmp.cleanup()

    def _cargar(self, aplicar):
        out = self.dir / "out"
        with psycopg.connect(URL_TEST) as c:
            acta = carga_apertura.ejecutar_apertura(
                c, "EMP-SINTETICA-001", inventarios_csv=out / "inventario_inicial.csv",
                incidencias_csv=out / "incidencias_iniciales.csv", activos_csv=out / "activos_iniciales.csv",
                aplicar=aplicar)
            c.commit()
        return acta

    def _contar(self):
        with psycopg.connect(URL_TEST) as c:
            return tuple(c.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                         for t in ("productos", "incidencias", "activos", "mantenciones_plan"))

    def test_dry_run_no_escribe_y_aplicar_es_idempotente(self):
        acta = self._cargar(False)
        self.assertTrue(acta["aprobado"], acta)
        self.assertEqual(self._contar(), (0, 0, 0, 0))
        primera = self._cargar(True)
        self.assertTrue(primera["aprobado"], primera)
        antes = self._contar()
        self.assertGreater(antes[0], 0)
        self.assertGreater(antes[1], 0)
        self.assertGreater(antes[2], 0)
        self.assertGreater(antes[3], 0)
        segunda = self._cargar(True)
        self.assertEqual(self._contar(), antes, "repetir la carga no debe duplicar filas")
        self.assertEqual(segunda["secciones"]["activos"]["aplicados"], 0)
        self.assertEqual(segunda["secciones"]["incidencias"]["aplicados"], 0)
        self.assertEqual(segunda["secciones"]["inventarios"]["aplicados"], 0)

    def test_habitacion_inexistente_deja_acta_con_error_y_no_escribe(self):
        with psycopg.connect(URL_TEST) as c:
            c.execute("DELETE FROM habitaciones WHERE id = 'HAB-10'")
            c.commit()
        acta = self._cargar(True)
        self.assertFalse(acta["aprobado"])
        self.assertEqual(self._contar()[2], 0)


if __name__ == "__main__":
    unittest.main()
