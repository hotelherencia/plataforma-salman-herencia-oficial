from datetime import date, datetime
import unittest

from hotel_inventario.dominio import EstadoReserva, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.puertos import PuertosVacios, ResultadoPedidos
from hotel_inventario.servicio import (
    AccesoDenegado,
    hotel_con_extras,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
LAS_15 = datetime(2026, 11, 10, 15, 0)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class _PedidosDobles:
    def __init__(self) -> None:
        self.llamadas = 0

    def hacer_pedido(self, pedido):
        self.llamadas += 1
        return ResultadoPedidos(aceptado=True, comanda_id="CMD-DOBLE", monto_clp=7_000)


class _PuertosDobles(PuertosVacios):
    def __init__(self) -> None:
        super().__init__()
        self.pedidos = _PedidosDobles()


class LoteFTest(unittest.TestCase):
    def test_AC_US_HOT_001_05_reintento_del_cambio_no_crea_segundo_cargo(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        propuesta = servicio.previsualizar_cambio(EMPRESA, reserva_id, 60_000)
        servicio.aplicar_cambio(EMPRESA, reserva_id, propuesta, aceptacion=True)
        saldo = servicio.saldo_clp(EMPRESA, reserva_id)
        servicio.aplicar_cambio(EMPRESA, reserva_id, propuesta, aceptacion=True)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), saldo)
        self.assertEqual(len(servicio.cuenta(EMPRESA, reserva_id)), 1)

    def test_AC_US_HOT_002_04_cargo_sin_entrega_no_informa_servicio_entregado(self):
        puertos = _PuertosDobles()
        servicio = servicio_con_una_unidad(puertos=puertos)
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        pedido = servicio.pedir_a_habitacion(EMPRESA, reserva_id, ("café",)).pedido

        self.assertFalse(servicio.servicio_entregado(EMPRESA, reserva_id, pedido.id))
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 57_000)

        servicio.marcar_entregado(EMPRESA, reserva_id, pedido.id)
        self.assertTrue(servicio.servicio_entregado(EMPRESA, reserva_id, pedido.id))
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 57_000)

    def test_AC_US_HOT_002_05_doble_respuesta_del_conector_una_comanda_y_un_cargo(self):
        puertos = _PuertosDobles()
        servicio = servicio_con_una_unidad(puertos=puertos)
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.check_in(EMPRESA, reserva_id, LAS_15)

        primero = servicio.pedir_a_habitacion(EMPRESA, reserva_id, ("té",), clave="ped-x")
        segundo = servicio.pedir_a_habitacion(EMPRESA, reserva_id, ("té",), clave="ped-x")
        self.assertEqual(primero.pedido.id, segundo.pedido.id)
        self.assertEqual(puertos.pedidos.llamadas, 1)
        self.assertEqual(len(servicio.pedidos(EMPRESA, reserva_id)), 1)
        self.assertEqual(
            len([c for c in servicio.cuenta(EMPRESA, reserva_id) if c.concepto == "Pedido a habitación"]),
            1,
        )

    def test_AT_018_cancelar_reserva_pagada_retienen_el_dinero(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.registrar_pago(EMPRESA, reserva_id, 100_000, clave="pag-total")
        cancelada = servicio.cancelar(EMPRESA, reserva_id, datetime(2026, 11, 5, 12, 0))
        self.assertIs(cancelada.reserva.estado, EstadoReserva.CANCELADA)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), -100_000)
        self.assertEqual(servicio.devoluciones(EMPRESA, reserva_id), ())
        with self.assertRaises(AccesoDenegado):
            servicio.cancelar("EMP-OTRA", reserva_id, datetime(2026, 11, 5, 12, 0))

    def test_AT_019_extras_calculan_cantidades_y_otro_tenant_se_deniega(self):
        servicio = hotel_con_extras()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        desayuno = servicio.agregar_extra(EMPRESA, reserva_id, "EXT-DESAYUNO", personas=2, noches=3)
        self.assertEqual(desayuno.cantidad, 6)
        botella = servicio.agregar_extra(EMPRESA, reserva_id, "EXT-BOTELLA", personas=2, noches=3)
        self.assertEqual(botella.cantidad, 1)
        with self.assertRaises(AccesoDenegado):
            servicio.agregar_extra("EMP-OTRA", reserva_id, "EXT-DESAYUNO", personas=2, noches=3)


if __name__ == "__main__":
    unittest.main()
