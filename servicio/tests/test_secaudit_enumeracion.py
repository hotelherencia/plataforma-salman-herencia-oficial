"""Auditoría de seguridad 2026-11-17 — SA-ENUM-01: el login con un usuario
inexistente también verifica un hash argon2 (sin diferencia de tiempo)."""
import unittest

import psycopg

from servicio import seguridad
from servicio.tests.secaudit_base import URL_TEST, BaseSesiones


class EnumeracionTest(BaseSesiones):
    # --- SA-ENUM-01 ------------------------------------------------------
    def test_enum01_usuario_inexistente_tambien_paga_argon2(self):
        """Sin verificación de hash para un usuario inexistente, el tiempo de
        respuesta distingue nombres válidos de inválidos (enumeración)."""
        from unittest import mock
        llamadas = []
        original = seguridad.verificar_clave

        def contar(*args, **kwargs):
            llamadas.append(1)
            return original(*args, **kwargs)

        with mock.patch.object(seguridad, "verificar_clave", side_effect=contar):
            with psycopg.connect(URL_TEST) as conexion:
                self.assertIsNone(seguridad.autenticar(conexion, "no-existe-nunca", "x"))
        self.assertEqual(len(llamadas), 1)


if __name__ == "__main__":
    unittest.main()
