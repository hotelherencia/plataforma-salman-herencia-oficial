from datetime import datetime, timedelta
import unittest

from hotel_reservas_incremento1.dominio import EstadoReserva
from hotel_reservas_incremento1.empresa import EMPRESA_FIJA, ESTABLECIMIENTO_FIJO
from hotel_reservas_incremento1.servicio import hotel_sintetico_con_una_unidad

EMPRESA = EMPRESA_FIJA.id
ESTABLECIMIENTO = ESTABLECIMIENTO_FIJO.id
UNIDAD = "HAB-SINT-101"
INICIO = datetime(2026, 11, 10, 14, 0)
FIN = datetime(2026, 11, 12, 11, 0)
LLEGADA = datetime(2026, 11, 10, 15, 0)
TARIFA_NOCHE = 60000


def huesped():
    from hotel_reservas_incremento1.dominio import Huesped

    return Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class CuentaTest(unittest.TestCase):
    def setUp(self):
        self.servicio = hotel_sintetico_con_una_unidad()
        self.resultado = self.servicio.reservar(EMPRESA, ESTABLECIMIENTO, UNIDAD, INICIO, FIN, LLEGADA, huesped())
        self.assertTrue(self.resultado.confirmada)
        self.reserva_id = self.resultado.reserva.id

    def cuenta_id(self):
        cuentas = [c for c in self.servicio._cuentas if c.reserva_id == self.reserva_id]
        self.assertEqual(len(cuentas), 1)
        return cuentas[0].id

    def test_cancelacion_antes_de_48h_sin_cargo(self):
        ahora = LLEGADA - timedelta(hours=49)
        reserva = self.servicio.cancelar(EMPRESA, self.reserva_id, ahora)
        self.assertEqual(reserva.estado, EstadoReserva.CANCELADA)
        self.assertEqual(self.servicio.cargos_de_cuenta(EMPRESA, self.cuenta_id()), [])
        self.assertEqual(self.servicio.saldo_cuenta(EMPRESA, self.cuenta_id()), 0)

    def test_cancelacion_despues_de_48h_cobra_primera_noche(self):
        ahora = LLEGADA - timedelta(hours=1)
        reserva = self.servicio.cancelar(EMPRESA, self.reserva_id, ahora)
        self.assertEqual(reserva.estado, EstadoReserva.CANCELADA)
        self.assertEqual(self.servicio.saldo_cuenta(EMPRESA, self.cuenta_id()), TARIFA_NOCHE)
        cargos = self.servicio.cargos_de_cuenta(EMPRESA, self.cuenta_id())
        self.assertEqual(len(cargos), 1)
        self.assertEqual(cargos[0].concepto, "cancelacion_tardia")

    def test_cargo_asentado_no_se_edita_se_revierve(self):
        cuenta = self.cuenta_id()
        cargo = self.servicio.asentar_cargo(EMPRESA, cuenta, "desayuno", 12000)
        self.assertEqual(self.servicio.saldo_cuenta(EMPRESA, cuenta), 12000)

        reverso = self.servicio.revertir_cargo(EMPRESA, cargo.id)
        self.assertEqual(reverso.monto_clp, -12000)
        self.assertEqual(reverso.cargo_origen_id, cargo.id)

        cargos = self.servicio.cargos_de_cuenta(EMPRESA, cuenta)
        original = next(c for c in cargos if c.id == cargo.id)
        self.assertEqual(original.monto_clp, 12000)
        self.assertEqual(len(cargos), 2)
        self.assertEqual(self.servicio.saldo_cuenta(EMPRESA, cuenta), 0)

    def test_revertir_un_cargo_ya_reversado_falla(self):
        cuenta = self.cuenta_id()
        cargo = self.servicio.asentar_cargo(EMPRESA, cuenta, "minibar", 5000)
        reverso = self.servicio.revertir_cargo(EMPRESA, cargo.id)
        with self.assertRaises(ValueError):
            self.servicio.revertir_cargo(EMPRESA, cargo.id)
        with self.assertRaises(ValueError):
            self.servicio.revertir_cargo(EMPRESA, reverso.id)


if __name__ == "__main__":
    unittest.main()
