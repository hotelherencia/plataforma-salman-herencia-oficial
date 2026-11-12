"""Fail-closed de reCAPTCHA en producción (C-HH-003)."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException

from servicio.rutas.hotel import _exigir_captcha


class CaptchaFailClosedTest(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("RECAPTCHA_OBLIGATORIO", None)

    def _request(self, cookie_segura: bool, secreto: str | None):
        request = MagicMock()
        request.app.state.configuracion = SimpleNamespace(
            cookie_segura=cookie_segura,
            recaptcha_secret_key=secreto,
        )
        request.headers.get = MagicMock(return_value=None)
        return request

    def test_prod_sin_secreto_falla_cerrado(self):
        request = self._request(cookie_segura=True, secreto=None)
        with self.assertRaises(HTTPException) as ctx:
            _exigir_captcha(request, "consulta", "127.0.0.1")
        self.assertEqual(ctx.exception.status_code, 503)

    def test_dev_sin_secreto_omite(self):
        request = self._request(cookie_segura=False, secreto=None)
        _exigir_captcha(request, "consulta", "127.0.0.1")  # no lanza

    def test_obligatorio_por_env_sin_secreto(self):
        os.environ["RECAPTCHA_OBLIGATORIO"] = "1"
        request = self._request(cookie_segura=False, secreto=None)
        with self.assertRaises(HTTPException) as ctx:
            _exigir_captcha(request, "consulta", "127.0.0.1")
        self.assertEqual(ctx.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
