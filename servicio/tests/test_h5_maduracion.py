import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.request

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
RANGO = {"inicio": "2026-11-10", "fin": "2026-11-12"}


class MaduracionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute(
                "TRUNCATE auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            from servicio.reservas import sembrar_habitaciones

            sembrar_habitaciones(conexion)
            conexion.execute(
                "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                "VALUES ('TAR-FIJA', 'HAB-SINT-101', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})

    def reservar(self, clave="res-1"):
        respuesta = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-SINT-101", **RANGO, "huesped": {"nombre": "Huésped"}},
            headers={"Idempotency-Key": clave},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()["reserva_id"]

    # ---- validación de datos consumidos ----

    def test_montos_capacidades_y_claves_invalidos_dan_422(self):
        casos = [
            ("capacidad cero", "/hotel/habitaciones/HAB-X", {"tipo": "doble", "capacidad": 0}),
            ("tarifa negativa", "/hotel/tarifas", {
                "habitacion_id": "HAB-SINT-101", "fecha_desde": "2026-01-01",
                "fecha_hasta": "2027-01-01", "tarifa_noche_clp": -1}),
        ]
        for nombre, ruta, cuerpo in casos:
            with self.subTest(caso=nombre):
                respuesta = self.cliente.put(ruta, json=cuerpo, headers={"Idempotency-Key": f"val-{nombre}"})
                self.assertEqual(respuesta.status_code, 422, respuesta.text)

    def test_pago_monto_negativo_y_modo_desconocido_dan_422(self):
        rid = self.reservar()
        for cuerpo in (
            {"monto_clp": -5, "clave": "k", "modo": "manual"},
            {"monto_clp": 1000, "clave": "k", "modo": "bitcoin"},
        ):
            with self.subTest(cuerpo=cuerpo):
                respuesta = self.cliente.post(
                    f"/hotel/reservas/{rid}/pagos", json=cuerpo, headers={"Idempotency-Key": "val-pago"}
                )
                self.assertEqual(respuesta.status_code, 422, respuesta.text)

    def test_integridad_de_base_responde_409_y_no_500(self):
        respuesta = self.cliente.put(
            "/hotel/tarifas",
            json={"habitacion_id": "HAB-NO-EXISTE", "fecha_desde": "2026-01-01",
                  "fecha_hasta": "2027-01-01", "tarifa_noche_clp": 1000},
            headers={"Idempotency-Key": "fk-1"},
        )
        self.assertEqual(respuesta.status_code, 409)

    # ---- diseño seguro ----

    def test_sesion_expirada_responde_401(self):
        self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        sid = self.cliente.cookies.get("sid")
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("UPDATE sesiones SET expira_en = now() - interval '1 second' WHERE id = %s", (sid,))
            conexion.commit()
        self.assertEqual(self.cliente.get("/sesion").status_code, 401)

    def test_freno_de_fuerza_bruta_en_login(self):
        for i in range(5):
            respuesta = self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": "mala"})
            self.assertEqual(respuesta.status_code, 401)
        respuesta = self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": "mala"})
        self.assertEqual(respuesta.status_code, 429)
        # el contador es por (ip, usuario): otro usuario no hereda el bloqueo
        with psycopg.connect(URL_TEST) as conexion:
            seguridad.crear_usuario(conexion, EMPRESA, "caja1", "caja", "clave-caja")
            conexion.commit()
        respuesta = self.cliente.post("/sesion", json={"usuario": "caja1", "clave": "clave-caja"})
        self.assertEqual(respuesta.status_code, 200)

    def test_cabeceras_seguras_presentes(self):
        respuesta = self.cliente.get("/salud")
        self.assertEqual(respuesta.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(respuesta.headers["X-Frame-Options"], "DENY")

    # ---- contrato servido y auditoría ----

    def test_openapi_cubre_las_diez_operaciones(self):
        esquema = self.cliente.get("/openapi.json").json()
        self.assertTrue(esquema["openapi"].startswith("3.1"))
        esperadas = {
            "POST": ["/sesion", "/hotel/reservas", "/hotel/reservas/{reserva_id}/pagos",
                     "/hotel/reservas/{reserva_id}/entrada", "/hotel/reservas/{reserva_id}/salida"],
            "PUT": ["/hotel/habitaciones/{habitacion_id}", "/hotel/tarifas"],
            "GET": ["/hotel/oferta", "/hotel/caja"],
            "DELETE": ["/sesion"],
        }
        for metodo, rutas in esperadas.items():
            for ruta in rutas:
                with self.subTest(metodo=metodo, ruta=ruta):
                    self.assertIn(metodo.lower(), esquema["paths"].get(ruta, {}))

    def test_auditoria_registra_actor_accion_recurso_resultado(self):
        rid = self.reservar()
        self.cliente.post(
            f"/hotel/reservas/{rid}/pagos",
            json={"monto_clp": 100_000, "clave": "cob-1", "modo": "manual"},
            headers={"Idempotency-Key": "pag-1"},
        )
        with psycopg.connect(URL_TEST) as conexion:
            filas = conexion.execute(
                "SELECT actor, accion, recurso, resultado FROM auditoria ORDER BY creado_en"
            ).fetchall()
        acciones = {(f[1], f[3]) for f in filas}
        self.assertIn(("reserva", "confirmada"), acciones)
        self.assertIn(("pago", "confirmado"), acciones)
        self.assertTrue(all(f[0] == "admin" for f in filas))


class ReinicioTest(unittest.TestCase):
    def test_reserva_y_pago_sobreviven_al_reinicio_del_proceso(self):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute(
                "TRUNCATE auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            from servicio.reservas import sembrar_habitaciones

            sembrar_habitaciones(conexion)
            conexion.execute(
                "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                "VALUES ('TAR-FIJA', 'HAB-SINT-101', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()

        puerto = _puerto_libre()

        def levantar():
            entorno = os.environ.copy()
            entorno.update({
                "DATABASE_URL": URL_TEST,
                "ADMIN_USUARIO": ADMIN[0],
                "ADMIN_CLAVE": ADMIN[1],
                "SERVICIO_PUERTO": str(puerto),
            })
            return subprocess.Popen(
                [sys.executable, "-m", "servicio"], env=entorno, cwd=RAIZ,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

        def http(metodo, ruta, cuerpo=None, cookies=None, idempotency_key=None):
            datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
            peticion = urllib.request.Request(f"http://127.0.0.1:{puerto}{ruta}", data=datos, method=metodo)
            peticion.add_header("Content-Type", "application/json")
            if idempotency_key:
                peticion.add_header("Idempotency-Key", idempotency_key)
            for clave, valor in (cookies or {}).items():
                peticion.add_header("Cookie", valor)
            with urllib.request.urlopen(peticion) as respuesta:
                return respuesta.status, json.loads(respuesta.read()), respuesta.headers

        try:
            proceso_a = levantar()
            _esperar(puerto)
            _, login, cabeceras = http("POST", "/sesion", {"usuario": ADMIN[0], "clave": ADMIN[1]})
            galleta = cabeceras.get("Set-Cookie").split(";")[0]
            _, creada, _ = http(
                "POST", "/hotel/reservas",
                {"habitacion_id": "HAB-SINT-101", **RANGO, "huesped": {"nombre": "Persistente"}},
                cookies={"Cookie": galleta}, idempotency_key="res-reinicio",
            )
            http("POST", f"/hotel/reservas/{creada['reserva_id']}/pagos",
                 {"monto_clp": 100_000, "clave": "cob-1", "modo": "manual"},
                 cookies={"Cookie": galleta}, idempotency_key="pag-reinicio")
            proceso_a.terminate()
            proceso_a.wait(timeout=10)

            proceso_b = levantar()
            _esperar(puerto)
            _, login_b, cab_b = http("POST", "/sesion", {"usuario": ADMIN[0], "clave": ADMIN[1]})
            galleta_b = cab_b.get("Set-Cookie").split(";")[0]
            estado, caja, _ = http("GET", f"/hotel/caja?fecha={time.strftime('%Y-%m-%d')}",
                                   cookies={"Cookie": galleta_b})
            self.assertEqual(estado, 200)
            self.assertEqual(caja["total_clp"], 100_000)
            self.assertEqual(caja["pagos"][0]["reserva_id"], creada["reserva_id"])
            estado, oferta, _ = http("GET", "/hotel/oferta?inicio=2026-11-10&fin=2026-11-12&personas=2",
                                     cookies={"Cookie": galleta_b})
            habitaciones = {i["habitacion_id"] for i in oferta["oferta"]}
            self.assertNotIn("HAB-SINT-101", habitaciones)  # la reserva sigue ocupando
            proceso_b.terminate()
            proceso_b.wait(timeout=10)
        finally:
            for p in (locals().get("proceso_a"), locals().get("proceso_b")):
                if p and p.poll() is None:
                    p.kill()


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _esperar(puerto: int, intentos: int = 40) -> None:
    for _ in range(intentos):
        try:
            with socket.create_connection(("127.0.0.1", puerto), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"el servicio no arrancó en {puerto}")


if __name__ == "__main__":
    unittest.main()
