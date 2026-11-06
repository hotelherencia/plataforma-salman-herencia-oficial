"""Indicador financiero `ingresos_periodo_clp` (#297, DECISIÓN 2026-11-06).

D-ROL-01 ratificada (opción a): no se crea `gerencia`; el indicador lo ve
solo `administrador`. Definición: pagos confirmados por fecha de pago dentro
del periodo (`pagos` join `reservas`) — lo cobrado, no lo reservado.
"""
import os
import unittest
import uuid
from datetime import date, timedelta

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
HOY = date.today()


class IngresosPeriodoTest(unittest.TestCase):
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
                "TRUNCATE auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "reservas, tarifas, tareas_operativas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            seguridad.crear_usuario(conexion, EMPRESA, "recepcion1", "recepcion", "clave-recepcion")
            conexion.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                "VALUES ('HAB-FIN-1', 'EST-SINT-001', 'doble', 2)"
            )
            conexion.execute(
                "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                "VALUES ('TAR-FIN', 'HAB-FIN-1', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.admin = TestClient(self.app)
        self.admin.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.recepcion = TestClient(self.app)
        self.recepcion.post("/sesion", json={"usuario": "recepcion1", "clave": "clave-recepcion"})

    def clave(self):
        return f"fin-{uuid.uuid4().hex[:10]}"

    def reservar_y_pagar(self, inicio, fin, monto, cliente=None):
        cliente = cliente or self.admin
        r = cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-FIN-1", "inicio": str(inicio), "fin": str(fin),
                  "huesped": {"nombre": "Huésped Fin", "documento": "DOC-FIN"}},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(r.status_code, 201, r.text)
        rid = r.json()["reserva_id"]
        p = cliente.post(
            f"/hotel/reservas/{rid}/pagos",
            json={"monto_clp": monto, "clave": f"pago-{uuid.uuid4().hex[:8]}", "modo": "manual"},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(p.status_code, 201, p.text)
        return rid

    def indicadores(self, cliente, desde, hasta):
        r = cliente.get("/hotel/indicadores", params={"desde": str(desde), "hasta": str(hasta)})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_admin_ve_ingresos_del_periodo(self):
        ayer = HOY - timedelta(days=1)
        manana = HOY + timedelta(days=1)
        self.reservar_y_pagar(ayer, HOY, 30000)
        self.reservar_y_pagar(HOY, manana, 70000)
        datos = self.indicadores(self.admin, ayer, manana + timedelta(days=1))
        indicador = datos["periodo_indicadores"]["ingresos_periodo_clp"]
        self.assertEqual(indicador["valor"], 100000)
        self.assertEqual(indicador["unidad"], "CLP")

    def test_recepcion_no_ve_el_indicador_financiero(self):
        ayer = HOY - timedelta(days=1)
        manana = HOY + timedelta(days=1)
        self.reservar_y_pagar(ayer, HOY, 30000)
        datos = self.indicadores(self.recepcion, ayer, manana + timedelta(days=1))
        self.assertNotIn("ingresos_periodo_clp", datos["periodo_indicadores"])

    def test_pagos_fuera_del_periodo_no_suman(self):
        hace_10 = HOY - timedelta(days=10)
        self.reservar_y_pagar(hace_10, hace_10 + timedelta(days=2), 50000)
        # el pago se registró hace 10 días (fecha de pago, no de la reserva):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("UPDATE pagos SET creado_en = %s::date WHERE reserva_id IN "
                             "(SELECT id FROM reservas WHERE huesped_documento = 'DOC-FIN')",
                             (str(hace_10),))
            conexion.commit()
        datos = self.indicadores(self.admin, HOY - timedelta(days=1), HOY + timedelta(days=2))
        self.assertEqual(datos["periodo_indicadores"]["ingresos_periodo_clp"]["valor"], 0)


if __name__ == "__main__":
    unittest.main()
