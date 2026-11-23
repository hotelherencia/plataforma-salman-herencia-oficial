"""Pruebas PR B (RES-007): titular con varias habitaciones en un grupo.

Cubre:
- Migración 0060 aditiva e idempotente (`reservas_grupo`, `grupo_id`, `titular_aloja`).
- Creación atómica de 2 habitaciones bajo un titular (familia de 4+ personas) preservando
  la invariante `1 reserva = 1 habitación` en dominio, cargos, pagos e imputaciones.
- Rollback atómico total si la 2ª habitación no tiene cupo o excede capacidad (sin
  dejar ni el grupo ni la 1ª habitación persistidos).
- `POST /hotel/grupos/{grupo_id}/reservas` (nueva habitación y vínculo de existente).
- `GET /hotel/grupos/{grupo_id}` (totales consolidados sin duplicación, restricción de documento a caja, 403 ajeno).
- `POST /hotel/grupos/{grupo_id}/entrada` (Llegada en lote atómica: bloquea con 409 y rollback
  si alguna habitación tiene huéspedes incompletos o `titular_aloja=false` sin ocupantes,
  y pasa en lote al completar todos los huéspedes).
- Auditoría sin PII (sin nombres ni documentos).
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
    "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_paso2",
)
HOY = date(2026, 11, 20)


class GruposHabitacionesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario="admin_g", admin_clave="Clave123!",
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
                "imputaciones_pago, pagos, cargos, reserva_noches, reservas, reservas_grupo, "
                "clientes, tarifas, excepciones_precio, habitaciones, politicas_hotel, "
                "claves_idempotencia, auditoria, sesiones, usuarios CASCADE"
            )
            clave_h = seguridad.hashear_clave("Clave123!")
            c.execute(
                "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                "('USR-G-ADMIN', 'admin_g', %s, 'admin_hotel', 'EMP-SINTETICA-001', true), "
                "('USR-G-RECEP', 'recep_g', %s, 'recepcion', 'EMP-SINTETICA-001', true), "
                "('USR-G-CAJA', 'caja_g', %s, 'caja', 'EMP-SINTETICA-001', true)",
                (clave_h, clave_h, clave_h),
            )
            c.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, estado_preparacion, en_inventario) VALUES "
                "('HAB-G1', 'EST-1', 'matrimonial', 2, 'disponible', 'limpia', true), "
                "('HAB-G2', 'EST-1', 'doble', 2, 'disponible', 'limpia', true), "
                "('HAB-G3', 'EST-1', 'single', 1, 'disponible', 'limpia', true)"
            )
            for hid, precio in (("HAB-G1", 60000), ("HAB-G2", 55000), ("HAB-G3", 45000)):
                c.execute(
                    "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, motivo, activa) "
                    "VALUES (%s, %s, %s, %s, %s, 'tarifa grupo test', true)",
                    (f"EXC-{hid}", hid, HOY, HOY + timedelta(days=30), precio),
                )
            c.commit()

        self.admin = self._login("admin_g")
        self.recep = self._login("recep_g")
        self.caja = self._login("caja_g")

    def _login(self, usuario: str) -> TestClient:
        c = TestClient(self.app)
        r = c.post("/sesion", json={"usuario": usuario, "clave": "Clave123!"})
        self.assertEqual(r.status_code, 200, r.text)
        return c

    def _idem(self) -> dict:
        self.__class__._n += 1
        return {"Idempotency-Key": f"grp-{self.__class__._n}"}

    def test_migracion_0060_es_idempotente(self):
        sql = Path("servicio/migraciones/0060_reservas_grupo.sql").read_text(encoding="utf-8")
        with psycopg.connect(URL_TEST) as c:
            c.execute(sql)
            c.execute(sql)
            c.commit()

    def test_crear_grupo_dos_habitaciones_familia_y_cuentas_sin_duplicacion(self):
        inicio = HOY.isoformat()
        fin = (HOY + timedelta(days=2)).isoformat()
        r = self.recep.post(
            "/hotel/grupos",
            headers=self._idem(),
            json={
                "titular": {"nombre": "Carlos Familia", "documento": "12.345.678-5", "documento_tipo": "rut"},
                "canal": "recepcion",
                "notas": "Habitaciones comunicadas por balcón (padres + 2 hijos)",
                "habitaciones": [
                    {
                        "habitacion_id": "HAB-G1",
                        "inicio": inicio,
                        "fin": fin,
                        "adultos": 2,
                        "ninos": 0,
                        "titular_aloja": True,
                        "huespedes": [{"nombre": "María Esposa", "rol": "acompanante"}],
                    },
                    {
                        "habitacion_id": "HAB-G2",
                        "inicio": inicio,
                        "fin": fin,
                        "adultos": 1,
                        "ninos": 1,
                        "titular_aloja": False,
                        "huespedes": [
                            {"nombre": "Sofía Hija", "rol": "acompanante", "es_nino": False},
                            {"nombre": "Tomás Hijo", "rol": "acompanante", "es_nino": True},
                        ],
                    },
                ],
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        g = r.json()
        self.assertTrue(g["grupo_id"].startswith("GRP-"))
        self.assertEqual(len(g["reservas"]), 2)
        self.assertEqual(g["resumen"]["total_habitaciones"], 2)
        # 2 noches × 60.000 + 2 noches × 55.000 = 230.000 sin duplicación
        self.assertEqual(g["resumen"]["total_aceptado_clp"], 230000)
        self.assertTrue(g["resumen"]["huespedes_completos"])

        hab1 = next(x for x in g["reservas"] if x["habitacion_id"] == "HAB-G1")
        hab2 = next(x for x in g["reservas"] if x["habitacion_id"] == "HAB-G2")
        self.assertTrue(hab1["titular_aloja"])
        self.assertFalse(hab2["titular_aloja"])
        self.assertEqual(hab1["huespedes"]["registrados"], 2)
        self.assertEqual(hab2["huespedes"]["registrados"], 2)

        # Cada reserva mantiene su ficha individual y referencia al grupo
        d1 = self.recep.get(f"/hotel/reservas/{hab1['reserva_id']}").json()
        self.assertEqual(d1["grupo_id"], g["grupo_id"])
        self.assertTrue(d1["titular_aloja"])

        # Caja puede leer el grupo pero NO recibe el documento del titular
        gc = self.caja.get(f"/hotel/grupos/{g['grupo_id']}")
        self.assertEqual(gc.status_code, 200, gc.text)
        self.assertNotIn("titular_documento", gc.json())

        # Grupo inexistente -> 403 sin revelar existencia
        self.assertEqual(self.recep.get("/hotel/grupos/GRP-NOEXISTE").status_code, 403)

    def test_crear_grupo_rollback_atomico_si_segunda_habitacion_sin_cupo(self):
        inicio = HOY.isoformat()
        fin = (HOY + timedelta(days=2)).isoformat()
        # Ocupamos HAB-G2 antes
        prev = self.recep.post(
            "/hotel/reservas",
            headers=self._idem(),
            json={
                "habitacion_id": "HAB-G2",
                "inicio": inicio,
                "fin": fin,
                "personas": 1,
                "huesped": {"nombre": "Otro Huésped", "documento": "11.111.111-1", "documento_tipo": "rut"},
            },
        )
        self.assertEqual(prev.status_code, 201, prev.text)

        # Intentamos crear grupo con HAB-G1 (libre) + HAB-G2 (ocupada) -> 409 y rollback total
        r = self.recep.post(
            "/hotel/grupos",
            headers=self._idem(),
            json={
                "titular": {"nombre": "Ana Rollback", "documento": "12.345.678-5", "documento_tipo": "rut"},
                "habitaciones": [
                    {"habitacion_id": "HAB-G1", "inicio": inicio, "fin": fin, "adultos": 1, "titular_aloja": True},
                    {"habitacion_id": "HAB-G2", "inicio": inicio, "fin": fin, "adultos": 1, "titular_aloja": False},
                ],
            },
        )
        self.assertEqual(r.status_code, 409, r.text)

        # Verificar que NO quedó ni el grupo ni la reserva de HAB-G1 en BD
        with psycopg.connect(URL_TEST) as c:
            n_grupos = c.execute("SELECT COUNT(*) FROM reservas_grupo").fetchone()[0]
            n_g1 = c.execute("SELECT COUNT(*) FROM reservas WHERE habitacion_id = 'HAB-G1'").fetchone()[0]
            self.assertEqual(n_grupos, 0)
            self.assertEqual(n_g1, 0)

    def test_agregar_reserva_a_grupo_y_llegada_en_lote_atomica(self):
        inicio = HOY.isoformat()
        fin = (HOY + timedelta(days=2)).isoformat()

        # 1. Crear grupo con 1 habitación (HAB-G1, 1 adulto titular)
        r = self.recep.post(
            "/hotel/grupos",
            headers=self._idem(),
            json={
                "titular": {"nombre": "Luis Lote", "documento": "12.345.678-5", "documento_tipo": "rut"},
                "habitaciones": [
                    {"habitacion_id": "HAB-G1", "inicio": inicio, "fin": fin, "adultos": 1, "titular_aloja": True},
                ],
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        grupo_id = r.json()["grupo_id"]

        # 2. Agregar segunda habitación (HAB-G2, 2 personas, titular_aloja=False, SIN registrar ocupantes aún)
        r_add = self.recep.post(
            f"/hotel/grupos/{grupo_id}/reservas",
            headers=self._idem(),
            json={
                "habitacion_id": "HAB-G2",
                "inicio": inicio,
                "fin": fin,
                "adultos": 2,
                "ninos": 0,
                "titular_aloja": False,
            },
        )
        self.assertEqual(r_add.status_code, 201, r_add.text)
        r2_id = r_add.json()["reserva_id"]
        self.assertEqual(r_add.json()["grupo"]["resumen"]["total_habitaciones"], 2)
        self.assertFalse(r_add.json()["grupo"]["resumen"]["huespedes_completos"])

        # 3. Intentar Llegada en lote: HAB-G1 está completa pero HAB-G2 tiene 0/2 huéspedes -> 409 y rollback total
        with a_las(HOY, hora=time(15, 30)):
            r_ent_fail = self.recep.post(
                f"/hotel/grupos/{grupo_id}/entrada",
                headers=self._idem(),
                json={},
            )
        self.assertEqual(r_ent_fail.status_code, 409, r_ent_fail.text)
        self.assertIn("HAB-G2", r_ent_fail.json()["detail"])

        # Confirmar que HAB-G1 tampoco pasó a en_estadia (rollback atómico)
        g_check = self.recep.get(f"/hotel/grupos/{grupo_id}").json()
        self.assertTrue(all(x["estado"] == "confirmada" for x in g_check["reservas"]))

        # 4. Registrar los 2 ocupantes reales en HAB-G2
        for nom in ("Pedro Acompañante", "Elena Acompañante"):
            rh = self.recep.post(
                f"/hotel/reservas/{r2_id}/huespedes",
                headers=self._idem(),
                json={"nombre": nom, "rol": "acompanante"},
            )
            self.assertEqual(rh.status_code, 201, rh.text)

        # 5. Reintentar Llegada en lote -> 200 y ambas habitaciones pasan a en_estadia con cargos asentados 1:1
        with a_las(HOY, hora=time(15, 30)):
            r_ent_ok = self.recep.post(
                f"/hotel/grupos/{grupo_id}/entrada",
                headers=self._idem(),
                json={},
            )
        self.assertEqual(r_ent_ok.status_code, 200, r_ent_ok.text)
        self.assertEqual(r_ent_ok.json()["total_procesadas"], 2)

        g_final = self.recep.get(f"/hotel/grupos/{grupo_id}").json()
        self.assertTrue(all(x["estado"] == "en_estadia" for x in g_final["reservas"]))
        # Cada habitación asentó sus 2 noches en su propia cuenta; resumen suma sin duplicar
        self.assertEqual(g_final["resumen"]["cargos_netos_clp"], 230000)
        self.assertEqual(g_final["resumen"]["saldo_clp"], 230000)

        # 6. Pagar una sola habitación mantiene cuentas independientes
        r1_id = next(x["reserva_id"] for x in g_final["reservas"] if x["habitacion_id"] == "HAB-G1")
        rp = self.recep.post(
            f"/hotel/reservas/{r1_id}/pagos",
            headers=self._idem(),
            json={"monto_clp": 120000, "clave": "pag-g1", "modo": "manual", "medio": "transferencia"},
        )
        self.assertEqual(rp.status_code, 201, rp.text)
        g_post_pago = self.recep.get(f"/hotel/grupos/{grupo_id}").json()
        self.assertEqual(g_post_pago["resumen"]["pagado_clp"], 120000)
        self.assertEqual(g_post_pago["resumen"]["saldo_clp"], 110000)

        # 7. Auditoría sin PII
        with psycopg.connect(URL_TEST) as c:
            filas = c.execute(
                "SELECT accion, resultado FROM auditoria WHERE accion LIKE 'grupo_%'"
            ).fetchall()
        self.assertGreaterEqual(len(filas), 3)
        for _acc, res in filas:
            self.assertNotIn("Luis Lote", res)
            self.assertNotIn("12.345.678-5", res)

    def test_vincular_reserva_existente_a_grupo(self):
        inicio = HOY.isoformat()
        fin = (HOY + timedelta(days=2)).isoformat()
        # Reserva individual previa en HAB-G3
        r_ind = self.recep.post(
            "/hotel/reservas",
            headers=self._idem(),
            json={
                "habitacion_id": "HAB-G3",
                "inicio": inicio,
                "fin": fin,
                "personas": 1,
                "huesped": {"nombre": "Clara Grupo", "documento": "12.345.678-5", "documento_tipo": "rut"},
            },
        )
        self.assertEqual(r_ind.status_code, 201, r_ind.text)
        rid_ind = r_ind.json()["reserva_id"]

        # Crear grupo con HAB-G1 y vincular la reserva existente HAB-G3
        rg = self.recep.post(
            "/hotel/grupos",
            headers=self._idem(),
            json={
                "titular": {"nombre": "Clara Grupo", "documento": "12.345.678-5", "documento_tipo": "rut"},
                "habitaciones": [
                    {"habitacion_id": "HAB-G1", "inicio": inicio, "fin": fin, "adultos": 1, "titular_aloja": True},
                ],
            },
        )
        self.assertEqual(rg.status_code, 201, rg.text)
        gid = rg.json()["grupo_id"]

        rv = self.recep.post(
            f"/hotel/grupos/{gid}/reservas",
            headers=self._idem(),
            json={"reserva_id": rid_ind, "titular_aloja": False},
        )
        self.assertEqual(rv.status_code, 201, rv.text)
        self.assertEqual(rv.json()["grupo"]["resumen"]["total_habitaciones"], 2)


if __name__ == "__main__":
    unittest.main()
