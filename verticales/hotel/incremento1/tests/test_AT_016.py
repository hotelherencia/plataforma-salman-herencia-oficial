from datetime import date, datetime
import unittest

from hotel_inventario.dominio import EstadoReserva, EstadoUnidad, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import (
    AccesoDenegado,
    CheckInNoPermitido,
    servicio_con_una_unidad,
    hotel_sintetico,
)

EMPRESA = EMPRESA_FIJA.id
OTRA = "EMP-OTRA-999"
UNIDAD = "HAB-SINT-101"
UNIDAD_SUCIA = "HAB-SINT-102"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
FUTURO_INICIO = date(2026, 12, 1)
FUTURO_FIN = date(2026, 12, 3)
LAS_15 = datetime(2026, 11, 10, 15, 0)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class AT016Test(unittest.TestCase):
    def test_AT_016_sucia_no_quita_inventario_futuro_y_mantenimiento_bloquea_aunque_este_limpia(self):
        # Dada habitación sucia hoy y reserva de fecha futura: el inventario futuro no
        # desaparece solo por suciedad actual.
        servicio = hotel_sintetico()
        disponibles = {u.id for u in servicio.consultar_disponibilidad(EMPRESA, FUTURO_INICIO, FUTURO_FIN, 2)}
        self.assertIn(UNIDAD_SUCIA, disponibles)
        futura = servicio.reservar(EMPRESA, UNIDAD_SUCIA, FUTURO_INICIO, FUTURO_FIN, HUESPED)
        self.assertTrue(futura.confirmada, futura.motivo)

        # Dada reserva de hoy en una habitación limpia con mantenimiento abierto: el check-in
        # presente se deniega aunque la habitación esté limpia, y la unidad sale del cupo.
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.abrir_mantenimiento(EMPRESA, UNIDAD)
        self.assertNotIn(UNIDAD, {u.id for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)})
        with self.assertRaises(CheckInNoPermitido):
            servicio.check_in(EMPRESA, reserva_id, LAS_15)
        self.assertIs(
            next(r for r in servicio.reservas_confirmadas(EMPRESA) if r.id == reserva_id).estado,
            EstadoReserva.CONFIRMADA,
        )

        # Recurso de otro tenant: se deniega y queda evidencia.
        with self.assertRaises(AccesoDenegado):
            servicio.check_in(OTRA, reserva_id, LAS_15)

        # Conservar evidencia: ambas denegaciones quedan registradas para la empresa dueña.
        evidencia = servicio.evidencia_denegaciones(EMPRESA)
        self.assertIn(("check_in", reserva_id, "mantenimiento abierto"), evidencia)
        self.assertIn(("check_in", reserva_id, "empresa desconocida"), evidencia)
        with self.assertRaises(AccesoDenegado):
            servicio.evidencia_denegaciones(OTRA)

        # Al cerrar el mantenimiento, la misma reserva entra.
        servicio.cerrar_mantenimiento(EMPRESA, UNIDAD)
        hospedada = servicio.check_in(EMPRESA, reserva_id, LAS_15)
        self.assertIs(hospedada.estado, EstadoReserva.HOSPEDADA)


if __name__ == "__main__":
    unittest.main()
