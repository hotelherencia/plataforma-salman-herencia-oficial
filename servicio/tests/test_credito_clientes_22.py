"""Pruebas Contable 2.2 (#392 / RES-008 / REC-003 / FIN-002):
políticas de crédito por cliente/empresa, límite, vencimiento, tramos de antigüedad
(0-30, 31-60, 61-90, +90 días) y abonos append-only e idempotentes."""
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
    "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_392",
)
HOY = date(2026, 11, 20)


class CreditoClientes22Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario="admin_cr", admin_clave="Clave123!",
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
                "TRUNCATE cxc_abonos, cuentas_por_cobrar, imputaciones_pago, reserva_huespedes, huespedes, "
                "reasignaciones, liquidaciones, pagos, cargos, reserva_noches, reservas, clientes, "
                "tarifas, excepciones_precio, habitaciones, tareas_operativas, claves_idempotencia, "
                "auditoria, sesiones, usuarios CASCADE"
            )
            clave_h = seguridad.hashear_clave("Clave123!")
            c.execute(
                "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                "('USR-CR-ADM', 'admin_cr', %s, 'admin_hotel', 'EMP-SINTETICA-001', true), "
                "('USR-CR-REC', 'recep_cr', %s, 'recepcion', 'EMP-SINTETICA-001', true), "
                "('USR-CR-CAJ', 'caja_cr', %s, 'caja', 'EMP-SINTETICA-001', true)",
                (clave_h, clave_h, clave_h),
            )
            for hid in ("HAB-CR1", "HAB-CR2", "HAB-CR3", "HAB-CR4"):
                c.execute(
                    "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, estado_preparacion, en_inventario) "
                    "VALUES (%s, 'EST-1', 'doble', 2, 'disponible', 'limpia', true)",
                    (hid,),
                )
                c.execute(
                    "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, motivo, activa) "
                    "VALUES (%s, %s, '2026-01-01', '2027-01-01', 60000, 'tarifa credito', true)",
                    (f"EXC-{hid}", hid),
                )
            c.commit()

        self.admin = self._login("admin_cr")
        self.recep = self._login("recep_cr")
        self.caja = self._login("caja_cr")

    def _login(self, usuario: str) -> TestClient:
        c = TestClient(self.app)
        r = c.post("/sesion", json={"usuario": usuario, "clave": "Clave123!"})
        self.assertEqual(r.status_code, 200, r.text)
        return c

    def _idem(self) -> dict:
        self.__class__._n += 1
        return {"Idempotency-Key": f"cr-{self.__class__._n}"}

    def _crear_cliente(self, rut="76.123.456-0", nombre="Empresa Convenio SpA"):
        r = self.admin.post(
            "/hotel/clientes",
            headers=self._idem(),
            json={"rut": rut, "nombre": nombre, "tipo": "empresa"},
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["id"]

    def _reservar_y_entrar(self, hab: str, rut: str, nombre: str, noches: int = 2) -> str:
        r = self.recep.post(
            "/hotel/reservas",
            headers=self._idem(),
            json={
                "habitacion_id": hab,
                "inicio": HOY.isoformat(),
                "fin": (HOY + timedelta(days=noches)).isoformat(),
                "personas": 1,
                "huesped": {"nombre": nombre, "documento": rut, "documento_tipo": "rut"},
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        rid = r.json()["reserva_id"]
        with a_las(HOY, hora=time(15, 30)):
            re = self.recep.post(f"/hotel/reservas/{rid}/entrada", headers=self._idem(), json={})
            self.assertEqual(re.status_code, 200, re.text)
        return rid

    def test_migracion_0064_idempotente_y_politicas_solo_admin_con_pci(self):
        sql = Path("servicio/migraciones/0064_credito_clientes_cxc.sql").read_text(encoding="utf-8")
        with psycopg.connect(URL_TEST) as c:
            c.execute(sql)
            c.execute(sql)
            c.commit()

        cid = self._crear_cliente()

        # Recepción y caja NO pueden editar política de crédito -> 403
        for cli in (self.recep, self.caja):
            r = cli.put(
                f"/hotel/clientes/{cid}/credito",
                headers=self._idem(),
                json={"politica_credito": "credito_autorizado", "cupo_credito_clp": 200000, "plazo_dias": 30},
            )
            self.assertEqual(r.status_code, 403)

        # PCI: rechaza número de tarjeta largo o últimos 4 no numéricos -> 422
        r_pci = self.admin.put(
            f"/hotel/clientes/{cid}/credito",
            headers=self._idem(),
            json={
                "politica_credito": "garantia_salida",
                "garantia_tarjeta_marca": "4532111122223333",
                "garantia_tarjeta_ultimos4": "3333",
            },
        )
        self.assertEqual(r_pci.status_code, 422)

        # Las 3 políticas funcionan desde el mantenedor
        for payload in (
            {"politica_credito": "credito_autorizado", "cupo_credito_clp": 300000, "plazo_dias": 30},
            {"politica_credito": "garantia_salida", "garantia_tarjeta_marca": "Visa", "garantia_tarjeta_ultimos4": "4242"},
            {"politica_credito": "pago_al_registrarse", "cupo_credito_clp": 0, "plazo_dias": 0},
        ):
            ok = self.admin.put(f"/hotel/clientes/{cid}/credito", headers=self._idem(), json=payload)
            self.assertEqual(ok.status_code, 200, ok.text)
            self.assertEqual(ok.json()["politica_credito"], payload["politica_credito"])

    def test_limite_credito_salida_autorizada_tramos_antiguedad_y_abonos(self):
        cid = self._crear_cliente("76.123.456-0", "Constructora Andina SpA")

        # 1. Sin crédito (pago_al_registrarse): salida a crédito bloqueada -> 409
        rid1 = self._reservar_y_entrar("HAB-CR1", "76.123.456-0", "Constructora Andina SpA", noches=2)  # 120.000
        r_bloq = self.recep.post(
            f"/hotel/reservas/{rid1}/salida-credito",
            headers=self._idem(),
            json={"cliente_id": cid},
        )
        self.assertEqual(r_bloq.status_code, 409)

        # 2. Habilitar crédito autorizado por $150.000 a 30 días
        r_cfg = self.admin.put(
            f"/hotel/clientes/{cid}/credito",
            headers=self._idem(),
            json={"politica_credito": "credito_autorizado", "cupo_credito_clp": 150000, "plazo_dias": 30},
        )
        self.assertEqual(r_cfg.status_code, 200, r_cfg.text)

        # 3. Salida a crédito de rid1 ($120.000 <= $150.000) -> 201 y crea CxC + tarea limpieza
        r_sal1 = self.recep.post(
            f"/hotel/reservas/{rid1}/salida-credito",
            headers=self._idem(),
            json={"cliente_id": cid, "nota": "Convenio 30 días"},
        )
        self.assertEqual(r_sal1.status_code, 201, r_sal1.text)
        cxc1_id = r_sal1.json()["cxc_id"]
        self.assertEqual(r_sal1.json()["saldo_a_credito_clp"], 120000)

        # 4. Segunda reserva ($120.000) supera límite ($240.000 > $150.000) -> 409 con supera_limite=True
        rid2 = self._reservar_y_entrar("HAB-CR2", "76.123.456-0", "Constructora Andina SpA", noches=2)
        r_exc = self.recep.post(
            f"/hotel/reservas/{rid2}/salida-credito",
            headers=self._idem(),
            json={"cliente_id": cid, "confirmar_exceso_cupo": True},  # recepción no puede autorizar exceso
        )
        self.assertEqual(r_exc.status_code, 409)
        self.assertTrue(r_exc.json().get("supera_limite"))

        # Admin SÍ puede autorizar exceso explícitamente
        r_exc_adm = self.admin.post(
            f"/hotel/reservas/{rid2}/salida-credito",
            headers=self._idem(),
            json={"cliente_id": cid, "confirmar_exceso_cupo": True},
        )
        self.assertEqual(r_exc_adm.status_code, 201, r_exc_adm.text)
        cxc2_id = r_exc_adm.json()["cxc_id"]
        self.assertTrue(r_exc_adm.json()["alerta_limite"])

        # Ficha de reserva refleja la alerta de límite superado
        det = self.recep.get(f"/hotel/reservas/{rid2}").json()
        self.assertTrue(det["credito_cliente"]["supera_limite"])
        self.assertGreater(len(det["credito_cliente"]["alertas"]), 0)

        # 5. Simular vencimientos en los 4 tramos (0-30, 31-60, 61-90, mas_90)
        rid3 = self._reservar_y_entrar("HAB-CR3", "76.123.456-0", "Constructora Andina SpA", noches=1)  # 60.000
        rid4 = self._reservar_y_entrar("HAB-CR4", "76.123.456-0", "Constructora Andina SpA", noches=1)  # 60.000
        cxc3_id = self.admin.post(
            f"/hotel/reservas/{rid3}/salida-credito",
            headers=self._idem(),
            json={"cliente_id": cid, "confirmar_exceso_cupo": True},
        ).json()["cxc_id"]
        cxc4_id = self.admin.post(
            f"/hotel/reservas/{rid4}/salida-credito",
            headers=self._idem(),
            json={"cliente_id": cid, "confirmar_exceso_cupo": True},
        ).json()["cxc_id"]

        hoy_real = date.today()
        with psycopg.connect(URL_TEST) as c:
            c.execute("UPDATE cuentas_por_cobrar SET fecha_vencimiento = %s WHERE id = %s", (hoy_real - timedelta(days=10), cxc1_id))
            c.execute("UPDATE cuentas_por_cobrar SET fecha_vencimiento = %s WHERE id = %s", (hoy_real - timedelta(days=45), cxc2_id))
            c.execute("UPDATE cuentas_por_cobrar SET fecha_vencimiento = %s WHERE id = %s", (hoy_real - timedelta(days=75), cxc3_id))
            c.execute("UPDATE cuentas_por_cobrar SET fecha_vencimiento = %s WHERE id = %s", (hoy_real - timedelta(days=120), cxc4_id))
            c.commit()

        # Recepción no accede al listado contable de CxC -> 403; Caja sí
        self.assertEqual(self.recep.get("/hotel/contabilidad/cuentas-por-cobrar").status_code, 403)
        rcxc = self.caja.get("/hotel/contabilidad/cuentas-por-cobrar")
        self.assertEqual(rcxc.status_code, 200, rcxc.text)
        tramos = rcxc.json()["tramos"]
        self.assertEqual(tramos["0-30"]["monto_clp"], 120000)
        self.assertEqual(tramos["31-60"]["monto_clp"], 120000)
        self.assertEqual(tramos["61-90"]["monto_clp"], 60000)
        self.assertEqual(tramos["mas_90"]["monto_clp"], 60000)
        self.assertEqual(rcxc.json()["total_vencido_clp"], 360000)

        # 6. Abonos append-only e idempotentes sobre cxc1
        clave_ab = self._idem()
        ab1 = self.caja.post(
            f"/hotel/contabilidad/cuentas-por-cobrar/{cxc1_id}/abonos",
            headers=clave_ab,
            json={"monto_clp": 50000, "medio": "transferencia", "comprobante": "TRF-01"},
        )
        self.assertEqual(ab1.status_code, 201, ab1.text)
        self.assertEqual(ab1.json()["estado"], "parcial")
        self.assertEqual(ab1.json()["saldo_pendiente_clp"], 70000)

        # Trigger append-only prohíbe UPDATE/DELETE en cxc_abonos
        abono_id = ab1.json()["abonos"][0]["abono_id"]
        with psycopg.connect(URL_TEST) as c:
            with self.assertRaises(psycopg.errors.RaiseException):
                c.execute("DELETE FROM cxc_abonos WHERE id = %s", (abono_id,))
            c.rollback()

        # Abono que supera saldo -> 409; abono exacto -> pagada
        self.assertEqual(
            self.caja.post(
                f"/hotel/contabilidad/cuentas-por-cobrar/{cxc1_id}/abonos",
                headers=self._idem(),
                json={"monto_clp": 90000, "medio": "transferencia"},
            ).status_code,
            409,
        )
        ab2 = self.caja.post(
            f"/hotel/contabilidad/cuentas-por-cobrar/{cxc1_id}/abonos",
            headers=self._idem(),
            json={"monto_clp": 70000, "medio": "transferencia"},
        )
        self.assertEqual(ab2.status_code, 201, ab2.text)
        self.assertEqual(ab2.json()["estado"], "pagada")
        self.assertEqual(ab2.json()["saldo_pendiente_clp"], 0)


if __name__ == "__main__":
    unittest.main()
