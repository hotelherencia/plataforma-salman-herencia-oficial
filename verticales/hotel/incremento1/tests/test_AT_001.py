from datetime import date, datetime
import unittest

from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import (
    AccesoDenegado,
    POLITICA_CANCELACION,
    hotel_sintetico,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
AHORA = datetime(2026, 11, 1, 10, 0)


class AT001Test(unittest.TestCase):
    def test_AT_001_la_oferta_incluye_tarifa_y_politica_vigentes(self):
        servicio = servicio_con_una_unidad()
        ofertas = servicio.consultar_oferta(EMPRESA, date(2026, 11, 10), date(2026, 11, 12), 2, AHORA)
        self.assertEqual(len(ofertas), 1)
        oferta = ofertas[0]
        self.assertEqual(oferta.tarifa_noche_clp, 50_000)
        self.assertEqual(oferta.politica_cancelacion, POLITICA_CANCELACION)
        self.assertEqual(oferta.emitida_en, AHORA)
        self.assertGreater(oferta.vigente_hasta, AHORA)

    def test_AT_001_unidad_en_mantenimiento_no_se_oferta(self):
        servicio = hotel_sintetico()
        servicio.abrir_mantenimiento(EMPRESA, "HAB-SINT-101")
        ofertas = servicio.consultar_oferta(EMPRESA, date(2026, 11, 10), date(2026, 11, 12), 2, AHORA)
        self.assertNotIn("HAB-SINT-101", {o.unidad_id for o in ofertas})

    def test_AT_001_otra_empresa_no_consulta_oferta(self):
        servicio = servicio_con_una_unidad()
        with self.assertRaises(AccesoDenegado):
            servicio.consultar_oferta("EMP-OTRA", date(2026, 11, 10), date(2026, 11, 12), 2, AHORA)


if __name__ == "__main__":
    unittest.main()
