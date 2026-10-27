from datetime import date, datetime
import unittest

from hotel_inventario.dominio import EstadoReserva, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import (
    AccesoDenegado,
    CheckInIncompleto,
    CheckInNoPermitido,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
LAS_15 = datetime(2026, 11, 10, 15, 0)


class AT006Test(unittest.TestCase):
    def test_AT_006_check_in_sin_documento_queda_incompleto_y_el_documento_exige_rol(self):
        servicio = servicio_con_una_unidad()
        huesped = Huesped(nombre="Huésped Sintético Sin Documento", documento=None)
        resultado = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, huesped)
        self.assertTrue(resultado.confirmada, resultado.motivo)
        reserva_id = resultado.reserva.id

        with self.assertRaises(CheckInIncompleto):
            servicio.check_in(EMPRESA, reserva_id, LAS_15)
        self.assertIs(
            servicio.reservas_confirmadas(EMPRESA)[0].estado, EstadoReserva.CONFIRMADA
        )
        self.assertIn(UNIDAD, {u.id for u in servicio.consultar_disponibilidad(EMPRESA, date(2026, 11, 20), date(2026, 11, 21), 2)})
        self.assertIn(reserva_id, servicio.ingresos_incompletos(EMPRESA))

        with self.assertRaises(AccesoDenegado):
            servicio.documento_huesped(EMPRESA, reserva_id, rol="limpieza")
        self.assertEqual(servicio.accesos_documento(EMPRESA), [])

        documento = servicio.documento_huesped(EMPRESA, reserva_id, rol="recepcion")
        self.assertIsNone(documento)
        self.assertEqual(servicio.accesos_documento(EMPRESA), [(reserva_id, "recepcion")])

    def test_AT_006_check_in_con_documento_sigue_entrando(self):
        servicio = servicio_con_una_unidad()
        huesped = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, huesped).reserva.id
        hospedada = servicio.check_in(EMPRESA, reserva_id, LAS_15)
        self.assertIs(hospedada.estado, EstadoReserva.HOSPEDADA)
        self.assertEqual(
            servicio.documento_huesped(EMPRESA, reserva_id, rol="administrador"), "DOC-SINT-0001"
        )


if __name__ == "__main__":
    unittest.main()
