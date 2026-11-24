"""Pruebas de integración para SPEC-CONV-01 (convenios y cierre de caja) y SPEC-PROV-01 (reserva provisoria)."""
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
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_conv01"
)


class ConveniosYProvisoriaTest(unittest.TestCase):
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
                admin_usuario="admin_conv",
                admin_clave="ClaveSegura123!",
            )
        )
        cls.cm = TestClient(cls.app)
        cls.cm.__enter__()
        cls._n = 0

    @classmethod
    def tearDownClass(cls):
        cls.cm.__exit__(None, None, None)

    def _clave(self) -> dict:
        type(self)._n += 1
        return {"Idempotency-Key": f"conv-prov-{type(self)._n}"}

    def _login(self, usuario: str, clave: str = "ClaveSegura123!") -> TestClient:
        c = TestClient(self.app)
        r = c.post("/sesion", json={"usuario": usuario, "clave": clave})
        assert r.status_code == 200, r.text
        return c

    def setUp(self):
        h = seguridad.hashear_clave("ClaveSegura123!")
        hoy = date.today()
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "TRUNCATE reserva_huespedes, huespedes, convenios_tarifarios, clientes, reasignaciones, "
                "liquidaciones, caja_movimientos, caja_turnos, cierres_diarios, pagos, cargos, "
                "reserva_noches, reservas, reservas_grupo, tarifas, excepciones_precio, habitaciones, "
                "politicas_hotel, claves_idempotencia, auditoria, sesiones, usuarios CASCADE"
            )
            c.execute(
                "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                "('USR-C-ADMIN', 'admin_conv', %s, 'administrador', 'EMP-SINTETICA-001', true), "
                "('USR-C-RECEP', 'recep_conv', %s, 'recepcion', 'EMP-SINTETICA-001', true), "
                "('USR-C-CAJA', 'caja_conv', %s, 'caja', 'EMP-SINTETICA-001', true)",
                (h, h, h),
            )
            c.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, "
                "estado_preparacion, en_inventario) VALUES "
                "('HAB-CONV-01', 'EST-1', 'doble', 2, 'disponible', 'limpia', true), "
                "('HAB-PROV-01', 'EST-1', 'triple', 3, 'disponible', 'limpia', true), "
                "('HAB-PROV-02', 'EST-1', 'doble', 2, 'disponible', 'limpia', true)"
            )
            for hab, precio in (("HAB-CONV-01", 55000), ("HAB-PROV-01", 68000), ("HAB-PROV-02", 55000)):
                c.execute(
                    "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, "
                    "motivo, activa) VALUES (%s, %s, %s, %s, %s, 'base test', true)",
                    (f"EXC-{hab}", hab, hoy - timedelta(days=5), hoy + timedelta(days=60), precio),
                )
            c.commit()
        self.admin = self._login("admin_conv")
        self.recep = self._login("recep_conv")
        self.caja = self._login("caja_conv")

    def test_convenios_tarifarios_y_cierre_de_caja(self):
        hoy = date.today()
        desde = hoy - timedelta(days=2)
        hasta = hoy + timedelta(days=30)

        cli_resp = self.admin.post(
            "/hotel/clientes",
            headers=self._clave(),
            json={"rut": "76123456-0", "nombre": "Club Deportivo BMX", "tipo": "empresa"},
        )
        self.assertIn(cli_resp.status_code, (200, 201), cli_resp.text)
        cliente_id = cli_resp.json()["id"]

        # Recepción no puede crear convenios (403)
        r_forb = self.recep.post(
            "/hotel/convenios",
            headers=self._clave(),
            json={
                "nombre": "No permitido",
                "tipo": "evento",
                "vigencia_desde": desde.isoformat(),
                "vigencia_hasta": hasta.isoformat(),
                "reglas_precio": {"descuento_pct": 10},
            },
        )
        self.assertEqual(r_forb.status_code, 403)

        # Admin crea convenio con tarifa fija para doble ($48.000 vs lista $55.000 -> dif -$7.000)
        r_conv = self.admin.post(
            "/hotel/convenios",
            headers=self._clave(),
            json={
                "nombre": "Delegación BMX 2026",
                "tipo": "delegacion",
                "cliente_id": cliente_id,
                "vigencia_desde": desde.isoformat(),
                "vigencia_hasta": hasta.isoformat(),
                "reglas_precio": {"por_tipo": {"doble": 48000}, "descuento_pct": 10},
                "requiere_abono_pct": 50,
            },
        )
        self.assertEqual(r_conv.status_code, 201, r_conv.text)
        conv_id = r_conv.json()["convenio_id"]

        # Recepción lista convenios vigentes
        r_list = self.recep.get(f"/hotel/convenios?solo_vigentes=true&fecha={hoy.isoformat()}")
        self.assertEqual(r_list.status_code, 200)
        self.assertTrue(any(c["convenio_id"] == conv_id for c in r_list.json()["convenios"]))

        # Recepción reserva aplicando el convenio
        r_res = self.recep.post(
            "/hotel/reservas",
            headers=self._clave(),
            json={
                "habitacion_id": "HAB-CONV-01",
                "inicio": hoy.isoformat(),
                "fin": (hoy + timedelta(days=2)).isoformat(),
                "personas": 2,
                "convenio_id": conv_id,
                "huesped": {"nombre": "Camila Ciclista", "documento": "12345678-5", "documento_tipo": "rut"},
            },
        )
        self.assertEqual(r_res.status_code, 201, r_res.text)
        res = r_res.json()
        self.assertEqual(res["convenio_id"], conv_id)
        self.assertEqual(res["tarifa_lista_clp"], 55000)
        self.assertEqual(res["tarifa_noche_aceptada_clp"], 48000)
        self.assertEqual(res["diferencia_convenio_clp"], -7000)
        self.assertEqual(res["abono_sugerido_pct"], 50)

        # Cierre diario / conciliación muestra la institución y diferencia exacta en CLP
        r_conc = self.caja.get(f"/hotel/caja/conciliacion?fecha={hoy.isoformat()}")
        self.assertEqual(r_conc.status_code, 200, r_conc.text)
        conc = r_conc.json()
        self.assertEqual(len(conc["convenios_aplicados"]), 1)
        item_c = conc["convenios_aplicados"][0]
        self.assertEqual(item_c["convenio_nombre"], "Delegación BMX 2026")
        self.assertEqual(item_c["tarifa_lista_total_clp"], 55000)
        self.assertEqual(item_c["tarifa_aplicada_total_clp"], 48000)
        self.assertEqual(item_c["diferencia_convenio_clp"], -7000)

        # Desactivar convenio impide aplicarlo en nuevas reservas (409)
        r_put = self.admin.put(f"/hotel/convenios/{conv_id}", json={"activo": False})
        self.assertEqual(r_put.status_code, 200)
        self.assertFalse(r_put.json()["activo"])

        r_rech = self.recep.post(
            "/hotel/reservas",
            headers=self._clave(),
            json={
                "habitacion_id": "HAB-CONV-01",
                "inicio": (hoy + timedelta(days=5)).isoformat(),
                "fin": (hoy + timedelta(days=6)).isoformat(),
                "personas": 1,
                "convenio_id": conv_id,
                "huesped": {"nombre": "Otro Pasajero", "documento": "11111111-1", "documento_tipo": "rut"},
            },
        )
        self.assertEqual(r_rech.status_code, 409)

    @a_las(date.today(), time(23, 0))  # el check-in exige la hora de llegada: no depender de la hora real del día
    def test_reserva_provisoria_grupo_bloqueo_llegada_y_reemplazo_real(self):
        hoy = date.today()
        cli_resp = self.admin.post(
            "/hotel/clientes",
            headers=self._clave(),
            json={"rut": "96555444-0", "nombre": "Institución Arauco", "tipo": "empresa"},
        )
        self.assertIn(cli_resp.status_code, (200, 201), cli_resp.text)
        cliente_id = cli_resp.json()["id"]

        r_conv = self.admin.post(
            "/hotel/convenios",
            headers=self._clave(),
            json={
                "nombre": "Convenio Institución Arauco",
                "tipo": "empresa",
                "cliente_id": cliente_id,
                "vigencia_desde": (hoy - timedelta(days=1)).isoformat(),
                "vigencia_hasta": (hoy + timedelta(days=60)).isoformat(),
                "reglas_precio": {"descuento_pct": 10},
                "requiere_abono_pct": 50,
            },
        )
        self.assertEqual(r_conv.status_code, 201, r_conv.text)
        conv_id = r_conv.json()["convenio_id"]

        # Grupo de 5 huéspedes a nombre provisorio de "Institución Arauco" sin cargar RUTs
        r_grp = self.recep.post(
            "/hotel/grupos",
            headers=self._clave(),
            json={
                "titular": {"nombre": "Institución Arauco"},
                "convenio_id": conv_id,
                "es_huesped_provisorio": True,
                "habitaciones": [
                    {
                        "habitacion_id": "HAB-PROV-01",
                        "inicio": hoy.isoformat(),
                        "fin": (hoy + timedelta(days=2)).isoformat(),
                        "adultos": 3,
                        "ninos": 0,
                        "titular_aloja": False,
                    },
                    {
                        "habitacion_id": "HAB-PROV-02",
                        "inicio": hoy.isoformat(),
                        "fin": (hoy + timedelta(days=2)).isoformat(),
                        "adultos": 2,
                        "ninos": 0,
                        "titular_aloja": False,
                    },
                ],
            },
        )
        self.assertEqual(r_grp.status_code, 201, r_grp.text)
        grp = r_grp.json()
        self.assertTrue(grp["es_huesped_provisorio"])
        self.assertEqual(grp["convenio_id"], conv_id)
        self.assertEqual(grp["cliente_id"], cliente_id)
        self.assertEqual(grp["resumen"]["total_personas"], 5)
        rsv_doble = next(r for r in grp["reservas"] if r["habitacion_id"] == "HAB-PROV-02")["reserva_id"]

        # Intento de Llegada mientras sigue provisoria -> 409
        r_ent_bloqueada = self.recep.post(
            f"/hotel/reservas/{rsv_doble}/entrada",
            headers=self._clave(),
        )
        self.assertEqual(r_ent_bloqueada.status_code, 409)
        self.assertIn("provisorio", r_ent_bloqueada.json()["detail"].lower())

        # Cargar los 2 pasajeros reales con RUT en la habitación doble
        r_h1 = self.recep.post(
            f"/hotel/reservas/{rsv_doble}/huespedes",
            json={"nombre": "Pedro Pasajero Uno", "documento": "12345678-5", "documento_tipo": "rut"},
        )
        self.assertEqual(r_h1.status_code, 201, r_h1.text)
        self.assertFalse(r_h1.json()["es_huesped_provisorio"])

        r_h2 = self.recep.post(
            f"/hotel/reservas/{rsv_doble}/huespedes",
            json={"nombre": "Laura Pasajera Dos", "documento": "11111111-1", "documento_tipo": "rut"},
        )
        self.assertEqual(r_h2.status_code, 201, r_h2.text)
        self.assertTrue(r_h2.json()["completo"])

        # Ahora la Llegada pasa a en_estadia y conserva la institución/convenio pagador
        r_ent_ok = self.recep.post(
            f"/hotel/reservas/{rsv_doble}/entrada",
            headers=self._clave(),
        )
        self.assertEqual(r_ent_ok.status_code, 200, r_ent_ok.text)

        r_det = self.recep.get(f"/hotel/reservas/{rsv_doble}")
        self.assertEqual(r_det.status_code, 200)
        det = r_det.json()
        self.assertEqual(det["estado"], "en_estadia")
        self.assertFalse(det["es_huesped_provisorio"])
        self.assertEqual(det["huesped_nombre"], "Pedro Pasajero Uno")
        self.assertEqual(det["convenio_id"], conv_id)
        self.assertEqual(det["cliente_id"], cliente_id)
