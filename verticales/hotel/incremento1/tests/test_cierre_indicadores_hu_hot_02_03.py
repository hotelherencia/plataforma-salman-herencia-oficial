from datetime import date, datetime
import unittest

from hotel_inventario.dominio import Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import AccesoDenegado, servicio_con_una_unidad

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
TARIFA = 50_000
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")
LAS_15 = datetime(2026, 11, 10, 15, 0)


def _servicio_con_noche_asentada():
    servicio = servicio_con_una_unidad()
    reserva = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva
    servicio.check_in(EMPRESA, reserva.id, LAS_15)
    return servicio, reserva


class CierreDiarioHU_HOT_02Test(unittest.TestCase):
    """HU-HOT-02 (propuesta): el cierre relaciona cada pago con su reserva y nunca declara conciliado."""

    def test_caja_ve_los_pagos_del_dia_sin_declararlos_conciliados(self):
        servicio, reserva = _servicio_con_noche_asentada()
        servicio.registrar_pago(EMPRESA, reserva.id, 20_000, clave="cob-001", fecha=INICIO)
        servicio.registrar_pago(EMPRESA, reserva.id, 5_000, clave="cob-002")  # sin fecha

        cierre = servicio.cierre_diario(EMPRESA, "caja", INICIO)

        self.assertEqual(cierre.total_pagos_clp, 20_000)
        self.assertEqual(len(cierre.pagos), 1)
        self.assertEqual(cierre.pagos[0]["reserva_id"], reserva.id)
        self.assertFalse(cierre.pagos[0]["conciliado"])
        self.assertTrue(any("sin fecha" in p for p in cierre.pendientes))
        self.assertTrue(any("conciliación bancaria" in p for p in cierre.pendientes))

    def test_rol_sin_permiso_es_denegado_y_queda_auditado(self):
        servicio, _ = _servicio_con_noche_asentada()

        with self.assertRaises(AccesoDenegado):
            servicio.cierre_diario(EMPRESA, "recepcion", INICIO)

        self.assertIn(("cierre_diario", INICIO.isoformat(), "rol no autorizado"), servicio.evidencia_denegaciones(EMPRESA))

    def test_pago_repetido_con_la_misma_clave_aparece_una_vez(self):
        servicio, reserva = _servicio_con_noche_asentada()
        servicio.registrar_pago(EMPRESA, reserva.id, 20_000, clave="cob-001", fecha=INICIO)
        servicio.registrar_pago(EMPRESA, reserva.id, 20_000, clave="cob-001", fecha=INICIO)

        cierre = servicio.cierre_diario(EMPRESA, "caja", INICIO)

        self.assertEqual(len(cierre.pagos), 1)
        self.assertEqual(cierre.total_pagos_clp, 20_000)


class IndicadoresDiariosHU_HOT_03Test(unittest.TestCase):
    """HU-HOT-03 (propuesta): ocupación, ADR y RevPAR con fórmula, periodo y fuente declarados."""

    def test_gerencia_ve_ocupacion_adr_y_revpar_del_dia(self):
        servicio, _ = _servicio_con_noche_asentada()

        ind = servicio.indicadores_diarios(EMPRESA, "gerencia", INICIO)

        self.assertEqual(ind.noches_vendidas, 1)
        self.assertEqual(ind.ocupacion, 1.0)
        self.assertEqual(ind.adr_clp, float(TARIFA))
        self.assertEqual(ind.revpar_clp, float(TARIFA))
        self.assertEqual(ind.formula["periodo"], "2026-11-10")
        self.assertTrue(ind.ingresos_por_canal.startswith("no disponible"))

    def test_noche_revertida_no_cuenta_como_vendida(self):
        servicio, reserva = _servicio_con_noche_asentada()
        noche = next(c for c in servicio.cuenta(EMPRESA, reserva.id) if c.referencia == "noche:2026-11-10")
        servicio.reversar_cargo(EMPRESA, noche.id)

        ind = servicio.indicadores_diarios(EMPRESA, "gerencia", INICIO)

        self.assertEqual(ind.noches_vendidas, 0)
        self.assertIsNone(ind.adr_clp)
        self.assertEqual(ind.ingresos_hospedaje_clp, 0)

    def test_dia_sin_noches_declara_sin_muestra(self):
        servicio, _ = _servicio_con_noche_asentada()

        ind = servicio.indicadores_diarios(EMPRESA, "gerencia", date(2026, 12, 1))

        self.assertEqual(ind.noches_vendidas, 0)
        self.assertIsNone(ind.adr_clp)
        self.assertEqual(ind.ocupacion, 0.0)

    def test_rol_sin_permiso_es_denegado_y_queda_auditado(self):
        servicio, _ = _servicio_con_noche_asentada()

        with self.assertRaises(AccesoDenegado):
            servicio.indicadores_diarios(EMPRESA, "caja", INICIO)

        self.assertIn(("indicadores", INICIO.isoformat(), "rol no autorizado"), servicio.evidencia_denegaciones(EMPRESA))


if __name__ == "__main__":
    unittest.main()
