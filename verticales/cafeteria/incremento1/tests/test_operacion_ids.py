from datetime import datetime, timedelta
import unittest

from cafeteria_mesas_pos.dominio import (
    EstadoGasto,
    EstadoPropuesta,
    Insumo,
    Producto,
)
from cafeteria_mesas_pos.empresa import EMPRESA_FIJA
from cafeteria_mesas_pos.servicio import (
    AccesoDenegado,
    cafeteria_sintetica,
)

EMPRESA = EMPRESA_FIJA.id
AHORA = datetime(2026, 11, 10, 12, 0, 0)


class OperacionIdsTest(unittest.TestCase):
    def test_AT_007_gasto_con_lineas_erroneas_es_borrador_y_solo_el_aprobador_valida(self):
        servicio = cafeteria_sintetica()
        borrador = servicio.registrar_gasto_borrador(
            EMPRESA, proveedor="Proveedor Sintético", monto_clp=25_000, fecha="2026-11-09", lineas_erroneas=2
        )
        self.assertIs(borrador.estado, EstadoGasto.PENDIENTE)
        self.assertEqual(borrador.lineas_erroneas, 2)

        with self.assertRaises(AccesoDenegado):
            servicio.aprobar_gasto(EMPRESA, borrador.id, rol="cocina", correcciones=())
        aprobado = servicio.aprobar_gasto(
            EMPRESA, borrador.id, rol="administrador", correcciones=("línea 2: monto corregido de OCR",)
        )
        self.assertIs(aprobado.estado, EstadoGasto.APROBADO)
        self.assertEqual(aprobado.correcciones, ("línea 2: monto corregido de OCR",))

    def test_AT_008_la_venta_con_receta_mueve_cada_insumo_una_sola_vez(self):
        servicio = cafeteria_sintetica()
        movimientos = servicio.vender(EMPRESA, "PROD-CAFE", 2, "venta-1")
        self.assertEqual(len(movimientos), 2)
        self.assertEqual([m.insumo_id for m in movimientos], ["INS-CAFE", "INS-LECHE"])
        self.assertEqual([m.cantidad for m in movimientos], [2.0, 1.0])

        repetida = servicio.vender(EMPRESA, "PROD-CAFE", 2, "venta-1")
        self.assertEqual(len(repetida), 2)
        self.assertEqual(len(servicio._movimientos), 2)

    def test_AT_008_sin_receta_el_costo_queda_desconocido(self):
        servicio = cafeteria_sintetica()
        estado, margen = servicio.margen_producto(EMPRESA, "PROD-SIN-RECETA")
        self.assertEqual(estado, "no_calculable")
        self.assertIsNone(margen)

    def test_AT_009_el_margen_se_calcula_con_costos_conocidos(self):
        servicio = cafeteria_sintetica()
        estado, margen = servicio.margen_producto(EMPRESA, "PROD-CAFE")
        self.assertEqual(estado, "calculable")
        self.assertAlmostEqual(margen, (2_500 - 1_000) / 2_500)

    def test_AC_US_CAF_002_01_receta_con_insumo_sin_costo_es_no_calculable(self):
        servicio = cafeteria_sintetica()
        servicio.cargar_carta(
            EMPRESA,
            productos=(
                Producto(
                    id="PROD-MIXTO",
                    nombre="Mixto",
                    precio_clp=3_000,
                    receta=(("INS-CAFE", 1.0), ("INS-SIN-COSTO", 1.0)),
                ),
            ),
            insumos=(
                Insumo("INS-CAFE", "Café molido", 10.0, 800.0, 2.0),
                Insumo("INS-SIN-COSTO", "Insumo sin costo", 3.0, None, 1.0),
            ),
        )
        estado, margen = servicio.margen_producto(EMPRESA, "PROD-MIXTO")
        self.assertEqual(estado, "no_calculable")
        self.assertIsNone(margen)

    def test_AT_011_propuesta_de_compra_sin_aprobacion_no_se_envia_y_expira(self):
        servicio = cafeteria_sintetica()
        for i in range(9):
            servicio.vender(EMPRESA, "PROD-CAFE", 1, f"venta-{i}")
        propuestas = servicio.generar_propuestas_compra(EMPRESA, AHORA)
        self.assertEqual(len(propuestas), 2)
        propuesta = next(p for p in propuestas if p.insumo_id == "INS-CAFE")
        self.assertEqual(propuesta.expira_en, AHORA + timedelta(hours=48))

        with self.assertRaises(AccesoDenegado):
            servicio.usar_propuesta(EMPRESA, propuesta.id, AHORA, rol="cocina")
        ejecutada = servicio.usar_propuesta(EMPRESA, propuesta.id, AHORA, rol="administrador")
        self.assertIs(ejecutada.estado, EstadoPropuesta.EJECUTADA)

    def test_AC_US_CAF_003_02_propuesta_vencida_se_bloquea_y_exige_revision(self):
        servicio = cafeteria_sintetica()
        for i in range(9):
            servicio.vender(EMPRESA, "PROD-CAFE", 1, f"venta-{i}")
        propuesta = next(
            p for p in servicio.generar_propuestas_compra(EMPRESA, AHORA) if p.insumo_id == "INS-CAFE"
        )
        tarde = propuesta.expira_en + timedelta(minutes=1)
        with self.assertRaises(ValueError):
            servicio.usar_propuesta(EMPRESA, propuesta.id, tarde, rol="administrador")
        self.assertIs(servicio._propuestas[propuesta.id].estado, EstadoPropuesta.EXPIRADA)

    def test_AT_012_anulacion_sobre_umbral_emite_una_alerta_registrada(self):
        servicio = cafeteria_sintetica()
        alerta = servicio.alerta_anulacion(EMPRESA, "anul-grande", 80_000, umbral_clp=50_000, ahora=AHORA)
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta.umbral_clp, 50_000)
        entradas = [e for e in servicio.ledger(EMPRESA) if e.fuente == "anulacion"]
        self.assertEqual(len(entradas), 1)
        self.assertIn("sin sanción automática", entradas[0].regla)


if __name__ == "__main__":
    unittest.main()
