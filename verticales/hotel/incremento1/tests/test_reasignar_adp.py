"""Port ADP al clon (#361): reasignar una reserva a otra unidad la decide el dominio."""
from datetime import date, datetime
import unittest

from hotel_inventario.dominio import EstadoReserva, EstadoTarea, EstadoUnidad, Huesped, Unidad
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import ReasignacionNoPermitida, hotel_sintetico

EMPRESA = EMPRESA_FIJA.id
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")
INICIO, FIN = date(2026, 12, 1), date(2026, 12, 3)
LLEGADA = datetime(2026, 12, 1, 15, 0)


class ReasignarTest(unittest.TestCase):
    def setUp(self):
        self.hotel = hotel_sintetico()
        self.hotel.alta_unidad(Unidad("HAB-SINT-106", "EST-SINT-001", 2, 50_000, EstadoUnidad.LIMPIA))
        self.r = self.hotel.reservar(EMPRESA, "HAB-SINT-101", INICIO, FIN, HUESPED).reserva

    def test_confirmada_cambia_de_unidad_y_conserva_la_tarifa_aceptada(self):
        tarifa = self.hotel.tarifa_vigente(EMPRESA, "HAB-SINT-101", INICIO)
        movida = self.hotel.reasignar(EMPRESA, self.r.id, "HAB-SINT-106")
        self.assertEqual(movida.unidad_id, "HAB-SINT-106")
        self.assertEqual(movida.estado, EstadoReserva.CONFIRMADA)
        self.assertEqual(self.hotel._tarifa_de_reserva(self.r.id), tarifa)
        # la unidad de origen vuelve a ser vendible en ese rango
        self.assertTrue(self.hotel._libre("HAB-SINT-101", INICIO, FIN))

    def test_hospedada_ocupa_la_nueva_y_deja_sucia_la_anterior_con_limpieza(self):
        self.hotel.check_in(EMPRESA, self.r.id, LLEGADA)
        self.hotel.reasignar(EMPRESA, self.r.id, "HAB-SINT-106")
        self.assertIs(self.hotel._unidades["HAB-SINT-106"].estado, EstadoUnidad.OCUPADA)
        self.assertIs(self.hotel._unidades["HAB-SINT-101"].estado, EstadoUnidad.SUCIA)
        pendientes = [t for t in self.hotel.tareas(EMPRESA)
                      if t.unidad_id == "HAB-SINT-101" and t.estado is EstadoTarea.PENDIENTE]
        self.assertEqual([t.tipo for t in pendientes], ["limpieza"])

    def test_hospedada_no_pasa_a_una_unidad_sucia(self):
        self.hotel.check_in(EMPRESA, self.r.id, LLEGADA)
        self.hotel.alta_unidad(Unidad("HAB-SINT-107", "EST-SINT-001", 2, 50_000, EstadoUnidad.SUCIA))
        with self.assertRaises(ReasignacionNoPermitida):
            self.hotel.reasignar(EMPRESA, self.r.id, "HAB-SINT-107")
        self.assertEqual(self.hotel._reservas[self.r.id].unidad_id, "HAB-SINT-101")

    def test_rechaza_misma_unidad_inexistente_y_no_vendible(self):
        for destino in ("HAB-SINT-101", "HAB-NO-EXISTE", "HAB-SINT-104", "HAB-SINT-105"):
            with self.subTest(destino=destino), self.assertRaises(ReasignacionNoPermitida):
                self.hotel.reasignar(EMPRESA, self.r.id, destino)
        self.assertEqual(self.hotel._reservas[self.r.id].unidad_id, "HAB-SINT-101")

    def test_rechaza_destino_en_mantenimiento(self):
        from dataclasses import replace

        u = self.hotel._unidades["HAB-SINT-106"]
        self.hotel._unidades["HAB-SINT-106"] = replace(u, mantenimiento=True)
        with self.assertRaises(ReasignacionNoPermitida):
            self.hotel.reasignar(EMPRESA, self.r.id, "HAB-SINT-106")

    def test_rechaza_destino_ocupado_en_el_rango_y_acepta_el_contiguo(self):
        self.hotel.reservar(EMPRESA, "HAB-SINT-106", date(2026, 12, 2), date(2026, 12, 4), HUESPED)
        with self.assertRaises(ReasignacionNoPermitida):
            self.hotel.reasignar(EMPRESA, self.r.id, "HAB-SINT-106")
        otra = self.hotel.reservar(EMPRESA, "HAB-SINT-101", date(2026, 12, 3), date(2026, 12, 5), HUESPED).reserva
        self.hotel.alta_unidad(Unidad("HAB-SINT-108", "EST-SINT-001", 2, 50_000, EstadoUnidad.LIMPIA))
        self.hotel.reservar(EMPRESA, "HAB-SINT-108", date(2026, 12, 1), date(2026, 12, 3), HUESPED)  # termina cuando empieza `otra`
        self.assertEqual(self.hotel.reasignar(EMPRESA, otra.id, "HAB-SINT-108").unidad_id, "HAB-SINT-108")

    def test_solo_confirmada_o_hospedada(self):
        self.hotel.cancelar(EMPRESA, self.r.id, datetime(2026, 11, 1))
        with self.assertRaises(ReasignacionNoPermitida):
            self.hotel.reasignar(EMPRESA, self.r.id, "HAB-SINT-106")
        with self.assertRaises(ReasignacionNoPermitida):
            self.hotel.reasignar(EMPRESA, "RSV-NO-EXISTE", "HAB-SINT-106")


if __name__ == "__main__":
    unittest.main()
