"""Entrega 1A — tipos de habitación, precio heredado, alta por lote y precio
congelado por noche. HTTP contra PostgreSQL real; datos 100% sintéticos
(tipos con prefijo `t1a_`, que se borran al terminar)."""
import os
import time
import unittest
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import inventario_documental, panel, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


def iso(dias: int) -> str:
    return (HOY + timedelta(days=dias)).isoformat()


def _limpiar(conexion):
    conexion.execute(
        "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
        "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
    )
    conexion.execute("DELETE FROM tipos_habitacion WHERE id LIKE 't1a%%'")


class TiposHabitacion1ATest(unittest.TestCase):
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
            _limpiar(conexion)
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            seguridad.crear_usuario(conexion, EMPRESA, "recepcion1", "recepcion", "clave-recepcion")
            seguridad.crear_usuario(conexion, EMPRESA, "caja1", "caja", "clave-caja")
        self.admin = self.login(*ADMIN)
        self.recepcion = self.login("recepcion1", "clave-recepcion")
        self.caja = self.login("caja1", "clave-caja")
        self._n = 0

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
        return {"Idempotency-Key": f"t1a-{self._n}"}

    def sql(self, consulta, parametros=()):
        with psycopg.connect(URL_TEST) as conexion:
            return conexion.execute(consulta, parametros).fetchall()

    def crear_tipo(self, tipo_id="t1a_suite", precio=70000, capacidad=2, cliente=None, esperado=201):
        cuerpo = {"tipo_id": tipo_id, "nombre": "Suite 1A", "capacidad_base": capacidad, "precio_base_clp": precio}
        respuesta = (cliente or self.admin).post("/hotel/tipos", json=cuerpo, headers=self.clave())
        self.assertEqual(respuesta.status_code, esperado, respuesta.text)
        return respuesta.json()

    def lote(self, cantidad=3, desde=1, prefijo="T1A-", tipo_id="t1a_suite", cliente=None, esperado=201, **extra):
        cuerpo = {"tipo_id": tipo_id, "cantidad": cantidad, "prefijo": prefijo, "desde_numero": desde, **extra}
        respuesta = (cliente or self.admin).post("/hotel/habitaciones/lote", json=cuerpo, headers=self.clave())
        self.assertEqual(respuesta.status_code, esperado, respuesta.text)
        return respuesta.json()

    def oferta(self, inicio, fin, personas=2):
        respuesta = self.recepcion.get(f"/hotel/oferta?inicio={iso(inicio)}&fin={iso(fin)}&personas={personas}")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return {o["habitacion_id"]: o for o in respuesta.json()["oferta"]}

    # --- Permisos --------------------------------------------------------
    def test_recepcion_y_caja_solo_leen(self):
        self.crear_tipo()
        for cliente in (self.recepcion, self.caja):
            lista = cliente.get("/hotel/tipos")
            self.assertEqual(lista.status_code, 200)
            self.assertFalse(lista.json()["puede_editar"])
            self.crear_tipo("t1a_otro", cliente=cliente, esperado=403)
            r = cliente.put("/hotel/tipos/t1a_suite", json={"precio_base_clp": 1000}, headers=self.clave())
            self.assertEqual(r.status_code, 403)
            self.lote(cliente=cliente, esperado=403)
        self.assertTrue(self.admin.get("/hotel/tipos").json()["puede_editar"])
        self.assertEqual(self.sql("SELECT precio_base_clp FROM tipos_habitacion WHERE id = 't1a_suite'"),
                         [(70000,)])
        self.assertEqual(self.sql("SELECT count(*) FROM habitaciones"), [(0,)])
        sin_sesion = TestClient(self.app).get("/hotel/tipos")
        self.assertEqual(sin_sesion.status_code, 401)

    # --- Alta por lote ---------------------------------------------------
    def test_lote_crea_numeracion_y_es_todo_o_nada(self):
        self.crear_tipo()
        creado = self.lote(cantidad=3, desde=8, digitos=2)
        self.assertEqual(creado["habitaciones"], ["T1A-08", "T1A-09", "T1A-10"])
        filas = self.sql("SELECT id, tipo, capacidad, estado_operativo, estado_preparacion, en_inventario "
                         "FROM habitaciones ORDER BY id")
        self.assertEqual(filas, [(i, "t1a_suite", 2, "disponible", "limpia", True)
                                 for i in ("T1A-08", "T1A-09", "T1A-10")])
        # Se solapa con T1A-10: no se crea ninguna.
        choque = self.lote(cantidad=3, desde=10, esperado=409)
        self.assertEqual(choque["existentes"], ["T1A-10"])
        self.assertEqual(self.sql("SELECT count(*) FROM habitaciones"), [(3,)])
        # Reintento con la misma clave: misma respuesta, sin duplicar.
        cabecera = {"Idempotency-Key": "t1a-lote-fija"}
        cuerpo = {"tipo_id": "t1a_suite", "cantidad": 2, "prefijo": "T1A-B", "desde_numero": 1, "capacidad": 3}
        uno = self.admin.post("/hotel/habitaciones/lote", json=cuerpo, headers=cabecera)
        dos = self.admin.post("/hotel/habitaciones/lote", json=cuerpo, headers=cabecera)
        self.assertEqual((uno.status_code, dos.status_code), (201, 201))
        self.assertEqual(uno.json(), dos.json())
        self.assertEqual(self.sql("SELECT count(*), min(capacidad) FROM habitaciones WHERE id LIKE 'T1A-B%%'"),
                         [(2, 3)])
        # Auditoría por habitación y por lote.
        self.assertEqual(self.sql("SELECT count(*) FROM auditoria WHERE accion = 'habitaciones_lote'"), [(2,)])
        self.assertEqual(self.sql("SELECT count(*) FROM auditoria WHERE accion = 'habitacion' "
                                  "AND resultado LIKE 'creada por lote%%'"), [(5,)])

    def test_lote_valida_tipo_y_numeracion(self):
        self.lote(tipo_id="t1a_no_existe", esperado=422)
        self.crear_tipo()
        r = self.admin.put("/hotel/tipos/t1a_suite", json={"activo": False}, headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.lote(esperado=409)
        self.lote(cantidad=101, esperado=422)
        self.lote(prefijo="mal/prefijo", esperado=422)
        self.assertEqual(self.sql("SELECT count(*) FROM habitaciones"), [(0,)])

    # --- Precio heredado y resolución -------------------------------------
    def test_precio_base_heredado_y_congelado_en_la_reserva(self):
        self.crear_tipo(precio=70000)
        self.lote(cantidad=2, desde=1)
        oferta = self.oferta(10, 12)
        self.assertEqual(sorted(oferta), ["T1A-01", "T1A-02"])
        self.assertEqual((oferta["T1A-01"]["tarifa_noche_clp"], oferta["T1A-01"]["total_clp"]), (70000, 140000))
        # Excepción por fecha de la unidad gana a la base en sus noches.
        r = self.admin.post("/hotel/precios/excepciones", json={
            "habitacion_id": "T1A-01", "fecha_desde": iso(11), "fecha_hasta": iso(12), "precio_clp": 90000,
        }, headers=self.clave())
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self.oferta(10, 12)["T1A-01"]["total_clp"], 160000)
        # Precio propio (mismo mantenedor, 1A.2) gana a la base, pierde con la excepción.
        r = self.admin.put("/hotel/habitaciones/T1A-02/precio", json={"precio_clp": 75000}, headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.oferta(10, 12)["T1A-02"]["total_clp"], 150000)

        reserva = self.recepcion.post("/hotel/reservas", json={
            "habitacion_id": "T1A-01", "inicio": iso(10), "fin": iso(12), "huesped": {"nombre": "Ana Prueba"},
        }, headers=self.clave())
        self.assertEqual(reserva.status_code, 201, reserva.text)
        reserva_id = reserva.json()["reserva_id"]
        self.assertEqual(reserva.json()["total_clp"], 160000)
        noches = self.sql("SELECT noche, precio_clp, origen FROM reserva_noches WHERE reserva_id = %s "
                          "ORDER BY noche", (reserva_id,))
        self.assertEqual([(n[0], n[1]) for n in noches],
                         [(HOY + timedelta(days=10), 70000), (HOY + timedelta(days=11), 90000)])
        self.assertEqual(noches[0][2], "tipo:t1a_suite")
        self.assertTrue(noches[1][2].startswith("excepcion_habitacion:EXC-"))
        self.assertEqual(self.sql("SELECT total_aceptado_clp, tarifa_noche_aceptada_clp FROM reservas "
                                  "WHERE id = %s", (reserva_id,)), [(160000, 70000)])

        # Subir la base mueve la cotización nueva, no la reserva aceptada.
        r = self.admin.put("/hotel/tipos/t1a_suite", json={"precio_base_clp": 80000}, headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["cambios"], {"precio_base_clp": [70000, 80000]})
        self.assertEqual(self.oferta(20, 21)["T1A-01"]["total_clp"], 80000)
        detalle = self.recepcion.get(f"/hotel/reservas/{reserva_id}").json()
        self.assertEqual(detalle["total_aceptado_clp"], 160000)
        self.assertEqual([n["precio_clp"] for n in detalle["precio_por_noche"]], [70000, 90000])
        self.assertEqual(detalle["cuenta"]["cargos_netos_clp"], 160000)

    def test_sin_precio_base_la_unidad_queda_sin_tarifa(self):
        self.crear_tipo(precio=None)
        creado = self.lote(cantidad=1, desde=1)
        self.assertTrue(creado["sin_precio"])
        self.assertEqual(self.oferta(5, 6), {})
        ocupacion = self.recepcion.get(f"/hotel/ocupacion?desde={iso(5)}&hasta={iso(6)}").json()
        self.assertEqual(ocupacion["habitaciones"][0]["noches"][0]["estado"], "sin_tarifa")
        reserva = self.recepcion.post("/hotel/reservas", json={
            "habitacion_id": "T1A-01", "inicio": iso(5), "fin": iso(6), "huesped": {"nombre": "Sin Precio"},
        }, headers=self.clave())
        self.assertEqual(reserva.status_code, 409)
        # Fijarlo después lo vuelve vendible; quitarlo (null) lo saca otra vez.
        self.admin.put("/hotel/tipos/t1a_suite", json={"precio_base_clp": 50000}, headers=self.clave())
        self.assertEqual(self.oferta(5, 6)["T1A-01"]["total_clp"], 50000)
        r = self.admin.put("/hotel/tipos/t1a_suite", json={"precio_base_clp": None}, headers=self.clave())
        self.assertEqual(r.json()["tipo"]["precio_base_clp"], None)
        self.assertEqual(self.oferta(5, 6), {})

    def test_listado_de_tipos_resume_origen_del_precio(self):
        self.crear_tipo(precio=60000)
        self.lote(cantidad=3, desde=1)
        self.admin.post("/hotel/precios/excepciones", json={
            "habitacion_id": "T1A-03", "fecha_desde": iso(-1), "fecha_hasta": iso(30), "precio_clp": 65000,
        }, headers=self.clave())
        tipos = {t["tipo_id"]: t for t in self.recepcion.get("/hotel/tipos").json()["tipos"]}
        resumen = tipos["t1a_suite"]["resumen"]
        self.assertEqual(resumen["habitaciones"], 3)
        self.assertEqual(resumen["heredan_precio_base"], 2)
        self.assertEqual(resumen["con_excepcion_hoy"], 1)
        self.assertEqual((resumen["precio_hoy_min_clp"], resumen["precio_hoy_max_clp"]), (60000, 65000))
        habitaciones = self.recepcion.get("/hotel/habitaciones").json()["habitaciones"]
        por_id = {h["habitacion_id"]: h for h in habitaciones}
        self.assertEqual(por_id["T1A-01"]["tarifa_vigente_hoy_clp"], 60000)
        self.assertEqual(por_id["T1A-01"]["origen_precio_hoy"], "tipo:t1a_suite")
        self.assertEqual(por_id["T1A-03"]["tarifa_vigente_hoy_clp"], 65000)
        self.assertEqual(por_id["T1A-01"]["tipo_nombre"], "Suite 1A")

    def test_crear_y_editar_tipo(self):
        self.crear_tipo()
        self.crear_tipo(esperado=409)
        r = self.admin.post("/hotel/tipos", json={"tipo_id": "Con Espacio", "nombre": "x", "capacidad_base": 1},
                            headers=self.clave())
        self.assertEqual(r.status_code, 422)
        r = self.admin.put("/hotel/tipos/t1a_suite", json={"nombre": "  Suite Jardín ", "capacidad_base": 3},
                           headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["tipo"]["nombre"], "Suite Jardín")
        r = self.admin.put("/hotel/tipos/t1a_suite", json={"nombre": None}, headers=self.clave())
        self.assertEqual(r.status_code, 422)
        r = self.admin.put("/hotel/tipos/t1a_nada", json={"orden": 1}, headers=self.clave())
        self.assertEqual(r.status_code, 404)
        auditoria = self.sql("SELECT resultado FROM auditoria WHERE recurso = 'tipo:t1a_suite' ORDER BY creado_en")
        self.assertTrue(auditoria[0][0].startswith("creado"))
        self.assertIn("nombre: Suite 1A→Suite Jardín", auditoria[1][0])

    def test_tipo_heredado_por_texto_se_crea_solo(self):
        """Caminos heredados (PUT con tipo en texto, siembras) crean su tipo."""
        r = self.admin.put("/hotel/habitaciones/T1A-X", json={"tipo": "t1a_heredado", "capacidad": 2},
                           headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.sql("SELECT nombre, capacidad_base, precio_base_clp FROM tipos_habitacion "
                                  "WHERE id = 't1a_heredado'"), [("T1a Heredado", 2, None)])

    # --- Inventario del titular y escala ---------------------------------
    def test_inventario_operativo_incluye_altas_por_lote(self):
        self.assertTrue(inventario_documental.es_inventario_operativo({"habitacion_id": "HAB-07"}))
        self.assertFalse(inventario_documental.es_inventario_operativo({"habitacion_id": "HAB-18"}))
        self.assertTrue(inventario_documental.es_inventario_operativo(
            {"habitacion_id": "HAB-18", "en_inventario": True}))
        self.crear_tipo()
        self.lote(cantidad=2, desde=18, prefijo="HAB-")
        self.sql("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                 "VALUES ('HAB-SINT-101', 'EST-SINT-001', 't1a_suite', 2) RETURNING id")
        with psycopg.connect(URL_TEST) as conexion:
            ids = [h["habitacion_id"] for h in panel._habitaciones(conexion, None, solo_inventario_real=True)]
        self.assertEqual(ids, ["HAB-18", "HAB-19"])

    def test_oferta_con_100_habitaciones_es_rapida(self):
        self.crear_tipo(precio=55000)
        self.lote(cantidad=100, desde=100, prefijo="T1A-", digitos=3)
        inicio = time.perf_counter()
        oferta = self.oferta(1, 31)
        transcurrido = time.perf_counter() - inicio
        self.assertEqual(len(oferta), 100)
        self.assertEqual(oferta["T1A-100"]["total_clp"], 55000 * 30)
        self.assertLess(transcurrido, 2.0, f"oferta de 100 habitaciones × 30 noches tardó {transcurrido:.2f}s")


if __name__ == "__main__":
    unittest.main()
