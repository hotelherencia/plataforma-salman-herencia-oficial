"""Avisos por correo (2026-11-19): eventos dentro de la transacción de
negocio e idempotentes, preferencias por tipo (encendido y destinatarios)
guardadas por la administración, resumen diario de las 08:00, envío de
prueba y contenido en texto + HTML sin datos del huésped.
"""
import unittest
import uuid
from datetime import datetime, timedelta

import psycopg

from servicio import avisos
from servicio.avisos import CanalBuzon, CanalCorreo, CanalWhatsapp, Despachador, MAX_INTENTOS
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests.test_canal_publico import CanalPublicoBaseTest, EMPRESA, EN_3, MANANA, URL_TEST

FRONT = "https://plataforma.test"


class CorreoFalso:
    """Canal de correo que guarda lo que enviaría (mismo contrato que CanalBuzon)."""
    nombre = "correo"

    def __init__(self, fallar=0, destino=None):
        self.fallar = fallar
        self.destino = destino
        self.enviados = []

    def enviar(self, evento):
        destinos = avisos._destinos(evento, self.destino)
        if self.fallar > 0:
            self.fallar -= 1
            raise TimeoutError("timed out")
        self.enviados.append((evento, destinos, avisos.componer(evento, FRONT)))
        return destinos


class AvisosCorreoTest(CanalPublicoBaseTest):
    def setUp(self):
        super().setUp()
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("TRUNCATE avisos_envios, avisos_eventos, avisos_preferencias, buzones_correo")
            conexion.commit()
        self.correo = CorreoFalso()
        self.usar(self.correo)

    def tearDown(self):
        self.app.state.avisos = Despachador([], URL_TEST)

    def usar(self, *canales, defecto=("admin@hotel.test",)):
        self.app.state.avisos = Despachador(list(canales), URL_TEST, FRONT, usar_buzones=False,
                                            empresa_id=EMPRESA, destinos_defecto=list(defecto))
        return self.app.state.avisos

    def eventos(self, tipo=None):
        sql = "SELECT tipo, referencia, datos, empresa_id FROM avisos_eventos"
        filas = self.select(sql + (" WHERE tipo = %s" if tipo else "") + " ORDER BY creado_en", (tipo,) if tipo else ())
        return filas

    def envios(self):
        return self.select("SELECT e.tipo, v.canal, v.estado, v.intentos, v.ultimo_error, v.destinatarios "
                           "FROM avisos_envios v JOIN avisos_eventos e ON e.id = v.evento_id ORDER BY v.actualizado_en")

    def reservar(self, clave=None):
        r = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-SINT-101", "inicio": str(MANANA), "fin": str(EN_3), "personas": 2,
                  "huesped": {"nombre": "Marta Privada", "documento": "11.111.111-1"}},
            headers={"Idempotency-Key": clave or self.clave()})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def lead(self, clave=None):
        r = self.anonima.post("/publico/leads", json={
            "nombre": "Lucía Privada", "correo": "lucia@example.test", "telefono": "+56 9 1234 5678",
            "huespedes": 3, "check_in": str(MANANA), "check_out": str(EN_3), "mensaje": "¿Tienen estacionamiento?"},
            headers={"Idempotency-Key": clave or self.clave()})
        self.assertIn(r.status_code, (200, 201), r.text)
        return r.json()["lead"]["id"]

    # --- eventos --------------------------------------------------------------
    def test_consulta_de_la_landing_registra_evento_y_avisa_sin_datos_personales(self):
        clave = self.clave()
        lead_id = self.lead(clave)
        self.lead(clave)  # reintento: mismo evento
        eventos = self.eventos("consulta_recibida")
        self.assertEqual([(e[0], e[1], e[3]) for e in eventos], [("consulta_recibida", lead_id, EMPRESA)])
        datos = str(eventos[0][2])
        for privado in ("Lucía", "lucia@", "1234", "estacionamiento"):
            self.assertNotIn(privado, datos)
        # la ruta despacha en segundo plano al responder
        self.assertEqual(len(self.correo.enviados), 1)
        evento, destinos, mensaje = self.correo.enviados[0]
        self.assertEqual(destinos, ["admin@hotel.test"])
        self.assertTrue(mensaje.asunto.startswith("[Hotel Herencia] Nueva consulta"))
        self.assertIn(f"{FRONT}/hotel/leads?id={lead_id}", mensaje.texto)
        self.assertIn("Trae mensaje: Sí", mensaje.texto)
        self.assertNotIn("Lucía", mensaje.html)

    def test_reserva_confirmada_y_pago_registrado_en_la_misma_transaccion(self):
        clave = self.clave()
        reserva = self.reservar(clave)
        self.reservar(clave)  # reintento idempotente: no duplica
        rid = reserva["reserva_id"]
        ev = self.eventos("reserva_confirmada")
        self.assertEqual([e[1] for e in ev], [rid])
        self.assertEqual(ev[0][2]["habitacion_id"], "HAB-SINT-101")
        self.assertEqual(ev[0][2]["total_clp"], reserva["total_clp"])
        self.assertNotIn("Marta", str(ev[0][2]))
        self.assertNotIn("11.111", str(ev[0][2]))
        pago = self.cliente.post(f"/hotel/reservas/{rid}/pagos",
                                 json={"monto_clp": 10000, "clave": "c-1", "modo": "manual"},
                                 headers={"Idempotency-Key": self.clave()})
        self.assertEqual(pago.status_code, 201, pago.text)
        pagos = self.eventos("pago_registrado")
        self.assertEqual([p[1] for p in pagos], [pago.json()["pago_id"]])
        self.assertEqual((pagos[0][2]["monto_clp"], pagos[0][2]["tipo_pago"], pagos[0][2]["reserva_id"]), (10000, "parcial", rid))
        # pago repetido con la misma clave de cobro: no hay segundo evento
        self.cliente.post(f"/hotel/reservas/{rid}/pagos", json={"monto_clp": 10000, "clave": "c-1", "modo": "manual"},
                          headers={"Idempotency-Key": self.clave()})
        self.assertEqual(len(self.eventos("pago_registrado")), 1)
        self.app.state.avisos.despachar()
        asuntos = [m.asunto for _, _, m in self.correo.enviados]
        self.assertTrue(any(a.startswith("[Hotel Herencia] Reserva confirmada: HAB-SINT-101") for a in asuntos))
        self.assertIn("[Hotel Herencia] Pago registrado: $10.000 · reserva " + rid, asuntos)
        enlaces = [m.enlace for _, _, m in self.correo.enviados]
        self.assertIn(f"{FRONT}/hotel/reservas/{rid}", enlaces)

    def test_reserva_rechazada_no_deja_evento(self):
        r = self.cliente.post("/hotel/reservas", json={
            "habitacion_id": "HAB-SINT-101", "inicio": str(MANANA), "fin": str(EN_3),
            "huesped": {"nombre": "X"}}, headers={"Idempotency-Key": self.clave()})
        self.assertEqual(r.status_code, 201)
        otra = self.cliente.post("/hotel/reservas", json={
            "habitacion_id": "HAB-SINT-101", "inicio": str(MANANA), "fin": str(EN_3),
            "huesped": {"nombre": "Y"}}, headers={"Idempotency-Key": self.clave()})
        self.assertEqual(otra.status_code, 409)
        self.assertEqual(len(self.eventos("reserva_confirmada")), 1)

    def test_convertir_solicitud_avisa_reserva_confirmada(self):
        sid = self.crear_solicitud()
        r = self.cliente.post(f"/hotel/solicitudes/{sid}/conversion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(len(self.eventos("solicitud_recibida")), 1)
        self.assertEqual(len(self.eventos("reserva_confirmada")), 1)

    # --- preferencias -----------------------------------------------------------
    def test_preferencias_por_defecto_guardar_y_validar(self):
        cuerpo = self.cliente.get("/hotel/avisos/configuracion").json()
        tipos = [p["tipo"] for p in cuerpo["preferencias"]]
        self.assertEqual(tipos, list(avisos.TIPOS))
        self.assertTrue(all(p["activo"] and p["destinatarios"] == [] for p in cuerpo["preferencias"]))
        self.assertEqual(cuerpo["destinatarios_defecto"], ["admin@hotel.test"])
        self.assertEqual(cuerpo["canal"]["origen"], "otro")
        r = self.cliente.put("/hotel/avisos/preferencias", json={"preferencias": [
            {"tipo": "pago_registrado", "activo": False, "destinatarios": []},
            {"tipo": "solicitud_recibida", "activo": True, "destinatarios": [" Reservas@Hotel.test ", "gerencia@hotel.test", "reservas@hotel.test"]},
        ]}, headers={"Idempotency-Key": self.clave()})
        self.assertEqual(r.status_code, 200, r.text)
        prefs = {p["tipo"]: p for p in r.json()["preferencias"]}
        self.assertEqual(prefs["solicitud_recibida"]["destinatarios"], ["reservas@hotel.test", "gerencia@hotel.test"])
        self.assertFalse(prefs["pago_registrado"]["activo"])
        self.assertEqual(prefs["solicitud_recibida"]["actualizado_por"], "admin")
        malo = self.cliente.put("/hotel/avisos/preferencias", json={"preferencias": [
            {"tipo": "solicitud_recibida", "activo": True, "destinatarios": ["no-es-correo"]}]},
            headers={"Idempotency-Key": self.clave()})
        self.assertEqual(malo.status_code, 422)
        self.assertIn("no es un correo válido", malo.json()["detail"])
        desconocido = self.cliente.put("/hotel/avisos/preferencias", json={"preferencias": [{"tipo": "x"}]},
                                       headers={"Idempotency-Key": self.clave()})
        self.assertEqual(desconocido.status_code, 422)
        sin_clave = self.cliente.put("/hotel/avisos/preferencias", json={"preferencias": []})
        self.assertEqual(sin_clave.status_code, 400)
        demasiados = self.cliente.put("/hotel/avisos/preferencias", json={"preferencias": [
            {"tipo": "resumen_diario", "destinatarios": [f"p{i}@hotel.test" for i in range(11)]}]},
            headers={"Idempotency-Key": self.clave()})
        self.assertEqual(demasiados.status_code, 422)

    def test_solo_administracion_del_hotel(self):
        self.crear_usuario("recepcion1", "recepcion")
        recepcion = self.login("recepcion1", "clave-usuario-1")
        self.assertEqual(recepcion.get("/hotel/avisos/configuracion").status_code, 403)
        self.assertEqual(recepcion.put("/hotel/avisos/preferencias", json={"preferencias": []},
                                       headers={"Idempotency-Key": self.clave()}).status_code, 403)
        self.assertEqual(recepcion.post("/hotel/avisos/prueba").status_code, 403)
        self.assertEqual(self.anonima.get("/hotel/avisos/configuracion").status_code, 401)

    def test_despachador_respeta_preferencias(self):
        self.cliente.put("/hotel/avisos/preferencias", json={"preferencias": [
            {"tipo": "solicitud_recibida", "activo": True, "destinatarios": ["reservas@hotel.test", "dueno@hotel.test"]},
            {"tipo": "reserva_confirmada", "activo": False, "destinatarios": []},
        ]}, headers={"Idempotency-Key": self.clave()})
        sid = self.crear_solicitud()
        self.reservar()
        self.app.state.avisos.despachar()
        por_tipo = {e[0]: e for e in self.envios()}
        self.assertEqual(por_tipo["solicitud_recibida"][2], "enviado")
        self.assertEqual(por_tipo["solicitud_recibida"][5], "reservas@hotel.test,dueno@hotel.test")
        self.assertEqual(por_tipo["reserva_confirmada"][2], "omitido")
        self.assertIn("apagado", por_tipo["reserva_confirmada"][4])
        self.assertEqual([e[0]["referencia"] for e in self.correo.enviados], [sid])
        # lo omitido no se reintenta
        self.assertEqual(self.app.state.avisos.despachar(), {"enviados": 0, "fallidos": 0})

    def test_destino_por_defecto_y_sin_destinatarios(self):
        # buzón con destino propio: manda a ese destino si no hay preferencia
        propio = CorreoFalso(destino="buzon@hotel.test")
        self.usar(propio, defecto=())
        self.crear_solicitud()
        self.assertEqual(propio.enviados[0][1], ["buzon@hotel.test"])
        # sin preferencia, sin destino propio y sin ADMIN_EMAIL: queda omitido
        nadie = CorreoFalso()
        self.usar(nadie, defecto=())
        self.reservar()
        self.app.state.avisos.despachar()
        omitidos = [e for e in self.envios() if e[0] == "reserva_confirmada"]
        self.assertEqual(omitidos[0][2], "omitido")
        self.assertIn("no hay destinatarios", omitidos[0][4])

    def test_whatsapp_solo_para_solicitudes(self):
        publicados = []
        whatsapp = CanalWhatsapp("123", "token", "56900000000", "solicitud_reserva", "es", FRONT,
                                 publicar=lambda url, cuerpo, cab: publicados.append(cuerpo))
        self.usar(self.correo, whatsapp)
        self.crear_solicitud()
        self.reservar()
        self.lead()
        self.app.state.avisos.despachar()
        self.assertEqual(len(publicados), 1)
        canales = sorted((e[0], e[1]) for e in self.envios())
        self.assertIn(("solicitud_recibida", "whatsapp"), canales)
        self.assertNotIn(("reserva_confirmada", "whatsapp"), canales)

    def test_fallo_se_reintenta_y_se_ve_como_reintentando(self):
        self.correo.fallar = 1
        self.crear_solicitud()
        envios = self.cliente.get("/hotel/avisos/configuracion").json()["envios"]
        self.assertEqual((envios[0]["estado"], envios[0]["intentos"]), ("reintentando", 1))
        self.assertEqual(envios[0]["detalle"], "El servidor de correo no respondió a tiempo.")
        self.assertEqual(envios[0]["nombre"], "Nueva solicitud de reserva")
        self.app.state.avisos.despachar()
        envios = self.cliente.get("/hotel/avisos/configuracion").json()["envios"]
        self.assertEqual((envios[0]["estado"], envios[0]["intentos"], envios[0]["destinatarios"]),
                         ("enviado", 2, ["admin@hotel.test"]))
        self.correo.fallar = 100
        self.reservar()
        for _ in range(MAX_INTENTOS + 1):
            self.app.state.avisos.despachar()
        envios = self.cliente.get("/hotel/avisos/configuracion").json()["envios"]
        self.assertEqual((envios[0]["estado"], envios[0]["intentos"]), ("fallido", MAX_INTENTOS))

    # --- resumen diario -----------------------------------------------------------
    def test_resumen_diario_una_vez_por_fecha_y_en_horario(self):
        self.crear_solicitud()
        self.reservar()  # Llegada mañana: no cuenta para hoy
        zona = avisos.ZONA_HOTEL
        hoy = avisos.ahora_hotel().date()
        temprano = datetime(hoy.year, hoy.month, hoy.day, 7, 30, tzinfo=zona)
        a_las_ocho = datetime(hoy.year, hoy.month, hoy.day, 8, 1, tzinfo=zona)
        tarde = datetime(hoy.year, hoy.month, hoy.day, 15, 0, tzinfo=zona)
        with psycopg.connect(URL_TEST) as conexion:
            self.assertFalse(avisos.programar_resumen(conexion, EMPRESA, temprano))
            self.assertFalse(avisos.programar_resumen(conexion, EMPRESA, tarde))
            self.assertTrue(avisos.programar_resumen(conexion, EMPRESA, a_las_ocho))
            self.assertFalse(avisos.programar_resumen(conexion, EMPRESA, a_las_ocho + timedelta(minutes=5)))
            conexion.commit()
        resumen = self.eventos("resumen_diario")
        self.assertEqual(len(resumen), 1)
        self.assertEqual(resumen[0][1], f"{EMPRESA}:{hoy.isoformat()}")
        datos = resumen[0][2]
        self.assertEqual((datos["fecha"], datos["llegadas"], datos["salidas"], datos["solicitudes_pendientes"]),
                         (hoy.isoformat(), [], [], 1))
        self.app.state.avisos.despachar()
        asuntos = [m.asunto for _, _, m in self.correo.enviados]
        self.assertIn(f"[Hotel Herencia] Resumen del {hoy.strftime('%d/%m/%Y')}: 0 Llegadas, 0 Salidas, 1 solicitud pendiente", asuntos)

    def test_resumen_apagado_o_vencido(self):
        self.cliente.put("/hotel/avisos/preferencias", json={"preferencias": [
            {"tipo": "resumen_diario", "activo": False, "destinatarios": []}]}, headers={"Idempotency-Key": self.clave()})
        hoy = avisos.ahora_hotel().date()
        ocho = datetime(hoy.year, hoy.month, hoy.day, 9, 0, tzinfo=avisos.ZONA_HOTEL)
        with psycopg.connect(URL_TEST) as conexion:
            self.assertFalse(avisos.programar_resumen(conexion, EMPRESA, ocho))
            ayer = hoy - timedelta(days=1)
            avisos.registrar_evento(conexion, "resumen_diario", f"{EMPRESA}:{ayer}", {"fecha": ayer.isoformat()}, EMPRESA)
            conexion.commit()
        self.cliente.put("/hotel/avisos/preferencias", json={"preferencias": [
            {"tipo": "resumen_diario", "activo": True, "destinatarios": []}]}, headers={"Idempotency-Key": self.clave()})
        self.app.state.avisos.despachar()
        self.assertEqual(self.envios()[0][2], "omitido")
        self.assertIn("otro día", self.envios()[0][4])

    def test_resumen_cuenta_llegadas_y_salidas_de_hoy(self):
        hoy = avisos.ahora_hotel().date()
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute(
                "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, estado, personas, "
                "tarifa_noche_aceptada_clp) VALUES "
                "('RSV-L', %s, 'HAB-SINT-101', %s, %s, 'Oculta', 'confirmada', 2, 50000), "
                "('RSV-S', %s, 'HAB-SINT-102', %s, %s, 'Oculta', 'en_estadia', 1, 50000)",
                (EMPRESA, hoy, hoy + timedelta(days=2), EMPRESA, hoy - timedelta(days=3), hoy))
            datos = avisos.datos_resumen(conexion, EMPRESA, hoy)
            conexion.rollback()
        self.assertEqual(datos["llegadas"], [{"habitacion_id": "HAB-SINT-101", "noches": 2, "personas": 2}])
        self.assertEqual(datos["salidas"], [{"habitacion_id": "HAB-SINT-102", "noches": 3, "personas": 1}])
        texto = avisos.componer({"tipo": "resumen_diario", "referencia": "x", "datos": datos}, FRONT).texto
        self.assertIn("- HAB-SINT-101 · 2 noches · 2 personas", texto)
        self.assertNotIn("Oculta", texto)

    # --- correo de prueba ------------------------------------------------------------
    def test_correo_de_prueba(self):
        sin_canal = self.usar()
        r = self.cliente.post("/hotel/avisos/prueba").json()
        self.assertFalse(r["ok"])
        self.assertIn("buzón de envío", r["detalle"])
        self.usar(self.correo)
        self.cliente.put("/hotel/avisos/preferencias", json={"preferencias": [
            {"tipo": "solicitud_recibida", "activo": True, "destinatarios": ["a@hotel.test"]},
            {"tipo": "pago_registrado", "activo": True, "destinatarios": ["b@hotel.test", "a@hotel.test"]},
            {"tipo": "consulta_recibida", "activo": False, "destinatarios": ["apagado@hotel.test"]},
        ]}, headers={"Idempotency-Key": self.clave()})
        r = self.cliente.post("/hotel/avisos/prueba").json()
        self.assertTrue(r["ok"], r)
        # los avisos sin lista propia llegan al correo por defecto: también reciben la prueba
        self.assertEqual(r["destinatarios"], ["a@hotel.test", "admin@hotel.test", "b@hotel.test"])
        self.assertTrue(self.correo.enviados[-1][2].asunto.startswith("[Hotel Herencia] Correo de prueba"))
        envios = self.cliente.get("/hotel/avisos/configuracion").json()["envios"]
        self.assertEqual((envios[0]["tipo"], envios[0]["estado"]), ("prueba", "enviado"))
        # una prueba fallida no queda reintentándose
        self.correo.fallar = 1
        r = self.cliente.post("/hotel/avisos/prueba").json()
        self.assertFalse(r["ok"])
        self.assertEqual(r["detalle"], "El servidor de correo no respondió a tiempo.")
        envios = self.cliente.get("/hotel/avisos/configuracion").json()["envios"]
        self.assertEqual(envios[0]["estado"], "fallido")
        antes = len(self.correo.enviados)
        self.app.state.avisos.despachar()
        self.assertEqual(len(self.correo.enviados), antes)
        del sin_canal


class ContenidoCorreoTest(unittest.TestCase):
    def evento(self, tipo, datos, referencia="REF-1"):
        return {"id": "AVI-1", "tipo": tipo, "referencia": referencia, "datos": datos}

    def test_texto_y_html_legibles_con_asunto_de_marca(self):
        mensajes = []
        CanalCorreo("smtp.test", 587, None, None, "avisos@hotel.test", "a@hotel.test, b@hotel.test", FRONT,
                    enviar_smtp=mensajes.append).enviar(self.evento(
                        "solicitud_recibida", {"tipo": "doble_superior", "inicio": "2026-12-01", "fin": "2026-12-04",
                                               "personas": 2, "origen": "web"}, "SOL-9"))
        m = mensajes[0]
        self.assertEqual(m["To"], "a@hotel.test, b@hotel.test")
        self.assertEqual(m["Subject"], "[Hotel Herencia] Nueva solicitud de reserva: Doble superior · Llegada 01/12/2026")
        texto = m.get_body(("plain",)).get_content()
        html = m.get_body(("html",)).get_content()
        for linea in ("Llegada: 01/12/2026", "Salida: 04/12/2026", "Noches: 3", "Personas: 2",
                      f"{FRONT}/hotel/solicitudes?id=SOL-9"):
            self.assertIn(linea, texto)
        self.assertIn('name="viewport"', html)
        self.assertIn("max-width:560px", html)
        self.assertIn(f'href="{FRONT}/hotel/solicitudes?id=SOL-9"', html)

    def test_html_escapa_valores(self):
        m = avisos.componer(self.evento("reserva_confirmada", {"habitacion_id": "<b>HAB</b>", "inicio": "2026-12-01",
                                                               "fin": "2026-12-02", "total_clp": 1234567}), FRONT)
        self.assertNotIn("<b>HAB</b>", m.html)
        self.assertIn("&lt;b&gt;HAB&lt;/b&gt;", m.html)
        self.assertIn("Total (IVA incluido): $1.234.567", m.texto)

    def test_pago_y_consulta(self):
        pago = avisos.componer(self.evento("pago_registrado", {"reserva_id": "RSV-1", "monto_clp": 85000,
                                                               "tipo_pago": "total", "saldo_despues_clp": 0}), FRONT)
        self.assertEqual(pago.asunto, "[Hotel Herencia] Pago registrado: $85.000 · reserva RSV-1")
        self.assertIn("Tipo: Pago total (cuenta saldada)", pago.texto)
        self.assertIn("Saldo pendiente: $0", pago.texto)
        self.assertEqual(pago.enlace, f"{FRONT}/hotel/reservas/RSV-1")
        consulta = avisos.componer(self.evento("consulta_recibida", {"inicio": None, "personas": None,
                                                                     "con_mensaje": False}, "LEAD-1"), FRONT)
        self.assertEqual(consulta.asunto, "[Hotel Herencia] Nueva consulta desde la web")
        self.assertIn("Trae mensaje: No", consulta.texto)

    def test_buzon_recibe_destinatarios_y_html(self):
        llamadas = []

        class BuzonFalso:
            parametros = {"destino": "buzon@hotel.test"}

            def enviar(self, asunto, cuerpo, destinos=None, html=None):
                llamadas.append((asunto, destinos, bool(html)))

        destinos = CanalBuzon(BuzonFalso(), FRONT).enviar(
            {**self.evento("pago_registrado", {"reserva_id": "RSV-1", "monto_clp": 1}), "destinos": ["x@hotel.test"]})
        self.assertEqual(destinos, ["x@hotel.test"])
        self.assertEqual(llamadas[0][1:], (["x@hotel.test"], True))

    def test_buzon_smtp_multiparte_a_varios(self):
        from servicio import correo

        class SmtpFalso:
            def __init__(self):
                self.mensajes = []

            def login(self, u, c):
                pass

            def send_message(self, m):
                self.mensajes.append(m)

            def quit(self):
                pass

        falso = SmtpFalso()
        buzon = correo.Buzon("BZN-1", "avisos", "envio_avisos", "smtp",
                             {"host": "h", "puerto": 587, "seguridad": "starttls", "usuario": "a@hotel.test",
                              "autenticacion": "clave", "remitente": "a@hotel.test", "destino": "admin@hotel.test"},
                             {"clave": "x"}, smtp_fabrica=lambda p: falso)
        buzon.enviar("asunto", "texto", destinos=["uno@hotel.test", "dos@hotel.test"], html="<p>hola</p>")
        m = falso.mensajes[0]
        self.assertEqual(m["To"], "uno@hotel.test, dos@hotel.test")
        self.assertTrue(m.is_multipart())
        buzon.enviar("asunto", "texto")
        self.assertEqual(falso.mensajes[1]["To"], "admin@hotel.test")

    def test_graph_envia_html_a_todos(self):
        from servicio import correo

        enviados = []

        def http(metodo, url, cab, cuerpo):
            if "oauth2" in url:
                return {"access_token": "t"}
            enviados.append(cuerpo)
            return {}

        buzon = correo.Buzon("BZN-2", "avisos", "envio_avisos", "microsoft_graph",
                             {"tenant_id": "t", "client_id": "c", "usuario": "m@hotel.test", "remitente": "m@hotel.test",
                              "destino": "admin@hotel.test"}, {"client_secret": "s"}, http=http)
        buzon.enviar("asunto", "texto", destinos=["uno@hotel.test", "dos@hotel.test"], html="<p>hola</p>")
        import json
        cuerpo = json.loads(enviados[0])
        self.assertEqual(cuerpo["message"]["body"]["contentType"], "HTML")
        self.assertEqual(len(cuerpo["message"]["toRecipients"]), 2)

    def test_lista_de_correos_y_detalle_legible(self):
        self.assertEqual(avisos.correos_desde_texto("A@x.cl; b@x.cl,malo"), ["a@x.cl", "b@x.cl"])
        self.assertIn("usuario o la clave", avisos.detalle_legible("SMTPAuthenticationError: (535, b'bad')"))
        self.assertIsNone(avisos.detalle_legible(None))
        self.assertEqual(avisos.detalle_legible("omitido: aviso apagado"), "aviso apagado")

    def test_config_de_entorno_sin_destino_igual_enciende_el_smtp(self):
        from servicio.configuracion import Configuracion

        config = Configuracion(host="h", puerto=0, database_url=None, cookie_segura=False, origen_front=None,
                               admin_usuario=None, admin_clave=None, smtp_host="smtp.test",
                               smtp_remitente="avisos@hotel.test", admin_email="dueno@hotel.test")
        canales = avisos.canales_desde_config(config)
        self.assertEqual([c.nombre for c in canales], ["correo"])
        self.assertEqual(avisos.destinos_defecto_desde_config(config), ["dueno@hotel.test"])


if __name__ == "__main__":
    unittest.main()
