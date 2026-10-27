import unittest
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta

from hotel_inventario.dominio import Huesped, TipoCargo
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import CargoNoReversible, HORA_LLEGADA, hotel_sintetico

EMPRESA = EMPRESA_FIJA.id
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")
LLEGADA = datetime.combine(INICIO, HORA_LLEGADA)


def reserva_con_cargo_de_cancelacion(servicio):
    reserva = servicio.reservar(EMPRESA, "HAB-SINT-101", INICIO, FIN, HUESPED).reserva
    cancelacion = servicio.cancelar(EMPRESA, reserva.id, LLEGADA - timedelta(hours=1))
    return reserva.id, cancelacion.cargo


class CuentaReversoTest(unittest.TestCase):
    def test_reverso_deja_el_saldo_en_cero_sin_editar_el_cargo_original(self):
        servicio = hotel_sintetico()
        reserva_id, cargo = reserva_con_cargo_de_cancelacion(servicio)
        servicio.reversar_cargo(EMPRESA, cargo.id)

        cuenta = servicio.cuenta(EMPRESA, reserva_id)
        self.assertEqual(len(cuenta), 2)
        original = next(c for c in cuenta if c.id == cargo.id)
        self.assertIs(original.tipo, TipoCargo.CARGO)
        self.assertEqual(original.monto_clp, cargo.monto_clp)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 0)

    def test_el_asiento_no_se_puede_modificar_en_memoria(self):
        servicio = hotel_sintetico()
        _, cargo = reserva_con_cargo_de_cancelacion(servicio)
        with self.assertRaises(FrozenInstanceError):
            cargo.monto_clp = 1

    def test_no_se_revierte_dos_veces_el_mismo_cargo(self):
        servicio = hotel_sintetico()
        _, cargo = reserva_con_cargo_de_cancelacion(servicio)
        servicio.reversar_cargo(EMPRESA, cargo.id)
        with self.assertRaises(CargoNoReversible):
            servicio.reversar_cargo(EMPRESA, cargo.id)

    def test_un_reverso_no_se_revierte(self):
        servicio = hotel_sintetico()
        _, cargo = reserva_con_cargo_de_cancelacion(servicio)
        reverso = servicio.reversar_cargo(EMPRESA, cargo.id)
        with self.assertRaises(CargoNoReversible):
            servicio.reversar_cargo(EMPRESA, reverso.id)

    def test_cargo_manual_asentado_y_luego_revertido(self):
        servicio = hotel_sintetico()
        reserva = servicio.reservar(EMPRESA, "HAB-SINT-103", INICIO, FIN, HUESPED).reserva
        cargo = servicio.asentar_cargo(EMPRESA, reserva.id, "Minibar sintético", 12_000)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva.id), 12_000)
        servicio.reversar_cargo(EMPRESA, cargo.id)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva.id), 0)


if __name__ == "__main__":
    unittest.main()
