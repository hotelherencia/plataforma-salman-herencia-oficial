"""Entrega 1A.2 — una sola fuente de precio, IVA y separación de roles.

HTTP contra PostgreSQL real; datos 100% sintéticos (tipos `t12_`, que se
borran al terminar; la tasa de IVA se restaura a 19)."""
import os
import unittest
from datetime import date, timedelta
from decimal import Decimal

import psycopg
from fastapi.testclient import TestClient

from servicio import iva, precios, roles, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()

# Vectores compartidos con front/tests/iva.test.mjs (misma regla en ambos lados).
VECTORES_IVA = [
    # (precio con IVA, tasa, neto, iva)
    (55000, "19", 46218, 8782),
    (47000, "19", 39496, 7504),
    (65000, "19", 54622, 10378),
    (119, "19", 100, 19),
    (1, "19", 1, 0),
    (100000, "0", 100000, 0),
    (55000, "19.5", 46025, 8975),
]
# (neto ingresado, tasa, precio con IVA guardado)
VECTORES_NETO = [(50000, "19", 59500), (46218, "19", 54999), (46219, "19", 55001), (100, "19", 119),
                 (1, "19", 1), (46025, "19.5", 55000)]


def iso(dias: int) -> str:
    return (HOY + timedelta(days=dias)).isoformat()


def _limpiar(conexion):
    conexion.execute(
        "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
        "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
    )
    conexion.execute("DELETE FROM tipos_habitacion WHERE id LIKE 't12%%'")
    conexion.execute("UPDATE ajustes_plataforma SET valor = 19 WHERE clave = 'iva_porcentaje'")


class IvaReglaTest(unittest.TestCase):
    def test_desglose_y_conversion_desde_neto(self):
        for precio, tasa, neto, monto_iva in VECTORES_IVA:
            with self.subTest(precio=precio, tasa=tasa):
                self.assertEqual(iva.desglose(precio, Decimal(tasa)), {"con_iva": precio, "neto": neto, "iva": monto_iva})
        for neto, tasa, precio in VECTORES_NETO:
            with self.subTest(neto=neto, tasa=tasa):
                self.assertEqual(iva.precio_desde_neto(neto, Decimal(tasa)), precio)

    def test_neto_mas_iva_es_siempre_el_precio(self):
        for precio in range(1, 200_001, 997):
            d = iva.desglose(precio, Decimal("19"))
            self.assertEqual(d["neto"] + d["iva"], precio)
            self.assertGreaterEqual(d["iva"], 0)


class PrecioUnico1A2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        ))

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            _limpiar(conexion)
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            for nombre, rol in (("hotel1", "admin_hotel"), ("plataforma1", "admin_plataforma"),
                                ("recepcion1", "recepcion"), ("caja1", "caja")):
                seguridad.crear_usuario(conexion, EMPRESA, nombre, rol, f"clave-{nombre}")
        self.admin = self.login(*ADMIN)
        self.hotel = self.login("hotel1", "clave-hotel1")
        self.plataforma = self.login("plataforma1", "clave-plataforma1")
        self.recepcion = self.login("recepcion1", "clave-recepcion1")
        self.caja = self.login("caja1", "clave-caja1")
        self._n = 0
        self.crear_tipo("t12_doble", 50000)
        r = self.hotel.post("/hotel/habitaciones/lote", json={
            "tipo_id": "t12_doble", "cantidad": 3, "prefijo": "T12-", "desde_numero": 1,
        }, headers=self.clave())
        self.assertEqual(r.status_code, 201, r.text)

    def tearDown(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            _limpiar(conexion)

    def login(self, usuario, clave):
        cliente = TestClient(self.app)
        respuesta = cliente.post("/sesion", json={"usuario": usuario, "clave": clave})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return cliente

    def clave(self):
        self._n += 1
        return {"Idempotency-Key": f"t12-{self._n}"}

    def sql(self, consulta, parametros=()):
        with psycopg.connect(URL_TEST) as conexion:
            return conexion.execute(consulta, parametros).fetchall()

    def crear_tipo(self, tipo_id, precio, **extra):
        r = self.hotel.post("/hotel/tipos", json={
            "tipo_id": tipo_id, "nombre": tipo_id, "capacidad_base": 2, "precio_base_clp": precio, **extra,
        }, headers=self.clave())
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def excepcion(self, cliente=None, esperado=201, **cuerpo):
        r = (cliente or self.hotel).post("/hotel/precios/excepciones", json=cuerpo, headers=self.clave())
        self.assertEqual(r.status_code, esperado, r.text)
        return r.json()

    def precio(self, habitacion_id, dias):
        with psycopg.connect(URL_TEST) as conexion:
            p = precios.precio_noche(conexion, habitacion_id, HOY + timedelta(days=dias))
        return (p.precio_clp, p.origen.split(":")[0]) if p else None

    # --- Una sola fuente, con prioridades -----------------------------------
    def test_prioridad_excepcion_habitacion_tipo_propio_base(self):
        self.assertEqual(self.precio("T12-01", 10), (50000, "tipo"))
        r = self.hotel.put("/hotel/habitaciones/T12-02/precio", json={"precio_clp": 52000}, headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.precio("T12-02", 10), (52000, "habitacion"))
        # Temporada del tipo (noches 10..11): gana al propio y al base.
        self.excepcion(tipo_id="t12_doble", fecha_desde=iso(10), fecha_hasta=iso(12), precio_clp=70000,
                       motivo="Fiestas")
        self.assertEqual(self.precio("T12-01", 10), (70000, "excepcion_tipo"))
        self.assertEqual(self.precio("T12-02", 11), (70000, "excepcion_tipo"))
        self.assertEqual(self.precio("T12-02", 12), (52000, "habitacion"))
        # Excepción de una habitación gana a la del tipo.
        self.excepcion(habitacion_id="T12-03", fecha_desde=iso(10), fecha_hasta=iso(11), precio_clp=80000)
        self.assertEqual(self.precio("T12-03", 10), (80000, "excepcion_habitacion"))
        self.assertEqual(self.precio("T12-03", 11), (70000, "excepcion_tipo"))
        # Sin venta (precio null): la noche no se ofrece y no se reserva.
        self.excepcion(tipo_id="t12_doble", fecha_desde=iso(20), fecha_hasta=iso(21), precio_clp=None,
                       motivo="Cierre")
        self.assertIsNone(self.precio("T12-01", 20))
        oferta = self.recepcion.get("/hotel/oferta", params={"inicio": iso(20), "fin": iso(21), "personas": 1})
        self.assertEqual([i for i in oferta.json()["oferta"] if i["habitacion_id"].startswith("T12-")], [])
        # Quitar el precio propio: vuelve a heredar la base.
        self.hotel.put("/hotel/habitaciones/T12-02/precio", json={"precio_clp": None}, headers=self.clave())
        self.assertEqual(self.precio("T12-02", 12), (50000, "tipo"))
        # El listado del mantenedor muestra las excepciones y el origen de hoy.
        tipo = next(t for t in self.recepcion.get("/hotel/tipos").json()["tipos"] if t["tipo_id"] == "t12_doble")
        self.assertEqual(len(tipo["excepciones"]), 3)
        self.assertEqual({e["alcance"] for e in tipo["excepciones"]}, {"tipo", "habitacion"})

    def test_retiro_logico_y_duplicado(self):
        creada = self.excepcion(tipo_id="t12_doble", fecha_desde=iso(5), fecha_hasta=iso(8), precio_clp=60000)
        self.excepcion(tipo_id="t12_doble", fecha_desde=iso(5), fecha_hasta=iso(8), precio_clp=60000, esperado=409)
        self.assertEqual(self.precio("T12-01", 6), (60000, "excepcion_tipo"))
        r = self.hotel.post(f"/hotel/precios/excepciones/{creada['excepcion_id']}/retiro", headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.precio("T12-01", 6), (50000, "tipo"))
        # Queda en el historial (no se borra) y retirarla otra vez → 404.
        self.assertEqual(self.sql("SELECT activa, retirada_por FROM excepciones_precio WHERE id = %s",
                                  (creada["excepcion_id"],)), [(False, "hotel1")])
        r = self.hotel.post(f"/hotel/precios/excepciones/{creada['excepcion_id']}/retiro", headers=self.clave())
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.sql("SELECT count(*) FROM auditoria WHERE accion = 'excepcion_precio'"), [(2,)])

    def test_validaciones_de_excepcion(self):
        self.excepcion(fecha_desde=iso(1), fecha_hasta=iso(2), precio_clp=1000, esperado=422)  # sin alcance
        self.excepcion(tipo_id="t12_doble", habitacion_id="T12-01", fecha_desde=iso(1), fecha_hasta=iso(2),
                       precio_clp=1000, esperado=422)  # ambos
        self.excepcion(tipo_id="t12_doble", fecha_desde=iso(2), fecha_hasta=iso(2), precio_clp=1000, esperado=422)
        self.excepcion(tipo_id="t12_no_existe", fecha_desde=iso(1), fecha_hasta=iso(2), precio_clp=1000, esperado=404)
        self.excepcion(habitacion_id="T12-99", fecha_desde=iso(1), fecha_hasta=iso(2), precio_clp=1000, esperado=404)
        r = self.hotel.put("/hotel/habitaciones/T12-99/precio", json={"precio_clp": 1000}, headers=self.clave())
        self.assertEqual(r.status_code, 404)

    def test_editor_heredado_de_tarifas_ya_no_existe(self):
        r = self.admin.put("/hotel/tarifas", json={
            "habitacion_id": "T12-01", "fecha_desde": iso(1), "fecha_hasta": iso(2), "tarifa_noche_clp": 1000,
        }, headers=self.clave())
        self.assertIn(r.status_code, (404, 405))
        self.assertNotIn("/hotel/tarifas", self.admin.get("/openapi.json").json()["paths"])

    # --- IVA -------------------------------------------------------------------
    def test_precio_ingresado_neto_se_guarda_con_iva(self):
        self.crear_tipo("t12_neto", 50000, precio_en="neto")
        self.assertEqual(self.sql("SELECT precio_base_clp FROM tipos_habitacion WHERE id = 't12_neto'"), [(59500,)])
        r = self.hotel.put("/hotel/tipos/t12_neto", json={"precio_base_clp": 100, "precio_en": "neto"},
                           headers=self.clave())
        self.assertEqual(r.json()["tipo"]["precio_base_clp"], 119)
        self.hotel.put("/hotel/habitaciones/T12-01/precio", json={"precio_clp": 100, "precio_en": "neto"},
                       headers=self.clave())
        self.assertEqual(self.sql("SELECT precio_propio_clp FROM habitaciones WHERE id = 'T12-01'"), [(119,)])
        creada = self.excepcion(tipo_id="t12_doble", fecha_desde=iso(3), fecha_hasta=iso(4), precio_clp=46218,
                                precio_en="neto")
        self.assertEqual(creada["precio_clp"], 54999)  # redondeo: el neto derivado vuelve a ser 46218
        auditoria = self.sql("SELECT resultado FROM auditoria WHERE accion = 'tipo_habitacion' "
                             "AND recurso = 'tipo:t12_neto' ORDER BY creado_en LIMIT 1")
        self.assertIn("$59.500 con IVA (neto $50.000, IVA $9.500)", auditoria[0][0])

    def test_tasa_de_iva_solo_la_cambia_plataforma(self):
        self.assertEqual(self.recepcion.get("/hotel/tipos").json()["iva"]["porcentaje"], "19")
        for cliente in (self.hotel, self.recepcion, self.caja):
            r = cliente.put("/plataforma/ajustes/iva", json={"iva_porcentaje": 20}, headers=self.clave())
            self.assertEqual(r.status_code, 403)
        r = self.plataforma.put("/plataforma/ajustes/iva", json={"iva_porcentaje": "19.5"}, headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["iva"]["porcentaje"], "19.5")
        self.assertEqual(self.recepcion.get("/plataforma/ajustes").json()["iva"]["porcentaje"], "19.5")
        # Los precios guardados (con IVA) no cambian; solo su desglose.
        self.assertEqual(self.precio("T12-01", 3), (50000, "tipo"))
        self.assertEqual(self.plataforma.put("/plataforma/ajustes/iva", json={"iva_porcentaje": 101},
                                             headers=self.clave()).status_code, 422)
        self.assertEqual(self.sql("SELECT resultado FROM auditoria WHERE accion = 'ajuste_plataforma'"),
                         [("IVA 19% → 19.5%",)])
        # El administrador histórico (ambos roles) también puede.
        r = self.admin.put("/plataforma/ajustes/iva", json={"iva_porcentaje": 19}, headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)

    # --- Roles -------------------------------------------------------------------
    def test_permisos_por_rol(self):
        precio = {"precio_clp": 51000}
        excepcion = {"tipo_id": "t12_doble", "fecha_desde": iso(1), "fecha_hasta": iso(2), "precio_clp": 1000}
        lote = {"tipo_id": "t12_doble", "cantidad": 1, "prefijo": "T12-X", "desde_numero": 1}
        for indice, (nombre, cliente, puede) in enumerate((
            ("admin_hotel", self.hotel, True), ("administrador", self.admin, True),
            ("admin_plataforma", self.plataforma, False), ("recepcion", self.recepcion, False),
            ("caja", self.caja, False),
        )):
            with self.subTest(rol=nombre):
                esperado = (200, 201) if puede else (403,)
                self.assertIn(cliente.put("/hotel/habitaciones/T12-01/precio", json=precio,
                                          headers=self.clave()).status_code, esperado)
                self.assertIn(cliente.post("/hotel/precios/excepciones", json={**excepcion, "precio_clp": 1000 + self._n},
                                           headers=self.clave()).status_code, esperado)
                self.assertIn(cliente.put("/hotel/tipos/t12_doble", json={"nombre": f"Doble {nombre}"},
                                          headers=self.clave()).status_code, esperado)
                lote["prefijo"] = f"T12-R{indice}-"
                self.assertIn(cliente.post("/hotel/habitaciones/lote", json=lote,
                                           headers=self.clave()).status_code, esperado)
                listado = cliente.get("/hotel/tipos")
                self.assertEqual(listado.status_code, 200)
                self.assertEqual(listado.json()["puede_editar"], puede)
                self.assertEqual(listado.json()["puede_editar_iva"], nombre in ("administrador", "admin_plataforma"))

    def test_usuarios_y_seguridad_solo_plataforma(self):
        self.assertEqual(self.hotel.get("/usuarios").status_code, 403)
        self.assertEqual(self.plataforma.get("/usuarios").status_code, 200)
        r = self.hotel.post("/usuarios", json={"nombre": "x1", "rol": "caja", "clave": "clave-larga-x1"},
                            headers=self.clave())
        self.assertEqual(r.status_code, 403)
        for rol in ("admin_hotel", "admin_plataforma"):
            r = self.plataforma.post("/usuarios", json={"nombre": f"nuevo-{rol}", "rol": rol,
                                                        "clave": "clave-larga-nuevo"}, headers=self.clave())
            self.assertEqual(r.status_code, 201, r.text)
        r = self.plataforma.post("/usuarios", json={"nombre": "malo", "rol": "gerencia", "clave": "clave-larga-x"},
                                 headers=self.clave())
        self.assertEqual(r.status_code, 422)

    def test_operacion_del_hotel_para_admin_hotel_no_para_plataforma(self):
        # Caja del día y cobro: negocio (admin del hotel sí; plataforma no).
        self.assertEqual(self.hotel.get("/hotel/caja", params={"fecha": iso(0)}).status_code, 200)
        self.assertEqual(self.plataforma.get("/hotel/caja", params={"fecha": iso(0)}).status_code, 403)
        reserva = self.hotel.post("/hotel/reservas", json={
            "habitacion_id": "T12-01", "inicio": iso(30), "fin": iso(31), "huesped": {"nombre": "Ana", "documento": "D-1"},
        }, headers=self.clave())
        self.assertEqual(reserva.status_code, 201, reserva.text)
        rid = reserva.json()["reserva_id"]
        # El documento del huésped no lo ve la administración de plataforma.
        self.assertIn("huesped_documento", self.hotel.get(f"/hotel/reservas/{rid}").json())
        self.assertNotIn("huesped_documento", self.plataforma.get(f"/hotel/reservas/{rid}").json())

    def test_doble_factor_aplica_a_ambas_administraciones(self):
        for cliente, esperado in ((self.hotel, True), (self.plataforma, True), (self.admin, True),
                                  (self.recepcion, False), (self.caja, False)):
            self.assertEqual(cliente.get("/sesion").json()["mfa_pendiente"], esperado)
        self.assertTrue(roles.exige_doble_factor("admin_hotel"))
        self.assertFalse(roles.exige_doble_factor("recepcion"))

    def test_no_se_da_de_baja_al_ultimo_admin_de_plataforma(self):
        ids = dict(self.sql("SELECT nombre, id FROM usuarios"))
        # Con dos (administrador + admin_plataforma) se puede dar de baja a uno.
        r = self.plataforma.post(f"/usuarios/{ids['admin']}/baja", headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        # Queda uno: el admin del hotel no cuenta como administración de plataforma.
        otro = self.login("plataforma1", "clave-plataforma1")
        self.sql("UPDATE usuarios SET rol = 'administrador' WHERE nombre = 'hotel1' RETURNING id")
        hotel_como_admin = self.login("hotel1", "clave-hotel1")
        r = hotel_como_admin.post(f"/usuarios/{ids['plataforma1']}/baja", headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.sql("UPDATE usuarios SET rol = 'admin_plataforma', activo = true WHERE nombre = 'plataforma1' RETURNING id")
        otro = self.login("plataforma1", "clave-plataforma1")
        r = otro.post(f"/usuarios/{ids['hotel1']}/baja", headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.sql("UPDATE usuarios SET activo = true WHERE nombre = 'hotel1' RETURNING id")
        self.sql("UPDATE usuarios SET rol = 'admin_hotel' WHERE nombre = 'hotel1' RETURNING id")
        ultimo = self.login("hotel1", "clave-hotel1")
        self.assertEqual(ultimo.get("/usuarios").status_code, 403)
        # plataforma1 es el único de plataforma activo: no puede quedar sin ninguno.
        with psycopg.connect(URL_TEST) as conexion:
            self.assertEqual(seguridad.contar_administradores_activos(conexion, EMPRESA), 1)


if __name__ == "__main__":
    unittest.main()
