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
FIN = date(2026, 11, 13)
LAS_15 = datetime(2026, 11, 10, 15, 0)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class AC00104Test(unittest.TestCase):
    def test_AC_US_HOT_001_04_previsualiza_diferencia_y_no_aplica_sin_aceptacion(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id

        propuesta = servicio.previsualizar_cambio(EMPRESA, reserva_id, 60_000)
        self.assertEqual(propuesta.tarifa_actual_clp, 50_000)
        self.assertEqual(propuesta.tarifa_nueva_clp, 60_000)
        self.assertEqual(propuesta.noches, 3)
        self.assertEqual(propuesta.diferencia_total_clp, 30_000)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 0)

        with self.assertRaises(ValueError):
            servicio.aplicar_cambio(EMPRESA, reserva_id, propuesta, aceptacion=False)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 0)

        servicio.aplicar_cambio(EMPRESA, reserva_id, propuesta, aceptacion=True)
        ajustes = [c for c in servicio.cuenta(EMPRESA, reserva_id) if c.concepto == "Ajuste de tarifa"]
        self.assertEqual(len(ajustes), 1)
        self.assertEqual(ajustes[0].monto_clp, 30_000)
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 30_000)

        otra = servicio.previsualizar_cambio(EMPRESA, reserva_id, 60_000)
        self.assertEqual(otra.diferencia_total_clp, 0)
        with self.assertRaises(ValueError):
            servicio.aplicar_cambio(EMPRESA, reserva_id, otra, aceptacion=True)

    def test_AC_US_HOT_001_04_nuevas_noches_usan_la_tarifa_aceptada(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.check_in(EMPRESA, reserva_id, LAS_15)
        propuesta = servicio.previsualizar_cambio(EMPRESA, reserva_id, 60_000)
        servicio.aplicar_cambio(EMPRESA, reserva_id, propuesta, aceptacion=True)
        servicio.asentar_noche(EMPRESA, reserva_id, date(2026, 11, 11), datetime(2026, 11, 11, 9, 0))
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva_id), 30_000 + 50_000 + 60_000)

    def test_AC_US_HOT_001_04_denegaciones_propuesta_obsoleta_y_reintento_idempotente(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        otra_id = servicio.reservar(EMPRESA, UNIDAD, date(2026, 12, 5), date(2026, 12, 8), HUESPED).reserva.id

        with self.assertRaises(AccesoDenegado):
            servicio.previsualizar_cambio("EMP-OTRA", reserva_id, 60_000)
        propuesta = servicio.previsualizar_cambio(EMPRESA, reserva_id, 60_000)
        with self.assertRaises(ValueError):
            servicio.aplicar_cambio(EMPRESA, otra_id, propuesta, aceptacion=True)

        vieja = servicio.previsualizar_cambio(EMPRESA, reserva_id, 70_000)
        servicio.aplicar_cambio(EMPRESA, reserva_id, propuesta, aceptacion=True)
        reintento = servicio.aplicar_cambio(EMPRESA, reserva_id, propuesta, aceptacion=True)
        self.assertEqual(reintento, propuesta)
        self.assertEqual(
            len([c for c in servicio.cuenta(EMPRESA, reserva_id) if c.concepto == "Ajuste de tarifa"]),
            1,
        )
        with self.assertRaises(ValueError):
            servicio.aplicar_cambio(EMPRESA, reserva_id, vieja, aceptacion=True)

        servicio.cancelar(EMPRESA, otra_id, datetime(2026, 11, 5, 12, 0))
        with self.assertRaises(ValueError):
            servicio.previsualizar_cambio(EMPRESA, otra_id, 60_000)


if __name__ == "__main__":
    unittest.main()
