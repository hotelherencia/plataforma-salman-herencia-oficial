"""SPEC-UPG-01: «Upgrade a tarifa Single» cuando no queda single libre."""
import os
import unittest
from datetime import date, time, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import migracion, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.reloj import a_las

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_upg01")
HOY = date(2026, 11, 20)


class UpgradeSingleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario="admin_h", admin_clave="Clave123!"))
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
                "TRUNCATE reserva_huespedes, huespedes, clientes, reasignaciones, liquidaciones, "
                "pagos, cargos, reserva_noches, reservas, tarifas, excepciones_precio, "
                "habitaciones, politicas_hotel, claves_idempotencia, auditoria, sesiones, usuarios CASCADE")
            c.execute(
                "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                "('USR-U-RECEP', 'recep_u', %s, 'recepcion', 'EMP-SINTETICA-001', true), "
                "('USR-U-CAJA', 'caja_u', %s, 'caja', 'EMP-SINTETICA-001', true)", (h, h))
            c.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, "
                "estado_preparacion, en_inventario) VALUES "
                "('HAB-S1', 'EST-1', 'single', 1, 'disponible', 'limpia', true), "
                "('HAB-D1', 'EST-1', 'doble', 3, 'disponible', 'limpia', true)")
            for hab, precio in (("HAB-S1", 47000), ("HAB-D1", 55000)):
                c.execute(
                    "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, "
                    "motivo, activa) VALUES (%s, %s, %s, %s, %s, 'base test', true)",
                    (f"EXC-{hab}", hab, HOY, HOY + timedelta(days=30), precio))
            c.commit()
        self.recep = self._login("recep_u")
        self.caja = self._login("caja_u")

    def _login(self, usuario):
        c = TestClient(self.app)
        self.assertEqual(c.post("/sesion", json={"usuario": usuario, "clave": "Clave123!"}).status_code, 200)
        return c

    def _idem(self):
        self.__class__._n += 1
        return {"Idempotency-Key": f"upg-{self.__class__._n}"}

    def _reservar(self, cliente, hab, upgrade, personas=1, noches=2):
        return cliente.post("/hotel/reservas", headers=self._idem(), json={
            "habitacion_id": hab, "inicio": HOY.isoformat(),
            "fin": (HOY + timedelta(days=noches)).isoformat(), "personas": personas,
            "upgrade_a_single": upgrade,
            "huesped": {"nombre": "Ana Solo", "documento": "12.345.678-5", "documento_tipo": "rut"}})

    def _ocupar_single(self):
        r = self._reservar(self.recep, "HAB-S1", False)
        self.assertEqual(r.status_code, 201, r.text)

    def test_con_single_libre_se_rechaza(self):
        r = self._reservar(self.recep, "HAB-D1", True)
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("Single disponible", r.json()["detail"])

    def test_sin_single_cobra_tarifa_single_y_guarda_trazabilidad(self):
        self._ocupar_single()
        r = self._reservar(self.recep, "HAB-D1", True)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["tarifa_noche_aceptada_clp"], 47000)
        with psycopg.connect(URL_TEST) as c:
            fila = c.execute(
                "SELECT upgrade_desde_tipo, tarifa_lista_clp, tarifa_noche_aceptada_clp FROM reservas "
                "WHERE id = %s", (r.json()["reserva_id"],)).fetchone()
            noches = [f[0] for f in c.execute(
                "SELECT precio_clp FROM reserva_noches WHERE reserva_id = %s",
                (r.json()["reserva_id"],)).fetchall()]
        self.assertEqual(fila, ("single", 55000, 47000))
        self.assertEqual(noches, [47000, 47000])

    def test_solo_una_persona_y_roles_autorizados(self):
        self._ocupar_single()
        self.assertEqual(self._reservar(self.recep, "HAB-D1", True, personas=2).status_code, 409)
        self.assertEqual(self._reservar(self.caja, "HAB-D1", True).status_code, 403)

    def test_llegada_con_dos_personas_ajusta_a_tarifa_de_la_habitacion(self):
        self._ocupar_single()
        rid = self._reservar(self.recep, "HAB-D1", True).json()["reserva_id"]
        a = self.recep.put(f"/hotel/reservas/{rid}/ocupacion", json={"adultos": 2, "ninos": 0})
        self.assertEqual(a.status_code, 200, a.text)
        with psycopg.connect(URL_TEST) as c:
            ajuste = c.execute("SELECT upgrade_ajustado_clp FROM reservas WHERE id = %s", (rid,)).fetchone()[0]
            cargos = [f[0] for f in c.execute(
                "SELECT monto_clp FROM cargos WHERE reserva_id = %s AND concepto LIKE 'Ajuste upgrade%%'",
                (rid,)).fetchall()]
        self.assertEqual(ajuste, (55000 - 47000) * 2)
        self.assertEqual(cargos, [16000])
        # Vuelve a 1 persona: se reversa (no se edita) y queda en cero.
        self.assertEqual(self.recep.put(f"/hotel/reservas/{rid}/ocupacion",
                                        json={"adultos": 1, "ninos": 0}).status_code, 200)
        with psycopg.connect(URL_TEST) as c:
            self.assertEqual(c.execute(
                "SELECT upgrade_ajustado_clp FROM reservas WHERE id = %s", (rid,)).fetchone()[0], 0)

    def test_primera_noche_en_la_llegada_usa_tarifa_single(self):
        self._ocupar_single()
        rid = self._reservar(self.recep, "HAB-D1", True).json()["reserva_id"]
        with a_las(HOY, hora=time(15, 30)):
            r = self.recep.post(f"/hotel/reservas/{rid}/entrada", headers=self._idem(), json={})
        self.assertEqual(r.status_code, 200, r.text)
        with psycopg.connect(URL_TEST) as c:
            noches = sorted(f[0] for f in c.execute(
                "SELECT monto_clp FROM cargos WHERE reserva_id = %s AND concepto = 'Noche'", (rid,)).fetchall())
        self.assertEqual(noches, [47000, 47000])


if __name__ == "__main__":
    unittest.main()
