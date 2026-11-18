"""#355 (2026-11-18): servidores de correo configurables desde la plataforma
y lead «contactado» automático cuando el hotel ya le escribió.

Decisión del propietario: cualquier servidor (IMAP/SMTP con clave u OAuth2,
API de Gmail, Microsoft Graph), todo parametrizado en Configuración;
revisión cada 15 minutos; la nota registra el buzón, no la persona.
Sin red: proveedores con dobles de prueba.
"""
import json
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
from cryptography.fernet import Fernet

from servicio import correo
from servicio.avisos import CanalBuzon, Despachador
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests.test_leads import LeadsBaseTest, URL_TEST

AHORA = datetime.now(timezone.utc)


def imap_cuerpo(**extra):
    return {"etiqueta": "reservas", "proposito": "lectura_enviados", "proveedor": "imap",
            "parametros": {"host": "imap.hotel.test", "usuario": "reservas@hotel.test", **extra},
            "secretos": {"clave": "clave-de-aplicacion"}}


class ImapFalso:
    """Doble de imaplib: registra los comandos para comprobar que solo se
    piden cabeceras (destinatarios y fecha), nunca el cuerpo."""

    def __init__(self, mensajes, carpetas=None):
        self.mensajes = mensajes
        self.carpetas = carpetas or [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren \\Sent) "/" "Enviados"']
        self.comandos = []

    def login(self, usuario, clave):
        self.comandos.append(("login", usuario))

    def authenticate(self, mecanismo, fn):
        self.comandos.append(("authenticate", mecanismo, fn(b"")))

    def list(self):
        return "OK", self.carpetas

    def select(self, carpeta, readonly=False):
        self.comandos.append(("select", carpeta, readonly))
        return "OK", [b"1"]

    def uid(self, comando, *args):
        self.comandos.append(("uid", comando) + args)
        if comando == "SEARCH":
            return "OK", [b" ".join(str(i + 1).encode() for i in range(len(self.mensajes)))]
        partes = []
        for i, (fecha, para) in enumerate(self.mensajes):
            cab = f"Date: {fecha.strftime('%a, %d %b %Y %H:%M:%S +0000')}\r\nTo: {para}\r\n\r\n".encode()
            partes += [(f"{i + 1} (UID {i + 1} BODY[HEADER.FIELDS (DATE TO CC BCC)] {{{len(cab)}}}".encode(), cab), b")"]
        return "OK", partes

    def logout(self):
        pass


class HttpFalso:
    def __init__(self, respuestas):
        self.respuestas = respuestas  # lista de (fragmento de URL, respuesta)
        self.llamadas = []

    def __call__(self, metodo, url, cabeceras, cuerpo):
        self.llamadas.append((metodo, url, cabeceras, cuerpo))
        for fragmento, respuesta in self.respuestas:
            if fragmento in url:
                return respuesta
        raise AssertionError(f"URL no esperada: {url}")


class CorreoConfigTest(LeadsBaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._clave_previa = os.environ.get("CORREO_CLAVE_CIFRADO")
        os.environ["CORREO_CLAVE_CIFRADO"] = Fernet.generate_key().decode()

    @classmethod
    def tearDownClass(cls):
        if cls._clave_previa is None:
            os.environ.pop("CORREO_CLAVE_CIFRADO", None)
        else:
            os.environ["CORREO_CLAVE_CIFRADO"] = cls._clave_previa
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("TRUNCATE buzones_correo, contactos CASCADE")
            conexion.execute("DELETE FROM ajustes WHERE clave = 'revision_correo'")
            conexion.commit()
        self.app.state.correo_fabrica = None

    def tearDown(self):
        self.app.state.correo_fabrica = None
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("TRUNCATE buzones_correo")
            conexion.commit()

    def idem(self):
        return {"Idempotency-Key": f"c-{uuid.uuid4().hex[:10]}"}

    def crear_buzon(self, cuerpo):
        return self.cliente.post("/hotel/correo/buzones", json=cuerpo, headers=self.idem())

    # --- configuración ---------------------------------------------------
    def test_alta_imap_con_defectos_y_secreto_cifrado_nunca_expuesto(self):
        r = self.crear_buzon(imap_cuerpo())
        self.assertEqual(r.status_code, 201, r.text)
        b = r.json()
        self.assertEqual((b["parametros"]["seguridad"], b["parametros"]["puerto"]), ("ssl", 993))
        self.assertEqual(b["secretos_guardados"], ["clave"])
        listado = self.cliente.get("/hotel/correo/buzones")
        self.assertNotIn("clave-de-aplicacion", listado.text)
        self.assertTrue(listado.json()["cifrado_disponible"])
        self.assertEqual(listado.json()["revision"], {"activo": True, "intervalo_minutos": 15, "registrar_buzon": True})
        with psycopg.connect(URL_TEST) as conexion:
            crudo = conexion.execute("SELECT secretos_cifrados::text FROM buzones_correo").fetchone()[0]
            huellas = conexion.execute("SELECT cuerpo_respuesta::text FROM claves_idempotencia").fetchall()
        self.assertNotIn("clave-de-aplicacion", crudo)
        self.assertNotIn("clave-de-aplicacion", str(huellas))

    def test_editar_conserva_secreto_omitido_y_valida(self):
        bid = self.crear_buzon(imap_cuerpo()).json()["buzon_id"]
        r = self.cliente.put(f"/hotel/correo/buzones/{bid}", headers=self.idem(), json={
            "etiqueta": "reservas", "proveedor": "imap",
            "parametros": {"host": "mail.hotel.test", "usuario": "reservas@hotel.test", "seguridad": "starttls"}})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["parametros"]["puerto"], r.json()["secretos_guardados"]), (143, ["clave"]))
        # borrar la clave obligatoria → 422
        r = self.cliente.put(f"/hotel/correo/buzones/{bid}", headers=self.idem(), json={
            "etiqueta": "reservas", "proveedor": "imap", "parametros": {"host": "h.test", "usuario": "u"},
            "secretos": {"clave": None}})
        self.assertEqual(r.status_code, 422)
        for malo in (imap_cuerpo(seguridad="tls9"), imap_cuerpo(puerto=70000), {**imap_cuerpo(), "proveedor": "smtp"},
                     {**imap_cuerpo(), "parametros": {"host": "h", "usuario": "u", "otro": 1}},
                     {**imap_cuerpo(), "secretos": {}}):
            with self.subTest(malo=malo):
                self.assertEqual(self.crear_buzon(malo).status_code, 422)

    def test_sin_clave_de_cifrado_no_guarda_secretos(self):
        previa = os.environ.pop("CORREO_CLAVE_CIFRADO")
        try:
            r = self.crear_buzon(imap_cuerpo())
            self.assertEqual(r.status_code, 409)
            self.assertIn("CORREO_CLAVE_CIFRADO", r.json()["detail"])
            self.assertFalse(self.cliente.get("/hotel/correo/buzones").json()["cifrado_disponible"])
        finally:
            os.environ["CORREO_CLAVE_CIFRADO"] = previa

    def test_proveedores_y_autenticaciones_validas(self):
        casos = [
            {"etiqueta": "comercial", "proposito": "lectura_enviados", "proveedor": "imap",
             "parametros": {"host": "imap.gmail.com", "usuario": "c@hotel.test", "autenticacion": "oauth2", "client_id": "cid"},
             "secretos": {"client_secret": "s", "refresh_token": "r"}},
            {"etiqueta": "workspace", "proposito": "lectura_enviados", "proveedor": "gmail_api",
             "parametros": {"usuario": "w@hotel.test", "autenticacion": "oauth2", "client_id": "cid"},
             "secretos": {"client_secret": "s", "refresh_token": "r"}},
            {"etiqueta": "m365", "proposito": "lectura_enviados", "proveedor": "microsoft_graph",
             "parametros": {"tenant_id": "t", "client_id": "c", "usuario": "m@hotel.test"}, "secretos": {"client_secret": "s"}},
            {"etiqueta": "avisos", "proposito": "envio_avisos", "proveedor": "smtp",
             "parametros": {"host": "smtp.hotel.test", "usuario": "avisos@hotel.test", "destino": "admin@hotel.test"},
             "secretos": {"clave": "x"}},
        ]
        for cuerpo in casos:
            with self.subTest(etiqueta=cuerpo["etiqueta"]):
                r = self.crear_buzon(cuerpo)
                self.assertEqual(r.status_code, 201, r.text)
        b = {x["etiqueta"]: x for x in self.cliente.get("/hotel/correo/buzones").json()["buzones"]}
        self.assertEqual(b["comercial"]["parametros"]["token_url"], correo.TOKEN_URL_GOOGLE)
        self.assertEqual((b["avisos"]["parametros"]["puerto"], b["avisos"]["parametros"]["remitente"]), (587, "avisos@hotel.test"))
        # cuenta de servicio con JSON inválido → 422
        r = self.crear_buzon({"etiqueta": "sa", "proposito": "lectura_enviados", "proveedor": "gmail_api",
                              "parametros": {"usuario": "w@hotel.test", "autenticacion": "cuenta_servicio"},
                              "secretos": {"cuenta_servicio_json": "{}"}})
        self.assertEqual(r.status_code, 422)

    def test_permisos(self):
        self.assertEqual(self.anonima.get("/hotel/correo/buzones").status_code, 401)
        r = self.cliente.post("/usuarios", json={"nombre": "recep-c", "rol": "recepcion", "clave": "clave-recep-1"},
                              headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        from fastapi.testclient import TestClient
        recep = TestClient(self.app)
        self.assertEqual(recep.post("/sesion", json={"usuario": "recep-c", "clave": "clave-recep-1"}).status_code, 200)
        self.assertEqual(recep.get("/hotel/correo/buzones").status_code, 403)
        self.assertEqual(recep.post("/hotel/correo/revision").status_code, 403)

    # --- proveedores (sin red) -------------------------------------------
    def test_imap_lee_solo_cabeceras_de_la_carpeta_sent(self):
        falso = ImapFalso([(AHORA - timedelta(hours=1), "Ana <ana@example.test>"),
                           (AHORA - timedelta(days=9), "viejo@example.test")])
        buzon = correo.Buzon("BZN-1", "reservas", "lectura_enviados", "imap",
                             {"host": "h", "puerto": 993, "seguridad": "ssl", "usuario": "u", "autenticacion": "clave"},
                             {"clave": "x"}, imap_fabrica=lambda p: falso)
        enviados = buzon.enviados_desde(AHORA - timedelta(days=2))
        self.assertEqual([e.destinatarios for e in enviados], [["ana@example.test"]])
        self.assertIn(("select", '"Enviados"', True), falso.comandos)
        fetch = [c for c in falso.comandos if c[:2] == ("uid", "FETCH")][0]
        self.assertEqual(fetch[3], "(BODY.PEEK[HEADER.FIELDS (DATE TO CC BCC)])")

    def test_imap_oauth2_xoauth2_y_carpeta_por_nombre(self):
        falso = ImapFalso([], carpetas=[b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren) "/" "[Gmail]/Sent Mail"'])
        http = HttpFalso([("oauth2.googleapis.com/token", {"access_token": "AT"})])
        buzon = correo.Buzon("BZN-2", "comercial", "lectura_enviados", "imap",
                             {"host": "h", "puerto": 993, "seguridad": "ssl", "usuario": "c@hotel.test",
                              "autenticacion": "oauth2", "client_id": "cid", "token_url": correo.TOKEN_URL_GOOGLE},
                             {"client_secret": "s", "refresh_token": "r"}, http=http, imap_fabrica=lambda p: falso)
        buzon.enviados_desde(AHORA - timedelta(days=1))
        self.assertEqual(falso.comandos[0], ("authenticate", "XOAUTH2", b"user=c@hotel.test\x01auth=Bearer AT\x01\x01"))
        self.assertIn(("select", '"[Gmail]/Sent Mail"', True), falso.comandos)

    def test_gmail_api_cuenta_servicio_alcance_metadata(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        pem = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
        cuenta = json.dumps({"client_email": "sa@proyecto.iam.test", "private_key": pem})
        ms = int((AHORA - timedelta(hours=2)).timestamp() * 1000)
        http = HttpFalso([
            ("oauth2.googleapis.com/token", {"access_token": "AT"}),
            ("/messages?", {"messages": [{"id": "m1"}]}),
            ("/messages/m1?", {"internalDate": str(ms), "payload": {"headers": [{"name": "To", "value": "ana@example.test"}]}}),
        ])
        buzon = correo.Buzon("BZN-3", "ws", "lectura_enviados", "gmail_api",
                             {"usuario": "w@hotel.test", "autenticacion": "cuenta_servicio"},
                             {"cuenta_servicio_json": cuenta}, http=http)
        enviados = buzon.enviados_desde(AHORA - timedelta(days=1))
        self.assertEqual(enviados[0].destinatarios, ["ana@example.test"])
        asercion = http.llamadas[0][3].decode()
        import base64
        carga = asercion.split("assertion=")[1].split(".")[1]
        carga = json.loads(base64.urlsafe_b64decode(carga + "=" * (-len(carga) % 4)))
        self.assertEqual((carga["sub"], carga["scope"]), ("w@hotel.test", "https://www.googleapis.com/auth/gmail.metadata"))
        self.assertIn("format=metadata", http.llamadas[2][1])

    def test_microsoft_graph_solo_campos_de_destinatarios(self):
        http = HttpFalso([
            ("login.microsoftonline.com", {"access_token": "AT"}),
            ("mailFolders/sentitems", {"value": [{"sentDateTime": AHORA.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                  "toRecipients": [{"emailAddress": {"address": "Ana@Example.test"}}]}]}),
        ])
        buzon = correo.Buzon("BZN-4", "m365", "lectura_enviados", "microsoft_graph",
                             {"tenant_id": "t", "client_id": "c", "usuario": "m@hotel.test"}, {"client_secret": "s"}, http=http)
        self.assertEqual(buzon.enviados_desde(AHORA - timedelta(days=1))[0].destinatarios, ["ana@example.test"])
        self.assertIn("%24select=sentDateTime%2CtoRecipients%2CccRecipients%2CbccRecipients", http.llamadas[1][1])

    def test_smtp_envio_con_clave(self):
        class SmtpFalso:
            def __init__(self):
                self.hechos = []

            def login(self, u, c):
                self.hechos.append(("login", u))

            def send_message(self, m):
                self.hechos.append(("send", m["To"], m["Subject"]))

            def quit(self):
                pass

        falso = SmtpFalso()
        buzon = correo.Buzon("BZN-5", "avisos", "envio_avisos", "smtp",
                             {"host": "h", "puerto": 587, "seguridad": "starttls", "usuario": "a@hotel.test",
                              "autenticacion": "clave", "remitente": "a@hotel.test", "destino": "admin@hotel.test"},
                             {"clave": "x"}, smtp_fabrica=lambda p: falso)
        CanalBuzon(buzon, "https://front.test").enviar(
            {"id": "AVI-1", "tipo": "solicitud_recibida", "referencia": "SOL-1",
             "datos": {"tipo": "doble", "inicio": "2026-12-01", "fin": "2026-12-03", "personas": 2, "origen": "web"}})
        self.assertEqual(falso.hechos[0], ("login", "a@hotel.test"))
        self.assertEqual(falso.hechos[1][1], "admin@hotel.test")

    def test_buzon_de_envio_reemplaza_al_smtp_de_entorno(self):
        class CanalEntorno:
            nombre = "correo"
        r = self.crear_buzon({"etiqueta": "avisos", "proposito": "envio_avisos", "proveedor": "smtp",
                              "parametros": {"host": "smtp.hotel.test", "usuario": "a@hotel.test", "destino": "x@hotel.test"},
                              "secretos": {"clave": "x"}})
        self.assertEqual(r.status_code, 201, r.text)
        despachador = Despachador([CanalEntorno()], URL_TEST)
        with psycopg.connect(URL_TEST) as conexion:
            canales = despachador.canales_vigentes(conexion)
        self.assertEqual(len(canales), 1)
        self.assertIsInstance(canales[0], CanalBuzon)

    # --- revisión → lead contactado ---------------------------------------
    def fabrica_con(self, enviados_por_etiqueta, fallar=()):
        def fabrica(fila):
            etiqueta = fila[1]

            class Doble:
                def enviados_desde(self, desde):
                    if etiqueta in fallar:
                        raise ConnectionError("servidor caído")
                    return enviados_por_etiqueta.get(etiqueta, [])
            return Doble()
        return fabrica

    def test_revision_marca_contactado_con_nota_del_buzon_y_es_reversible(self):
        self.assertEqual(self.crear_buzon(imap_cuerpo()).status_code, 201)
        con_respuesta = self.crear_lead(correo="Ana@Example.test")
        sin_respuesta = self.crear_lead(correo="otro@example.test")
        despues = datetime.now(timezone.utc) + timedelta(seconds=5)
        antes = datetime.now(timezone.utc) - timedelta(days=1)
        self.app.state.correo_fabrica = self.fabrica_con({"reservas": [
            correo.Enviado(despues, ["ana@example.test"]),
            correo.Enviado(antes, ["otro@example.test"]),  # anterior al lead: no cuenta
        ]})
        r = self.cliente.post("/hotel/correo/revision")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["leads_contactados"], 1)
        with psycopg.connect(URL_TEST) as conexion:
            filas = dict(conexion.execute("SELECT id, estado || '|' || coalesce(nota, '') || '|' || coalesce(gestion_por, '') "
                                          "FROM leads").fetchall())
        estado, nota, autor = filas[con_respuesta].split("|")
        self.assertEqual((estado, autor), ("contactado", "auto:correo"))
        self.assertTrue(nota.startswith("auto: correo enviado desde reservas el "))
        self.assertTrue(filas[sin_respuesta].startswith("nuevo|"))
        # reversible a mano
        d = self.cliente.post(f"/hotel/leads/{con_respuesta}/estado", json={"estado": "nuevo"}, headers=self.idem())
        self.assertEqual(d.status_code, 200, d.text)
        # un contactado manual no vuelve a nuevo
        m = self.cliente.post(f"/hotel/leads/{sin_respuesta}/estado", json={"estado": "contactado", "nota": "llamé"},
                              headers=self.idem())
        self.assertEqual(m.status_code, 200, m.text)
        self.assertEqual(self.cliente.post(f"/hotel/leads/{sin_respuesta}/estado", json={"estado": "nuevo"},
                                           headers=self.idem()).status_code, 409)
        buzon = self.cliente.get("/hotel/correo/buzones").json()["buzones"][0]
        self.assertIn("1 lead(s) marcado(s)", buzon["ultimo_resultado"])
        self.assertIsNotNone(buzon["revisado_hasta"])

    def test_sin_registrar_buzon_y_fallo_aislado(self):
        self.assertEqual(self.crear_buzon(imap_cuerpo()).status_code, 201)
        self.assertEqual(self.crear_buzon({**imap_cuerpo(), "etiqueta": "comercial"}).status_code, 201)
        self.assertEqual(self.cliente.put("/hotel/ajustes/revision_correo", json={"registrar_buzon": False},
                                          headers=self.idem()).status_code, 200)
        lead = self.crear_lead(correo="bea@example.test")
        self.app.state.correo_fabrica = self.fabrica_con(
            {"comercial": [correo.Enviado(datetime.now(timezone.utc) + timedelta(seconds=5), ["bea@example.test"])]},
            fallar=("reservas",))
        r = self.cliente.post("/hotel/correo/revision").json()
        self.assertEqual((r["buzones"], r["errores"], r["leads_contactados"]), (2, 1, 1))
        with psycopg.connect(URL_TEST) as conexion:
            nota = conexion.execute("SELECT nota FROM leads WHERE id = %s", (lead,)).fetchone()[0]
        self.assertTrue(nota.startswith("auto: correo enviado el "))
        b = {x["etiqueta"]: x for x in self.cliente.get("/hotel/correo/buzones").json()["buzones"]}
        self.assertIn("servidor caído", b["reservas"]["ultimo_error"])
        self.assertIsNone(b["comercial"]["ultimo_error"])

    def test_prueba_de_conexion(self):
        bid = self.crear_buzon(imap_cuerpo()).json()["buzon_id"]
        self.app.state.correo_fabrica = lambda fila: type("D", (), {"probar": lambda self: {"ok": True, "detalle": "conexión correcta: 3"}})()
        r = self.cliente.post(f"/hotel/correo/buzones/{bid}/prueba")
        self.assertEqual(r.json(), {"ok": True, "detalle": "conexión correcta: 3"})
        self.app.state.correo_fabrica = self.fabrica_con({}, fallar=("reservas",))
        self.app.state.correo_fabrica = lambda fila: type("D", (), {"probar": lambda self: (_ for _ in ()).throw(OSError("rechazado"))})()
        r = self.cliente.post(f"/hotel/correo/buzones/{bid}/prueba")
        self.assertEqual(r.json()["ok"], False)
        self.assertIn("rechazado", r.json()["detalle"])
        self.assertEqual(self.cliente.delete(f"/hotel/correo/buzones/{bid}", headers=self.idem()).status_code, 200)
        self.assertEqual(self.cliente.get("/hotel/correo/buzones").json()["buzones"], [])


if __name__ == "__main__":
    unittest.main()
