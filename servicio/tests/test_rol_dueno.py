"""Rol dueño: lee todo lo de la administración del hotel, no cambia datos y deja observaciones."""
import os
import unittest
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import migracion, roles, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_dueno")
CLAVE = "Clave123!"


class RolDuenoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario="root_d", admin_clave=CLAVE))
        cls.cm = TestClient(cls.app)
        cls.cm.__enter__()
        cls._n = 0

    @classmethod
    def tearDownClass(cls):
        cls.cm.__exit__(None, None, None)

    def setUp(self):
        h = seguridad.hashear_clave(CLAVE)
        with psycopg.connect(URL_TEST) as c:
            c.execute("TRUNCATE observaciones_direccion, sesiones, claves_idempotencia, avisos_eventos CASCADE")
            for nombre, rol in (("ricardo_d", "dueno"), ("admin_d", "admin_hotel"), ("recep_d", "recepcion")):
                c.execute(
                    "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                    "(%s, %s, %s, %s, 'EMP-SINTETICA-001', true) ON CONFLICT (id) DO UPDATE SET "
                    "clave_hash = EXCLUDED.clave_hash, rol = EXCLUDED.rol, activo = true",
                    (f"USR-D-{nombre}", nombre, h, rol))
            c.commit()
        self.dueno, self.admin, self.recep = (self._login(n) for n in ("ricardo_d", "admin_d", "recep_d"))

    def _login(self, usuario):
        c = TestClient(self.app)
        r = c.post("/sesion", json={"usuario": usuario, "clave": CLAVE})
        self.assertEqual(r.status_code, 200, r.text)
        return c

    def _h(self):
        self.__class__._n += 1
        return {"Idempotency-Key": f"dueno-{self._n}-xxxxxxxxxxxxxxxx"}

    def test_rol_registrado_y_exige_doble_factor(self):
        self.assertIn(roles.DUENO, roles.ROLES_VALIDOS)
        self.assertTrue(roles.exige_doble_factor(roles.DUENO))
        self.assertEqual(self.dueno.get("/sesion").json()["rol"], "dueno")  # la lectura global no cambia su identidad

    def test_lee_lo_que_lee_la_administracion_pero_no_gestiona_usuarios(self):
        hoy = date.today()
        r = self.dueno.get("/hotel/indicadores", params={"desde": str(hoy), "hasta": str(hoy + timedelta(days=7))})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.dueno.get("/hotel/contabilidad/cuentas-por-cobrar").status_code, 200)
        lista = self.dueno.get("/usuarios")  # lectura global: ve quién tiene qué rol, pero no gestiona a nadie
        self.assertEqual(lista.status_code, 200)
        self.assertFalse(any(u["gestionable"] for u in lista.json()["usuarios"]))
        self.assertEqual(lista.json()["roles_que_puedes_crear"], [])
        # La recepción no ve lo financiero que sí ve el dueño.
        fin = self.dueno.get("/hotel/indicadores", params={"desde": str(hoy), "hasta": str(hoy + timedelta(days=7))}).json()
        fin_recep = self.recep.get("/hotel/indicadores", params={"desde": str(hoy), "hasta": str(hoy + timedelta(days=7))}).json()
        self.assertGreaterEqual(len(fin.get("indicadores", fin)), len(fin_recep.get("indicadores", fin_recep)))

    def test_no_escribe_fuera_de_las_observaciones(self):
        self.assertEqual(self.dueno.post("/hotel/productos", headers=self._h(), json={
            "nombre": "Producto X", "categoria": "extra", "precio_clp": 1000}).status_code, 403)
        self.assertEqual(self.dueno.post("/usuarios", headers=self._h(), json={
            "nombre": "zz", "rol": "administrador", "clave": "ClaveSegura123!"}).status_code, 403)

    def test_ciclo_de_observacion_dueno_administracion_dueno(self):
        r = self.dueno.post("/hotel/observaciones", headers=self._h(),
                            json={"texto": "Explícame la diferencia de caja del lunes", "referencia": "/hotel/caja"})
        self.assertEqual(r.status_code, 200, r.text)
        oid = r.json()["observacion_id"]
        # La recepción no la ve ni la responde; la administración sí.
        self.assertEqual(self.recep.get("/hotel/observaciones").status_code, 403)
        self.assertEqual(self.recep.post(f"/hotel/observaciones/{oid}/respuesta", headers=self._h(),
                                         json={"respuesta": "ok"}).status_code, 403)
        lista = self.admin.get("/hotel/observaciones", params={"estado": "abierta"}).json()
        self.assertEqual(lista["abiertas"], 1)
        self.assertEqual(lista["observaciones"][0]["referencia"], "/hotel/caja")
        # El dueño no puede responderse a sí mismo; la administración responde.
        self.assertEqual(self.dueno.post(f"/hotel/observaciones/{oid}/respuesta", headers=self._h(),
                                         json={"respuesta": "x"}).status_code, 403)
        ok = self.admin.post(f"/hotel/observaciones/{oid}/respuesta", headers=self._h(),
                             json={"respuesta": "Fue un depósito pendiente; ya está conciliado."})
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(self.dueno.get("/hotel/observaciones").json()["observaciones"][0]["estado"], "respondida")
        # Solo el dueño la cierra; la administración no.
        self.assertEqual(self.admin.post(f"/hotel/observaciones/{oid}/cierre", headers=self._h()).status_code, 403)
        self.assertEqual(self.dueno.post(f"/hotel/observaciones/{oid}/cierre", headers=self._h()).status_code, 200)
        self.assertEqual(self.admin.post(f"/hotel/observaciones/{oid}/respuesta", headers=self._h(),
                                         json={"respuesta": "tarde"}).status_code, 409)

    def test_aviso_a_la_administracion_sin_el_texto(self):
        self.dueno.post("/hotel/observaciones", headers=self._h(), json={"texto": "Texto confidencial del dueño"})
        with psycopg.connect(URL_TEST) as c:
            datos = c.execute("SELECT datos::text FROM avisos_eventos WHERE tipo = 'observacion_dueno'").fetchall()
        self.assertEqual(len(datos), 1)
        self.assertNotIn("confidencial", datos[0][0])


if __name__ == "__main__":
    unittest.main()
