"""Auditoría de seguridad 2026-11-17 — SA-TOTP-01: un código TOTP ya aceptado
no vuelve a servir (RFC 6238 §5.2), ni el de activación ni el de un login."""
import unittest

import psycopg
from fastapi.testclient import TestClient

from servicio import totp
from servicio.tests.secaudit_base import URL_TEST, BaseSesiones


class TotpUnSoloUsoTest(BaseSesiones):
    # --- SA-TOTP-01 ------------------------------------------------------
    def _activar_totp(self, cliente):
        alta = cliente.post("/cuenta/2fa")
        self.assertEqual(alta.status_code, 200, alta.text)
        secreto = alta.json()["secreto"]
        r = cliente.post("/cuenta/2fa/activar", json={"codigo": totp.codigo(secreto)})
        self.assertEqual(r.status_code, 200, r.text)
        return secreto

    def test_totp01_codigo_de_login_no_se_reutiliza(self):
        self.alta("admin_totp", "administrador", "ClaveTotp123", "totp-alta")
        cliente = self.cliente_como("admin_totp", "ClaveTotp123")
        secreto = self._activar_totp(cliente)
        # El código de activación ya quedó consumido; se simula un paso nuevo
        # sin esperar 30 s liberando la marca del último paso usado.
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("UPDATE usuarios SET totp_ultimo_paso = NULL WHERE nombre = 'admin_totp'")
            conexion.commit()
        codigo = totp.codigo(secreto)
        primero = TestClient(self.app).post(
            "/sesion", json={"usuario": "admin_totp", "clave": "ClaveTotp123", "totp": codigo})
        self.assertEqual(primero.status_code, 200, primero.text)
        repetido = TestClient(self.app).post(
            "/sesion", json={"usuario": "admin_totp", "clave": "ClaveTotp123", "totp": codigo})
        self.assertEqual(repetido.status_code, 401, repetido.text)

    def test_totp01_codigo_de_activacion_no_sirve_para_login(self):
        self.alta("admin_totp2", "administrador", "ClaveTotp123", "totp-alta-2")
        cliente = self.cliente_como("admin_totp2", "ClaveTotp123")
        alta = cliente.post("/cuenta/2fa")
        secreto = alta.json()["secreto"]
        codigo = totp.codigo(secreto)
        self.assertEqual(cliente.post("/cuenta/2fa/activar", json={"codigo": codigo}).status_code, 200)
        repetido = TestClient(self.app).post(
            "/sesion", json={"usuario": "admin_totp2", "clave": "ClaveTotp123", "totp": codigo})
        self.assertEqual(repetido.status_code, 401, repetido.text)


if __name__ == "__main__":
    unittest.main()
