from datetime import date, datetime
import unittest

from hotel_inventario.dominio import EstadoReserva, EstadoTarea, EstadoUnidad, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import (
    AccesoDenegado,
    CheckInNoPermitido,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")
LAS_15 = datetime(2026, 11, 10, 15, 0)


class HousekeepingTest(unittest.TestCase):
    def setUp(self):
        self.servicio = servicio_con_una_unidad()

    def reservar(self, inicio=INICIO, fin=FIN):
        resultado = self.servicio.reservar(EMPRESA, UNIDAD, inicio, fin, HUESPED)
        assert resultado.confirmada, resultado.motivo
        return resultado.reserva.id

    def check_in_out(self, reserva_id):
        self.servicio.check_in(EMPRESA, reserva_id, LAS_15)
        return self.servicio.check_out(EMPRESA, reserva_id, datetime(2026, 11, 12, 11, 0))

    def test_check_out_crea_tarea_de_limpieza_pendiente(self):
        reserva_id = self.reservar()
        self.check_in_out(reserva_id)
        tareas = self.servicio.tareas(EMPRESA)
        self.assertEqual(len(tareas), 1)
        self.assertEqual(tareas[0].tipo, "limpieza")
        self.assertIs(tareas[0].estado, EstadoTarea.PENDIENTE)
        self.assertEqual(tareas[0].unidad_id, UNIDAD)

    def test_completar_tarea_deja_unidad_limpia_y_tarea_completada(self):
        reserva_id = self.reservar()
        self.check_in_out(reserva_id)
        tarea = self.servicio.tareas(EMPRESA)[0]
        completada = self.servicio.completar_tarea(EMPRESA, tarea.id)
        self.assertIs(completada.estado, EstadoTarea.COMPLETADA)
        unidad = [u for u in self.servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)][0]
        self.assertIs(unidad.estado, EstadoUnidad.LIMPIA)

    def test_flujo_completo_sucia_no_entra_hasta_limpiar(self):
        primera = self.reservar()
        self.check_in_out(primera)
        segunda = self.reservar()
        with self.assertRaises(CheckInNoPermitido) as ctx:
            self.servicio.check_in(EMPRESA, segunda, LAS_15)
        self.assertIn("unidad no preparada", str(ctx.exception))
        tarea = self.servicio.tareas(EMPRESA)[0]
        self.servicio.completar_tarea(EMPRESA, tarea.id)
        hospedada = self.servicio.check_in(EMPRESA, segunda, LAS_15)
        self.assertIs(hospedada.estado, EstadoReserva.HOSPEDADA)

    def test_completar_tarea_inexistente_o_dos_veces_falla(self):
        reserva_id = self.reservar()
        self.check_in_out(reserva_id)
        tarea = self.servicio.tareas(EMPRESA)[0]
        with self.assertRaises(ValueError):
            self.servicio.completar_tarea(EMPRESA, "TSK-SINT-9999")
        self.servicio.completar_tarea(EMPRESA, tarea.id)
        with self.assertRaises(ValueError):
            self.servicio.completar_tarea(EMPRESA, tarea.id)

    def test_otra_empresa_no_completa_tareas(self):
        reserva_id = self.reservar()
        self.check_in_out(reserva_id)
        tarea = self.servicio.tareas(EMPRESA)[0]
        with self.assertRaises(AccesoDenegado):
            self.servicio.completar_tarea("EMP-OTRA", tarea.id)
        with self.assertRaises(AccesoDenegado):
            self.servicio.tareas("EMP-OTRA")


if __name__ == "__main__":
    unittest.main()
