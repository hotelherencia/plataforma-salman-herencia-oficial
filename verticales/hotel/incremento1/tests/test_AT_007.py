from datetime import date, datetime
import unittest

from hotel_inventario.dominio import EstadoReserva, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.puertos import PuertosVacios, ResultadoPedidos
from hotel_inventario.servicio import (
    AccesoDenegado,
    hotel_sintetico,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
LAS_15 = datetime(2026, 11, 10, 15, 0)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class _PedidosConfigurados:
    def __init__(self, monto_clp: int) -> None:
        self._monto = monto_clp
        self.llamadas = 0

    def hacer_pedido(self, pedido):
        self.llamadas += 1
        return ResultadoPedidos(aceptado=True, comanda_id="CMD-SINT-1", monto_clp=self._monto)


class PuertoCafeteriaConfigurado(PuertosVacios):
    def __init__(self, monto_clp: int) -> None:
        super().__init__()
        self.pedidos = _PedidosConfigurados(monto_clp)


class AT007Test(unittest.TestCase):
    def hospedar(self, servicio=None):
        servicio = servicio or servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        return servicio, reserva_id

    def test_AT_007_sin_cafeteria_habilitada_el_servicio_se_declara_no_disponible(self):
        servicio, reserva_id = self.hospedar()
        resultado = servicio.pedir_a_habitacion(EMPRESA, reserva_id, ("café",))
        self.assertFalse(resultado.confirmado)
        self.assertEqual(resultado.motivo, "servicio no disponible")
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 50_000)

        # sin bloquear reservas: el flujo de inventario sigue operando
        self.assertIn(UNIDAD, {u.id for u in servicio.consultar_disponibilidad(EMPRESA, date(2026, 12, 1), date(2026, 12, 2), 1)})
        futura = servicio.reservar(EMPRESA, UNIDAD, date(2026, 12, 1), date(2026, 12, 2), HUESPED)
        self.assertTrue(futura.confirmada, futura.motivo)

    def test_AT_007_pedido_aprobado_crea_comanda_y_cargo_con_idempotencia(self):
        puertos = PuertoCafeteriaConfigurado(monto_clp=15_000)
        servicio, reserva_id = self.hospedar(servicio_con_una_unidad(puertos=puertos))
        resultado = servicio.pedir_a_habitacion(EMPRESA, reserva_id, ("café", "tostada"), clave="ped-001")
        self.assertTrue(resultado.confirmado)
        self.assertEqual(puertos.pedidos.llamadas, 1)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 65_000)
        cargo = [c for c in servicio.cuenta(EMPRESA, reserva_id) if c.concepto == "Pedido a habitación"]
        self.assertEqual(len(cargo), 1)
        self.assertEqual(cargo[0].monto_clp, 15_000)
        self.assertEqual(cargo[0].referencia, "pedido:CMD-SINT-1")

        reintento = servicio.pedir_a_habitacion(EMPRESA, reserva_id, ("café", "tostada"), clave="ped-001")
        self.assertEqual(reintento.pedido.id, resultado.pedido.id)
        self.assertEqual(puertos.pedidos.llamadas, 1)
        self.assertEqual(len([c for c in servicio.cuenta(EMPRESA, reserva_id) if c.concepto == "Pedido a habitación"]), 1)

    def test_AT_007_denegaciones(self):
        servicio, reserva_id = self.hospedar()
        with self.assertRaises(AccesoDenegado):
            servicio.pedir_a_habitacion("EMP-OTRA", reserva_id, ("café",))
        with self.assertRaises(ValueError):
            servicio.pedir_a_habitacion(EMPRESA, reserva_id, ())
        otra = servicio.reservar(EMPRESA, UNIDAD, date(2026, 12, 5), date(2026, 12, 6), HUESPED)
        with self.assertRaises(ValueError):
            servicio.pedir_a_habitacion(EMPRESA, otra.reserva.id, ("café",))


if __name__ == "__main__":
    unittest.main()
