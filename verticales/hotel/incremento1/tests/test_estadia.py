from datetime import date, datetime
import unittest

from hotel_inventario.dominio import EstadoReserva, EstadoUnidad, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.puertos import PuertosVacios
from hotel_inventario.servicio import (
    CheckInNoPermitido,
    CheckOutNoPermitido,
    HORA_LLEGADA,
    NocheNoAsentable,
    ReservaNoCancelable,
    hotel_sintetico,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
TARIFA = 50_000
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")
LAS_15 = datetime(2026, 11, 10, 15, 0)
LAS_1459 = datetime(2026, 11, 10, 14, 59)


class _Boom:
    def __getattr__(self, item):
        raise AssertionError(f"puerto invocado: {item}")


class PuertosEspia(PuertosVacios):
    def __init__(self) -> None:
        self.pms = _Boom()
        self.canal = _Boom()
        self.pago = _Boom()
        self.documento_tributario = _Boom()


class EstadiaTest(unittest.TestCase):
    def reservar_101(self, servicio=None, inicio=INICIO, fin=FIN):
        servicio = servicio or servicio_con_una_unidad()
        resultado = servicio.reservar(EMPRESA, UNIDAD, inicio, fin, HUESPED)
        assert resultado.confirmada, resultado.motivo
        return servicio, resultado.reserva.id

    def test_check_in_a_las_15_hospeda_ocupa_y_asienta_la_noche(self):
        servicio, reserva_id = self.reservar_101()
        reserva = servicio.check_in(EMPRESA, reserva_id, LAS_15)
        self.assertIs(reserva.estado, EstadoReserva.HOSPEDADA)
        unidad = [u for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)]
        self.assertNotIn(UNIDAD, {u.id for u in unidad})
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), TARIFA)
        cargos = servicio.cuenta(EMPRESA, reserva_id)
        self.assertEqual(len(cargos), 1)
        self.assertEqual(cargos[0].concepto, "Noche")
        self.assertEqual(cargos[0].monto_clp, TARIFA)

    def test_check_in_a_las_1459_rechazado_sin_cargo_y_unidad_vendible(self):
        servicio, reserva_id = self.reservar_101()
        with self.assertRaises(CheckInNoPermitido) as ctx:
            servicio.check_in(EMPRESA, reserva_id, LAS_1459)
        self.assertIn("aún no es hora de llegada", str(ctx.exception))
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 0)
        libres = {u.id for u in servicio.consultar_disponibilidad(EMPRESA, date(2026, 11, 20), date(2026, 11, 21), 2)}
        self.assertIn(UNIDAD, libres)

    def test_segundo_check_in_de_la_misma_reserva_falla(self):
        servicio, reserva_id = self.reservar_101()
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        with self.assertRaises(CheckInNoPermitido):
            servicio.check_in(EMPRESA, reserva_id, LAS_15)

    def test_check_in_no_permite_unidad_bloqueada(self):
        servicio, reserva_id = self.reservar_101()
        servicio.cambiar_estado_unidad(EMPRESA, UNIDAD, EstadoUnidad.BLOQUEADA)
        with self.assertRaises(CheckInNoPermitido):
            servicio.check_in(EMPRESA, reserva_id, LAS_15)

    def test_check_in_no_permite_unidad_fuera_de_servicio(self):
        servicio, reserva_id = self.reservar_101()
        servicio.cambiar_estado_unidad(EMPRESA, UNIDAD, EstadoUnidad.FUERA_DE_SERVICIO)
        with self.assertRaises(CheckInNoPermitido):
            servicio.check_in(EMPRESA, reserva_id, LAS_15)

    def test_al_salir_la_unidad_queda_sucia_y_el_rango_libera(self):
        servicio, reserva_id = self.reservar_101()
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        salida = servicio.check_out(EMPRESA, reserva_id, datetime(2026, 11, 12, 11, 0))
        self.assertIs(salida.estado, EstadoReserva.SALIDA)
        unidades = {u.id: u for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2)}
        self.assertIn(UNIDAD, unidades)
        self.assertIs(unidades[UNIDAD].estado, EstadoUnidad.SUCIA)
        nueva = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED)
        self.assertTrue(nueva.confirmada, nueva.motivo)

    def test_dos_noches_asiento_del_checkin_mas_noche_posterior(self):
        servicio, reserva_id = self.reservar_101()
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        servicio.asentar_noche(EMPRESA, reserva_id, date(2026, 11, 11), datetime(2026, 11, 11, 9, 0))
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 2 * TARIFA)
        with self.assertRaises(NocheNoAsentable):
            servicio.asentar_noche(EMPRESA, reserva_id, date(2026, 11, 12), datetime(2026, 11, 12, 9, 0))
        with self.assertRaises(NocheNoAsentable) as ctx:
            servicio.asentar_noche(EMPRESA, reserva_id, date(2026, 11, 11), datetime(2026, 11, 11, 18, 0))
        self.assertIn("noche ya asentada", str(ctx.exception))
        with self.assertRaises(NocheNoAsentable):
            servicio.asentar_noche(EMPRESA, reserva_id, date(2026, 11, 10), datetime(2026, 11, 10, 20, 0))

    def test_check_out_con_saldo_positivo_completa_sin_invocar_puertos(self):
        servicio, reserva_id = self.reservar_101(servicio_con_una_unidad(puertos=PuertosEspia()))
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        servicio.asentar_noche(EMPRESA, reserva_id, date(2026, 11, 11), datetime(2026, 11, 11, 9, 0))
        salida = servicio.check_out(EMPRESA, reserva_id, datetime(2026, 11, 12, 11, 0))
        self.assertIs(salida.estado, EstadoReserva.SALIDA)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 2 * TARIFA)

    def test_otra_empresa_no_hace_check_in_ni_check_out(self):
        servicio, reserva_id = self.reservar_101()
        from hotel_inventario.servicio import AccesoDenegado

        with self.assertRaises(AccesoDenegado):
            servicio.check_in("EMP-OTRA", reserva_id, LAS_15)
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        with self.assertRaises(AccesoDenegado):
            servicio.check_out("EMP-OTRA", reserva_id, datetime(2026, 11, 12, 11, 0))

    def test_check_in_de_reserva_cancelada_falla(self):
        servicio, reserva_id = self.reservar_101()
        servicio.cancelar(EMPRESA, reserva_id, datetime(2026, 11, 5, 12, 0))
        with self.assertRaises(CheckInNoPermitido):
            servicio.check_in(EMPRESA, reserva_id, LAS_15)

    def test_check_out_de_reserva_solo_confirmada_falla(self):
        servicio, reserva_id = self.reservar_101()
        with self.assertRaises(CheckOutNoPermitido):
            servicio.check_out(EMPRESA, reserva_id, LAS_15)

    def test_la_hospedada_sigue_ocupando_el_rango(self):
        servicio, reserva_id = self.reservar_101()
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        otra = servicio.reservar(EMPRESA, UNIDAD, date(2026, 11, 11), date(2026, 11, 13), HUESPED)
        self.assertFalse(otra.confirmada)


if __name__ == "__main__":
    unittest.main()
