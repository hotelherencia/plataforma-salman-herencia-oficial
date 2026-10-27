from datetime import date, datetime, timedelta
import unittest

from hotel_inventario.dominio import EstadoReserva, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import (
    AccesoDenegado,
    hotel_con_extras,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
LAS_15 = datetime(2026, 11, 10, 15, 0)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


class AT011Test(unittest.TestCase):
    def test_AT_011_accion_fuera_de_politica_se_deniega(self):
        servicio = servicio_con_una_unidad()
        with self.assertRaises(AccesoDenegado):
            servicio.ejecutar_sin_aprobacion(EMPRESA, 1_000, LAS_15)
        self.assertEqual(
            servicio.ejecutar_sin_aprobacion(EMPRESA, 0, LAS_15), "ejecutada dentro de política"
        )

    def test_AT_011_modificar_parametros_invalida_la_aprobacion(self):
        servicio = servicio_con_una_unidad()
        aprobacion = servicio.autorizar_accion(
            EMPRESA,
            descripcion="cambio de habitación",
            parametros={"monto": 5_000, "unidad": "HAB-SINT-103"},
            monto_clp=5_000,
            ahora=LAS_15,
            vigencia_minutos=60,
        )
        self.assertEqual(
            servicio.ejecutar_accion_aprobada(
                EMPRESA, aprobacion.id, {"monto": 5_000, "unidad": "HAB-SINT-103"}, LAS_15
            ),
            "ejecutada bajo aprobación",
        )
        with self.assertRaises(AccesoDenegado):
            servicio.ejecutar_accion_aprobada(
                EMPRESA, aprobacion.id, {"monto": 5_000, "unidad": "HAB-SINT-103"}, LAS_15
            )
        otra = servicio.autorizar_accion(
            EMPRESA, "x", {"monto": 5_000}, 5_000, LAS_15, 60
        )
        with self.assertRaises(AccesoDenegado):
            servicio.ejecutar_accion_aprobada(EMPRESA, otra.id, {"monto": 6_000}, LAS_15)
        tercera = servicio.autorizar_accion(
            EMPRESA, "y", {"monto": 1}, 1, LAS_15, 60
        )
        with self.assertRaises(AccesoDenegado):
            servicio.ejecutar_accion_aprobada(
                EMPRESA, tercera.id, {"monto": 1}, LAS_15 + timedelta(minutes=61)
            )
        cuarta = servicio.autorizar_accion(EMPRESA, "z", {"monto": 2}, 2, LAS_15, 60)
        servicio.ejecutar_accion_aprobada(EMPRESA, cuarta.id, {"monto": 2}, LAS_15)
        with self.assertRaises(AccesoDenegado):
            servicio.ejecutar_accion_aprobada(EMPRESA, cuarta.id, {"monto": 2}, LAS_15)


class AT012Test(unittest.TestCase):
    def test_AT_012_upsell_propone_link_y_solo_pago_confirmado_convierte(self):
        servicio = hotel_con_extras()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        servicio.check_in(EMPRESA, reserva_id, LAS_15)

        upsell = servicio.ofrecer_upsell(EMPRESA, reserva_id, "EXT-BOTELLA", LAS_15)
        self.assertEqual(upsell.monto_clp, 15_000)
        self.assertIn("https://pago.sintetico.local/upsell/", upsell.link)

        self.assertEqual(servicio.contabilizar_conversion(EMPRESA, upsell.id), 0)
        servicio.registrar_pago(EMPRESA, reserva_id, 15_000, clave=f"upsell:{upsell.id}")
        self.assertEqual(servicio.contabilizar_conversion(EMPRESA, upsell.id), 1)


class AT017Test(unittest.TestCase):
    def test_AT_017_oferta_sin_vigencia_queda_pendiente_sin_cupo_y_transfiere(self):
        servicio = servicio_con_una_unidad()
        emitida = datetime(2026, 11, 1, 10, 0)
        ofertas = servicio.consultar_oferta(EMPRESA, INICIO, FIN, 2, emitida)
        oferta = ofertas[0]
        tarde = oferta.vigente_hasta + timedelta(minutes=1)

        resultado = servicio.confirmar_con_oferta(EMPRESA, oferta, HUESPED, tarde)
        self.assertFalse(resultado.confirmada)
        self.assertIs(resultado.reserva.estado, EstadoReserva.PENDIENTE)
        self.assertIn(UNIDAD, {u.id for u in servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2)})

        transferencias = servicio.transferencias(EMPRESA)
        self.assertEqual(len(transferencias), 1)
        self.assertEqual(transferencias[0].reserva_id, resultado.reserva.id)
        self.assertEqual(transferencias[0].receptor, "recepcion")
        self.assertFalse(transferencias[0].resuelto)

    def test_AT_017_oferta_vigente_confirma_normal(self):
        servicio = servicio_con_una_unidad()
        emitida = datetime(2026, 11, 1, 10, 0)
        oferta = servicio.consultar_oferta(EMPRESA, INICIO, FIN, 2, emitida)[0]
        resultado = servicio.confirmar_con_oferta(EMPRESA, oferta, HUESPED, emitida)
        self.assertTrue(resultado.confirmada, resultado.motivo)


if __name__ == "__main__":
    unittest.main()
