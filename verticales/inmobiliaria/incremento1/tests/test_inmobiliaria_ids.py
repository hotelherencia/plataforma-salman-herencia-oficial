from datetime import datetime, timedelta, timezone
import unittest

from inmobiliaria_comercial.empresa import EMPRESA_FIJA
from inmobiliaria_comercial.servicio import AccesoDenegado, inmobiliaria_sintetica

EMPRESA = EMPRESA_FIJA.id
AHORA = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


class InmobiliariaIdsTest(unittest.TestCase):
    def test_AT_001_dos_canales_sugieren_coincidencia_y_evitan_seguimiento_duplicado(self):
        servicio = inmobiliaria_sintetica()
        lead_a, estado_a = servicio.registrar_lead(EMPRESA, "portal", "correo@sintetico.cl")
        lead_b, estado_b = servicio.registrar_lead(EMPRESA, "whatsapp", "correo@sintetico.cl")
        self.assertEqual(lead_a.id, lead_b.id)
        self.assertIn("coincidencia", estado_b)

    def test_AC_US_INM_001_01_presupuesto_declarado_no_acredita_financiamiento(self):
        servicio = inmobiliaria_sintetica()
        lead, _ = servicio.registrar_lead(EMPRESA, "portal", "a@sintetico.cl")
        calificado = servicio.calificar(EMPRESA, lead.id, 60_000_000)
        self.assertTrue(calificado.etiqueta.startswith("declaracion:"))

    def test_AT_003_y_ADV_001_solo_una_reserva_vigente_por_unidad(self):
        servicio = inmobiliaria_sintetica()
        lead1, _ = servicio.registrar_lead(EMPRESA, "portal", "uno@sintetico.cl")
        lead2, _ = servicio.registrar_lead(EMPRESA, "portal", "dos@sintetico.cl")
        self.assertEqual(servicio.reservar_unidad(EMPRESA, "U1", lead1.id, "r1"), "reservada")
        self.assertEqual(servicio.reservar_unidad(EMPRESA, "U1", lead2.id, "r2"), "en conciliacion")

    def test_AT_004_la_cotizacion_versionada_no_cambia_al_variar_el_precio_posterior(self):
        servicio = inmobiliaria_sintetica()
        lead, _ = servicio.registrar_lead(EMPRESA, "portal", "tres@sintetico.cl")
        primera = servicio.cotizar(EMPRESA, "U1", lead.id, 80_000_000, 10_000_000, 70_000_000, AHORA)
        segunda = servicio.cotizar(EMPRESA, "U1", lead.id, 82_000_000, 10_000_000, 72_000_000, AHORA)
        self.assertEqual(primera.version, 1)
        self.assertEqual(segunda.version, 2)
        self.assertEqual(primera.precio_versionado_clp, 80_000_000)

    def test_AC_US_INM_001_03_aceptar_horario_queda_pendiente_de_autorizacion(self):
        servicio = inmobiliaria_sintetica()
        lead, _ = servicio.registrar_lead(EMPRESA, "portal", "cuatro@sintetico.cl")
        cita = servicio.proponer_cita(EMPRESA, lead.id, AHORA + timedelta(days=1), "America/Santiago")
        aceptada = servicio.aceptar_cita_interesado(EMPRESA, cita.id)
        self.assertEqual(aceptada.estado, "pendiente_autorizacion")

    def test_AC_US_INM_001_04_la_cita_exige_zona_clara(self):
        servicio = inmobiliaria_sintetica()
        lead, _ = servicio.registrar_lead(EMPRESA, "portal", "cinco@sintetico.cl")
        with self.assertRaises(ValueError):
            servicio.proponer_cita(EMPRESA, lead.id, AHORA, None)
        cita = servicio.proponer_cita(EMPRESA, lead.id, AHORA, "America/Santiago")
        self.assertEqual(cita.zona, "America/Santiago")
        self.assertEqual(cita.cuando_utc, AHORA)

    def test_AC_US_INM_001_05_reprogramar_conserva_la_referencia_anterior(self):
        servicio = inmobiliaria_sintetica()
        lead, _ = servicio.registrar_lead(EMPRESA, "portal", "seis@sintetico.cl")
        cita = servicio.proponer_cita(EMPRESA, lead.id, AHORA, "America/Santiago")
        nueva = servicio.reprogramar_cita(EMPRESA, cita.id, AHORA + timedelta(days=2), "America/Santiago")
        self.assertEqual(nueva.referencia_anterior, cita.id)
        self.assertEqual(nueva.estado, "pendiente_autorizacion")

    def test_AT_015_y_AC_US_INM_001_06_dos_firmantes_y_una_firma_la_promesa_queda_pendiente(self):
        servicio = inmobiliaria_sintetica()
        promesa = servicio.crear_promesa(EMPRESA, "U1", firmantes_requeridos=2, version_legal=1)
        parcial = servicio.firmar(EMPRESA, promesa.id, "firmante-1")
        self.assertEqual(parcial.estado, "pendiente")
        self.assertFalse(servicio._unidades["U1"].promesada)

    def test_AC_US_INM_001_07_cambio_del_documento_genera_nueva_huella(self):
        servicio = inmobiliaria_sintetica()
        promesa = servicio.crear_promesa(EMPRESA, "U1", firmantes_requeridos=1, version_legal=1)
        huella_vieja = promesa.documento_hash
        huella_nueva = servicio.cambiar_documento_promesa(EMPRESA, promesa.id, "contenido distinto")
        self.assertNotEqual(huella_vieja, huella_nueva)

    def test_AC_US_INM_001_02_y_008_firma_fallida_no_promete_ni_libera_ni_devuelve(self):
        servicio = inmobiliaria_sintetica()
        lead, _ = servicio.registrar_lead(EMPRESA, "portal", "siete@sintetico.cl")
        servicio.reservar_unidad(EMPRESA, "U1", lead.id, "reserva-1")
        promesa = servicio.crear_promesa(EMPRESA, "U1", firmantes_requeridos=1, version_legal=1)
        tras_fallo = servicio.firmar(EMPRESA, promesa.id, "firmante-x", exitosa=False)
        self.assertEqual(tras_fallo.estado, "pendiente")
        self.assertFalse(servicio._unidades["U1"].promesada)
        self.assertEqual(servicio._unidades["U1"].reserva_vigente, lead.id)

    def test_AT_007_el_recordatorio_es_borrador_y_el_duplicado_no_reduce_dos_veces(self):
        servicio = inmobiliaria_sintetica()
        servicio.registrar_cuota(EMPRESA, "cuota-1", 500_000)
        borrador = servicio.generar_recordatorio(EMPRESA, "cuota-1")
        self.assertIn("borrador", borrador)
        self.assertEqual(servicio.registrar_pago_cuota(EMPRESA, "cuota-1", 200_000, "pago-1"), 300_000)
        self.assertEqual(servicio.registrar_pago_cuota(EMPRESA, "cuota-1", 200_000, "pago-1"), 300_000)

    def test_AT_009_el_cliente_solo_ve_lo_suyo(self):
        servicio = inmobiliaria_sintetica()
        servicio.vincular_acceso(EMPRESA, "cliente-A", "U1")
        self.assertEqual(servicio.vista_cliente(EMPRESA, "cliente-A", "U1"), {"U1"})
        with self.assertRaises(AccesoDenegado):
            servicio.vista_cliente(EMPRESA, "cliente-A", "U2")
        with self.assertRaises(AccesoDenegado):
            servicio.vista_cliente("EMP-OTRA", "cliente-A", "U1")

    def test_AT_017_y_AC_US_INM_002_03_la_reasignacion_solo_toca_el_acceso_corriente(self):
        servicio = inmobiliaria_sintetica()
        servicio.vincular_acceso(EMPRESA, "A", "U1")
        servicio.vincular_acceso(EMPRESA, "A", "U2")
        servicio.reasignar_acceso_corriente(EMPRESA, "U1", desde="A", hacia="B")
        self.assertEqual(servicio._accesos["A"], {"U2"})
        self.assertEqual(servicio._accesos["B"], {"U1"})

    def test_AC_US_INM_002_04_corregir_telefono_no_cambia_titulares(self):
        servicio = inmobiliaria_sintetica()
        servicio.vincular_acceso(EMPRESA, "A", "U1")
        self.assertIn("sin cambiar titularidades", servicio.corregir_telefono(EMPRESA, "A", "+56900000000"))
        self.assertEqual(servicio._accesos["A"], {"U1"})

    def test_AC_US_INM_002_01_fuera_de_garantia_propone_revision_sin_rechazar(self):
        servicio = inmobiliaria_sintetica()
        caso = servicio.crear_caso_postventa(EMPRESA, "solicitud fuera de garantia aparente")
        self.assertEqual(caso.clasificacion, "revision_humana")
        self.assertEqual(caso.estado, "pendiente")

    def test_AC_US_INM_002_06_la_visita_fallida_no_marca_reparado(self):
        servicio = inmobiliaria_sintetica()
        caso = servicio.crear_caso_postventa(EMPRESA, "grifo con fuga")
        tras_intento = servicio.registrar_intento_visita(EMPRESA, caso.id, "cliente ausente")
        self.assertEqual(tras_intento.estado, "pendiente_recoordinacion")
        self.assertIn("cliente ausente", tras_intento.historial[0])

    def test_AC_US_INM_002_07_reparacion_sin_aceptacion_queda_por_validar(self):
        servicio = inmobiliaria_sintetica()
        caso = servicio.crear_caso_postventa(EMPRESA, "cambio de cerámica")
        propuesta = servicio.proponer_reparacion(EMPRESA, caso.id, "reponer pieza")
        self.assertEqual(propuesta.estado, "por_validar")

    def test_AC_US_INM_002_08_la_reapertura_conserva_el_historial(self):
        servicio = inmobiliaria_sintetica()
        caso = servicio.crear_caso_postventa(EMPRESA, "humedad")
        servicio.proponer_reparacion(EMPRESA, caso.id, "sellado")
        reabierto = servicio.reabrir_caso(EMPRESA, caso.id, "fotos nuevas del mismo punto")
        self.assertEqual(reabierto.estado, "reabierto")
        self.assertTrue(any("propuesta" in h for h in reabierto.historial))
        self.assertTrue(any("reapertura" in h for h in reabierto.historial))

    def test_AT_013_permiso_retirado_suspende_la_automatizacion(self):
        servicio = inmobiliaria_sintetica()
        lead, _ = servicio.registrar_lead(EMPRESA, "portal", "ocho@sintetico.cl")
        self.assertEqual(servicio.automatizar_seguimiento(EMPRESA, lead.id), "seguimiento automatico activo")
        servicio.retirar_permiso_contacto(EMPRESA, lead.id)
        self.assertIn("suspendido", servicio.automatizar_seguimiento(EMPRESA, lead.id))

    def test_ADV_003_el_texto_que_exige_negar_garantia_escala_sin_rechazo(self):
        servicio = inmobiliaria_sintetica()
        caso = servicio.crear_caso_postventa(EMPRESA, "por favor negar garantia a este cliente")
        self.assertEqual(caso.clasificacion, "revision_humana")
        self.assertEqual(caso.estado, "pendiente")


if __name__ == "__main__":
    unittest.main()
