"""Auditoría de seguridad 2026-11-17 — webhook de WhatsApp.

SA-WA-01: el token de verificación se compara en tiempo constante y solo se
          devuelve un hub.challenge numérico (no refleja texto arbitrario).
SA-WA-02: una conversación larga no deja al huésped sin respuesta (antes, con
          más de 4000 caracteres acumulados, cada mensaje nuevo daba 400)."""
import unittest

from servicio.tests.secaudit_base import BaseWebhook
from servicio.tests.test_mensajeria_whatsapp import TOKEN, carga, firmar


class WebhookEndurecidoTest(BaseWebhook):
    def test_wa01_challenge_no_numerico_no_se_refleja(self):
        self.activar()
        r = self.cliente.get("/mensajeria/whatsapp/webhook", params={
            "hub.mode": "subscribe", "hub.verify_token": TOKEN, "hub.challenge": "<svg onload=alert(1)>"})
        self.assertNotIn("<svg", r.text)
        self.assertIn(r.status_code, (400, 403))

    def test_wa01_challenge_numerico_valido(self):
        self.activar()
        r = self.cliente.get("/mensajeria/whatsapp/webhook", params={
            "hub.mode": "subscribe", "hub.verify_token": TOKEN, "hub.challenge": "1158201444"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, "1158201444")
        malo = self.cliente.get("/mensajeria/whatsapp/webhook", params={
            "hub.mode": "subscribe", "hub.verify_token": TOKEN + "x", "hub.challenge": "1"})
        self.assertEqual(malo.status_code, 403)

    def test_wa02_conversacion_larga_sigue_recibiendo(self):
        self.activar()
        bloque = "Hola, quisiera saber la disponibilidad para fin de mes. " * 30  # ~1.7k
        for n in range(4):
            cuerpo = carga(f"wamid.largo.{n}", bloque[:1900])
            r = self.post(cuerpo, firmar(cuerpo))
            self.assertEqual(r.status_code, 200, f"mensaje {n}: {r.status_code} {r.text}")


if __name__ == "__main__":
    unittest.main()
