from datetime import date, datetime
import unittest

from hotel_inventario.dominio import EstadoReserva, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import (
    AccesoDenegado,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class AC00103Test(unittest.TestCase):
    def reserva_pagada(self, monto=100_000):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.registrar_pago(EMPRESA, reserva_id, monto, clave="pag-total")
        return servicio, reserva_id

    def test_AC_US_HOT_001_03_el_dinero_permanece_sin_devolver_hasta_operacion_confirmada(self):
        servicio, reserva_id = self.reserva_pagada()
        cancelada = servicio.cancelar(EMPRESA, reserva_id, datetime(2026, 11, 5, 12, 0))
        self.assertIs(cancelada.reserva.estado, EstadoReserva.CANCELADA)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), -100_000)
        self.assertEqual(servicio.devoluciones(EMPRESA, reserva_id), ())

        solicitud = servicio.solicitar_devolucion(EMPRESA, reserva_id, 100_000)
        self.assertEqual(solicitud.estado.value, "pendiente")
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), -100_000)

        with self.assertRaises(ValueError):
            servicio.ejecutar_devolucion(EMPRESA, solicitud.id, operacion_confirmada=True)

        autorizada = servicio.autorizar_devolucion(EMPRESA, solicitud.id, aprobador="Ricardo Salman")
        self.assertEqual(autorizada.estado.value, "autorizada")
        self.assertEqual(autorizada.aprobador, "Ricardo Salman")
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), -100_000)

        sin_confirmar = servicio.ejecutar_devolucion(EMPRESA, solicitud.id, operacion_confirmada=False)
        self.assertEqual(sin_confirmar.estado.value, "autorizada")
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), -100_000)

        efectuada = servicio.ejecutar_devolucion(EMPRESA, solicitud.id, operacion_confirmada=True)
        self.assertEqual(efectuada.estado.value, "efectuada")
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 0)
        with self.assertRaises(ValueError):
            servicio.ejecutar_devolucion(EMPRESA, solicitud.id, operacion_confirmada=True)

    def test_AC_US_HOT_001_03_denegaciones(self):
        servicio, reserva_id = self.reserva_pagada()
        with self.assertRaises(AccesoDenegado):
            servicio.solicitar_devolucion("EMP-OTRA", reserva_id, 1_000)
        with self.assertRaises(ValueError):
            servicio.solicitar_devolucion(EMPRESA, reserva_id, 150_000)
        sin_pagos = servicio.reservar(EMPRESA, UNIDAD, date(2026, 12, 5), date(2026, 12, 6), HUESPED).reserva.id
        with self.assertRaises(ValueError):
            servicio.solicitar_devolucion(EMPRESA, sin_pagos, 10_000)


if __name__ == "__main__":
    unittest.main()
