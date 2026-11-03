import concurrent.futures
import os
import unittest

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.tests.aislamiento import exigir_base_libre
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
RANGO = {"inicio": "2026-11-10", "fin": "2026-11-12"}


class ReservaPersistenteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "TRUNCATE claves_idempotencia, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            from servicio.reservas import sembrar_habitaciones

            sembrar_habitaciones(conexion)
            conexion.commit()
        self.cliente = TestClient(self.app)
        self.login()

    def login(self, usuario=ADMIN[0], clave=ADMIN[1]):
        respuesta = self.cliente.post("/sesion", json={"usuario": usuario, "clave": clave})
        self.assertEqual(respuesta.status_code, 200)
        return respuesta

    def poner_tarifa(self, habitacion_id="HAB-SINT-101", monto=50_000):
        respuesta = self.cliente.put(
            "/hotel/tarifas",
            json={
                "habitacion_id": habitacion_id,
                "fecha_desde": "2026-01-01",
                "fecha_hasta": "2027-12-31",
                "tarifa_noche_clp": monto,
            },
            headers={"Idempotency-Key": f"tarifa-{habitacion_id}-{monto}"},
        )
        self.assertEqual(respuesta.status_code, 201)
        return respuesta

    def test_admin_define_habitacion_y_tarifa_y_oferta_muestra_vigencia(self):
        self.cliente.put(
            "/hotel/habitaciones/HAB-101",
            json={"tipo": "matrimonial", "capacidad": 2},
            headers={"Idempotency-Key": "hab-101"},
        )
        self.poner_tarifa("HAB-101", 55_000)
        respuesta = self.cliente.get("/hotel/oferta", params={**RANGO, "personas": 2})
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["vigencia_minutos"], 15)
        habitaciones = {item["habitacion_id"] for item in cuerpo["oferta"]}
        self.assertIn("HAB-101", habitaciones)
        item = next(i for i in cuerpo["oferta"] if i["habitacion_id"] == "HAB-101")
        self.assertEqual(item["tarifa_noche_clp"], 55_000)
        self.assertEqual(item["total_clp"], 110_000)  # 2 noches

    def test_no_admin_no_define_tarifa_ni_habitacion(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            seguridad.crear_usuario(conexion, EMPRESA, "recepcion", "recepcion", "clave-recepcion")
            conexion.commit()
        self.login("recepcion", "clave-recepcion")
        respuesta = self.cliente.put(
            "/hotel/tarifas",
            json={"habitacion_id": "HAB-SINT-101", "fecha_desde": "2026-01-01", "fecha_hasta": "2027-01-01", "tarifa_noche_clp": 1},
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_reserva_congela_la_tarifa_aceptada(self):
        self.poner_tarifa(monto=50_000)
        primera = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-SINT-101", **RANGO, "huesped": {"nombre": "Huésped Uno"}},
            headers={"Idempotency-Key": "res-1"},
        )
        self.assertEqual(primera.status_code, 201)
        self.assertEqual(primera.json()["tarifa_noche_aceptada_clp"], 50_000)
        self.poner_tarifa(monto=70_000)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (aceptada,) = conexion.execute(
                "SELECT tarifa_noche_aceptada_clp FROM reservas WHERE id = %s",
                (primera.json()["reserva_id"],),
            ).fetchone()
        self.assertEqual(aceptada, 50_000)  # la reserva ya aceptada no cambia

    def test_carrera_por_la_ultima_unidad_deja_una_sola_reserva(self):
        respuesta = self.cliente.put(
            "/hotel/habitaciones/HAB-ULT-1",
            json={"tipo": "doble", "capacidad": 2},
            headers={"Idempotency-Key": "hab-ult-1"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.poner_tarifa("HAB-ULT-1", 40_000)
        cuerpo = {
            "habitacion_id": "HAB-ULT-1",
            **RANGO,
            "huesped": {"nombre": "Concurrente"},
        }

        def intentar(i: int):
            cliente = TestClient(self.app)
            self.login_en(cliente)
            return cliente.post("/hotel/reservas", json=cuerpo, headers={"Idempotency-Key": f"corrida-{i}"})

        self.login()  # asegura cookie en self.cliente; los hilos loguean por su cuenta
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as pool:
            respuestas = list(pool.map(intentar, range(100)))
        codigos = [r.status_code for r in respuestas]
        self.assertEqual(codigos.count(201), 1)
        self.assertEqual(codigos.count(409), 99)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (n,) = conexion.execute(
                "SELECT count(*) FROM reservas WHERE habitacion_id = 'HAB-ULT-1' AND estado = 'confirmada'"
            ).fetchone()
        self.assertEqual(n, 1)  # sin sobreventa en la base

    def login_en(self, cliente: TestClient, usuario=ADMIN[0], clave=ADMIN[1]):
        respuesta = cliente.post("/sesion", json={"usuario": usuario, "clave": clave})
        assert respuesta.status_code == 200, respuesta.text

    def test_idempotencia_repite_resultado_y_conflicto_da_409(self):
        self.poner_tarifa()
        cuerpo = {"habitacion_id": "HAB-SINT-101", **RANGO, "huesped": {"nombre": "Reintento"}}
        primera = self.cliente.post("/hotel/reservas", json=cuerpo, headers={"Idempotency-Key": "k-1"})
        segunda = self.cliente.post("/hotel/reservas", json=cuerpo, headers={"Idempotency-Key": "k-1"})
        self.assertEqual(primera.status_code, 201)
        self.assertEqual(segunda.status_code, 201)
        self.assertEqual(primera.json()["reserva_id"], segunda.json()["reserva_id"])
        otro_cuerpo = {**cuerpo, "huesped": {"nombre": "Otro"}}
        conflicto = self.cliente.post("/hotel/reservas", json=otro_cuerpo, headers={"Idempotency-Key": "k-1"})
        self.assertEqual(conflicto.status_code, 409)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (n,) = conexion.execute("SELECT count(*) FROM reservas").fetchone()
        self.assertEqual(n, 1)

    def test_reserva_sin_tarifa_vigente_responde_409(self):
        respuesta = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-SINT-102", **RANGO, "huesped": {"nombre": "Sin tarifa"}},
            headers={"Idempotency-Key": "sin-tarifa-1"},
        )
        self.assertEqual(respuesta.status_code, 409)

    def test_oferta_excluye_la_unidad_ocupada(self):
        self.poner_tarifa("HAB-SINT-101")
        self.poner_tarifa("HAB-SINT-102")
        self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-SINT-101", **RANGO, "huesped": {"nombre": "Ocupante"}},
            headers={"Idempotency-Key": "ocupo-1"},
        )
        respuesta = self.cliente.get("/hotel/oferta", params={**RANGO, "personas": 2})
        habitaciones = {item["habitacion_id"] for item in respuesta.json()["oferta"]}
        self.assertNotIn("HAB-SINT-101", habitaciones)
        self.assertIn("HAB-SINT-102", habitaciones)


if __name__ == "__main__":
    unittest.main()
