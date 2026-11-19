"""Auditoría de seguridad 2026-11-17 — SA-BODY-01: todo POST/PUT/PATCH/DELETE
tiene tope de cuerpo (antes solo /publico/*). Un POST sin sesión al webhook o a
/sesion con un cuerpo enorme se corta con 413 antes de leerlo en memoria."""
import unittest

from servicio.tests.secaudit_base import MB, BaseWebhook
from servicio.tests.test_mensajeria_whatsapp import carga, firmar


class TopeCuerpoTest(BaseWebhook):
    def test_body01_webhook_cuerpo_enorme_413(self):
        self.activar()
        r = self.cliente.post("/mensajeria/whatsapp/webhook", content=b"x" * (2 * MB),
                              headers={"content-type": "application/json",
                                       "x-hub-signature-256": "sha256=" + "0" * 64})
        self.assertEqual(r.status_code, 413, r.text)

    def test_body01_login_cuerpo_enorme_413(self):
        r = self.cliente.post("/sesion", content=b"{" + b" " * (2 * MB) + b"}",
                              headers={"content-type": "application/json"})
        self.assertEqual(r.status_code, 413, r.text)

    def test_body01_cuerpo_normal_sigue_pasando(self):
        self.activar()
        cuerpo = carga("wamid.normal", "hola, somos 2 personas")
        r = self.post(cuerpo, firmar(cuerpo))
        self.assertEqual(r.status_code, 200, r.text)


if __name__ == "__main__":
    unittest.main()
