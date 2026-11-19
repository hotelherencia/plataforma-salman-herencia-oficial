"""Port ADP al clon (#359): el reverso del dominio puede llevar el motivo del operador."""
from datetime import date
import unittest

from hotel_inventario.dominio import Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import CargoNoReversible, hotel_sintetico

EMPRESA = EMPRESA_FIJA.id
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class ReversoConMotivoTest(unittest.TestCase):
    def setUp(self):
        self.hotel = hotel_sintetico()
        unidad = next(iter(self.hotel._unidades))
        r = self.hotel.reservar(EMPRESA, unidad, date(2026, 12, 1), date(2026, 12, 3), HUESPED).reserva
        self.reserva = r.id
        self.cargo = self.hotel.asentar_cargo(EMPRESA, r.id, "Minibar", 3_000)

    def test_sin_motivo_conserva_el_concepto_de_siempre(self):
        reverso = self.hotel.reversar_cargo(EMPRESA, self.cargo.id)
        self.assertEqual(reverso.concepto, f"Reverso de {self.cargo.id}")

    def test_con_motivo_dice_que_se_revierte_y_por_que(self):
        reverso = self.hotel.reversar_cargo(EMPRESA, self.cargo.id, motivo="se cobró dos veces")
        self.assertEqual(reverso.concepto, "Reverso de Minibar: se cobró dos veces")
        self.assertEqual(reverso.referencia, self.cargo.id)
        self.assertEqual(reverso.monto_clp, 3_000)

    def test_el_motivo_no_salta_la_regla_de_un_solo_reverso(self):
        self.hotel.reversar_cargo(EMPRESA, self.cargo.id, motivo="uno")
        with self.assertRaises(CargoNoReversible):
            self.hotel.reversar_cargo(EMPRESA, self.cargo.id, motivo="dos")


if __name__ == "__main__":
    unittest.main()
