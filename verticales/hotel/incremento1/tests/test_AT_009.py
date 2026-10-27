from datetime import date, datetime
import unittest

from hotel_inventario.dominio import EstadoReserva, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.puertos import PuertosVacios
from hotel_inventario.servicio import (
    AccesoDenegado,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
LAS_15 = datetime(2026, 11, 10, 15, 0)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class _Boom:
    def __getattr__(self, item):
        raise AssertionError(f"puerto invocado: {item}")


class PuertosEspia(PuertosVacios):
    def __init__(self) -> None:
        self.pms = _Boom()
        self.canal = _Boom()
        self.pago = _Boom()
        self.documento_tributario = _Boom()


class AT009Test(unittest.TestCase):
    def test_AT_009_cuenta_acumula_cargos_y_anticipos_y_liquida_al_salir(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id

        anticipo = servicio.registrar_pago(EMPRESA, reserva_id, 30_000, clave="ant-001")
        self.assertEqual(anticipo.monto_clp, 30_000)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), -30_000)

        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        servicio.asentar_cargo(EMPRESA, reserva_id, "Minibar sintético", 10_000, clave="min-001")

        salida = servicio.check_out(EMPRESA, reserva_id, datetime(2026, 11, 12, 11, 0))
        self.assertIs(salida.estado, EstadoReserva.SALIDA)

        liquidacion = servicio.liquidacion(EMPRESA, reserva_id)
        self.assertEqual(liquidacion.total_cargos_clp, 60_000)
        self.assertEqual(liquidacion.total_pagos_clp, 30_000)
        self.assertEqual(liquidacion.saldo_clp, 30_000)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 30_000)

    def test_AT_009_reintentar_cargo_o_pago_no_duplica(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id

        primero = servicio.asentar_cargo(EMPRESA, reserva_id, "Desayuno", 8_000, clave="des-001")
        reintento = servicio.asentar_cargo(EMPRESA, reserva_id, "Desayuno", 8_000, clave="des-001")
        self.assertEqual(primero.id, reintento.id)
        self.assertEqual(len(servicio.cuenta(EMPRESA, reserva_id)), 1)

        pago1 = servicio.registrar_pago(EMPRESA, reserva_id, 8_000, clave="pag-001")
        pago2 = servicio.registrar_pago(EMPRESA, reserva_id, 8_000, clave="pag-001")
        self.assertEqual(pago1.id, pago2.id)
        self.assertEqual(len(servicio.pagos(EMPRESA, reserva_id)), 1)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 0)

    def test_AT_009_denegaciones(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        with self.assertRaises(AccesoDenegado):
            servicio.registrar_pago("EMP-OTRA", reserva_id, 1_000)
        with self.assertRaises(AccesoDenegado):
            servicio.liquidacion("EMP-OTRA", reserva_id)
        with self.assertRaises(ValueError):
            servicio.registrar_pago(EMPRESA, reserva_id, 0)
        with self.assertRaises(ValueError):
            servicio.registrar_pago(EMPRESA, "RSV-SINT-9999", 1_000)
        with self.assertRaises(ValueError):
            servicio.liquidacion(EMPRESA, reserva_id)

    def test_AT_009_recuperacion_reverso_reflejado_en_liquidacion(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        cargo = servicio.asentar_cargo(EMPRESA, reserva_id, "Error de cargo", 10_000, clave="err-001")
        servicio.reversar_cargo(EMPRESA, cargo.id)
        servicio.check_out(EMPRESA, reserva_id, datetime(2026, 11, 12, 11, 0))
        liquidacion = servicio.liquidacion(EMPRESA, reserva_id)
        self.assertEqual(liquidacion.total_cargos_clp, 50_000)
        self.assertEqual(liquidacion.saldo_clp, 50_000)

    def test_AT_009_importe_cubierto_no_dispara_documento_ni_pago(self):
        servicio = servicio_con_una_unidad(puertos=PuertosEspia())
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.registrar_pago(EMPRESA, reserva_id, 100_000, clave="pag-total")
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        servicio.check_out(EMPRESA, reserva_id, datetime(2026, 11, 12, 11, 0))
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), -50_000)


if __name__ == "__main__":
    unittest.main()
