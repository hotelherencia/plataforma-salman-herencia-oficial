from datetime import datetime, timedelta
import unittest

from nucleo.empresa import EMPRESA_FIJA
from nucleo.servicio import (
    AccesoDenegado,
    EfectoNoAplicable,
    nucleo_sintetico,
)

EMPRESA = EMPRESA_FIJA.id
AHORA = datetime(2026, 11, 10, 12, 0)


class ACCoreIdsTest(unittest.TestCase):
    def test_AC_US_CORE_001_01_otra_empresa_no_usa_la_referencia_del_conector(self):
        nucleo = nucleo_sintetico()
        nucleo.registrar_conector(EMPRESA, "CON-1", permisos={"lectura", "escritura"})
        nucleo.vincular_referencia(EMPRESA, "CON-1", "ref-123")
        self.assertEqual(nucleo.usar_referencia(EMPRESA, "ref-123", "lectura"), "ok:lectura")
        with self.assertRaises(AccesoDenegado):
            nucleo.usar_referencia("EMP-OTRA", "ref-123", "lectura")

    def test_AC_US_CORE_001_02_capacidad_no_habilitada_se_informa_y_registra(self):
        nucleo = nucleo_sintetico()
        nucleo.registrar_conector(EMPRESA, "CON-1", permisos=set())
        nucleo.vincular_referencia(EMPRESA, "CON-1", "ref-1")
        with self.assertRaises(AccesoDenegado):
            nucleo.usar_referencia(EMPRESA, "ref-1", "captura")

    def test_AC_US_CORE_002_01_resultado_repetido_diez_veces_un_solo_efecto(self):
        nucleo = nucleo_sintetico()
        nucleo.registrar_deuda(EMPRESA, "deuda-1", 10_000)
        primero = None
        for _ in range(10):
            efecto = nucleo.aplicar_resultado_pago(EMPRESA, "retorno-1", "autorizado", 10_000)
            primero = primero or efecto
            self.assertEqual(efecto.id, primero.id)
        self.assertEqual(nucleo.deuda(EMPRESA, "deuda-1"), 0)

    def test_AC_US_CORE_002_02_rechazo_posterior_no_figura_autorizado_ni_borra_la_deuda(self):
        nucleo = nucleo_sintetico()
        nucleo.registrar_deuda(EMPRESA, "deuda-2", 10_000)
        nucleo.aplicar_resultado_pago(EMPRESA, "offline-1", "autorizado", 10_000)
        rechazado = nucleo.aplicar_resultado_pago(EMPRESA, "retorno-2", "rechazado", 10_000)
        self.assertEqual(rechazado.estado, "rechazado")
        self.assertEqual(nucleo.deuda(EMPRESA, "deuda-2"), 0)
        self.assertEqual(nucleo.aplicar_resultado_pago(EMPRESA, "retorno-2", "rechazado", 10_000).estado, "rechazado")

    def test_AC_US_CORE_003_01_la_propuesta_cambia_de_monto_y_no_se_ejecuta(self):
        nucleo = nucleo_sintetico()
        aprobacion = nucleo.aprobar(EMPRESA, 10_000, {"concepto": "ajuste"}, AHORA, 60)
        self.assertEqual(
            nucleo.ejecutar_con_aprobacion(EMPRESA, aprobacion.id, 10_000, {"concepto": "ajuste"}, AHORA),
            "ejecutado",
        )
        otra = nucleo.aprobar(EMPRESA, 10_000, {"concepto": "ajuste"}, AHORA, 60)
        with self.assertRaises(EfectoNoAplicable):
            nucleo.ejecutar_con_aprobacion(EMPRESA, otra.id, 11_000, {"concepto": "ajuste"}, AHORA)

    def test_AC_US_CORE_003_02_conector_de_lectura_deniegue_escritura(self):
        nucleo = nucleo_sintetico()
        nucleo.registrar_conector(EMPRESA, "CON-LECTURA", permisos={"lectura"})
        nucleo.vincular_referencia(EMPRESA, "CON-LECTURA", "ref-l")
        with self.assertRaises(AccesoDenegado):
            nucleo.usar_referencia(EMPRESA, "ref-l", "escritura")

    def test_AC_US_CORE_003_03_flag_de_envio_no_autorizado_no_envia_y_registra(self):
        nucleo = nucleo_sintetico()
        nucleo.registrar_herramienta(EMPRESA, "contacto", efectos_permitidos={"guardar"})
        with self.assertRaises(AccesoDenegado):
            nucleo.invocar_herramienta(EMPRESA, "contacto", "enviar_correo")
        self.assertIn(("contacto", "enviar_correo"), nucleo.efectos_excluidos(EMPRESA))

    def test_AC_US_CORE_003_04_placeholder_queda_bloqueada_sin_llamar_al_destino(self):
        nucleo = nucleo_sintetico()
        nucleo.registrar_conector(EMPRESA, "CON-PLACEHOLDER", permisos={"lectura"}, placeholder=True)
        nucleo.vincular_referencia(EMPRESA, "CON-PLACEHOLDER", "ref-p")
        with self.assertRaises(AccesoDenegado):
            nucleo.usar_referencia(EMPRESA, "ref-p", "lectura")

    def test_AC_US_CORE_003_05_referencia_de_otra_cuenta_no_accede_ni_repite(self):
        nucleo = nucleo_sintetico()
        nucleo.registrar_conector(EMPRESA, "CON-A", permisos={"lectura"})
        nucleo.vincular_referencia(EMPRESA, "CON-A", "ref-de-A")
        with self.assertRaises(AccesoDenegado):
            nucleo.usar_referencia("EMP-OTRA", "ref-de-A", "lectura")
        self.assertEqual(nucleo.usar_referencia(EMPRESA, "ref-de-A", "lectura"), "ok:lectura")


if __name__ == "__main__":
    unittest.main()
