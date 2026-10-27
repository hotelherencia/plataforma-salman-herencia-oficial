from datetime import date, datetime
import unittest

from hotel_inventario.dominio import EstadoReserva, EstadoTarea, EstadoUnidad, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import (
    CheckInNoPermitido,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
LAS_15 = datetime(2026, 11, 10, 15, 0)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class MantenimientoYLimpiezaTest(unittest.TestCase):
    def flujo_ocupada_salida(self, servicio):
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        servicio.check_out(EMPRESA, reserva_id, datetime(2026, 11, 12, 11, 0))
        return reserva_id

    def test_AT_008_mantenimiento_abierto_impide_asignacion_aunque_termine_limpieza(self):
        servicio = servicio_con_una_unidad()
        self.flujo_ocupada_salida(servicio)
        tarea = servicio.tareas(EMPRESA)[0]
        servicio.abrir_mantenimiento(EMPRESA, UNIDAD)
        completada = servicio.completar_tarea(EMPRESA, tarea.id)
        self.assertIs(completada.estado, EstadoTarea.COMPLETADA)
        self.assertNotIn(UNIDAD, {u.id for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)})

    def test_AT_008_el_cierre_autorizado_habilita_el_estado_operativo(self):
        servicio = servicio_con_una_unidad()
        self.flujo_ocupada_salida(servicio)
        tarea = servicio.tareas(EMPRESA)[0]
        servicio.abrir_mantenimiento(EMPRESA, UNIDAD)
        servicio.completar_tarea(EMPRESA, tarea.id)
        cerrada = servicio.cerrar_mantenimiento(EMPRESA, UNIDAD)
        self.assertFalse(cerrada.mantenimiento)
        self.assertIn(UNIDAD, {u.id for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)})

    def test_AC_US_HOT_002_01_limpia_con_mantenimiento_abierto_bloquea_el_check_in(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.abrir_mantenimiento(EMPRESA, UNIDAD)
        with self.assertRaises(CheckInNoPermitido):
            servicio.check_in(EMPRESA, reserva_id, LAS_15)
        self.assertIn(
            ("check_in", reserva_id, "mantenimiento abierto"),
            servicio.evidencia_denegaciones(EMPRESA),
        )
        self.assertIs(
            next(r for r in servicio.reservas_confirmadas(EMPRESA) if r.id == reserva_id).estado,
            EstadoReserva.CONFIRMADA,
        )

    def test_AC_US_HOT_002_02_al_terminar_limpieza_solo_cambia_la_preparacion(self):
        servicio = servicio_con_una_unidad()
        self.flujo_ocupada_salida(servicio)
        futura_id = servicio.reservar(EMPRESA, UNIDAD, date(2026, 12, 1), date(2026, 12, 3), HUESPED).reserva.id
        futura_antes = next(r for r in servicio.reservas_confirmadas(EMPRESA) if r.id == futura_id)

        tarea = servicio.tareas(EMPRESA)[0]
        servicio.completar_tarea(EMPRESA, tarea.id)
        unidad = [u for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)][0]
        self.assertIs(unidad.estado, EstadoUnidad.LIMPIA)

        futura_despues = next(r for r in servicio.reservas_confirmadas(EMPRESA) if r.id == futura_id)
        self.assertEqual(futura_antes, futura_despues)


if __name__ == "__main__":
    unittest.main()
