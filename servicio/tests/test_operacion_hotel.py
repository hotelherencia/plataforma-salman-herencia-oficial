"""Maduración de la operación del hotel V1 (spec-api-v1, ampliación 2026-10-30).

Búsqueda de reservas, gestión de usuarios, operación de la habitación
(mantenimiento/limpieza), cancelación con reversos y cargos de estadía. Cada
criterio se ejercita por HTTP y se comprueba la persistencia con SELECT.
"""
import os
import unittest
import uuid
from datetime import date, timedelta

_BASE = (date.today() - timedelta(days=40))

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
OTRA_EMPRESA = "EMP-OTRA-001"
ADMIN = ("admin", "clave-admin-sintetica")


class OperacionBaseTest(unittest.TestCase):
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
            from servicio.reservas import sembrar_habitaciones

            sembrar_habitaciones(conexion)
            conexion.execute(
                "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                "VALUES ('TAR-FIJA', 'HAB-SINT-101', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})

    def clave(self):
        return f"op-{uuid.uuid4().hex[:10]}"

    def login(self, nombre, clave):
        cliente = TestClient(self.app)
        respuesta = cliente.post("/sesion", json={"usuario": nombre, "clave": clave})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return cliente

    def crear_usuario(self, nombre, rol, clave="clave-usuario-1"):
        respuesta = self.cliente.post(
            "/usuarios", json={"nombre": nombre, "rol": rol, "clave": clave},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()["id"]

    def reservar(self, inicio=str(_BASE), fin=str(_BASE + timedelta(days=4)), habitacion="HAB-SINT-101",
                 nombre="Huésped Operación", documento="12345678-9"):
        respuesta = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": habitacion, "inicio": inicio, "fin": fin,
                  "huesped": {"nombre": nombre, "documento": documento}},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()["reserva_id"]

    def entrada(self, reserva_id):
        return self.cliente.post(
            f"/hotel/reservas/{reserva_id}/entrada", headers={"Idempotency-Key": self.clave()}
        )

    def salida(self, reserva_id):
        return self.cliente.post(
            f"/hotel/reservas/{reserva_id}/salida", headers={"Idempotency-Key": self.clave()}
        )

    def pagar(self, reserva_id, monto, clave_cobro):
        return self.cliente.post(
            f"/hotel/reservas/{reserva_id}/pagos",
            json={"monto_clp": monto, "clave": clave_cobro, "modo": "manual"},
            headers={"Idempotency-Key": self.clave()},
        )

    def select(self, sql, parametros=()):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            return conexion.execute(sql, parametros).fetchall()


class BusquedaReservasTest(OperacionBaseTest):
    def test_filtros_opcionales_combinados_con_and_y_orden(self):
        r1 = self.reservar(inicio=str(_BASE), fin=str(_BASE + timedelta(days=4)), nombre="Ana Pérez", documento="111-1")
        r2 = self.reservar(inicio=str(_BASE + timedelta(days=9)), fin=str(_BASE + timedelta(days=11)), nombre="bruno diaz", documento="222-2")
        self.entrada(r2)  # r2 queda en_estadia

        # sin filtros: las dos, ordenadas por inicio, id
        respuesta = self.cliente.get("/hotel/reservas")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        items = respuesta.json()["reservas"]
        self.assertEqual([i["reserva_id"] for i in items], [r1, r2])
        self.assertEqual(items[0]["inicio"], str(_BASE))

        # fecha: la noche que contiene el día
        respuesta = self.cliente.get("/hotel/reservas", params={"fecha": str(_BASE + timedelta(days=2))})
        self.assertEqual({i["reserva_id"] for i in respuesta.json()["reservas"]}, {r1})
        respuesta = self.cliente.get("/hotel/reservas", params={"fecha": str(_BASE + timedelta(days=4))})
        self.assertEqual(respuesta.json()["reservas"], [])  # fin exclusivo

        # estado: igualdad exacta
        respuesta = self.cliente.get("/hotel/reservas", params={"estado": "en_estadia"})
        self.assertEqual({i["reserva_id"] for i in respuesta.json()["reservas"]}, {r2})

        # texto: ILIKE sobre nombre, documento, habitación e id
        for termino, esperado in (("ana", {r1}), ("BRUNO", {r2}), ("222-2", {r2}),
                                  ("HAB-SINT-101", {r1, r2}), (r1[4:10], {r1})):
            with self.subTest(texto=termino):
                respuesta = self.cliente.get("/hotel/reservas", params={"texto": termino})
                self.assertEqual({i["reserva_id"] for i in respuesta.json()["reservas"]}, esperado)

        # AND de filtros
        respuesta = self.cliente.get(
            "/hotel/reservas", params={"fecha": str(_BASE + timedelta(days=10)), "estado": "en_estadia", "texto": "bruno"}
        )
        self.assertEqual([i["reserva_id"] for i in respuesta.json()["reservas"]], [r2])
        respuesta = self.cliente.get(
            "/hotel/reservas", params={"fecha": str(_BASE + timedelta(days=10)), "estado": "confirmada"}
        )
        self.assertEqual(respuesta.json()["reservas"], [])

    def test_campos_y_documento_según_rol(self):
        rid = self.reservar(nombre="Carla Ruiz", documento="DOC-SECRETO-1")
        item = self.cliente.get("/hotel/reservas").json()["reservas"][0]
        for campo in ("reserva_id", "habitacion_id", "inicio", "fin", "huesped_nombre",
                      "estado", "tarifa_noche_aceptada_clp"):
            self.assertIn(campo, item)
        self.assertEqual(item["huesped_documento"], "DOC-SECRETO-1")

        self.crear_usuario("caja1", "caja")
        caja = self.login("caja1", "clave-usuario-1")
        item = caja.get("/hotel/reservas").json()["reservas"][0]
        self.assertEqual(item["reserva_id"], rid)
        self.assertNotIn("huesped_documento", item)

        self.crear_usuario("recepcion1", "recepcion")
        recepcion = self.login("recepcion1", "clave-usuario-1")
        item = recepcion.get("/hotel/reservas").json()["reservas"][0]
        self.assertEqual(item["huesped_documento"], "DOC-SECRETO-1")

    def test_estado_invalido_422_y_lista_vacia_200(self):
        self.assertEqual(self.cliente.get("/hotel/reservas", params={"estado": "hospedada"}).status_code, 422)
        respuesta = self.cliente.get("/hotel/reservas", params={"texto": "nada-por-aqui"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"reservas": [], "total": 0})

    def test_sesion_ajena_no_ve_reservas_y_operaciones_403(self):
        rid = self.reservar()
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            seguridad.crear_usuario(conexion, OTRA_EMPRESA, "admin-ajeno", "administrador", "clave-ajena-1")
            conexion.commit()
        ajeno = self.login("admin-ajeno", "clave-ajena-1")
        # SEC-A04 (#329): la sesión ajena se niega en el límite HTTP (403) en
        # vez de ver listas vacías con 200.
        self.assertEqual(ajeno.get("/hotel/reservas").status_code, 403)
        self.assertEqual(ajeno.post(f"/hotel/reservas/{rid}/cancelacion",
                                    headers={"Idempotency-Key": self.clave()}).status_code, 403)
        self.assertEqual(ajeno.post(f"/hotel/reservas/{rid}/cargos",
                                    json={"concepto": "x", "monto_clp": 1000},
                                    headers={"Idempotency-Key": self.clave()}).status_code, 403)
        self.assertEqual(ajeno.post(f"/usuarios/{'USR-inexistente'}/baja",
                                    headers={"Idempotency-Key": self.clave()}).status_code, 403)


class GestionUsuariosTest(OperacionBaseTest):
    def test_alta_guarda_solo_hash_argon2id(self):
        respuesta = self.cliente.post(
            "/usuarios", json={"nombre": "recepcion1", "rol": "recepcion", "clave": "clave-secreta-1"},
            headers={"Idempotency-Key": "alta-1"},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        cuerpo = respuesta.json()
        self.assertNotIn("clave_hash", cuerpo)
        self.assertTrue(cuerpo["activo"])
        (hash_guardado,) = self.select("SELECT clave_hash FROM usuarios WHERE nombre='recepcion1'")[0]
        self.assertTrue(hash_guardado.startswith("$argon2id$"), hash_guardado)
        self.assertNotIn("clave-secreta-1", hash_guardado)
        # idempotencia: misma clave y cuerpo repite; mismo cuerpo con otra clave repite igual
        repetida = self.cliente.post(
            "/usuarios", json={"nombre": "recepcion1", "rol": "recepcion", "clave": "clave-secreta-1"},
            headers={"Idempotency-Key": "alta-1"},
        )
        self.assertEqual(repetida.status_code, 201)
        self.assertEqual(repetida.json()["id"], cuerpo["id"])
        conflicto = self.cliente.post(
            "/usuarios", json={"nombre": "recepcion1", "rol": "caja", "clave": "clave-secreta-1"},
            headers={"Idempotency-Key": "alta-1"},
        )
        self.assertEqual(conflicto.status_code, 409)

    def test_nombre_repetido_en_la_empresa_409(self):
        self.crear_usuario("recepcion1", "recepcion")
        respuesta = self.cliente.post(
            "/usuarios", json={"nombre": "recepcion1", "rol": "caja", "clave": "otra-clave-1"},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(len(self.select("SELECT id FROM usuarios WHERE nombre='recepcion1'")), 1)

    def test_rol_limpieza_no_es_creable_422(self):
        respuesta = self.cliente.post(
            "/usuarios", json={"nombre": "limpieza1", "rol": "limpieza", "clave": "clave-limpieza"},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(respuesta.status_code, 422)

    def test_listar_solo_administrador(self):
        uid = self.crear_usuario("recepcion1", "recepcion")
        lista = self.cliente.get("/usuarios")
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(
            [(u["nombre"], u["rol"], u["activo"]) for u in lista.json()["usuarios"]],
            [("admin", "administrador", True), ("recepcion1", "recepcion", True)],
        )
        self.assertNotIn("clave_hash", lista.text)
        recepcion = self.login("recepcion1", "clave-usuario-1")
        self.assertEqual(recepcion.get("/usuarios").status_code, 403)
        self.assertEqual(uid, self.select("SELECT id FROM usuarios WHERE nombre='recepcion1'")[0][0])

    def test_cambio_de_clave_permiso_y_efecto(self):
        uid = self.crear_usuario("recepcion1", "recepcion", clave="clave-vieja-1")
        # el propio usuario cambia su clave
        propio = self.login("recepcion1", "clave-vieja-1")
        respuesta = propio.post(f"/usuarios/{uid}/clave", json={"clave": "clave-nueva-1"},
                                headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertFalse(seguridad.verificar_clave(
            self.select("SELECT clave_hash FROM usuarios WHERE id=%s", (uid,))[0][0], "clave-vieja-1"))
        self.login("recepcion1", "clave-nueva-1")  # la nueva abre sesión
        # un no administrador no cambia la clave de otro
        uid2 = self.crear_usuario("caja1", "caja")
        self.assertEqual(propio.post(f"/usuarios/{uid2}/clave", json={"clave": "clave-x-123"},
                                     headers={"Idempotency-Key": self.clave()}).status_code, 403)
        # el administrador sí
        respuesta = self.cliente.post(f"/usuarios/{uid2}/clave", json={"clave": "clave-admin-1"},
                                      headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 200)

    def test_revocacion_cierra_todas_las_sesiones(self):
        uid = self.crear_usuario("recepcion1", "recepcion")
        self.login("recepcion1", "clave-usuario-1")
        self.login("recepcion1", "clave-usuario-1")
        respuesta = self.cliente.post(f"/usuarios/{uid}/revocacion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["sesiones_revocadas"], 2)
        vivas = self.select(
            "SELECT count(*) FROM sesiones WHERE usuario_id=%s AND revocada_en IS NULL", (uid,)
        )[0][0]
        self.assertEqual(vivas, 0)
        # la revocación no es baja: el usuario, aún activo, puede abrir sesión nueva
        self.login("recepcion1", "clave-usuario-1")

    def test_revocacion_sobre_si_mismo_409(self):
        admin_id = self.select("SELECT id FROM usuarios WHERE nombre='admin'")[0][0]
        respuesta = self.cliente.post(f"/usuarios/{admin_id}/revocacion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 409)

    def test_baja_rechaza_login_revoca_y_no_autobaja(self):
        uid = self.crear_usuario("recepcion1", "recepcion")
        self.login("recepcion1", "clave-usuario-1")
        respuesta = self.cliente.post(f"/usuarios/{uid}/baja", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertFalse(respuesta.json()["activo"])
        self.assertFalse(self.select("SELECT activo FROM usuarios WHERE id=%s", (uid,))[0][0])
        vivas = self.select("SELECT count(*) FROM sesiones WHERE usuario_id=%s AND revocada_en IS NULL", (uid,))[0][0]
        self.assertEqual(vivas, 0)
        cliente = TestClient(self.app)
        self.assertEqual(cliente.post("/sesion", json={"usuario": "recepcion1", "clave": "clave-usuario-1"}).status_code, 401)
        # no se puede dar de baja a uno mismo
        admin_id = self.select("SELECT id FROM usuarios WHERE nombre='admin'")[0][0]
        self.assertEqual(self.cliente.post(f"/usuarios/{admin_id}/baja",
                                           headers={"Idempotency-Key": self.clave()}).status_code, 409)
        # la baja sobre OTRO administrador sí se permite y deja el conteo en uno
        otro_admin = self.crear_usuario("admin2", "administrador")
        self.assertEqual(self.select(
            "SELECT count(*) FROM usuarios WHERE empresa_id=%s AND rol='administrador' AND activo",
            (EMPRESA,))[0][0], 2)
        respuesta = self.cliente.post(f"/usuarios/{otro_admin}/baja", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertFalse(self.select("SELECT activo FROM usuarios WHERE id=%s", (otro_admin,))[0][0])
        cliente = TestClient(self.app)
        self.assertEqual(cliente.post("/sesion", json={"usuario": "admin2", "clave": "clave-usuario-1"}).status_code, 401)
        # repetir la baja cae en 409 (ya está de baja), sin tocar nada
        respuesta = self.cliente.post(f"/usuarios/{otro_admin}/baja", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 409)


class HabitacionOperacionTest(OperacionBaseTest):
    def test_la_prueba_que_decide_el_fallo_de_operacion(self):
        # Turnover (DECISIÓN 2026-10-30, fuente check_in del dominio): una
        # reserva no solapada puede hacer check-in aunque la unidad esté
        # ocupada por otra estadía. A [1,5) entra; B [5,7) entra después;
        # C que solapa con B no consigue cupo.
        a = self.reservar(inicio=str(_BASE), fin=str(_BASE + timedelta(days=4)), nombre="Estadia A")
        b = self.reservar(inicio=str(_BASE + timedelta(days=4)), fin=str(_BASE + timedelta(days=6)), nombre="Estadia B")
        self.assertEqual(self.entrada(a).status_code, 200)
        self.assertEqual(
            self.select("SELECT estado_operativo FROM habitaciones WHERE id='HAB-SINT-101'")[0][0], "ocupada")

        respuesta = self.entrada(b)
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["estado"], "en_estadia")

        solape = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-SINT-101", "inicio": str(_BASE + timedelta(days=4)), "fin": str(_BASE + timedelta(days=6)),
                  "huesped": {"nombre": "C"}},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(solape.status_code, 409, solape.text)

        # Salida de A (saldo en cero): finalizada. V1-ISSUE-15: con B todavía
        # en_estadia en la unidad, la habitación sigue ocupada y limpia, sin
        # tarea nueva; B no se altera.
        self.pagar(a, 200_000, "cobro-a")
        respuesta = self.salida(a)
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        operativo, preparacion = self.select(
            "SELECT estado_operativo, estado_preparacion FROM habitaciones WHERE id='HAB-SINT-101'")[0]
        self.assertEqual((operativo, preparacion), ("ocupada", "limpia"))
        self.assertEqual(self.select(
            "SELECT count(*) FROM tareas_operativas WHERE habitacion_id='HAB-SINT-101' AND estado='pendiente'")[0][0], 0)
        self.assertEqual(self.select("SELECT estado FROM reservas WHERE id=%s", (b,))[0][0], "en_estadia")

        # La salida de B —la última estadía de la unidad— sí deja disponible y
        # sucia, y abre la tarea de limpieza.
        self.pagar(b, 100_000, "cobro-b")
        respuesta = self.salida(b)
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        operativo, preparacion = self.select(
            "SELECT estado_operativo, estado_preparacion FROM habitaciones WHERE id='HAB-SINT-101'")[0]
        self.assertEqual((operativo, preparacion), ("disponible", "sucia"))
        tarea = self.select(
            "SELECT tipo, estado FROM tareas_operativas WHERE habitacion_id='HAB-SINT-101' AND estado='pendiente'")
        self.assertEqual(tarea, [("limpieza", "pendiente")])

        # Mientras la unidad está sucia, una estadía nueva no puede entrar.
        d = self.reservar(inicio=str(_BASE + timedelta(days=6)), fin=str(_BASE + timedelta(days=8)), nombre="Estadia D")
        self.assertEqual(self.entrada(d).status_code, 409)
        self.assertEqual(self.select("SELECT estado FROM reservas WHERE id=%s", (d,))[0][0], "confirmada")

        # Después de completar la limpieza, la entrada responde 200 y ocupa.
        respuesta = self.cliente.post(
            "/hotel/habitaciones/HAB-SINT-101/limpieza", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["estado_preparacion"], "limpia")
        self.assertEqual(respuesta.json()["tareas_completadas"], 1)
        pendientes = self.select(
            "SELECT count(*) FROM tareas_operativas WHERE habitacion_id='HAB-SINT-101' AND estado='pendiente'")
        self.assertEqual(pendientes[0][0], 0)
        respuesta = self.entrada(d)
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["estado"], "en_estadia")
        self.assertEqual(
            self.select("SELECT estado_operativo FROM habitaciones WHERE id='HAB-SINT-101'")[0][0], "ocupada")

    def test_mantenimiento_bloquea_entrada_y_oferta_aunque_este_limpia(self):
        rid = self.reservar()
        respuesta = self.cliente.post(
            "/hotel/habitaciones/HAB-SINT-101/mantenimiento", json={"abierto": True},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertTrue(self.select("SELECT mantenimiento FROM habitaciones WHERE id='HAB-SINT-101'")[0][0])
        tarea = self.select(
            "SELECT tipo, estado FROM tareas_operativas WHERE habitacion_id='HAB-SINT-101' AND tipo='mantenimiento'")
        self.assertEqual(tarea, [("mantenimiento", "pendiente")])

        oferta = self.cliente.get("/hotel/oferta", params={"inicio": str(_BASE), "fin": str(_BASE + timedelta(days=1)), "personas": 2})
        self.assertNotIn("HAB-SINT-101", {i["habitacion_id"] for i in oferta.json()["oferta"]})

        self.assertEqual(self.entrada(rid).status_code, 409)  # mantenimiento abierto, aunque esté limpia
        self.assertEqual(self.select("SELECT estado FROM reservas WHERE id=%s", (rid,))[0][0], "confirmada")

        respuesta = self.cliente.post(
            "/hotel/habitaciones/HAB-SINT-101/mantenimiento", json={"abierto": False},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.json()["mantenimiento"])
        self.assertEqual(self.entrada(rid).status_code, 200)

    def test_mantenimiento_solo_administrador_y_limpieza_no(self):
        self.crear_usuario("recepcion1", "recepcion")
        recepcion = self.login("recepcion1", "clave-usuario-1")
        self.assertEqual(recepcion.post(
            "/hotel/habitaciones/HAB-SINT-101/mantenimiento", json={"abierto": True},
            headers={"Idempotency-Key": self.clave()}).status_code, 403)
        respuesta = recepcion.post(
            "/hotel/habitaciones/HAB-SINT-101/limpieza", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)

        self.crear_usuario("caja1", "caja")
        caja = self.login("caja1", "clave-usuario-1")
        self.assertEqual(caja.post(
            "/hotel/habitaciones/HAB-SINT-101/limpieza", headers={"Idempotency-Key": self.clave()}).status_code, 403)

    def test_oferta_incluye_unidad_ocupada_en_otras_fechas(self):
        a = self.reservar(inicio=str(_BASE), fin=str(_BASE + timedelta(days=4)))
        self.entrada(a)  # HAB-SINT-101 queda ocupada
        oferta = self.cliente.get("/hotel/oferta", params={"inicio": str(_BASE + timedelta(days=9)), "fin": str(_BASE + timedelta(days=11)), "personas": 2})
        self.assertIn("HAB-SINT-101", {i["habitacion_id"] for i in oferta.json()["oferta"]})

    def test_salida_con_saldo_pendiente_no_cambia_nada(self):
        a = self.reservar()
        self.entrada(a)
        respuesta = self.salida(a)
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(self.select("SELECT estado FROM reservas WHERE id=%s", (a,))[0][0], "en_estadia")
        self.assertEqual(
            self.select("SELECT estado_operativo FROM habitaciones WHERE id='HAB-SINT-101'")[0][0], "ocupada")

    def test_salida_con_otra_estadia_en_curso_no_marca_disponible(self):
        """V1-ISSUE-15: entrada admite el turnover no solapado (rangos
        contiguos), así que una unidad puede tener dos estadías en curso. La
        salida de una no debe marcar disponible+sucia ni abrir limpieza si la
        otra estadía sigue en curso."""
        a = self.reservar(inicio=str(_BASE), fin=str(_BASE + timedelta(days=2)))  # 2 noches
        b = self.reservar(inicio=str(_BASE + timedelta(days=2)), fin=str(_BASE + timedelta(days=4)))
        self.assertEqual(self.entrada(a).status_code, 200)
        self.assertEqual(self.entrada(b).status_code, 200)  # contigua: no solapa

        self.assertEqual(self.pagar(a, 100_000, self.clave()).status_code, 201)  # 2 x 50000
        respuesta = self.salida(a)
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["estado"], "liquidada")

        # A finalizada, B sigue en_estadia
        self.assertEqual(self.select("SELECT estado FROM reservas WHERE id=%s", (a,))[0][0], "finalizada")
        self.assertEqual(self.select("SELECT estado FROM reservas WHERE id=%s", (b,))[0][0], "en_estadia")
        # la unidad NO queda disponible ni sucia: B sigue dentro
        operativo, preparacion = self.select(
            "SELECT estado_operativo, estado_preparacion FROM habitaciones WHERE id='HAB-SINT-101'"
        )[0]
        self.assertEqual(operativo, "ocupada")
        self.assertEqual(preparacion, "limpia")
        # sin tarea de limpieza nueva: la del turnover ya pasó antes de la entrada de B
        self.assertEqual(self.select(
            "SELECT count(*) FROM tareas_operativas WHERE habitacion_id='HAB-SINT-101' "
            "AND tipo='limpieza' AND estado='pendiente'")[0][0], 0)

        # la salida de la última estadía sí libera la unidad
        self.assertEqual(self.pagar(b, 100_000, self.clave()).status_code, 201)
        self.assertEqual(self.salida(b).status_code, 200)
        self.assertEqual(
            self.select("SELECT estado_operativo FROM habitaciones WHERE id='HAB-SINT-101'")[0][0], "disponible")


class CancelacionTest(OperacionBaseTest):
    def test_dentro_de_48_horas_sin_penalidad_y_libera_cupo(self):
        futuro = date.today() + timedelta(days=30)
        rid = self.reservar(inicio=str(futuro), fin=str(futuro + timedelta(days=4)))
        respuesta = self.cliente.post(
            f"/hotel/reservas/{rid}/cancelacion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["estado"], "cancelada")
        self.assertEqual(cuerpo["penalidad_clp"], 0)
        self.assertEqual(len(cuerpo["reversos"]), 1)
        self.assertEqual(self.select("SELECT estado FROM reservas WHERE id=%s", (rid,))[0][0], "cancelada")

        # un reverso por el cargo de alojamiento, con referencia y monto positivo
        reverso = self.select(
            "SELECT tipo, monto_clp, referencia FROM cargos WHERE reserva_id=%s AND tipo='reverso'", (rid,))
        self.assertEqual(len(reverso), 1)
        self.assertEqual(reverso[0][0], "reverso")
        self.assertEqual(reverso[0][1], 200_000)  # 4 noches x 50000
        original = self.select(
            "SELECT id, concepto, monto_clp FROM cargos WHERE reserva_id=%s AND tipo='cargo'", (rid,))
        self.assertEqual(reverso[0][2], original[0][0])
        self.assertIn("Alojamiento", original[0][1])

        # el cupo queda libre: la oferta muestra la habitación y se puede re-reservar
        oferta = self.cliente.get("/hotel/oferta", params={"inicio": str(_BASE + timedelta(days=1)), "fin": str(_BASE + timedelta(days=2)), "personas": 2})
        self.assertIn("HAB-SINT-101", {i["habitacion_id"] for i in oferta.json()["oferta"]})
        self.reservar(inicio=str(_BASE + timedelta(days=1)), fin=str(_BASE + timedelta(days=2)), nombre="Reemplazo")

    def test_fuera_de_plazo_carga_la_primera_noche(self):
        manana = date.today() + timedelta(days=1)
        pasado = date.today() + timedelta(days=3)
        rid = self.reservar(inicio=manana.isoformat(), fin=pasado.isoformat())
        respuesta = self.cliente.post(
            f"/hotel/reservas/{rid}/cancelacion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["penalidad_clp"], 50_000)
        penalidad = self.select(
            "SELECT concepto, monto_clp, tipo FROM cargos WHERE reserva_id=%s AND tipo='cargo'", (rid,))
        self.assertEqual(len(penalidad), 2)  # alojamiento + penalidad
        conceptos = {c[0] for c in penalidad}
        self.assertIn("Cancelación fuera de plazo: primera noche", conceptos)
        # neto = penalidad (alojamiento reverzado)
        (neto,) = self.select(
            "SELECT COALESCE(SUM(CASE WHEN tipo='reverso' THEN -monto_clp ELSE monto_clp END),0) "
            "FROM cargos WHERE reserva_id=%s", (rid,))[0]
        self.assertEqual(neto, 50_000)

    def test_solo_desde_confirmada_y_sin_dobles_reversos(self):
        rid = self.reservar()
        self.entrada(rid)
        self.assertEqual(self.cliente.post(
            f"/hotel/reservas/{rid}/cancelacion", headers={"Idempotency-Key": self.clave()}).status_code, 409)
        self.assertEqual(self.select("SELECT estado FROM reservas WHERE id=%s", (rid,))[0][0], "en_estadia")

        rid2 = self.reservar(inicio=str(_BASE + timedelta(days=9)), fin=str(_BASE + timedelta(days=11)), nombre="Otra reserva")
        self.assertEqual(self.cliente.post(
            f"/hotel/reservas/{rid2}/cancelacion", headers={"Idempotency-Key": "cancela-1"}).status_code, 200)
        # repetir con otra clave: 409 (estado) y sin reversos duplicados
        self.assertEqual(self.cliente.post(
            f"/hotel/reservas/{rid2}/cancelacion", headers={"Idempotency-Key": "cancela-2"}).status_code, 409)
        self.assertEqual(self.select(
            "SELECT count(*) FROM cargos WHERE reserva_id=%s AND tipo='reverso'", (rid2,))[0][0], 1)

    def test_con_pagos_el_neto_a_favor_se_confirma_sin_reembolso(self):
        futuro = date.today() + timedelta(days=30)
        rid = self.reservar(inicio=str(futuro), fin=str(futuro + timedelta(days=4)))
        self.pagar(rid, 200_000, "cobro-total")
        respuesta = self.cliente.post(
            f"/hotel/reservas/{rid}/cancelacion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["reembolso"], "no configurado")
        # el pago sigue intacto; el neto queda a favor del huésped
        (pagado,) = self.select(
            "SELECT COALESCE(SUM(monto_clp),0) FROM pagos WHERE reserva_id=%s", (rid,))[0]
        self.assertEqual(pagado, 200_000)
        (neto,) = self.select(
            "SELECT COALESCE(SUM(CASE WHEN tipo='reverso' THEN -monto_clp ELSE monto_clp END),0) "
            "FROM cargos WHERE reserva_id=%s", (rid,))[0]
        self.assertEqual(neto, 0)

    def test_rol_caja_no_cancela(self):
        rid = self.reservar()
        self.crear_usuario("caja1", "caja")
        caja = self.login("caja1", "clave-usuario-1")
        self.assertEqual(caja.post(
            f"/hotel/reservas/{rid}/cancelacion", headers={"Idempotency-Key": self.clave()}).status_code, 403)


class CargosEstadiaTest(OperacionBaseTest):
    def test_cargo_aparece_en_la_liquidacion_de_salida(self):
        rid = self.reservar()
        self.entrada(rid)
        respuesta = self.cliente.post(
            f"/hotel/reservas/{rid}/cargos",
            json={"concepto": "minibar", "monto_clp": 12_000},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        self.assertEqual(respuesta.json()["tipo"], "cargo")
        (tipo, monto) = self.select(
            "SELECT tipo, monto_clp FROM cargos WHERE reserva_id=%s AND concepto='minibar'", (rid,))[0]
        self.assertEqual((tipo, monto), ("cargo", 12_000))

        total = 200_000 + 12_000
        self.pagar(rid, total, "cobro-total")
        respuesta = self.salida(rid)
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["total_clp"], total)

    def test_monto_invalido_422_y_estado_cerrado_409(self):
        rid = self.reservar()
        for monto in (0, -100):
            with self.subTest(monto=monto):
                respuesta = self.cliente.post(
                    f"/hotel/reservas/{rid}/cargos", json={"concepto": "x", "monto_clp": monto},
                    headers={"Idempotency-Key": self.clave()})
                self.assertEqual(respuesta.status_code, 422)
        self.entrada(rid)
        self.pagar(rid, 200_000, "cobro-total")
        self.assertEqual(self.salida(rid).status_code, 200)
        respuesta = self.cliente.post(
            f"/hotel/reservas/{rid}/cargos", json={"concepto": "tarde", "monto_clp": 5000},
            headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 409)

    def test_rol_caja_puede_asentar_y_idempotencia_de_clave(self):
        rid = self.reservar()
        self.crear_usuario("caja1", "caja")
        caja = self.login("caja1", "clave-usuario-1")
        cuerpo = {"concepto": "consumo", "monto_clp": 7_500}
        r1 = caja.post(f"/hotel/reservas/{rid}/cargos", json=cuerpo, headers={"Idempotency-Key": "cargo-1"})
        self.assertEqual(r1.status_code, 201, r1.text)
        r2 = caja.post(f"/hotel/reservas/{rid}/cargos", json=cuerpo, headers={"Idempotency-Key": "cargo-1"})
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r1.json()["cargo_id"], r2.json()["cargo_id"])
        r3 = caja.post(f"/hotel/reservas/{rid}/cargos", json={"concepto": "otro", "monto_clp": 1},
                       headers={"Idempotency-Key": "cargo-1"})
        self.assertEqual(r3.status_code, 409)
        self.assertEqual(self.select("SELECT count(*) FROM cargos WHERE reserva_id=%s", (rid,))[0][0], 2)  # alojamiento + 1 cargo


if __name__ == "__main__":
    unittest.main()
