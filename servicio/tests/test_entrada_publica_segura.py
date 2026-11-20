"""Endurecimiento del canal público (2026-11-16): lista blanca de parámetros
y cuerpos, normalización de texto, SQL parametrizado frente a cadenas de
inyección, referencia opaca sin filtrarse al log, X-Request-Id propagado y
contadores del canal público. Datos 100 % sintéticos, base dedicada."""
import io
import json
import logging

import psycopg

from servicio import entrada_publica, observabilidad
from servicio.tests.test_leads import EN_3, MANANA, URL_TEST, LeadsBaseTest

XSS = '<script>alert(1)</script>'
SQLI = "Robert'); DROP TABLE leads;--"


class EntradaPublicaSeguraTest(LeadsBaseTest):
    def lead(self, **cambios):
        cuerpo = {"nombre": "Ana Sintética", "correo": "ana@example.test", "telefono": "+56 9 1111 2222",
                  "huespedes": 2, "check_in": MANANA.isoformat(), "check_out": EN_3.isoformat(), "mensaje": None}
        cuerpo.update(cambios)
        return self.anonima.post("/publico/leads", json=cuerpo, headers={"Idempotency-Key": self.clave()})

    def test_limpiar_texto_nfc_controles_y_bidi(self):
        self.assertEqual(entrada_publica.limpiar_texto("  Jose\u0301 \u202eX\u0000\u200b  Y "), "José X Y")
        self.assertEqual(entrada_publica.limpiar_texto("a\r\nb\tc"), "a b c")
        self.assertEqual(entrada_publica.limpiar_texto("a\r\nb", multilinea=True), "a\nb")
        self.assertFalse(entrada_publica.telefono_con_formato("<b>912345678</b>"))
        self.assertTrue(entrada_publica.telefono_con_formato("+56 (9) 1234-5678"))

    def test_sqli_y_html_se_guardan_como_texto_literal(self):
        r = self.lead(nombre=SQLI, mensaje=XSS + "\r\nhola")
        self.assertEqual(r.status_code, 201, r.text)
        with psycopg.connect(URL_TEST) as conexion:
            fila = conexion.execute(
                "SELECT nombre, mensaje FROM leads WHERE token_consulta = %s", (r.json()["referencia"],)
            ).fetchone()
            self.assertEqual(fila, (SQLI, XSS + "\nhola"))
            self.assertEqual(conexion.execute("SELECT count(*) FROM leads").fetchone()[0], 1)

    def test_lead_normaliza_correo_y_nombre(self):
        r = self.lead(nombre="  Jose\u0301\u0000 Pérez ", correo="Ana@Example.TEST")
        self.assertEqual(r.status_code, 201, r.text)
        datos = self.anonima.get(f"/publico/referencia?token={r.json()['referencia']}").json()
        self.assertEqual((datos["nombre"], datos["correo"]), ("José Pérez", "ana@example.test"))
        self.assertNotIn("telefono", datos)
        self.assertNotIn("mensaje", datos)

    def test_lead_rechaza_campos_ajenos_y_formatos_invalidos(self):
        for cambios in (
            {"admin": True},
            {"telefono": "+56 9 1234 abcd"},
            {"telefono": "<b>912345678</b>"},
            {"nombre": "x" * 201},
            {"correo": "sin-arroba"},
            {"check_in": "2026-02-31"},
            {"check_in": "<img src=x>"},
            {"huespedes": 31},
            {"mensaje": "x" * 2001},
        ):
            with self.subTest(cambios=cambios):
                self.assertEqual(self.lead(**cambios).status_code, 422)

    def test_referencia_rechaza_inyeccion_y_parametros_extra(self):
        for consulta in (
            "token=' OR 1=1 --xxxxxxxxxxxxxx",
            "token=%3Cscript%3Ealert(1)%3C%2Fscript%3Exxxxxxx",
            "token=" + "A" * 129,
            "token=corto",
            "token=" + "A" * 30 + "&next=https://evil.example",
        ):
            with self.subTest(consulta=consulta):
                r = self.anonima.get(f"/publico/referencia?{consulta}")
                self.assertEqual(r.status_code, 422, r.text)
                self.assertNotIn("evil", r.text)
                self.assertNotIn("<script>", r.text)
        self.assertEqual(self.anonima.get("/publico/referencia?token=" + "A" * 43).status_code, 404)

    def test_disponibilidad_rechaza_fechas_y_personas_fuera_de_lista_blanca(self):
        for consulta in (
            "inicio=2026-02-31&fin=2026-03-02&personas=2",
            "inicio=%3Cscript%3E&fin=2026-12-02&personas=2",
            f"inicio={MANANA}&fin={EN_3}&personas=99",
            f"inicio={MANANA}&fin={EN_3}&personas=1%20OR%201%3D1",
            f"inicio={EN_3}&fin={MANANA}&personas=2",
            f"inicio={MANANA}&fin={EN_3}&personas=2&ref=x",
        ):
            with self.subTest(consulta=consulta):
                r = self.anonima.get(f"/publico/disponibilidad?{consulta}")
                self.assertIn(r.status_code, (400, 422), r.text)
                self.assertNotIn("<script>", r.text)

    def test_solicitud_rechaza_campos_ajenos_y_normaliza(self):
        oferta = self.anonima.get(
            f"/publico/disponibilidad?inicio={MANANA}&fin={EN_3}&personas=2"
        ).json()
        self.assertIn("capacidad_maxima_habitacion", oferta)
        self.assertIn("capacidad", oferta["oferta"][0])
        # #346: la disponibilidad pública no expone números; la solicitud va por tipo.
        self.assertNotIn("habitacion_id", oferta["oferta"][0])
        base = {"tipo": oferta["oferta"][0]["tipo"], "inicio": MANANA.isoformat(),
                "fin": EN_3.isoformat(), "personas": 2, "huesped_nombre": "Ana\u0000 Sintética",
                "huesped_contacto": "ana@example.test"}
        extra = self.anonima.post("/publico/solicitudes", json={**base, "estado": "confirmada"},
                                  headers={"Idempotency-Key": self.clave()})
        self.assertEqual(extra.status_code, 422)
        r = self.anonima.post("/publico/solicitudes", json=base, headers={"Idempotency-Key": self.clave()})
        self.assertIn(r.status_code, (200, 201), r.text)
        with psycopg.connect(URL_TEST) as conexion:
            nombre = conexion.execute("SELECT huesped_nombre FROM solicitudes").fetchone()[0]
        self.assertEqual(nombre, "Ana Sintética")

    def test_request_id_propagado_y_log_sin_token(self):
        buffer = io.StringIO()
        manejador = logging.StreamHandler(buffer)
        manejador.setFormatter(observabilidad.FormatoJson())
        logger = logging.getLogger("servicio")
        logger.addHandler(manejador)
        try:
            ref = self.lead().json()["referencia"]
            r = self.anonima.get(f"/publico/referencia?token={ref}", headers={"X-Request-Id": "landing-abc123"})
            self.assertEqual(r.headers["X-Request-ID"], "landing-abc123")
            malo = self.anonima.get("/publico/referencia?token=" + "B" * 30, headers={"X-Request-Id": "x\ny"})
            self.assertRegex(malo.headers["X-Request-ID"], r"^[a-f0-9]{16}$")
        finally:
            logger.removeHandler(manejador)
        texto = buffer.getvalue()
        self.assertNotIn(ref, texto)
        self.assertNotIn("ana@example.test", texto)
        eventos = [json.loads(linea) for linea in texto.splitlines() if linea.strip()]
        refs = [e for e in eventos if e.get("evento") == "referencia"]
        self.assertTrue(any(e["resultado"] == "ok" and len(e["ref_hash"]) == 12 for e in refs))
        publicos = [e for e in eventos if e.get("evento") == "publico"]
        self.assertTrue(any(e["request_id"] == "landing-abc123" for e in publicos))

    def test_metricas_publicas_solo_administrador_y_sin_pii(self):
        self.lead()
        self.lead(telefono="abc")
        self.assertEqual(self.anonima.get("/hotel/metricas-publicas").status_code, 401)
        r = self.cliente.get("/hotel/metricas-publicas")
        self.assertEqual(r.status_code, 200, r.text)
        rutas = r.json()["rutas"]
        self.assertGreaterEqual(rutas["/publico/leads"].get("ok", 0), 1)
        self.assertGreaterEqual(rutas["/publico/leads"].get("entrada_rechazada", 0), 1)
        self.assertNotIn("example.test", r.text)

    def test_freno_de_referencia_por_ip(self):
        self.app.state.freno_solicitudes.max_por_minuto = 3
        try:
            estados = [self.anonima.get("/publico/referencia?token=" + "C" * 40).status_code for _ in range(5)]
        finally:
            self.app.state.freno_solicitudes.max_por_minuto = 1000
        self.assertIn(429, estados)
