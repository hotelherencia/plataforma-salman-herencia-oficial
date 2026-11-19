"""#353 (2026-11-18): avisos al administrador por cada solicitud de reserva.
Contador para la insignia, bandeja de salida idempotente, envío por canal
configurado, reintento y que un fallo de envío no impide guardar.
"""
import unittest

import psycopg

from servicio.avisos import CanalCorreo, CanalWhatsapp, Despachador, MAX_INTENTOS
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests.test_canal_publico import CanalPublicoBaseTest, URL_TEST


class CanalFalso:
    def __init__(self, nombre="correo", fallar=0):
        self.nombre = nombre
        self.fallar = fallar
        self.enviados = []

    def enviar(self, evento):
        if self.fallar > 0:
            self.fallar -= 1
            raise ConnectionError("smtp caído")
        self.enviados.append(evento)


class AvisosHallazgosTest(CanalPublicoBaseTest):
    def setUp(self):
        super().setUp()
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("TRUNCATE avisos_envios, avisos_eventos")
            conexion.commit()
        self.app.state.avisos = Despachador([], URL_TEST)

    def tearDown(self):
        self.app.state.avisos = Despachador([], URL_TEST)

    def envios(self):
        with psycopg.connect(URL_TEST) as conexion:
            return conexion.execute(
                "SELECT canal, estado, intentos, ultimo_error FROM avisos_envios ORDER BY canal").fetchall()

    def test_contador_de_solicitudes_recibidas(self):
        self.assertEqual(self.cliente.get("/hotel/avisos").json()["solicitudes_recibidas"], 0)
        self.crear_solicitud()
        self.crear_solicitud()
        cuerpo = self.cliente.get("/hotel/avisos").json()
        self.assertEqual(cuerpo["solicitudes_recibidas"], 2)
        self.assertEqual(cuerpo["canales_activos"], [])
        self.assertEqual(self.anonima.get("/hotel/avisos").status_code, 401)

    def test_sin_canales_la_solicitud_se_guarda_y_queda_el_evento(self):
        sid = self.crear_solicitud()
        with psycopg.connect(URL_TEST) as conexion:
            eventos = conexion.execute("SELECT tipo, referencia, datos FROM avisos_eventos").fetchall()
        self.assertEqual([(e[0], e[1]) for e in eventos], [("solicitud_recibida", sid)])
        # sin datos personales en el aviso
        self.assertNotIn("huesped", str(eventos[0][2]))
        self.assertEqual(self.envios(), [])

    def test_envio_por_canal_tras_guardar_e_idempotente(self):
        correo, whatsapp = CanalFalso("correo"), CanalFalso("whatsapp")
        self.app.state.avisos = Despachador([correo, whatsapp], URL_TEST)
        sid = self.crear_solicitud()  # la tarea de fondo despacha al responder
        self.assertEqual([e["referencia"] for e in correo.enviados], [sid])
        self.assertEqual([e["referencia"] for e in whatsapp.enviados], [sid])
        self.assertEqual(self.app.state.avisos.despachar(), {"enviados": 0, "fallidos": 0})
        self.assertEqual([(c, e, i) for c, e, i, _ in self.envios()], [("correo", "enviado", 1), ("whatsapp", "enviado", 1)])

    def test_fallo_no_impide_guardar_y_se_reintenta(self):
        correo = CanalFalso("correo", fallar=2)
        self.app.state.avisos = Despachador([correo], URL_TEST)
        sid = self.crear_solicitud()  # 201 aunque el envío falle
        self.assertEqual(self.envios()[0][:3], ("correo", "fallido", 1))
        self.assertIn("smtp caído", self.envios()[0][3])
        self.assertEqual(self.app.state.avisos.despachar()["fallidos"], 1)
        self.assertEqual(self.app.state.avisos.despachar()["enviados"], 1)
        self.assertEqual(self.envios()[0][:3], ("correo", "enviado", 3))
        self.assertEqual([e["referencia"] for e in correo.enviados], [sid])

    def test_tope_de_reintentos(self):
        correo = CanalFalso("correo", fallar=100)
        self.app.state.avisos = Despachador([correo], URL_TEST)
        self.crear_solicitud()
        for _ in range(MAX_INTENTOS + 2):
            self.app.state.avisos.despachar()
        self.assertEqual(self.envios()[0][2], MAX_INTENTOS)

    def test_contenido_de_correo_y_whatsapp(self):
        evento = {"id": "AVI-1", "tipo": "solicitud_recibida", "referencia": "SOL-1",
                  "datos": {"tipo": "doble", "inicio": "2026-12-01", "fin": "2026-12-03", "personas": 2, "origen": "web"}}
        mensajes = []
        CanalCorreo("smtp.test", 587, None, None, "reservas@hotel.test", "admin@hotel.test", "https://front.test",
                    enviar_smtp=mensajes.append).enviar(evento)
        self.assertIn("01/12/2026", mensajes[0]["Subject"])
        self.assertTrue(mensajes[0]["Subject"].startswith("[Hotel Herencia] "))
        self.assertIn("https://front.test/hotel/solicitudes?id=SOL-1", mensajes[0].get_body(("plain",)).get_content())
        publicados = []
        CanalWhatsapp("123", "token", "56900000000", "solicitud_reserva", "es", "https://front.test",
                      publicar=lambda url, cuerpo, cab: publicados.append((url, cuerpo, cab))).enviar(evento)
        url, cuerpo, cabeceras = publicados[0]
        self.assertTrue(url.endswith("/123/messages"))
        self.assertEqual(cuerpo["template"]["name"], "solicitud_reserva")
        self.assertEqual(cabeceras["Authorization"], "Bearer token")


if __name__ == "__main__":
    unittest.main()
