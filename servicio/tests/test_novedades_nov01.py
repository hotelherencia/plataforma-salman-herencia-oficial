"""Pruebas SPEC-NOV-01 (#448): Libro de novedades turno a turno,
asignación de estacionamiento (~14 cupos) y conteos de desayunos/bebestibles."""
import os
import unittest
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient

from servicio import contabilidad, migracion, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_nov01",
)


class LibroNovedadesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(
            configuracion=Configuracion(
                host="127.0.0.1",
                puerto=0,
                database_url=URL_TEST,
                cookie_segura=False,
                origen_front=None,
                admin_usuario="admin_nov",
                admin_clave="Clave123!",
            )
        )
        cls.client_cm = TestClient(cls.app)
        cls.client = cls.client_cm.__enter__()
        cls._n = 0

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "TRUNCATE conteos_turno_fnb, estacionamiento_asignaciones, libro_novedades, "
                "habitaciones, claves_idempotencia, auditoria, sesiones, usuarios CASCADE"
            )
            clave_h = seguridad.hashear_clave("Clave123!")
            c.execute(
                "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                "('USR-NOV-ADM', 'admin_nov', %s, 'admin_hotel', 'EMP-SINTETICA-001', true), "
                "('USR-NOV-REC', 'recep_nov', %s, 'recepcion', 'EMP-SINTETICA-001', true), "
                "('USR-NOV-ASE', 'aseo_nov', %s, 'aseo', 'EMP-SINTETICA-001', true)",
                (clave_h, clave_h, clave_h),
            )
            c.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, estado_preparacion, en_inventario) "
                "VALUES ('HAB-01', 'EST-1', 'doble', 2, 'disponible', 'limpia', true)"
            )
            c.commit()

        self.admin = self._login("admin_nov")
        self.recep = self._login("recep_nov")
        self.aseo = self._login("aseo_nov")

    def _login(self, usuario: str) -> TestClient:
        c = TestClient(self.app)
        r = c.post("/sesion", json={"usuario": usuario, "clave": "Clave123!"})
        self.assertEqual(r.status_code, 200, r.text)
        return c

    def _idem(self) -> dict:
        self.__class__._n += 1
        return {"Idempotency-Key": f"nov-{self.__class__._n}"}

    def test_migracion_0073_idempotente_y_permisos(self):
        sql = Path("servicio/migraciones/0073_novedades_estacionamiento_conteos.sql").read_text(encoding="utf-8")
        with psycopg.connect(URL_TEST) as c:
            c.execute(sql)
            c.execute(sql)
            c.commit()
        self.assertEqual(self.aseo.get("/hotel/novedades").status_code, 403)
        self.assertEqual(self.recep.get("/hotel/novedades").status_code, 200)

    def test_flujo_novedades_estacionamiento_y_conteos(self):
        hoy = contabilidad.hoy_chile().isoformat()
        # 1. Entrega de turno idempotente
        hdr = self._idem()
        r1 = self.recep.post(
            "/hotel/novedades",
            headers=hdr,
            json={
                "fecha_contable": hoy,
                "turno": "manana",
                "resumen": "Todo tranquilo, 2 llegadas confirmadas para la tarde.",
                "desayunos_servidos": 12,
                "bebestibles_detalle": [{"nombre": "Agua mineral", "cantidad": 4}],
            },
        )
        self.assertEqual(r1.status_code, 201, r1.text)
        r1_dup = self.recep.post(
            "/hotel/novedades",
            headers=hdr,
            json={
                "fecha_contable": hoy,
                "turno": "manana",
                "resumen": "Todo tranquilo, 2 llegadas confirmadas para la tarde.",
                "desayunos_servidos": 12,
                "bebestibles_detalle": [{"nombre": "Agua mineral", "cantidad": 4}],
            },
        )
        self.assertEqual(r1_dup.json()["novedad_id"], r1.json()["novedad_id"])

        # 2. Estacionamiento: cupo fuera de rango (>14) -> 422; cupo 3 válido -> 200
        self.assertEqual(
            self.recep.put(
                "/hotel/estacionamiento/asignacion",
                json={"fecha": hoy, "cupo": 15, "habitacion_id": "HAB-01", "patente": "ABCD12", "estado": "ocupado"},
            ).status_code,
            422,
        )
        r_est = self.recep.put(
            "/hotel/estacionamiento/asignacion",
            json={"fecha": hoy, "cupo": 3, "habitacion_id": "HAB-01", "patente": "abcd12", "estado": "ocupado"},
        )
        self.assertEqual(r_est.status_code, 200, r_est.text)
        self.assertEqual(r_est.json()["patente"], "ABCD12")

        # 3. Conteo operativo F&B
        r_fnb = self.recep.post(
            "/hotel/novedades/conteos",
            headers=self._idem(),
            json={"fecha_contable": hoy, "turno": "manana", "categoria": "bebestible", "cantidad": 6, "observacion": "Jugos naturales"},
        )
        self.assertEqual(r_fnb.status_code, 201, r_fnb.text)

        # 4. Lectura consolidada del día
        dia = self.recep.get("/hotel/novedades", params={"fecha": hoy}).json()
        self.assertEqual(dia["cupos_estacionamiento"], 14)
        self.assertEqual(dia["estacionamiento_ocupados"], 1)
        self.assertEqual(dia["estacionamiento_libres"], 13)
        self.assertEqual(dia["resumen_fnb"]["desayunos_total"], 12)
        self.assertEqual(dia["resumen_fnb"]["bebestibles_total"], 6)

        # 5. Liberar cupo 3
        r_lib = self.recep.put(
            "/hotel/estacionamiento/asignacion",
            json={"fecha": hoy, "cupo": 3, "estado": "liberado"},
        )
        self.assertEqual(r_lib.status_code, 200, r_lib.text)
        self.assertEqual(self.recep.get("/hotel/novedades", params={"fecha": hoy}).json()["estacionamiento_ocupados"], 0)


if __name__ == "__main__":
    unittest.main()
