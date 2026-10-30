"""Pre-H7: arranque seguro, cookie según entorno, origin en mutaciones,
freno de logins por usuario y nombre de usuario único.

Pruebas HTTP contra PostgreSQL de test (mismo patrón que test_h5_maduracion).
"""
import os
import unittest

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import ErrorArranque, crear_app
from servicio.configuracion import Configuracion, cargar_desde_entorno

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
FRONT = "https://front.example"


def app_de_prueba(origen_front=None, cookie_segura=False):
    config = Configuracion(
        host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=cookie_segura,
        origen_front=origen_front, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
    )
    return crear_app(configuracion=config)


class PreH7SeguridadTest(unittest.TestCase):
    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute(
                "TRUNCATE auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.commit()

    # ---- arranque ----

    def test_origen_front_exige_cookie_segura(self):
        with self.assertRaises(ErrorArranque):
            app_de_prueba(origen_front=FRONT, cookie_segura=False)

    def test_origen_front_con_barra_final_normalizado(self):
        os.environ["ORIGEN_FRONT"] = FRONT + "/"
        try:
            config = cargar_desde_entorno()
        finally:
            del os.environ["ORIGEN_FRONT"]
        self.assertEqual(config.origen_front, FRONT)

    # ---- cookie según entorno (spec-api-v1) ----

    def test_cookie_local_es_lax_sin_secure(self):
        cliente = TestClient(app_de_prueba())
        r = cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("SameSite=lax", r.headers["set-cookie"])
        self.assertNotIn("Secure", r.headers["set-cookie"])

    def test_cookie_produccion_none_con_secure(self):
        cliente = TestClient(app_de_prueba(origen_front=FRONT, cookie_segura=True),
                             base_url="https://testserver")
        r = cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("SameSite=none", r.headers["set-cookie"])
        self.assertIn("Secure", r.headers["set-cookie"])
        r2 = cliente.request("DELETE", "/sesion")
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertIn("SameSite=none", r2.headers["set-cookie"])

    # ---- origin en mutaciones ----

    def test_origin_ajeno_rechazado_aun_con_sesion(self):
        cliente = TestClient(app_de_prueba(origen_front=FRONT, cookie_segura=True),
                             base_url="https://testserver")
        login = cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.assertEqual(login.status_code, 200, login.text)
        r = cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-X", "inicio": "2026-11-10", "fin": "2026-11-11",
                  "huesped": {"nombre": "P"}},
            headers={"Idempotency-Key": "o-1", "Origin": "https://evil.example"},
        )
        self.assertEqual(r.status_code, 403, r.text)

    def test_origin_correcto_permitido(self):
        cliente = TestClient(app_de_prueba(origen_front=FRONT, cookie_segura=True),
                             base_url="https://testserver")
        cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        cliente.put("/hotel/habitaciones/HAB-X", json={"tipo": "doble", "capacidad": 2},
                    headers={"Idempotency-Key": "o-2", "Origin": FRONT})
        cliente.put("/hotel/tarifas", json={"habitacion_id": "HAB-X", "fecha_desde": "2026-01-01",
                                            "fecha_hasta": "2027-01-01", "tarifa_noche_clp": 50000},
                    headers={"Idempotency-Key": "o-3", "Origin": FRONT})
        r = cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-X", "inicio": "2026-11-10", "fin": "2026-11-11",
                  "huesped": {"nombre": "P"}},
            headers={"Idempotency-Key": "o-4", "Origin": FRONT},
        )
        self.assertEqual(r.status_code, 201, r.text)

    def test_sin_cabecera_origin_la_mutacion_sigue(self):
        cliente = TestClient(app_de_prueba(origen_front=FRONT, cookie_segura=True))
        r = cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.assertEqual(r.status_code, 200, r.text)

    # ---- freno de logins por usuario ----

    def test_cinco_fallos_bloquean_al_usuario_aunque_ruede_la_ip(self):
        cliente = TestClient(app_de_prueba())
        mala = {"usuario": ADMIN[0], "clave": "clave-mala"}
        for i in range(5):
            r = cliente.post("/sesion", json=mala, headers={"X-Forwarded-For": f"10.0.0.{i}"})
            self.assertEqual(r.status_code, 401, r.text)
        r = cliente.post("/sesion", json=mala, headers={"X-Forwarded-For": "10.9.9.9"})
        self.assertEqual(r.status_code, 429, r.text)
        bien = {"usuario": ADMIN[0], "clave": ADMIN[1]}
        r = cliente.post("/sesion", json=bien)
        self.assertEqual(r.status_code, 429, r.text)

    def test_freno_por_usuario_no_depende_de_la_ip(self):
        freno = seguridad.FrenoDeLogins()
        for i in range(5):
            freno.registrar_fallo(f"ip-{i}", "recepcion1", float(i))
            freno.registrar_fallo_usuario("recepcion1", float(i))
        self.assertFalse(freno.bloqueado("ip-nueva", "recepcion1", 6.0))
        self.assertTrue(freno.bloqueado_usuario("recepcion1", 6.0))
        freno.reiniciar_usuario("recepcion1")
        self.assertFalse(freno.bloqueado_usuario("recepcion1", 7.0))

    # ---- nombre de usuario único ----

    def test_usuario_duplicado_rechazado_por_la_base(self):
        with psycopg.connect(URL_TEST) as conexion:
            with self.assertRaises(psycopg.IntegrityError):
                seguridad.crear_usuario(conexion, EMPRESA, ADMIN[0], "recepcion", "otra-clave-sintetica")


if __name__ == "__main__":
    unittest.main()
