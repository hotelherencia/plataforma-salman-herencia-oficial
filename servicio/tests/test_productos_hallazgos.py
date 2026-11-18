"""#357 (2026-11-18): catálogo de productos con búsqueda, precio automático
en el cargo (copiado, inmutable) y stock de minibar que el cargo descuenta y
el reverso devuelve. HTTP contra PostgreSQL real, datos sintéticos.
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


class ProductosHallazgosTest(unittest.TestCase):
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
                "pagos, cargos, movimientos_stock, productos, reservas, tarifas, sesiones, usuarios, habitaciones "
                "RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES ('HAB-PRD-1', 'EST-SINT-001', 'doble', 2)"
            )
            conexion.execute(
                "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                "VALUES ('TAR-PRD-1', 'HAB-PRD-1', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.admin = TestClient(self.app)
        self.assertEqual(self.admin.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)
        r = self.admin.post("/usuarios", json={"nombre": "recep1", "rol": "recepcion", "clave": "clave-recep-1"},
                            headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        self.recepcion = TestClient(self.app)
        self.assertEqual(self.recepcion.post("/sesion", json={"usuario": "recep1", "clave": "clave-recep-1"}).status_code, 200)
        r = self.admin.post("/hotel/reservas", json={
            "habitacion_id": "HAB-PRD-1", "inicio": str(HOY), "fin": str(HOY + timedelta(days=2)),
            "huesped": {"nombre": "Pablo Minibar", "documento": "11.111.111-1"}}, headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        self.rid = r.json()["reserva_id"]

    def idem(self):
        return {"Idempotency-Key": f"k-{uuid.uuid4().hex[:10]}"}

    def producto(self, nombre="Agua mineral", categoria="minibar", precio=2500, stock=None):
        cuerpo = {"nombre": nombre, "categoria": categoria, "precio_clp": precio}
        if stock is not None:
            cuerpo |= {"controla_stock": True, "stock": stock}
        r = self.admin.post("/hotel/productos", json=cuerpo, headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["producto_id"]

    def cargo(self, cuerpo, cliente=None):
        return (cliente or self.recepcion).post(f"/hotel/reservas/{self.rid}/cargos", json=cuerpo, headers=self.idem())

    def stock(self, pid):
        return next(p for p in self.admin.get("/hotel/productos").json()["productos"] if p["producto_id"] == pid)["stock"]

    def test_busqueda_por_palabra_y_categoria(self):
        self.producto("Agua mineral sin gas", "minibar")
        self.producto("Bebida cola", "minibar")
        self.producto("Lavandería por prenda", "servicio", 3000)
        buscar = lambda **q: [p["nombre"] for p in self.recepcion.get("/hotel/productos", params=q).json()["productos"]]
        self.assertEqual(buscar(texto="agua"), ["Agua mineral sin gas"])
        self.assertEqual(buscar(texto="sin gas agua"), ["Agua mineral sin gas"])
        self.assertEqual(buscar(categoria="servicio"), ["Lavandería por prenda"])
        self.assertEqual(len(buscar()), 3)

    def test_cargo_por_producto_copia_precio_y_es_inmutable(self):
        pid = self.producto(precio=2500)
        r = self.cargo({"producto_id": pid, "cantidad": 3})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual((r.json()["monto_clp"], r.json()["precio_unitario_clp"], r.json()["cantidad"]), (7500, 2500, 3))
        self.assertEqual(r.json()["concepto"], "Agua mineral × 3")
        # cambiar el precio no altera el cargo ya asentado
        cambio = self.admin.put(f"/hotel/productos/{pid}", json={"precio_clp": 3000}, headers=self.idem())
        self.assertEqual(cambio.status_code, 200, cambio.text)
        cargos = self.admin.get(f"/hotel/reservas/{self.rid}").json()["cargos"]
        asentado = next(c for c in cargos if c["producto_id"] == pid)
        self.assertEqual((asentado["monto_clp"], asentado["precio_unitario_clp"]), (7500, 2500))

    def test_stock_se_descuenta_bloquea_sin_stock_y_el_reverso_devuelve(self):
        pid = self.producto(stock=2)
        primero = self.cargo({"producto_id": pid, "cantidad": 2})
        self.assertEqual(primero.status_code, 201, primero.text)
        self.assertEqual(self.stock(pid), 0)
        sin = self.cargo({"producto_id": pid})
        self.assertEqual(sin.status_code, 409)
        self.assertIn("sin stock", sin.json()["detail"])
        reverso = self.admin.post(f"/hotel/reservas/{self.rid}/cargos/{primero.json()['cargo_id']}/reverso",
                                  json={"motivo": "no consumió"}, headers=self.idem())
        self.assertEqual(reverso.status_code, 201, reverso.text)
        self.assertEqual(self.stock(pid), 2)
        movimientos = self.admin.get(f"/hotel/productos/{pid}/movimientos").json()["movimientos"]
        self.assertEqual(sorted(m["delta"] for m in movimientos), [-2, 2, 2])  # inicial, cargo, reverso

    def test_ajuste_de_stock_con_motivo_y_nunca_negativo(self):
        pid = self.producto(stock=1)
        r = self.admin.post(f"/hotel/productos/{pid}/stock", json={"delta": 5, "motivo": "reposición"}, headers=self.idem())
        self.assertEqual((r.status_code, r.json()["stock"]), (200, 6))
        self.assertEqual(self.admin.post(f"/hotel/productos/{pid}/stock", json={"delta": -7, "motivo": "merma"},
                                         headers=self.idem()).status_code, 409)
        self.assertEqual(self.recepcion.post(f"/hotel/productos/{pid}/stock", json={"delta": 1, "motivo": "xxx"},
                                             headers=self.idem()).status_code, 403)

    def test_inactivo_no_se_lista_ni_se_carga(self):
        pid = self.producto()
        self.assertEqual(self.admin.put(f"/hotel/productos/{pid}", json={"activo": False}, headers=self.idem()).status_code, 200)
        self.assertEqual(self.recepcion.get("/hotel/productos").json()["productos"], [])
        self.assertEqual(len(self.admin.get("/hotel/productos", params={"inactivos": True}).json()["productos"]), 1)
        self.assertEqual(self.cargo({"producto_id": pid}).status_code, 409)

    def test_concepto_libre_solo_administracion(self):
        self.assertEqual(self.cargo({"concepto": "varios", "monto_clp": 1000}).status_code, 403)
        self.assertEqual(self.cargo({"concepto": "varios (motivo: daño)", "monto_clp": 1000}, cliente=self.admin).status_code, 201)
        self.assertEqual(self.cargo({"producto_id": "PRD-x", "monto_clp": 1}).status_code, 422)
        self.assertEqual(self.cargo({}).status_code, 422)

    def test_mantenedor_solo_administracion_y_nombre_unico(self):
        r = self.recepcion.post("/hotel/productos", json={"nombre": "X producto", "categoria": "extra", "precio_clp": 10},
                                headers=self.idem())
        self.assertEqual(r.status_code, 403)
        self.producto("Agua mineral")
        r = self.admin.post("/hotel/productos", json={"nombre": "agua MINERAL", "categoria": "minibar", "precio_clp": 10},
                            headers=self.idem())
        self.assertEqual(r.status_code, 409)


if __name__ == "__main__":
    unittest.main()
