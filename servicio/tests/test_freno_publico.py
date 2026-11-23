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


class FrenoPorRutaTest(unittest.TestCase):
    """CE-HH-2026-001 C-02: techos y claves separados por ámbito."""

    def test_inundar_un_ambito_no_agota_otro(self):
        freno = FrenoDeSolicitudes(1)
        for i in range(5):
            self.assertTrue(freno.permite(f"ip:{i}", ambito="disponibilidad"))
        self.assertFalse(freno.permite("ip:x", ambito="disponibilidad"))
        self.assertTrue(freno.permite("ip:x", ambito="leads"))
        self.assertTrue(freno.permite("wa:conv-1", ambito="whatsapp"))

    def test_misma_clave_en_ambitos_distintos_no_comparte_ventana(self):
        freno = FrenoDeSolicitudes(1)
        self.assertTrue(freno.permite("ip:a", ambito="leads:pre"))
        self.assertTrue(freno.permite("ip:a", ambito="leads"))
        self.assertFalse(freno.permite("ip:a", ambito="leads"))


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

    def test_w16_a01_acepta_dominios_propios(self):
        # /reservar en la plataforma y la landing en www y apex (W16-A01).
        for host in ("plataforma.hotelherencia.cl", "www.hotelherencia.cl", "hotelherencia.cl", "WWW.HotelHerencia.cl"):
            with self.subTest(host=host):
                juzgar({"success": True, "action": "consulta", "score": 0.9, "hostname": host}, "consulta")

    def test_w16_a01_rechaza_hosts_parecidos(self):
        for host in ("plataforma.hotelherencia.cl.evil.example", "hotelherencia.cl.example", "evilhotelherencia.cl", ""):
            with self.subTest(host=host):
                with self.assertRaises(CaptchaRechazado):
                    juzgar({"success": True, "action": "consulta", "score": 0.9, "hostname": host}, "consulta")

    def test_recaptcha_hostnames_agrega_hosts_sin_quitar_los_fijos(self):
        from unittest import mock

        cuerpo = {"success": True, "action": "consulta", "score": 0.9, "hostname": "preview.hotelherencia.cl"}
        with mock.patch.dict(os.environ, {"RECAPTCHA_HOSTNAMES": " preview.hotelherencia.cl , "}):
            juzgar(cuerpo, "consulta")
            juzgar({**cuerpo, "hostname": "plataforma.hotelherencia.cl"}, "consulta")
        with mock.patch.dict(os.environ, {"RECAPTCHA_HOSTNAMES": ""}):
            with self.assertRaises(CaptchaRechazado):
                juzgar(cuerpo, "consulta")


class FrenoPersistentePostgresTest(unittest.TestCase):
    """OBS-01 / #414: el freno persiste en PostgreSQL entre instancias sin guardar PII."""

    URL_TEST = os.environ.get(
        "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
    )

    def setUp(self):
        import psycopg
        from servicio import migracion

        migracion.aplicar_migraciones(self.URL_TEST)
        with psycopg.connect(self.URL_TEST) as conn:
            conn.execute("DELETE FROM freno_solicitudes_eventos")
            conn.commit()

    def test_ventana_persiste_entre_instancias_y_no_guarda_pii(self):
        import psycopg

        instancia_a = FrenoDeSolicitudes(max_por_minuto=2, database_url=self.URL_TEST)
        instancia_b = FrenoDeSolicitudes(max_por_minuto=2, database_url=self.URL_TEST)
        self.assertTrue(instancia_a.permite("ip:203.0.113.9", "correo:ana@hotelherencia.test", ambito="solicitudes"))
        self.assertTrue(instancia_b.permite("ip:203.0.113.9", "correo:ana@hotelherencia.test", ambito="solicitudes"))
        # Tercera llamada en otra instancia dentro de 60 s debe bloquearse
        self.assertFalse(instancia_a.permite("ip:203.0.113.9", "correo:ana@hotelherencia.test", ambito="solicitudes"))
        # Ámbito distinto no queda agotado
        self.assertTrue(instancia_b.permite("ip:203.0.113.9", ambito="disponibilidad"))
        # Ningún dato en claro (ni IP ni correo) en la tabla
        with psycopg.connect(self.URL_TEST) as conn:
            valores = [r[0] for r in conn.execute("SELECT clave_hash FROM freno_solicitudes_eventos").fetchall()]
        self.assertTrue(len(valores) > 0)
        for v in valores:
            self.assertNotIn("203.0.113.9", v)
            self.assertNotIn("ana@hotelherencia.test", v)


if __name__ == "__main__":
    unittest.main()
