import unittest
from datetime import date, datetime, timedelta

from hotel_inventario.dominio import Huesped, TipoCargo
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import HORA_LLEGADA, ReservaNoCancelable, hotel_sintetico

EMPRESA = EMPRESA_FIJA.id
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")
LLEGADA = datetime.combine(INICIO, HORA_LLEGADA)
TARIFA_PRIMERA_NOCHE = 50_000  # tarifa de HAB-SINT-101 en hotel_sintetico()


def reservar_101(servicio):
    resultado = servicio.reservar(EMPRESA, "HAB-SINT-101", INICIO, FIN, HUESPED)
    assert resultado.confirmada, resultado.motivo
    return resultado.reserva.id


class CancelacionTest(unittest.TestCase):
    def test_cancelar_exactamente_48_horas_antes_no_genera_cargo(self):
        servicio = hotel_sintetico()
        reserva_id = reservar_101(servicio)
        resultado = servicio.cancelar(EMPRESA, reserva_id, LLEGADA - timedelta(hours=48))
        self.assertIsNone(resultado.cargo)
        self.assertEqual(servicio.cuenta(EMPRESA, reserva_id), ())

    def test_cancelar_mas_de_48_horas_antes_no_genera_cargo(self):
        servicio = hotel_sintetico()
        reserva_id = reservar_101(servicio)
        resultado = servicio.cancelar(EMPRESA, reserva_id, LLEGADA - timedelta(days=5))
        self.assertIsNone(resultado.cargo)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 0)

    def test_cancelar_menos_de_48_horas_antes_carga_la_primera_noche(self):
        servicio = hotel_sintetico()
        reserva_id = reservar_101(servicio)
        resultado = servicio.cancelar(EMPRESA, reserva_id, LLEGADA - timedelta(hours=47, minutes=59))
        self.assertIsNotNone(resultado.cargo)
        self.assertIs(resultado.cargo.tipo, TipoCargo.CARGO)
        self.assertEqual(resultado.cargo.monto_clp, TARIFA_PRIMERA_NOCHE)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), TARIFA_PRIMERA_NOCHE)

    def test_la_reserva_cancelada_libera_la_unidad(self):
        servicio = hotel_sintetico()
        reserva_id = reservar_101(servicio)
        servicio.cancelar(EMPRESA, reserva_id, LLEGADA - timedelta(days=5))
        disponibles = {u.id for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)}
        self.assertIn("HAB-SINT-101", disponibles)

    def test_no_se_puede_cancelar_dos_veces(self):
        servicio = hotel_sintetico()
        reserva_id = reservar_101(servicio)
        servicio.cancelar(EMPRESA, reserva_id, LLEGADA - timedelta(days=5))
        with self.assertRaises(ReservaNoCancelable):
            servicio.cancelar(EMPRESA, reserva_id, LLEGADA - timedelta(days=5))


if __name__ == "__main__":
    unittest.main()
