"""Freno, IP visible y juicio de reCAPTCHA, sin base de datos."""
import os
import unittest

from servicio.canal_publico import FrenoDeSolicitudes, ip_visible
from servicio.recaptcha import CaptchaRechazado, juzgar


class _Cliente:
    def __init__(self, host):
        self.host = host


class _Pedido:
    def __init__(self, host, forwarded=None):
        self.client = _Cliente(host)
        self.headers = {}
        if forwarded is not None:
            self.headers["x-forwarded-for"] = forwarded


class FrenoPublicoTest(unittest.TestCase):
    def test_una_llamada_cuenta_cada_clave_una_vez(self):
        freno = FrenoDeSolicitudes(2)
        self.assertTrue(freno.permite("ip:a", "correo:a@b.test"))
        self.assertTrue(freno.permite("ip:a", "correo:a@b.test"))
        self.assertFalse(freno.permite("ip:b", "correo:a@b.test"))
        self.assertFalse(freno.permite("ip:a", "correo:otro@b.test"))

    def test_techo_del_proceso_sigue_al_maximo(self):
        freno = FrenoDeSolicitudes(1)
        for i in range(5):
            self.assertTrue(freno.permite(f"ip:{i}"))
        self.assertFalse(freno.permite("ip:otro"))
        freno.max_por_minuto = 2
        self.assertTrue(freno.permite("ip:nuevo"))


class IpVisibleTest(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("CONFIAR_PROXY", None)

    def test_sin_proxy_ignora_el_encabezado(self):
        pedido = _Pedido("10.0.0.8", "1.1.1.1, 2.2.2.2")
        self.assertEqual(ip_visible(pedido), "10.0.0.8")

    def test_con_proxy_usa_el_ultimo_salto(self):
        os.environ["CONFIAR_PROXY"] = "1"
        pedido = _Pedido("10.0.0.8", "1.1.1.1, 2.2.2.2")
        self.assertEqual(ip_visible(pedido), "2.2.2.2")


class RecaptchaJuzgarTest(unittest.TestCase):
    def test_acepta_un_token_del_host_y_la_accion(self):
        juzgar(
            {"success": True, "action": "consulta", "score": 0.9, "hostname": "hotelherencia-landing.vercel.app"},
            "consulta",
        )

    def test_rechaza_host_accion_o_puntaje(self):
        base = {"success": True, "action": "consulta", "score": 0.9, "hostname": "hotelherencia.cl"}
        for cambio in (
            {"success": False},
            {"action": "reserva"},
            {"score": 0.2},
            {"hostname": "otro.example"},
        ):
            with self.subTest(cambio=cambio):
                with self.assertRaises(CaptchaRechazado):
                    juzgar({**base, **cambio}, "consulta")


if __name__ == "__main__":
    unittest.main()
