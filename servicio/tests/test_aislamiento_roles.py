"""Aislamiento entre roles: ningún rol puede saltar a operaciones de otro.

1. Guarda estática: toda ruta que escribe y exige sesión valida el rol en su handler; las únicas
   excepciones están enumeradas aquí (si aparece una ruta nueva sin chequeo, esta prueba falla).
2. Barrido dinámico por rol: aseo y dueño solo llegan a su lista blanca; recepción, caja, dueño y
   aseo reciben 403 en cada operación de administración (precios, usuarios, políticas, stock, correo…).
3. La separación de funciones: administración del hotel no crea usuarios y administración de
   plataforma no cambia precios.
"""
import importlib
import inspect
import os
import pkgutil
import re
import unittest

import psycopg
from fastapi.testclient import TestClient

import servicio.rutas as paquete_rutas
from servicio import migracion, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.rutas import comun

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_aislamiento")
CLAVE = "Clave123!"
ROLES = ["super_admin", "administrador", "admin_hotel", "admin_plataforma", "dueno", "recepcion", "caja", "aseo"]
RX_ROL = re.compile(
    r"exigir_|ROLES_|roles\.(es_|ROLES|con_)|es_admin|\.rol\b|sesion\.rol|permite\(|firma_valida|verify_token|app_secret")

# Escriben con sesión sin chequeo de rol a propósito (se justifica cada una).
SIN_ROL_A_PROPOSITO = {
    ("POST", "/cuenta/2fa"), ("POST", "/cuenta/2fa/activar"), ("DELETE", "/cuenta/2fa"),  # su propia cuenta
    ("POST", "/hotel/sugerencias"),          # buzón de sugerencias: todo el personal
    ("POST", "/hotel/politicas/simulacion"),  # simulación sin escritura
}
PUBLICAS = {
    ("POST", "/sesion"), ("DELETE", "/sesion"), ("POST", "/auth/google/totp"), ("POST", "/publico/solicitudes"),
    ("POST", "/publico/leads"), ("POST", "/publico/asistente"), ("POST", "/mensajeria/whatsapp/webhook"),
}
# Operaciones que solo administración (hotel o plataforma) puede hacer.
SOLO_ADMIN = [
    ("POST", r"^/usuarios$"), ("POST", r"^/usuarios/[^/]+/email$"), ("PUT", r"^/hotel/tipos/[^/]+$"),
    ("POST", r"^/hotel/tipos$"), ("POST", r"^/hotel/precios/excepciones$"),
    ("PUT", r"^/hotel/habitaciones/[^/]+/precio$"), ("POST", r"^/hotel/habitaciones/lote$"),
    ("POST", r"^/hotel/productos/[^/]+/stock$"), ("PUT", r"^/hotel/politicas$"),
    ("POST", r"^/hotel/habitaciones/[^/]+/servicio$"),
]


# Cuerpos válidos donde el esquema mínimo no alcanza: sin ellos un 422 taparía la verificación de rol.
CUERPOS = {
    ("POST", "/usuarios"): {"nombre": "zz_aislamiento", "rol": "recepcion", "clave": "ClaveSegura123!"},
    ("POST", "/usuarios/{usuario_id}/email"): {"email": "zz.aislamiento@example.com"},
}


def _rutas():
    salida = []
    for m in pkgutil.iter_modules(paquete_rutas.__path__):
        router = getattr(importlib.import_module(f"servicio.rutas.{m.name}"), "router", None)
        for r in getattr(router, "routes", []):
            if hasattr(r, "methods"):
                for met in r.methods - {"HEAD", "OPTIONS"}:
                    salida.append((met, r.path, r.endpoint))
    return salida


class GuardaEstaticaTest(unittest.TestCase):
    def test_toda_ruta_que_escribe_valida_rol_o_esta_justificada(self):
        sin_chequeo = set()
        for met, ruta, endpoint in _rutas():
            if met == "GET" or (met, ruta) in PUBLICAS:
                continue
            fuente = inspect.getsource(endpoint)
            if "requerir_sesion" not in fuente and "SesionActiva" not in fuente:
                self.fail(f"{met} {ruta} escribe sin sesión y no está en PUBLICAS")
            if not RX_ROL.search(fuente):
                sin_chequeo.add((met, ruta))
        self.assertEqual(sin_chequeo, SIN_ROL_A_PROPOSITO)


class BarridoPorRolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario="root_t", admin_clave=CLAVE))
        cls.cm = TestClient(cls.app)
        cls.cm.__enter__()
        h = seguridad.hashear_clave(CLAVE)
        with psycopg.connect(URL_TEST) as c:
            c.execute("TRUNCATE sesiones, claves_idempotencia CASCADE")
            for rol in ROLES:
                c.execute(
                    "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                    "(%s, %s, %s, %s, 'EMP-SINTETICA-001', true) ON CONFLICT (id) DO UPDATE SET "
                    "clave_hash = EXCLUDED.clave_hash, rol = EXCLUDED.rol, activo = true, totp_activado = false",
                    (f"USR-AISL-{rol}", f"aisl_{rol}", h, rol))
            c.commit()
        cls.cli = {}
        for rol in ROLES:
            cl = TestClient(cls.app)
            r = cl.post("/sesion", json={"usuario": f"aisl_{rol}", "clave": CLAVE})
            assert r.status_code == 200, (rol, r.text)
            cls.cli[rol] = cl
        with psycopg.connect(URL_TEST) as c:  # el súper administrador solo opera con segundo factor activo
            c.execute("UPDATE usuarios SET totp_activado = true WHERE nombre = 'aisl_super_admin'")
            c.commit()
        cls.esquema = cls.app.openapi()
        cls._n = 0

    @classmethod
    def tearDownClass(cls):
        cls.cm.__exit__(None, None, None)

    # --- cuerpos mínimos válidos a partir del esquema OpenAPI ------------------------------------
    def _resolver(self, esq):
        while "$ref" in esq:
            esq = self.esquema["components"]["schemas"][esq["$ref"].split("/")[-1]]
        if "anyOf" in esq:
            return self._resolver(next((x for x in esq["anyOf"] if x.get("type") != "null"), esq["anyOf"][0]))
        return esq

    def _valor(self, esq, prof=0):
        esq = self._resolver(esq)
        if "enum" in esq:
            return esq["enum"][0]
        t = esq.get("type")
        if t == "string" and esq.get("format") == "date":
            return "2030-01-10"
        if t == "string" and esq.get("format") == "email":
            return "zz.aislamiento@example.com"
        if t == "string":
            return "a" * max(esq.get("minLength", 1), 3)
        if t == "integer":
            return max(esq.get("minimum", 1), 1)
        if t == "number":
            return 1
        if t == "boolean":
            return False
        if t == "array":
            return []
        if t == "object" and prof < 4:
            return {k: self._valor(v, prof + 1) for k, v in esq.get("properties", {}).items() if k in esq.get("required", [])}
        return {}

    def _peticion(self, met, ruta):
        url = re.sub(r"\{[^}]+\}", "X-1", ruta)
        op = self.esquema["paths"].get(ruta, {}).get(met.lower(), {})
        cuerpo = None
        rb = op.get("requestBody", {}).get("content", {}).get("application/json")
        if (met, ruta) in CUERPOS:
            cuerpo = CUERPOS[(met, ruta)]
        elif rb:
            cuerpo = self._valor(rb["schema"])
        self.__class__._n += 1
        return url, cuerpo, {"Idempotency-Key": f"aisl-{self._n}-xxxxxxxxxxxxxxxx"}

    def _enviar(self, rol, met, ruta):
        url, cuerpo, cab = self._peticion(met, ruta)
        return self.cli[rol].request(met, url, json=cuerpo, headers=cab).status_code

    def _mutantes(self):
        return [(m, r) for m, r, _ in _rutas() if m != "GET" and (m, r) not in PUBLICAS]

    def test_aseo_solo_llega_a_su_lista_blanca(self):
        for met, ruta in self._mutantes():
            url, _, _ = self._peticion(met, ruta)
            if any(p.match(url) for p in comun.RUTAS_ASEO):
                continue
            self.assertEqual(self._enviar("aseo", met, ruta), 403, f"aseo no debe alcanzar {met} {ruta}")

    def test_dueno_no_escribe_fuera_de_su_lista_blanca(self):
        for met, ruta in self._mutantes():
            url, _, _ = self._peticion(met, ruta)
            if any(p.match(url) for p in comun.RUTAS_DUENO):
                continue
            self.assertEqual(self._enviar("dueno", met, ruta), 403, f"dueño no debe escribir en {met} {ruta}")

    def test_operaciones_de_administracion_niegan_a_roles_operativos(self):
        sensibles = [(m, r) for m, r in self._mutantes() if any(m == mm and re.match(p, re.sub(r"\{[^}]+\}", "X-1", r))
                                                                for mm, p in SOLO_ADMIN)]
        self.assertGreaterEqual(len(sensibles), 8, "la lista SOLO_ADMIN dejó de coincidir con rutas reales")
        fallos = [f"{rol} {met} {ruta} -> {estado}" for met, ruta in sensibles
                  for rol in ("recepcion", "caja", "aseo", "dueno")
                  if (estado := self._enviar(rol, met, ruta)) != 403]
        self.assertEqual(fallos, [])

    def test_separacion_de_funciones_entre_administraciones(self):
        # La administración del hotel no administra usuarios; la de plataforma no toca precios.
        self.assertEqual(self._enviar("admin_hotel", "POST", "/usuarios"), 403)
        self.assertEqual(self._enviar("admin_hotel", "POST", "/usuarios/{usuario_id}/email"), 403)
        self.assertEqual(self._enviar("admin_plataforma", "POST", "/hotel/precios/excepciones"), 403)
        self.assertEqual(self._enviar("admin_plataforma", "PUT", "/hotel/habitaciones/{habitacion_id}/precio"), 403)
        # Y las dos sí pueden lo suyo (cualquier cosa menos 401/403).
        self.assertNotIn(self._enviar("admin_hotel", "POST", "/hotel/precios/excepciones"), (401, 403))
        self.assertNotIn(self._enviar("admin_plataforma", "POST", "/usuarios"), (401, 403))

    def test_super_admin_hace_lo_de_ambas_administraciones(self):
        self.assertNotIn(self._enviar("super_admin", "POST", "/usuarios"), (401, 403))
        self.assertNotIn(self._enviar("super_admin", "POST", "/hotel/precios/excepciones"), (401, 403))
        self.assertNotIn(self._enviar("super_admin", "PUT", "/hotel/politicas"), (401, 403))

    def test_sin_sesion_toda_ruta_protegida_responde_401(self):
        anonimo = TestClient(self.app)
        for met, ruta in self._mutantes():
            url, cuerpo, cab = self._peticion(met, ruta)
            self.assertEqual(anonimo.request(met, url, json=cuerpo, headers=cab).status_code, 401, f"{met} {ruta}")


if __name__ == "__main__":
    unittest.main()


class ObservabilidadDeAccesoTest(BarridoPorRolTest):
    """Los intentos de saltar de rol dejan rastro con quién y qué pidió, sin filtrar secretos."""

    def test_acceso_denegado_deja_actor_rol_y_ruta_sin_secretos(self):
        from servicio import observabilidad
        observabilidad.DETECTOR_ESCALADA._marcas.clear()
        observabilidad.DETECTOR_ESCALADA._alertado.clear()
        sid = self.cli["recepcion"].cookies.get(comun.NOMBRE_COOKIE_SESION)
        with self.assertLogs("servicio", level="WARNING") as capturado:
            for _ in range(5):
                self.assertEqual(self._enviar("recepcion", "POST", "/usuarios"), 403)
        registros = capturado.records
        eventos = [r for r in registros if getattr(r, "evento", None) == "acceso_denegado"]
        self.assertEqual(len(eventos), 5)
        self.assertEqual((eventos[0].actor, eventos[0].rol, eventos[0].ruta), ("aisl_recepcion", "recepcion", "/usuarios"))
        http = [r for r in registros if r.name == "servicio.http" and getattr(r, "estado", None) == 403]
        self.assertTrue(all(getattr(r, "actor", None) == "aisl_recepcion" for r in http))
        # La quinta negación seguida dispara la alerta de escalada (una sola vez por ventana).
        alertas = [r for r in registros if getattr(r, "evento", None) == "escalada_privilegios_sospechada"]
        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].levelname, "ERROR")
        # Ningún registro contiene la clave ni el identificador de sesión.
        texto = " ".join(str(vars(r)) + r.getMessage() for r in registros)
        self.assertNotIn(CLAVE, texto)
        self.assertNotIn(sid or "sin-sid", texto)

    def test_login_no_registra_la_clave(self):
        with self.assertLogs("servicio", level="INFO") as capturado:
            TestClient(self.app).post("/sesion", json={"usuario": "aisl_caja", "clave": CLAVE})
        self.assertNotIn(CLAVE, " ".join(str(vars(r)) + r.getMessage() for r in capturado.records))
