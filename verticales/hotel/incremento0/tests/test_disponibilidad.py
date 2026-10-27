from datetime import date
import unittest

from hotel_reservas_incremento0.dominio import EstadoReserva, Huesped
from hotel_reservas_incremento0.empresa import DATOS_SINTETICOS, EMPRESA_FIJA
from hotel_reservas_incremento0.servicio import (
    SIN_CUPO,
    UNIDAD_INEXISTENTE,
    AccesoDenegado,
    hotel_sintetico_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)


class DisponibilidadTest(unittest.TestCase):
    def setUp(self):
        self.servicio = hotel_sintetico_con_una_unidad()
        self.huesped = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")

    def test_empresa_y_datos_marcados_como_sinteticos(self):
        self.assertTrue(EMPRESA_FIJA.es_sintetico)
        self.assertTrue(DATOS_SINTETICOS)
        self.assertIn("SINTETICA", EMPRESA_FIJA.id)

    def test_consulta_disponible_devuelve_la_unidad(self):
        ofertas = self.servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2)
        self.assertEqual([o.unidad.id for o in ofertas], [UNIDAD])

    def test_consulta_con_mas_huespedes_que_capacidad_vacia(self):
        ofertas = self.servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 3)
        self.assertEqual(ofertas, [])

    def test_acceso_cruzado_denegado(self):
        with self.assertRaises(AccesoDenegado):
            self.servicio.consultar_disponibilidad("EMP-OTRA", INICIO, FIN, 2)
        with self.assertRaises(AccesoDenegado):
            self.servicio.reservar("EMP-OTRA", UNIDAD, INICIO, FIN, self.huesped)

    def test_reserva_confirma_y_bloquea_rango_solapado(self):
        primera = self.servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, self.huesped)
        self.assertTrue(primera.confirmada)
        self.assertEqual(primera.reserva.estado, EstadoReserva.CONFIRMADA)

        solapada = self.servicio.reservar(
            EMPRESA, UNIDAD, date(2026, 11, 11), date(2026, 11, 13), self.huesped
        )
        self.assertFalse(solapada.confirmada)
        self.assertEqual(solapada.motivo, SIN_CUPO)
        self.assertEqual(solapada.reserva.estado, EstadoReserva.RECHAZADA)

        ofertas = self.servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2)
        self.assertEqual(ofertas, [])

    def test_rango_no_solapado_sigue_disponible(self):
        self.servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, self.huesped)
        ofertas = self.servicio.consultar_disponibilidad(EMPRESA, date(2026, 11, 12), date(2026, 11, 14), 2)
        self.assertEqual([o.unidad.id for o in ofertas], [UNIDAD])

    def test_unidad_inexistente_rechazada(self):
        resultado = self.servicio.reservar(EMPRESA, "HAB-INEXISTENTE", INICIO, FIN, self.huesped)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, UNIDAD_INEXISTENTE)


if __name__ == "__main__":
    unittest.main()
