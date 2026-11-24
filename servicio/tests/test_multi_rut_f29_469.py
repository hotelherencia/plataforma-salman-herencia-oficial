"""#469: el crédito fiscal del F29 solo suma facturas emitidas al RUT de la empresa (EMPRESA_RUT)."""
import os
import unittest
from unittest import mock

import psycopg

from servicio import migracion, tributario

URL_TEST = os.environ.get("DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_469")
RUT_EMPRESA = "77685187-6"
RUT_OTRA = "76111111-1"


class MultiRutF29Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            c.execute("TRUNCATE documentos_proveedor CASCADE")
            c.commit()
        self._n = 0

    def _doc(self, c, clase, estado, iva, receptor):
        self._n += 1
        c.execute(
            "INSERT INTO documentos_proveedor (id, clase, origen, estado, lectura, emisor_rut, tipo_dte, folio, "
            "fecha_emision, monto_neto_clp, iva_clp, monto_total_clp, actor, receptor_rut) "
            "VALUES (%s,%s,'xml',%s,'xml','76222222-2',%s,%s,'2026-11-10',%s,%s,%s,'test',%s)",
            (f"DOC-T{self._n}", clase, estado, 33 if clase == "factura" else 61, str(self._n),
             iva * 5, iva, iva * 6, receptor),
        )

    def _f29(self, rut):
        env = {"EMPRESA_RUT": rut} if rut else {}
        with mock.patch.dict(os.environ, env, clear=False):
            if not rut:
                os.environ.pop("EMPRESA_RUT", None)
            with psycopg.connect(URL_TEST) as c:
                return tributario.resumen_tributario_mensual(c, "EMP-SINTETICA-001", 2026, 11)["compras_credito_fiscal"]

    def test_credito_solo_del_rut_de_la_empresa_y_lo_ajeno_se_informa(self):
        with psycopg.connect(URL_TEST) as c:
            self._doc(c, "factura", "cargada", 1000, RUT_EMPRESA)
            self._doc(c, "factura", "cargada", 5000, RUT_OTRA)          # Consorcio / Herencia SpA
            self._doc(c, "factura", "cargada", 200, None)               # sin receptor: cuenta y se avisa
            self._doc(c, "nota_credito", "aplicada", 100, RUT_EMPRESA)
            self._doc(c, "nota_credito", "aplicada", 700, RUT_OTRA)
            c.commit()
        r = self._f29(RUT_EMPRESA)
        self.assertEqual(r["facturas_iva_clp"], 1200)
        self.assertEqual(r["notas_credito_iva_clp"], 100)
        self.assertEqual(r["credito_fiscal_neto_clp"], 1100)
        self.assertEqual(r["excluidas_otro_receptor"], {
            "facturas_cantidad": 1, "facturas_iva_clp": 5000, "notas_credito_cantidad": 1, "notas_credito_iva_clp": 700})
        self.assertEqual(r["sin_receptor_cantidad"], 1)
        self.assertEqual(r["rut_empresa"], RUT_EMPRESA)

    def test_sin_rut_de_empresa_configurado_no_se_excluye_nada(self):
        with psycopg.connect(URL_TEST) as c:
            self._doc(c, "factura", "cargada", 1000, RUT_EMPRESA)
            self._doc(c, "factura", "cargada", 5000, RUT_OTRA)
            c.commit()
        r = self._f29(None)
        self.assertEqual(r["credito_fiscal_neto_clp"], 6000)
        self.assertIsNone(r["rut_empresa"])
        self.assertEqual(r["excluidas_otro_receptor"]["facturas_cantidad"], 0)


if __name__ == "__main__":
    unittest.main()
