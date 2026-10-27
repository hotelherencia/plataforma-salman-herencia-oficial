from datetime import date, datetime
import unittest

from hotel_inventario.dominio import Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import (
    AccesoDenegado,
    hotel_con_extras,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 13)
LAS_15 = datetime(2026, 11, 10, 15, 0)
HUESPED = Huesped(nombre="Huésped Sintético Dos", documento="DOC-SINT-0002")


class AC00203Test(unittest.TestCase):
    def test_AC_US_HOT_002_03_desayuno_seis_unidades_y_botella_una_con_reglas_visibles(self):
        servicio = hotel_con_extras()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.check_in(EMPRESA, reserva_id, LAS_15)

        desayuno = servicio.agregar_extra(EMPRESA, reserva_id, "EXT-DESAYUNO", personas=2, noches=3)
        self.assertEqual(desayuno.cantidad, 6)
        self.assertEqual(desayuno.monto_clp, 6 * 5_000)
        self.assertIn("2 personas", desayuno.regla_visible)
        self.assertIn("3 noches", desayuno.regla_visible)

        botella = servicio.agregar_extra(EMPRESA, reserva_id, "EXT-BOTELLA", personas=2, noches=3)
        self.assertEqual(botella.cantidad, 1)
        self.assertEqual(botella.monto_clp, 15_000)
        self.assertIn("por estadía", botella.regla_visible)

        servicio.asentar_noche(EMPRESA, reserva_id, date(2026, 11, 11), datetime(2026, 11, 11, 9, 0))
        servicio.asentar_noche(EMPRESA, reserva_id, date(2026, 11, 12), datetime(2026, 11, 12, 9, 0))
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 3 * 50_000 + 30_000 + 15_000)

    def test_AC_US_HOT_002_03_denegaciones(self):
        servicio = hotel_con_extras()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        with self.assertRaises(AccesoDenegado):
            servicio.agregar_extra("EMP-OTRA", reserva_id, "EXT-DESAYUNO", personas=2, noches=3)
        with self.assertRaises(ValueError):
            servicio.agregar_extra(EMPRESA, reserva_id, "EXT-INEXISTENTE", personas=2, noches=3)


if __name__ == "__main__":
    unittest.main()
