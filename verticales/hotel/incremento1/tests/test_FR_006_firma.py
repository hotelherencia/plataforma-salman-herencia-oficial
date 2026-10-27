from datetime import date, datetime
import unittest

from hotel_inventario.dominio import EstadoReserva, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import AccesoDenegado, servicio_con_una_unidad

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
LAS_15 = datetime(2026, 11, 10, 15, 0)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class FR006FirmaTest(unittest.TestCase):
    def test_FR_006_el_check_in_registra_la_firma_del_huesped_y_su_acceso_exige_rol(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        hospedada = servicio.check_in(
            EMPRESA, reserva_id, LAS_15, firma_registro="firma-sintetica-001"
        )
        self.assertIs(hospedada.estado, EstadoReserva.HOSPEDADA)

        with self.assertRaises(AccesoDenegado):
            servicio.firma_de_registro(EMPRESA, reserva_id, rol="limpieza")
        self.assertEqual(
            servicio.firma_de_registro(EMPRESA, reserva_id, rol="recepcion"),
            "firma-sintetica-001",
        )

        servicio2 = servicio_con_una_unidad()
        otra = servicio2.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio2.check_in(EMPRESA, otra, LAS_15)
        with self.assertRaises(ValueError):
            servicio2.firma_de_registro(EMPRESA, otra, rol="recepcion")


if __name__ == "__main__":
    unittest.main()
