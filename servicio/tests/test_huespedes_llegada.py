"""Pruebas PR A: ocupación real (adultos/niños), registro de todos los huéspedes
en la Llegada, políticas de recargo y búsqueda por documento.
"""
import os
import unittest
from datetime import date, time, timedelta
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient

from servicio import migracion, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.reloj import a_las

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_huespedes",
)
HOY = date(2026, 11, 20)


class HuespedesLlegadaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario="admin_h", admin_clave="Clave123!",
        ))
        cls.client_cm = TestClient(cls.app)
        cls.client = cls.client_cm.__enter__()
        cls._n = 0

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "TRUNCATE reserva_huespedes, huespedes, reasignaciones, liquidaciones, "
                "pagos, cargos, reserva_noches, reservas, tarifas, excepciones_precio, "
                "habitaciones, politicas_hotel, claves_idempotencia, auditoria, sesiones CASCADE"
            )
            c.execute(
                "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                "('USR-H-ADMIN', 'admin_h', %s, 'admin_hotel', 'EMP-SINTETICA-001', true), "
                "('USR-H-RECEP', 'recep_h', %s, 'recepcion', 'EMP-SINTETICA-001', true), "
                "('USR-H-CAJA', 'caja_h', %s, 'caja', 'EMP-SINTETICA-001', true) "
                "ON CONFLICT (id) DO UPDATE SET clave_hash = EXCLUDED.clave_hash, rol = EXCLUDED.rol, activo = true",
                (seguridad.hashear_clave("Clave123!"), seguridad.hashear_clave("Clave123!"), seguridad.hashear_clave("Clave123!")),
            )
            c.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, estado_preparacion, en_inventario) "
                "VALUES ('HAB-H1', 'EST-1', 'doble', 3, 'disponible', 'limpia', true)"
            )
            c.execute(
                "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, motivo, activa) "
                "VALUES ('EXC-H1', 'HAB-H1', %s, %s, 50000, 'base test', true)",
                (HOY, HOY + timedelta(days=30)),
            )
            c.commit()

        self.admin = self._login("admin_h")
        self.recep = self._login("recep_h")
        self.caja = self._login("caja_h")

    def _login(self, usuario: str) -> TestClient:
        c = TestClient(self.app)
        r = c.post("/sesion", json={"usuario": usuario, "clave": "Clave123!"})
        self.assertEqual(r.status_code, 200, r.text)
        return c

    def _idem(self) -> dict:
        self.__class__._n += 1
        return {"Idempotency-Key": f"hsp-{self.__class__._n}"}

    def _reservar(self, personas=2, doc="12.345.678-5", doc_tipo="rut", nombre="Ana Titular"):
        r = self.recep.post(
            "/hotel/reservas",
            headers=self._idem(),
            json={
                "habitacion_id": "HAB-H1",
                "inicio": HOY.isoformat(),
                "fin": (HOY + timedelta(days=2)).isoformat(),
                "personas": personas,
                "huesped": {"nombre": nombre, "documento": doc, "documento_tipo": doc_tipo},
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["reserva_id"]

    def test_migracion_0056_idempotente_y_backfill_titular(self):
        rid = self._reservar(personas=1)
        with psycopg.connect(URL_TEST) as c:
            c.execute("DELETE FROM reserva_huespedes WHERE reserva_id = %s", (rid,))
            c.execute("UPDATE reservas SET adultos = NULL, ninos = NULL WHERE id = %s", (rid,))
            c.commit()
            sql = Path("servicio/migraciones/0056_huespedes_y_ocupacion_llegada.sql").read_text(encoding="utf-8")
            c.execute(sql)
            c.execute(sql)  # segunda ejecución idempotente
            c.commit()
            ad, ni = c.execute("SELECT adultos, ninos FROM reservas WHERE id = %s", (rid,)).fetchone()
            self.assertEqual((ad, ni), (1, 0))
            tit = c.execute(
                "SELECT rol FROM reserva_huespedes WHERE reserva_id = %s", (rid,)
            ).fetchone()
            self.assertEqual(tit[0], "titular")

        # Compatibilidad: reserva migrada con 1 titular puede completar Llegada
        with a_las(HOY, hora=time(15, 30)):
            r_ent = self.recep.post(f"/hotel/reservas/{rid}/entrada", headers=self._idem(), json={})
        self.assertEqual(r_ent.status_code, 200, r_ent.text)

    def test_bloqueo_entrada_si_faltan_huespedes_y_desbloqueo_al_registrar(self):
        rid = self._reservar(personas=2)
        with a_las(HOY, hora=time(15, 30)):
            r_fail = self.recep.post(f"/hotel/reservas/{rid}/entrada", headers=self._idem(), json={})
        self.assertEqual(r_fail.status_code, 409, r_fail.text)
        self.assertIn("Faltan 1", r_fail.json()["detail"])

        # Registrar acompañante
        r_add = self.recep.post(
            f"/hotel/reservas/{rid}/huespedes",
            headers=self._idem(),
            json={
                "rol": "acompanante",
                "nombre": "Luis Acompañante",
                "documento_tipo": "pasaporte",
                "documento": "AB123456",
            },
        )
        self.assertEqual(r_add.status_code, 201, r_add.text)
        self.assertEqual(r_add.json()["faltantes"], 0)
        self.assertTrue(r_add.json()["completo"])

        with a_las(HOY, hora=time(15, 30)):
            r_ok = self.recep.post(f"/hotel/reservas/{rid}/entrada", headers=self._idem(), json={})
        self.assertEqual(r_ok.status_code, 200, r_ok.text)

    def test_ocupacion_capacidad_politicas_no_configuradas_y_con_recargo_append_only(self):
        rid = self._reservar(personas=1)

        # Exceder capacidad (3) -> 409
        r_cap = self.recep.put(
            f"/hotel/reservas/{rid}/ocupacion",
            json={"adultos": 3, "ninos": 1},
        )
        self.assertEqual(r_cap.status_code, 409, r_cap.text)

        # Política sin configurar (None) -> $0 y aviso claro, sin bloquear Llegada
        r_sin_pol = self.recep.put(
            f"/hotel/reservas/{rid}/ocupacion",
            json={"adultos": 2, "ninos": 1},
        )
        self.assertEqual(r_sin_pol.status_code, 200, r_sin_pol.text)
        self.assertEqual(r_sin_pol.json()["delta_clp"], 0)
        self.assertTrue(len(r_sin_pol.json()["avisos"]) >= 1)

        # Configurar políticas: persona extra $10.000/noche, niño $5.000/noche, edad_nino_hasta=12
        pol = self.admin.get("/hotel/politicas").json()["cuerpo"]
        pol["ninos_cama"]["recargo_persona_extra_clp"] = 10000
        pol["ninos_cama"]["edad_nino_hasta"] = 12
        pol["ninos_cama"]["recargo_nino"] = {"modo": "monto_clp", "valor": 5000, "por": "noche"}
        r_save = self.admin.put("/hotel/politicas", headers=self._idem(), json={"cuerpo": pol})
        self.assertEqual(r_save.status_code, 200, r_save.text)

        # Bajar a 1 adulto, 0 niños primero
        r_baja = self.recep.put(f"/hotel/reservas/{rid}/ocupacion", json={"adultos": 1, "ninos": 0})
        self.assertEqual(r_baja.status_code, 200, r_baja.text)

        # Subir a 2 adultos, 1 niño (2 noches): +1 adulto ($20.000) + 1 niño ($10.000) = $30.000
        r_sube = self.recep.put(f"/hotel/reservas/{rid}/ocupacion", json={"adultos": 2, "ninos": 1})
        self.assertEqual(r_sube.status_code, 200, r_sube.text)
        self.assertEqual(r_sube.json()["delta_clp"], 30000)

        det = self.recep.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(det["cuenta"]["cargos_netos_clp"], 30000)

        # Reducir a 2 adultos, 0 niños: reverso append-only (-$10.000 -> neto $20.000)
        r_adj = self.recep.put(f"/hotel/reservas/{rid}/ocupacion", json={"adultos": 2, "ninos": 0})
        self.assertEqual(r_adj.status_code, 200, r_adj.text)
        self.assertEqual(r_adj.json()["delta_clp"], -10000)
        det2 = self.recep.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(det2["cuenta"]["cargos_netos_clp"], 20000)
        self.assertTrue(any(c["tipo"] == "reverso" for c in det2["cargos"]))

    def test_crud_huespedes_busqueda_roles_y_auditoria_sin_pii(self):
        rid = self._reservar(personas=2, doc="12.345.678-5", doc_tipo="rut", nombre="Titular Uno")

        # Búsqueda por documento: caja -> 403; recepcion -> 200
        self.assertEqual(self.caja.get("/hotel/huespedes/busqueda", params={"documento": "12345678-5"}).status_code, 403)
        r_bus = self.recep.get("/hotel/huespedes/busqueda", params={"documento": "12345678-5", "documento_tipo": "rut"})
        self.assertEqual(r_bus.status_code, 200, r_bus.text)
        self.assertEqual(r_bus.json()["total"], 1)
        self.assertEqual(r_bus.json()["huespedes"][0]["documento"], "12.345.678-5")

        # Caja ve lista de huéspedes sin el campo documento
        r_caja = self.caja.get(f"/hotel/reservas/{rid}/huespedes")
        self.assertEqual(r_caja.status_code, 200)
        self.assertNotIn("documento", r_caja.json()["huespedes"][0])

        # Agregar acompañante
        r_add = self.recep.post(
            f"/hotel/reservas/{rid}/huespedes",
            json={"nombre": "Marta Acompañante", "documento_tipo": "rut", "documento": "11.111.111-1"},
        )
        self.assertEqual(r_add.status_code, 201, r_add.text)
        acomp = next(h for h in r_add.json()["huespedes"] if h["rol"] == "acompanante")
        tit = next(h for h in r_add.json()["huespedes"] if h["rol"] == "titular")

        # Editar titular sincroniza reservas.huesped_nombre
        r_ed = self.recep.put(
            f"/hotel/reservas/{rid}/huespedes/{tit['huesped_id']}",
            json={"nombre": "Titular Renombrado"},
        )
        self.assertEqual(r_ed.status_code, 200, r_ed.text)
        self.assertEqual(self.recep.get(f"/hotel/reservas/{rid}").json()["huesped_nombre"], "Titular Renombrado")

        # No se puede quitar al titular (409)
        self.assertEqual(self.recep.delete(f"/hotel/reservas/{rid}/huespedes/{tit['huesped_id']}").status_code, 409)

        # Quitar acompañante (200)
        r_del = self.recep.delete(f"/hotel/reservas/{rid}/huespedes/{acomp['huesped_id']}")
        self.assertEqual(r_del.status_code, 200, r_del.text)
        self.assertEqual(r_del.json()["faltantes"], 1)

        # Auditoría sin PII (sin nombres ni documentos en resultado)
        with psycopg.connect(URL_TEST) as c:
            auds = c.execute(
                "SELECT accion, resultado FROM auditoria WHERE accion LIKE 'reserva_%'"
            ).fetchall()
            self.assertTrue(len(auds) >= 3)
            for _, res in auds:
                self.assertNotIn("Marta", res)
                self.assertNotIn("11.111.111-1", res)
                self.assertNotIn("Titular", res)


if __name__ == "__main__":
    unittest.main()
