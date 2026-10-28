from datetime import date, datetime
import unittest

from hotel_inventario.dominio import Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import AccesoDenegado, servicio_con_una_unidad

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
TARIFA_BASE = 50_000
TARIFA_NUEVA = 70_000
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")
LAS_15 = datetime(2026, 11, 10, 15, 0)


class ConfiguracionTarifasHU_HOT_01Test(unittest.TestCase):
    """HU-HOT-01 (propuesta, sin ratificar): tarifas por unidad y fecha, solo administrador, precio fijado al reservar."""

    def test_administrador_configura_tarifa_y_el_motor_la_consulta(self):
        servicio = servicio_con_una_unidad()
        servicio.configurar_tarifa(EMPRESA, "administrador", UNIDAD, INICIO, "estandar", TARIFA_NUEVA)

        oferta = servicio.consultar_oferta(EMPRESA, INICIO, FIN, 2, LAS_15)

        self.assertEqual(oferta[0].tarifa_noche_clp, TARIFA_NUEVA)
        self.assertEqual(servicio.tarifa_vigente(EMPRESA, UNIDAD, INICIO), TARIFA_NUEVA)
        otra_fecha = servicio.consultar_oferta(EMPRESA, date(2026, 12, 1), date(2026, 12, 3), 2, LAS_15)
        self.assertEqual(otra_fecha[0].tarifa_noche_clp, TARIFA_BASE)

    def test_rol_sin_permiso_es_denegado_y_queda_auditado(self):
        servicio = servicio_con_una_unidad()

        with self.assertRaises(AccesoDenegado):
            servicio.configurar_tarifa(EMPRESA, "recepcion", UNIDAD, INICIO, "estandar", TARIFA_NUEVA)

        self.assertIn(("configuracion", UNIDAD, "rol no autorizado"), servicio.evidencia_denegaciones(EMPRESA))
        self.assertEqual(servicio.tarifa_vigente(EMPRESA, UNIDAD, INICIO), TARIFA_BASE)

    def test_tarifa_superpuesta_para_la_misma_unidad_y_fecha_se_rechaza(self):
        servicio = servicio_con_una_unidad()
        servicio.configurar_tarifa(EMPRESA, "administrador", UNIDAD, INICIO, "estandar", TARIFA_NUEVA)

        with self.assertRaises(ValueError) as caso:
            servicio.configurar_tarifa(EMPRESA, "administrador", UNIDAD, INICIO, "estandar", 80_000)

        self.assertIn("superpuesta", str(caso.exception))
        self.assertEqual(servicio.tarifa_vigente(EMPRESA, UNIDAD, INICIO), TARIFA_NUEVA)

    def test_reserva_existente_conserva_el_precio_aceptado(self):
        servicio = servicio_con_una_unidad()
        reserva = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva

        servicio.configurar_tarifa(EMPRESA, "administrador", UNIDAD, INICIO, "estandar", TARIFA_NUEVA)

        self.assertEqual(servicio._tarifa_de_reserva(reserva.id), TARIFA_BASE)

    def test_empresa_ajena_no_configura_ni_consulta(self):
        servicio = servicio_con_una_unidad()
        with self.assertRaises(AccesoDenegado):
            servicio.configurar_tarifa("EMP-OTRA", "administrador", UNIDAD, INICIO, "estandar", TARIFA_NUEVA)
        with self.assertRaises(AccesoDenegado):
            servicio.tarifa_vigente("EMP-OTRA", UNIDAD, INICIO)


if __name__ == "__main__":
    unittest.main()
