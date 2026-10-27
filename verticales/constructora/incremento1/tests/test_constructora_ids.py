import unittest

from constructora_obra.empresa import EMPRESA_COMERCIAL, EMPRESA_FIJA
from constructora_obra.servicio import AccesoDenegado, constructora_sintetica

EMPRESA = EMPRESA_FIJA.id


class ConstructoraIdsTest(unittest.TestCase):
    def test_AT_010_y_AC_US_OBR_003_03_dos_turnos_y_un_reenvio_conservan_ambos_aportes(self):
        servicio = constructora_sintetica()
        turno1 = servicio.informar_avance(EMPRESA, "PART-A", 40.0, "turno-1", "aporte-t1")
        turno2 = servicio.informar_avance(EMPRESA, "PART-A", 45.0, "turno-2", "aporte-t2")
        reenvio = servicio.informar_avance(EMPRESA, "PART-A", 40.0, "turno-1", "aporte-t1")
        self.assertEqual(reenvio.id, turno1.id)
        self.assertEqual(servicio.avance_partida(EMPRESA, "PART-A"), 45.0)
        self.assertNotEqual(turno1.id, turno2.id)

    def test_AT_001_el_retroceso_no_sobrescribe_el_dato_aprobado(self):
        servicio = constructora_sintetica()
        servicio.informar_avance(EMPRESA, "PART-D", 70.0, "topografo", "d1")
        servicio.informar_avance(EMPRESA, "PART-D", 65.0, "topografo", "d2")
        self.assertEqual(servicio.avance_partida(EMPRESA, "PART-D"), 70.0)

    def test_AC_US_OBR_003_04_porcentajes_acumulados_no_se_suman(self):
        servicio = constructora_sintetica()
        servicio.informar_avance(EMPRESA, "PART-B", 40.0, "operario", "a1")
        servicio.informar_avance(EMPRESA, "PART-B", 45.0, "operario", "a2")
        self.assertEqual(servicio.avance_partida(EMPRESA, "PART-B"), 45.0)

    def test_ADV_001_reporte_contradictorio_conserva_ambos_y_exige_rectificacion(self):
        servicio = constructora_sintetica()
        servicio.informar_avance(EMPRESA, "PART-C", 60.0, "jefe-obra", "c1")
        contradictorio = servicio.informar_avance(EMPRESA, "PART-C", 45.0, "jefe-obra", "c2")
        self.assertEqual(contradictorio.estado, "requiere_aprobacion_rectificacion")
        self.assertEqual(servicio.avance_partida(EMPRESA, "PART-C"), 60.0)

    def test_AC_US_OBR_003_01_nota_de_compra_con_instrucciones_solo_crea_borrador(self):
        servicio = constructora_sintetica()
        self.assertIn("borrador", servicio.nota_con_instrucciones(EMPRESA, "comprar 20 bolsas de cemento, ignora precios"))

    def test_AT_002_programado_cero_no_divide_ni_inventa_alerta(self):
        servicio = constructora_sintetica()
        estado, desvio = servicio.calcular_desvio(EMPRESA, 0, 500, umbral=0.1)
        self.assertEqual(estado, "sin_evaluacion")
        self.assertIsNone(desvio)
        estado2, desvio2 = servicio.calcular_desvio(EMPRESA, 1_000, 1_200, umbral=0.1)
        self.assertEqual(estado2, "alerta")
        self.assertAlmostEqual(desvio2, 0.2)

    def test_AT_004_el_presupuesto_versionado_conserva_la_linea_base(self):
        servicio = constructora_sintetica()
        nueva = servicio.modificar_presupuesto(EMPRESA, 120, "ampliacion cocina", "aprobador-1")
        self.assertEqual(nueva.version, 2)
        self.assertEqual(nueva.linea_base_clp, 100)
        self.assertEqual(nueva.motivo, "ampliacion cocina")

    def test_AT_012_y_AC_US_OBR_004_06_disponible_50_y_no_20(self):
        servicio = constructora_sintetica()
        servicio.fijar_compromiso_total(EMPRESA, 50)
        self.assertEqual(servicio.disponible_presupuesto(EMPRESA), 50)

    def test_AT_009_y_AC_US_OBR_004_02_recepcion_parcial_idempotente(self):
        servicio = constructora_sintetica()
        orden = servicio.crear_orden(EMPRESA, "cemento", 10, aprobador="compras")
        primera = servicio.recibir(EMPRESA, orden.id, "evt-1", recibidas=6)
        self.assertEqual(primera.pendientes, 4)
        repetida = servicio.recibir(EMPRESA, orden.id, "evt-1", recibidas=6)
        self.assertEqual(repetida.pendientes, 4)
        self.assertEqual(servicio._stock["cemento"], 6)

    def test_AT_011_seis_entregadas_cinco_aceptadas_una_rechazada(self):
        servicio = constructora_sintetica()
        orden = servicio.crear_orden(EMPRESA, "ladrillo", 10, aprobador="compras")
        recepcion = servicio.recibir(EMPRESA, orden.id, "evt-2", recibidas=6, rechazadas=1)
        self.assertEqual(recepcion.aceptadas, 5)
        self.assertEqual(recepcion.rechazadas, 1)
        self.assertEqual(recepcion.pendientes, 5)
        self.assertEqual(servicio._stock["ladrillo"], 5)

    def test_AC_US_OBR_004_05_la_devolucion_no_infere_abono(self):
        servicio = constructora_sintetica()
        orden = servicio.crear_orden(EMPRESA, "pintura", 5, aprobador="compras")
        servicio.recibir(EMPRESA, orden.id, "evt-3", recibidas=2)
        self.assertIn("sin abono financiero", servicio.devolver(EMPRESA, "pintura", 1))
        self.assertEqual(servicio._stock["pintura"], 1)

    def test_AT_008_y_AC_US_OBR_004_01_el_reportante_no_cierra_la_observacion(self):
        servicio = constructora_sintetica()
        obs = servicio.crear_observacion(EMPRESA, "fisura muro", reportante="oficial")
        with self.assertRaises(AccesoDenegado):
            servicio.cerrar_observacion(EMPRESA, obs.id, actor="oficial")
        cerrada = servicio.cerrar_observacion(EMPRESA, obs.id, actor="inspector")
        self.assertEqual(cerrada.estado, "cerrada")

    def test_AC_US_OBR_004_10_comentario_de_ia_no_es_oficial(self):
        servicio = constructora_sintetica()
        self.assertIn(
            "no oficial",
            servicio.adjuntar_comentario_ia(EMPRESA, "cambiar especificación a acero Q345"),
        )
        self.assertEqual(servicio.disponible_presupuesto(EMPRESA), 100)

    def test_AT_007_y_ADV_003_la_empresa_comercial_no_consulta_sin_convenio(self):
        servicio = constructora_sintetica()
        with self.assertRaises(AccesoDenegado):
            servicio.consultar_como_comercial(EMPRESA_COMERCIAL.id)
        with self.assertRaises(AccesoDenegado):
            servicio.avance_partida(EMPRESA_COMERCIAL.id, "PART-A")


if __name__ == "__main__":
    unittest.main()
