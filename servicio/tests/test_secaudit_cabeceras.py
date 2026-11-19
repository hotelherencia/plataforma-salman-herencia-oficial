"""Auditoría de seguridad 2026-11-17 — SA-HDR-01: ninguna respuesta de la API
queda en caché (Cache-Control: no-store); HSTS cuando la cookie es Secure."""
import unittest

from fastapi.testclient import TestClient

from servicio.tests.secaudit_base import BaseWebhook


class CabecerasApiTest(BaseWebhook):
    def test_hdr01_respuesta_con_sesion_no_cacheable(self):
        r = self.cliente.get("/sesion")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("no-store", r.headers.get("cache-control", ""))

    def test_hdr01_401_tampoco_cacheable(self):
        r = TestClient(self.app).get("/hotel/reservas")
        self.assertEqual(r.status_code, 401)
        self.assertIn("no-store", r.headers.get("cache-control", ""))


    def test_hdr01_hsts_con_cookie_segura(self):
        from servicio.aplicacion import crear_app
        from servicio.configuracion import Configuracion
        config = Configuracion(host="127.0.0.1", puerto=0, database_url=None, cookie_segura=True,
                               origen_front=None, admin_usuario=None, admin_clave=None)
        r = TestClient(crear_app(configuracion=config)).get("/salud")
        self.assertEqual(r.status_code, 200)
        self.assertIn("max-age=", r.headers.get("strict-transport-security", ""))
        self.assertIn("no-store", r.headers.get("cache-control", ""))


if __name__ == "__main__":
    unittest.main()
