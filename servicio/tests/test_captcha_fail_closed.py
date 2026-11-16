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

    def test_sin_secreto_mensaje_amable_y_log_con_causa(self):
        """Regresión fix-e2e: el 503 de producción mostraba al visitante
        'canal público temporalmente no disponible' sin dejar la causa en el
        log. Ahora el detalle es útil para el visitante y el log nombra la
        variable faltante (sin valores)."""
        request = self._request(cookie_segura=True, secreto=None)
        with self.assertLogs("servicio.seguridad", level="ERROR") as logs:
            with self.assertRaises(HTTPException) as ctx:
                _exigir_captcha(request, "reserva", "127.0.0.1")
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("WhatsApp", ctx.exception.detail)
        self.assertNotIn("canal público", ctx.exception.detail)
        registro = logs.records[0]
        self.assertEqual(registro.evento, "recaptcha_sin_configurar")
        self.assertEqual(registro.accion, "reserva")
        self.assertIn("RECAPTCHA_SECRET_KEY", registro.causa)

    def test_rechazo_de_google_queda_en_el_log_sin_token(self):
        from servicio import recaptcha

        cuerpo = {"success": False, "error-codes": ["invalid-input-secret"]}
        with self.assertLogs("servicio.seguridad", level="WARNING") as logs:
            with self.assertRaises(recaptcha.CaptchaRechazado):
                recaptcha.juzgar(cuerpo, "consulta")
        r = logs.records[0]
        self.assertEqual(r.motivo, "success_false")
        self.assertEqual(r.codigos, ["invalid-input-secret"])

    def test_motivos_de_rechazo(self):
        from servicio import recaptcha

        hosts = frozenset({"www.hotelherencia.cl"})
        base = {"success": True, "action": "consulta", "score": 0.9, "hostname": "www.hotelherencia.cl"}
        self.assertIsNone(recaptcha.motivo_rechazo(base, "consulta", hosts))
        self.assertEqual(recaptcha.motivo_rechazo({**base, "action": "reserva"}, "consulta", hosts), "accion_distinta")
        self.assertEqual(recaptcha.motivo_rechazo({**base, "score": 0.1}, "consulta", hosts), "puntaje_bajo")
        self.assertEqual(recaptcha.motivo_rechazo({**base, "hostname": "otro.cl"}, "consulta", hosts), "host_no_permitido")


if __name__ == "__main__":
    unittest.main()
