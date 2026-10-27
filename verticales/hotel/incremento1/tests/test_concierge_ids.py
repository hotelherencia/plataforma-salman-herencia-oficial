from datetime import date, datetime
import unittest

from hotel_inventario.concierge import ConciergeLocal
from hotel_inventario.dominio import EstadoReserva, EstadoTarea, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import (
    AccesoDenegado,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
LAS_15 = datetime(2026, 11, 10, 15, 0)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class ConciergeIdsTest(unittest.TestCase):
    def test_AC_US_HOT_003_01_solicitud_de_cancelacion_deriva_y_no_cancela_ni_resuelve(self):
        servicio = servicio_con_una_unidad()
        concierge = ConciergeLocal(servicio)
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id

        respuesta = concierge.atender(EMPRESA, "conv-1", "quiero cancelar mi reserva")
        self.assertTrue(respuesta.escalado)
        self.assertIsNotNone(respuesta.transferencia_id)
        transferencia = servicio.transferencias(EMPRESA)[0]
        self.assertEqual(transferencia.reserva_id, "conv-1")
        self.assertFalse(transferencia.resuelto)
        self.assertIs(
            next(r for r in servicio.reservas_confirmadas(EMPRESA) if r.id == reserva_id).estado,
            EstadoReserva.CONFIRMADA,
        )

    def test_AC_US_HOT_003_02_en_atencion_humana_no_hay_accion_autonoma_ni_segunda_respuesta(self):
        servicio = servicio_con_una_unidad()
        concierge = ConciergeLocal(servicio)
        primera = concierge.atender(EMPRESA, "conv-2", "cancelar por favor")
        self.assertTrue(primera.escalado)
        segunda = concierge.atender(EMPRESA, "conv-2", "¿ya cancelaron?")
        self.assertEqual(segunda.accion, "ninguna")
        self.assertEqual(len(servicio.transferencias(EMPRESA)), 1)

    def test_AC_US_HOT_003_03_cancelar_y_devolver_prepara_contexto_y_escala_sin_ejecutar(self):
        servicio = servicio_con_una_unidad()
        concierge = ConciergeLocal(servicio)
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.check_in(EMPRESA, reserva_id, LAS_15)

        respuesta = concierge.atender(EMPRESA, "conv-3", "cancelar y devolver el dinero")
        self.assertTrue(respuesta.escalado)
        reserva = servicio.datos_reserva(EMPRESA, reserva_id, solicitante=f"huesped:{reserva_id}")
        self.assertIs(reserva.estado, EstadoReserva.HOSPEDADA)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 50_000)
        self.assertEqual(servicio.devoluciones(EMPRESA, reserva_id), ())

    def test_AC_US_HOT_003_04_la_misma_modificacion_tres_veces_emite_una_sola_notificacion(self):
        servicio = servicio_con_una_unidad()
        concierge = ConciergeLocal(servicio)
        link = "https://pago.sintetico.local/hecho/abc"
        primera = concierge.notificar_hecho(EMPRESA, "hecho-1", link)
        self.assertEqual(primera.link, link)
        for _ in range(2):
            repetida = concierge.notificar_hecho(EMPRESA, "hecho-1", link)
            self.assertIsNone(repetida.link)
            self.assertEqual(repetida.accion, "ninguna")

    def test_AC_US_HOT_003_05_respuesta_con_link_no_figura_como_reserva_pagada(self):
        servicio = servicio_con_una_unidad()
        concierge = ConciergeLocal(servicio)
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id

        concierge.notificar_hecho(EMPRESA, "hecho-2", f"https://pago.sintetico.local/reserva/{reserva_id}")
        self.assertNotIn(reserva_id, servicio.reservas_pagadas(EMPRESA))
        servicio.registrar_pago(EMPRESA, reserva_id, 50_000, clave="pag-1")
        self.assertIn(reserva_id, servicio.reservas_pagadas(EMPRESA))

    def test_concierge_respeta_la_empresa_fija(self):
        servicio = servicio_con_una_unidad()
        concierge = ConciergeLocal(servicio)
        with self.assertRaises(AccesoDenegado):
            concierge.atender("EMP-OTRA", "conv-9", "cancelar")


class FR008TareasMantenimientoTest(unittest.TestCase):
    def test_AT_008_abrir_mantenimiento_genera_tarea_que_el_cierre_completa(self):
        servicio = servicio_con_una_unidad()
        servicio.abrir_mantenimiento(EMPRESA, UNIDAD)
        tareas = [t for t in servicio.tareas(EMPRESA) if t.tipo == "mantenimiento"]
        self.assertEqual(len(tareas), 1)
        self.assertIs(tareas[0].estado, EstadoTarea.PENDIENTE)

        servicio.cerrar_mantenimiento(EMPRESA, UNIDAD)
        cerradas = [t for t in servicio.tareas(EMPRESA) if t.tipo == "mantenimiento"]
        self.assertIs(cerradas[0].estado, EstadoTarea.COMPLETADA)
        self.assertIn(UNIDAD, {u.id for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)})


if __name__ == "__main__":
    unittest.main()
