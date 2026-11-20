"""Pruebas de integración para #324 (ingresos por canal), #323 (catálogo de roles
fuera del módulo hotel) y #358 (stock en el core con bodegas y reposición)."""
import os
import unittest
import uuid
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


class CanalRolesStockCoreTest(unittest.TestCase):
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
                "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
                "caja_movimientos, movimientos_directos, caja_turnos, cierres_diarios, pagos, cargos, "
                "solicitudes, reservas, tarifas, sesiones, usuarios, habitaciones, clientes, "
                "core_stock_bodega, movimientos_stock, importaciones_productos, productos "
                "RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                "VALUES ('HAB-C-1', 'EST-SINT-001', 'doble', 2), ('HAB-C-2', 'EST-SINT-001', 'doble', 2)"
            )
            conexion.execute(
                "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                "VALUES ('TAR-C-1', 'HAB-C-1', '2026-01-01', '2027-12-31', 60000), "
                "('TAR-C-2', 'HAB-C-2', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        self.assertEqual(self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)

    def idem(self):
        return {"Idempotency-Key": f"k-{uuid.uuid4().hex[:10]}"}

    def test_324_ingresos_por_canal_desde_recepcion_y_landing(self):
        inicio = (HOY + timedelta(days=2)).isoformat()
        fin = (HOY + timedelta(days=4)).isoformat()

        # 1. Reserva directa por teléfono en recepción.
        r1 = self.cliente.post(
            "/hotel/reservas",
            headers=self.idem(),
            json={
                "habitacion_id": "HAB-C-1",
                "inicio": inicio,
                "fin": fin,
                "personas": 2,
                "canal": "telefono",
                "huesped": {"nombre": "Camila Soto", "documento": "11.111.111-1", "documento_tipo": "rut"},
            },
        )
        self.assertEqual(r1.status_code, 201, r1.text)
        self.assertEqual(r1.json()["canal"], "telefono")
        res1_id = r1.json()["reserva_id"]

        # 2. Solicitud pública desde landing → convertida a reserva (hereda canal='landing').
        sol = self.cliente.post(
            "/publico/solicitudes",
            headers=self.idem(),
            json={
                "tipo": "doble",
                "inicio": inicio,
                "fin": fin,
                "personas": 2,
                "huesped_nombre": "Diego Paredes",
                "huesped_contacto": "diego@ejemplo.cl",
            },
        )
        self.assertEqual(sol.status_code, 201, sol.text)
        conv = self.cliente.post(
            f"/hotel/solicitudes/{sol.json()['solicitud_id']}/conversion",
            headers=self.idem(),
        )
        self.assertEqual(conv.status_code, 201, conv.text)
        res2_id = conv.json()["reserva_id"]

        det2 = self.cliente.get(f"/hotel/reservas/{res2_id}")
        self.assertEqual(det2.status_code, 200)
        self.assertEqual(det2.json()["canal"], "landing")

        # 3. Registrar pagos por transferencia en ambas reservas (sin requerir turno de efectivo).
        p1 = self.cliente.post(
            f"/hotel/reservas/{res1_id}/pagos",
            headers=self.idem(),
            json={"monto_clp": 60000, "clave": f"p-{uuid.uuid4().hex[:8]}", "modo": "manual", "medio": "transferencia"},
        )
        self.assertEqual(p1.status_code, 201, p1.text)
        p2 = self.cliente.post(
            f"/hotel/reservas/{res2_id}/pagos",
            headers=self.idem(),
            json={"monto_clp": 50000, "clave": f"p-{uuid.uuid4().hex[:8]}", "modo": "manual", "medio": "transferencia"},
        )
        self.assertEqual(p2.status_code, 201, p2.text)

        # 4. Consultar panel operativo: ingresos_por_canal debe cuadrar con ingresos_periodo_clp.
        desde = HOY.isoformat()
        hasta = (HOY + timedelta(days=1)).isoformat()
        panel = self.cliente.get(f"/hotel/indicadores?desde={desde}&hasta={hasta}")
        self.assertEqual(panel.status_code, 200, panel.text)
        datos = panel.json()
        self.assertFalse(any("canal" in x["indicador"].lower() for x in datos["no_disponibles"]))

        ind = datos["periodo_indicadores"]
        self.assertEqual(ind["ingresos_periodo_clp"]["valor"], 110000)
        canales = ind["ingresos_por_canal"]
        self.assertEqual(canales["valor"], 110000)
        por_canal = {c["canal"]: c for c in canales["por_canal"]}
        self.assertEqual(por_canal["telefono"]["ingresos_clp"], 60000)
        self.assertEqual(por_canal["telefono"]["reservas"], 1)
        self.assertEqual(por_canal["landing"]["ingresos_clp"], 50000)
        self.assertEqual(por_canal["landing"]["reservas"], 1)

    def test_323_catalogo_roles_transversal_fuera_de_hotel(self):
        r = self.cliente.get("/roles")
        self.assertEqual(r.status_code, 200, r.text)
        datos = r.json()
        self.assertIn("core", datos["modulos_activos"])
        self.assertIn("hotel", datos["modulos_activos"])
        self.assertNotIn("cafeteria", datos["modulos_activos"])
        codigos = {rol["codigo"]: rol for rol in datos["roles"]}
        self.assertEqual(codigos["admin_plataforma"]["modulo"], "core")
        self.assertEqual(codigos["administrador"]["modulo"], "core")
        self.assertEqual(codigos["recepcion"]["modulo"], "hotel")
        self.assertEqual(codigos["aseo"]["modulo"], "hotel")
        self.assertTrue(codigos["admin_hotel"]["exige_doble_factor"])
        self.assertFalse(codigos["recepcion"]["exige_doble_factor"])

    def test_358_stock_core_bodegas_reposicion_y_transferencias(self):
        # 1. Bodegas compartidas disponibles desde /core/stock/bodegas.
        bods = self.cliente.get("/core/stock/bodegas")
        self.assertEqual(bods.status_code, 200, bods.text)
        cods = {b["codigo"] for b in bods.json()["bodegas"]}
        self.assertEqual(cods, {"bodega_principal", "minibar", "cafeteria"})

        # 2. Crear productos con stock_minimo (uno sin stock, uno bajo mínimo, uno ok).
        p_cero = self.cliente.post(
            "/hotel/productos", headers=self.idem(),
            json={"nombre": "Agua sin gas", "categoria": "minibar", "precio_clp": 2000,
                  "controla_stock": True, "stock": 0, "stock_minimo": 5},
        )
        self.assertEqual(p_cero.status_code, 201, p_cero.text)

        p_bajo = self.cliente.post(
            "/hotel/productos", headers=self.idem(),
            json={"nombre": "Café espresso", "categoria": "cafeteria", "precio_clp": 3000,
                  "controla_stock": True, "stock": 3, "stock_minimo": 5},
        )
        self.assertEqual(p_bajo.status_code, 201, p_bajo.text)

        p_ok = self.cliente.post(
            "/hotel/productos", headers=self.idem(),
            json={"nombre": "Snack mix", "categoria": "extra", "precio_clp": 2500,
                  "controla_stock": True, "stock": 12, "stock_minimo": 4},
        )
        self.assertEqual(p_ok.status_code, 201, p_ok.text)
        p_ok_id = p_ok.json()["producto_id"]

        # 3. Reporte de reposición y filtro solo_alertas.
        rep = self.cliente.get("/core/stock/reposicion")
        self.assertEqual(rep.status_code, 200, rep.text)
        resumen = rep.json()["resumen"]
        self.assertEqual(resumen["productos_controlados"], 3)
        self.assertEqual(resumen["sin_stock"], 1)
        self.assertEqual(resumen["bajo_minimo"], 1)
        self.assertEqual(resumen["ok"], 1)

        alertas = self.cliente.get("/core/stock/reposicion?solo_alertas=true")
        self.assertEqual(alertas.status_code, 200)
        self.assertEqual(len(alertas.json()["items"]), 2)

        # 4. Transferencia entre bodegas (bodega_principal → minibar) sin alterar stock total.
        tr = self.cliente.post(
            "/core/stock/transferencias", headers=self.idem(),
            json={
                "producto_id": p_ok_id,
                "origen": "bodega_principal",
                "destino": "minibar",
                "cantidad": 4,
                "motivo": "Reposición habitaciones piso 1",
            },
        )
        self.assertEqual(tr.status_code, 200, tr.text)
        self.assertEqual(tr.json()["stock"], 12)
        self.assertEqual(tr.json()["por_bodega"]["bodega_principal"], 8)
        self.assertEqual(tr.json()["por_bodega"]["minibar"], 4)

        # 5. Rechaza transferir más de lo disponible en la bodega origen.
        tr_mal = self.cliente.post(
            "/core/stock/transferencias", headers=self.idem(),
            json={
                "producto_id": p_ok_id,
                "origen": "minibar",
                "destino": "cafeteria",
                "cantidad": 5,
                "motivo": "Exceso",
            },
        )
        self.assertEqual(tr_mal.status_code, 409)


if __name__ == "__main__":
    unittest.main()
