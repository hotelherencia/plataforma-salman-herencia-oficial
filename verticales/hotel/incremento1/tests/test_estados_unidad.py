import unittest
from datetime import date

from hotel_inventario.dominio import EstadoReserva, EstadoUnidad, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import ESTADO_NO_VENDIBLE, hotel_sintetico

EMPRESA = EMPRESA_FIJA.id
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class EstadosUnidadTest(unittest.TestCase):
    def test_limpia_sucia_e_inspeccionada_se_pueden_vender(self):
        servicio = hotel_sintetico()
        disponibles = {u.id for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)}
        self.assertIn("HAB-SINT-101", disponibles)  # limpia
        self.assertIn("HAB-SINT-102", disponibles)  # sucia
        self.assertIn("HAB-SINT-103", disponibles)  # inspeccionada

    def test_bloqueada_y_fuera_de_servicio_no_entran_al_cupo(self):
        servicio = hotel_sintetico()
        disponibles = {u.id for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)}
        self.assertNotIn("HAB-SINT-104", disponibles)  # bloqueada
        self.assertNotIn("HAB-SINT-105", disponibles)  # fuera de servicio

    def test_reservar_unidad_bloqueada_se_rechaza_sin_confirmar(self):
        servicio = hotel_sintetico()
        resultado = servicio.reservar(EMPRESA, "HAB-SINT-104", INICIO, FIN, HUESPED)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, ESTADO_NO_VENDIBLE)
        self.assertIs(resultado.reserva.estado, EstadoReserva.RECHAZADA)

    def test_unidad_que_vuelve_a_limpia_se_puede_reservar(self):
        servicio = hotel_sintetico()
        servicio.cambiar_estado_unidad(EMPRESA, "HAB-SINT-104", EstadoUnidad.LIMPIA)
        resultado = servicio.reservar(EMPRESA, "HAB-SINT-104", INICIO, FIN, HUESPED)
        self.assertTrue(resultado.confirmada)

    def test_pasar_a_bloqueada_saca_la_unidad_del_cupo(self):
        servicio = hotel_sintetico()
        servicio.cambiar_estado_unidad(EMPRESA, "HAB-SINT-101", EstadoUnidad.BLOQUEADA)
        disponibles = {u.id for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)}
        self.assertNotIn("HAB-SINT-101", disponibles)


if __name__ == "__main__":
    unittest.main()
