"""Pruebas de devolución formal de saldo a favor (#91 / Q-HOT-04) y soporte
Gemini + reintentos 429 en ModeloHttp (#319 / D-AGT-02)."""
import json
import os
import unittest
import uuid
from datetime import date, time, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.modelo_http import ModeloHttp
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests.apoyo_huespedes import registrar_acompanantes
from servicio.tests.reloj import a_las

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


class DevolucionSaldoTest(unittest.TestCase):
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
                "solicitudes, reservas, tarifas, sesiones, usuarios, habitaciones, clientes "
                "RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                "VALUES ('HAB-DEV-1', 'EST-SINT-001', 'doble', 2)"
            )
            conexion.execute(
                "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                "VALUES ('TAR-DEV-1', 'HAB-DEV-1', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        self.assertEqual(self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)

    def idem(self):
        return {"Idempotency-Key": f"k-{uuid.uuid4().hex[:10]}"}

    def test_devolucion_formal_deja_saldo_en_cero_y_permite_salida(self):
        inicio = HOY.isoformat()
        fin = (HOY + timedelta(days=1)).isoformat()

        r = self.cliente.post(
            "/hotel/reservas", headers=self.idem(),
            json={
                "habitacion_id": "HAB-DEV-1", "inicio": inicio, "fin": fin, "personas": 2,
                "huesped": {"nombre": "Laura Méndez", "documento": "11.111.111-1", "documento_tipo": "rut"},
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        res_id = r.json()["reserva_id"]

        registrar_acompanantes(self.cliente, res_id, 1, self.idem)
        # Llegada (asienta 1 noche = $50.000).
        with a_las(HOY, time(15, 30)):
            ent = self.cliente.post(f"/hotel/reservas/{res_id}/entrada", headers=self.idem())
        self.assertEqual(ent.status_code, 200, ent.text)

        # Pago en exceso confirmado: $70.000 -> saldo = -$20.000 (a favor del huésped).
        pago = self.cliente.post(
            f"/hotel/reservas/{res_id}/pagos", headers=self.idem(),
            json={
                "monto_clp": 70000, "clave": f"p-{uuid.uuid4().hex[:8]}",
                "modo": "manual", "medio": "transferencia", "confirmar_exceso": True,
            },
        )
        self.assertEqual(pago.status_code, 201, pago.text)

        # Rechaza devolver más que el saldo a favor ($20.000).
        mal = self.cliente.post(
            f"/hotel/reservas/{res_id}/devolucion", headers=self.idem(),
            json={"monto_clp": 25000, "medio": "transferencia", "motivo": "Devolución por exceso de pago"},
        )
        self.assertEqual(mal.status_code, 409)

        # Devolución formal exacta de $20.000 -> saldo queda en $0.
        dev = self.cliente.post(
            f"/hotel/reservas/{res_id}/devolucion", headers=self.idem(),
            json={"monto_clp": 20000, "medio": "transferencia", "motivo": "Devolución de saldo a favor por exceso"},
        )
        self.assertEqual(dev.status_code, 201, dev.text)
        self.assertEqual(dev.json()["saldo_antes_clp"], -20000)
        self.assertEqual(dev.json()["saldo_clp"], 0)

        # Ahora la salida procede limpiamente porque saldo == 0.
        with a_las(HOY + timedelta(days=1), time(11, 0)):
            sal = self.cliente.post(f"/hotel/reservas/{res_id}/salida", headers=self.idem())
        self.assertEqual(sal.status_code, 200, sal.text)
        self.assertEqual(sal.json()["saldo_clp"], 0)


class ModeloGeminiYReintento429Test(unittest.TestCase):
    def test_seleccion_gemini_por_proveedor_sin_duplicar_clave(self):
        cfg = Configuracion(
            host="127.0.0.1", puerto=0, database_url=None, cookie_segura=False,
            origen_front=None, admin_usuario=None, admin_clave=None,
            modelo_proveedor="gemini", gemini_api_key="clave-sintetica", gemini_modelo="gemini-3.5-flash-lite",
        )
        app = crear_app(configuracion=cfg)
        self.assertIsInstance(app.state.modelo_agente, ModeloHttp)
        self.assertIn("generativelanguage.googleapis.com", app.state.modelo_agente._url)

    def test_reintento_429_recupera_respuesta_valida(self):
        intentos = {"n": 0}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                largo = int(self.headers.get("Content-Length", 0))
                self.rfile.read(largo)
                intentos["n"] += 1
                if intentos["n"] == 1:
                    self.send_response(429)
                    self.send_header("Retry-After", "0")
                    self.end_headers()
                    return
                cuerpo = json.dumps({
                    "choices": [{"message": {"role": "assistant", "content": json.dumps({"herramienta": "consultar_politicas", "argumentos": {"tema": "general"}})}}]
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(cuerpo)

            def log_message(self, *args):
                pass

        srv = HTTPServer(("127.0.0.1", 0), Handler)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            m = ModeloHttp(f"http://127.0.0.1:{srv.server_address[1]}", api_key="k", modelo="prueba", reintentos_429=2)
            res = m.decidir([{"rol": "user", "texto": "hola"}], ["consultar_politicas"])
            self.assertEqual(res["herramienta"], "consultar_politicas")
            self.assertEqual(intentos["n"], 2)
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
