import unittest
from datetime import date, datetime

from hotel_inventario.dominio import EstadoUnidad, Huesped
from hotel_inventario.servicio import AccesoDenegado, hotel_sintetico

OTRA = "EMP-OTRA-999"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class AccesoOtraEmpresaTest(unittest.TestCase):
    def test_otra_empresa_no_consulta_ni_reserva(self):
        servicio = hotel_sintetico()
        with self.assertRaises(AccesoDenegado):
            servicio.consultar_disponibilidad(OTRA, INICIO, FIN, 1)
        with self.assertRaises(AccesoDenegado):
            servicio.reservar(OTRA, "HAB-SINT-101", INICIO, FIN, HUESPED)

    def test_otra_empresa_no_ve_ni_cambia_cuentas_ni_reservas(self):
        servicio = hotel_sintetico()
        reserva = servicio.reservar(servicio.empresa.id, "HAB-SINT-101", INICIO, FIN, HUESPED).reserva
        with self.assertRaises(AccesoDenegado):
            servicio.cuenta(OTRA, reserva.id)
        with self.assertRaises(AccesoDenegado):
            servicio.saldo_clp(OTRA, reserva.id)
        with self.assertRaises(AccesoDenegado):
            servicio.cancelar(OTRA, reserva.id, datetime(2026, 11, 9, 12, 0))
        with self.assertRaises(AccesoDenegado):
            servicio.asentar_cargo(OTRA, reserva.id, "Cargo ajeno", 1_000)
        with self.assertRaises(AccesoDenegado):
            servicio.reversar_cargo(OTRA, "CGO-SINT-0001")
        with self.assertRaises(AccesoDenegado):
            servicio.cambiar_estado_unidad(OTRA, "HAB-SINT-101", EstadoUnidad.BLOQUEADA)


if __name__ == "__main__":
    unittest.main()
