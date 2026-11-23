"""#453: el contacto de la solicitud queda en columnas propias y normalizadas."""
import os
import unittest
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import canal_publico, migracion, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_contacto453")
HOY = date.today()


class ExtraccionTest(unittest.TestCase):
    def test_telefono_e164(self):
        self.assertEqual(canal_publico.telefono_e164("9 5649 1501"), "+56956491501")
        self.assertEqual(canal_publico.telefono_e164("+56 9 5649 1501"), "+56956491501")
        self.assertEqual(canal_publico.telefono_e164("+1 (415) 555-0100"), "+14155550100")
        self.assertIsNone(canal_publico.telefono_e164("123"))
        self.assertIsNone(canal_publico.telefono_e164(None))

    def test_extraer_contacto_estructurado_y_simple(self):
        d = canal_publico.extraer_contacto("Ana@Example.com · Tel: 9 1234 5678 · Doc: 12.345.678-5")
        self.assertEqual(d, {"huesped_correo": "ana@example.com", "huesped_telefono": "+56912345678",
                             "huesped_documento": "12.345.678-5"})
        self.assertEqual(canal_publico.extraer_contacto("9 8765 4321")["huesped_telefono"], "+56987654321")
        self.assertIsNone(canal_publico.extraer_contacto("9 8765 4321")["huesped_correo"])
        solo = canal_publico.extraer_contacto("luis@example.com")
        self.assertEqual((solo["huesped_correo"], solo["huesped_telefono"]), ("luis@example.com", None))


class SolicitudContactoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario="admin_c", admin_clave="Clave123!"))
        cls.cm = TestClient(cls.app)
        cls.cm.__enter__()
        cls._n = 0

    @classmethod
    def tearDownClass(cls):
        cls.cm.__exit__(None, None, None)

    def setUp(self):
        h = seguridad.hashear_clave("Clave123!")
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "TRUNCATE freno_solicitudes_eventos, reserva_huespedes, huespedes, clientes, reasignaciones, liquidaciones, pagos, cargos, "
                "reserva_noches, reservas, solicitudes, tarifas, excepciones_precio, habitaciones, "
                "politicas_hotel, claves_idempotencia, auditoria, sesiones, usuarios CASCADE")
            c.execute("INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                      "('USR-C-RECEP', 'recep_c', %s, 'recepcion', 'EMP-SINTETICA-001', true)", (h,))
            c.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, "
                      "estado_preparacion, en_inventario) VALUES ('HAB-C1', 'EST-1', 'doble', 3, 'disponible', "
                      "'limpia', true)")
            c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, "
                      "motivo, activa) VALUES ('EXC-C1', 'HAB-C1', %s, %s, 55000, 'base', true)",
                      (HOY, HOY + timedelta(days=60)))
            c.commit()
        self.app.state.freno_solicitudes.max_por_minuto = 1000  # el freno se ejercita en test_canal_publico
        self.recep = TestClient(self.app)
        self.assertEqual(self.recep.post("/sesion", json={"usuario": "recep_c", "clave": "Clave123!"}).status_code, 200)

    def _publica(self, contacto):
        self.__class__._n += 1
        return TestClient(self.app).post("/publico/solicitudes", headers={"Idempotency-Key": f"pub-453-{self._n}-xxxxxxxxxxxx"}, json={
            "tipo": "doble", "inicio": str(HOY + timedelta(days=5)), "fin": str(HOY + timedelta(days=7)),
            "personas": 2, "huesped_nombre": "Ana Prueba", "huesped_contacto": contacto})

    def test_solicitud_guarda_columnas_y_las_muestra_a_recepcion(self):
        r = self._publica("Ana@Example.com · Tel: 9 1234 5678 · Doc: 12.345.678-5")
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["huesped_correo"], "ana@example.com")
        self.assertEqual(r.json()["huesped_telefono"], "+56912345678")
        lista = self.recep.get("/hotel/solicitudes").json()["solicitudes"]
        self.assertEqual(lista[0]["huesped_telefono"], "+56912345678")
        self.assertEqual(lista[0]["huesped_documento"], "12.345.678-5")
        self.assertFalse(lista[0]["contacto_verificado"])

    def test_personas_fuera_de_rango_sigue_rechazado(self):
        r = TestClient(self.app).post("/publico/solicitudes", headers={"Idempotency-Key": "pub-453-rango-xxxxxxxxxxxx"}, json={
            "tipo": "doble", "inicio": str(HOY + timedelta(days=5)), "fin": str(HOY + timedelta(days=7)),
            "personas": 0, "huesped_nombre": "Ana", "huesped_contacto": "ana@example.com"})
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
