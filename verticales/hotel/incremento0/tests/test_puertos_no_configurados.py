from datetime import date
import unittest

from hotel_reservas_incremento0.puertos import (
    PuertoCanal,
    PuertoDocumentoTributario,
    PuertoPMS,
    PuertoPago,
    PuertosVacios,
)


class PuertosNoConfiguradosTest(unittest.TestCase):
    def test_todos_los_puertos_devuelven_no_configurado(self):
        puertos = PuertosVacios()
        rango = (date(2026, 11, 10), date(2026, 11, 12))
        respuestas = [
            puertos.pms.consultar_reserva("REF-EXT-1"),
            puertos.pms.propagar_disponibilidad("HAB-SINT-101", rango),
            puertos.canal.publicar_disponibilidad("HAB-SINT-101", rango),
            puertos.canal.recibir_evento({"tipo": "reserva"}),
            puertos.pago.iniciar_cobro("RSV-SINT-0001", 100000),
            puertos.documento_tributario.emitir("RSV-SINT-0001"),
        ]
        self.assertEqual(len(respuestas), 6)
        for respuesta in respuestas:
            self.assertFalse(respuesta.configurado)
            self.assertEqual(respuesta.detalle, "no configurado")

    def test_clases_puerto_individuales_tambien_no_configurado(self):
        self.assertFalse(PuertoPMS().consultar_reserva("X").configurado)
        self.assertFalse(PuertoCanal().recibir_evento({}).configurado)
        self.assertFalse(PuertoPago().iniciar_cobro("R", 1).configurado)
        self.assertFalse(PuertoDocumentoTributario().emitir("R").configurado)


if __name__ == "__main__":
    unittest.main()
