"""Maduración operativa V1 (2026-10-30), reescrita al adaptador ADP: las
reglas de hotel las decide ServicioHotelInventario y estas pruebas ejercitan
el HTTP contra PostgreSQL real. Entradas con inicio en fecha pasada y
documento del huésped (HECHO DOCUMENTADO, fuente check_in); turnover: la
unidad OCUPADA no bloquea el check-in de una reserva no solapada (DECISIÓN
2026-10-30, fuente check_in).
"""
import os
import unittest
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
FUTURO = (HOY + timedelta(days=30)).isoformat()
FUTURO_FIN = (HOY + timedelta(days=33)).isoformat()
P1 = (HOY - timedelta(days=9)).isoformat()
P2 = (HOY - timedelta(days=8)).isoformat()
P3 = (HOY - timedelta(days=7)).isoformat()
P5 = (HOY - timedelta(days=5)).isoformat()
P7 = (HOY - timedelta(days=3)).isoformat()
P9 = (HOY - timedelta(days=1)).isoformat()


class MaduracionOperativaTest(unittest.TestCase):
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
                "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            for n in (1, 2, 3):
                conexion.execute(
                    "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                    "VALUES (%s, 'EST-SINT-001', 'doble', 2)",
                    (f"HAB-SINT-10{n}",),
                )
                conexion.execute(
                    "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                    "VALUES (%s, %s, '2026-01-01', '2027-12-31', 50000)",
                    (f"TAR-10{n}", f"HAB-SINT-10{n}"),
                )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})

    # ---- helpers ----

    def cliente_como(self, usuario, clave):
        cliente = TestClient(self.app)
        respuesta = cliente.post("/sesion", json={"usuario": usuario, "clave": clave})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return cliente

    def reservar(self, habitacion_id="HAB-SINT-101", inicio=FUTURO, fin=FUTURO_FIN,
                 nombre="Huésped", documento="DOC-H6", clave="res-1"):
        huesped = {"nombre": nombre}
        if documento is not None:
            huesped["documento"] = documento
        respuesta = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": habitacion_id, "inicio": inicio, "fin": fin, "huesped": huesped},
            headers={"Idempotency-Key": clave},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()["reserva_id"]

    def pagar(self, reserva_id, monto, clave="cob-1", idem="pag-1"):
        return self.cliente.post(
            f"/hotel/reservas/{reserva_id}/pagos",
            json={"monto_clp": monto, "clave": clave, "modo": "manual"},
            headers={"Idempotency-Key": idem},
        )

    def entrada(self, reserva_id, clave="ent-1"):
        return self.cliente.post(
            f"/hotel/reservas/{reserva_id}/entrada",
            json={},
            headers={"Idempotency-Key": clave},
        )

    def salida(self, reserva_id, clave="sal-1"):
        return self.cliente.post(
            f"/hotel/reservas/{reserva_id}/salida",
            json={},
            headers={"Idempotency-Key": clave},
        )

    def cancelar(self, reserva_id, clave="can-1"):
        return self.cliente.post(
            f"/hotel/reservas/{reserva_id}/cancelacion",
            json={},
            headers={"Idempotency-Key": clave},
        )

    def alta_usuario(self, nombre, rol, clave, idem):
        return self.cliente.post(
            "/usuarios",
            json={"nombre": nombre, "rol": rol, "clave": clave},
            headers={"Idempotency-Key": idem},
        )

    def _cargos_de(self, reserva_id):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            return conexion.execute(
                "SELECT id, tipo, concepto, monto_clp, referencia FROM cargos WHERE reserva_id = %s",
                (reserva_id,),
            ).fetchall()

    # ---- 1. búsqueda de reservas ----

    def test_busqueda_combina_filtros_con_and_y_ordena(self):
        rid_a = self.reservar("HAB-SINT-101", "2026-11-10", "2026-11-12", "Ana Pérez", "DOC-100", "b-a")
        rid_b = self.reservar("HAB-SINT-102", "2026-11-11", "2026-11-13", "Bruno Díaz", None, "b-b")
        rid_c = self.reservar("HAB-SINT-101", "2026-11-01", "2026-11-02", "Cora Luna", None, "b-c")

        def buscar(**params):
            return self.cliente.get("/hotel/reservas", params=params)

        por_fecha = buscar(fecha="2026-11-11").json()["reservas"]
        self.assertEqual({r["reserva_id"] for r in por_fecha}, {rid_a, rid_b})
        combinado = buscar(fecha="2026-11-11", estado="confirmada", texto="ana").json()["reservas"]
        self.assertEqual([r["reserva_id"] for r in combinado], [rid_a])
        por_documento = buscar(texto="doc-100").json()["reservas"]
        self.assertEqual([r["reserva_id"] for r in por_documento], [rid_a])
        por_habitacion = buscar(texto="hab-sint-102").json()["reservas"]
        self.assertEqual([r["reserva_id"] for r in por_habitacion], [rid_b])
        ordenadas = buscar().json()["reservas"]
        self.assertEqual([r["reserva_id"] for r in ordenadas], [rid_c, rid_a, rid_b])  # inicio, id
        item = combinado[0]
        for campo in ("reserva_id", "habitacion_id", "inicio", "fin", "huesped_nombre",
                      "estado", "tarifa_noche_aceptada_clp", "huesped_documento"):
            self.assertIn(campo, item)
        self.assertEqual(item["huesped_documento"], "DOC-100")
        self.assertEqual(buscar(texto="no-existe-nadie").status_code, 200)
        self.assertEqual(buscar(texto="no-existe-nadie").json()["reservas"], [])
        self.assertEqual(buscar(estado="fumando").status_code, 422)

    def test_busqueda_documento_solo_recepcion_o_administrador(self):
        rid = self.reservar("HAB-SINT-101", "2026-11-10", "2026-11-12", "Ana Pérez", "DOC-100", "b-doc")
        self.alta_usuario("recepcion1", "recepcion", "clave-rec", "u-rec")
        self.alta_usuario("caja1", "caja", "clave-caja", "u-caja")
        for nombre, clave, espera_documento in (
            ("recepcion1", "clave-rec", True),
            ("caja1", "clave-caja", False),
        ):
            with self.subTest(rol=nombre):
                cliente = self.cliente_como(nombre, clave)
                items = cliente.get("/hotel/reservas", params={"texto": rid}).json()["reservas"]
                self.assertEqual(len(items), 1)
                self.assertEqual("huesped_documento" in items[0], espera_documento)

    # ---- 2. gestión de usuarios ----

    def test_alta_usuario_guarda_hash_y_puede_entrar(self):
        respuesta = self.alta_usuario("recepcion1", "recepcion", "clave-rec", "u-1")
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        cuerpo = respuesta.json()
        self.assertNotIn("clave_hash", cuerpo)
        self.assertTrue(cuerpo["activo"])
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (hash_guardado,) = conexion.execute(
                "SELECT clave_hash FROM usuarios WHERE nombre = 'recepcion1'"
            ).fetchone()
        self.assertTrue(hash_guardado.startswith("$argon2id$"), hash_guardado)
        self.assertNotIn("clave-rec", hash_guardado)
        cliente = self.cliente_como("recepcion1", "clave-rec")
        self.assertEqual(cliente.get("/sesion").status_code, 200)

    def test_alta_duplicada_409_y_rol_limpieza_422(self):
        self.assertEqual(self.alta_usuario("recepcion1", "recepcion", "clave-rec", "u-1").status_code, 201)
        duplicada = self.alta_usuario("recepcion1", "recepcion", "otra-clave", "u-2")
        self.assertEqual(duplicada.status_code, 409)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (n,) = conexion.execute("SELECT count(*) FROM usuarios WHERE nombre = 'recepcion1'").fetchone()
        self.assertEqual(n, 1)
        self.assertEqual(self.alta_usuario("limpieza1", "limpieza", "clave-limp", "u-3").status_code, 422)

    def test_listar_usuarios_solo_administrador(self):
        self.alta_usuario("recepcion1", "recepcion", "clave-rec", "u-1")
        cliente = self.cliente_como("recepcion1", "clave-rec")
        self.assertEqual(cliente.get("/usuarios").status_code, 403)
        respuesta = self.cliente.get("/usuarios")
        self.assertEqual(respuesta.status_code, 200)
        usuarios = {u["nombre"]: u for u in respuesta.json()["usuarios"]}
        self.assertEqual(set(usuarios), {"admin", "recepcion1"})
        self.assertEqual(set(usuarios["recepcion1"]), {"id", "nombre", "rol", "activo"})

    def test_cambio_de_clave_propio_o_administrador(self):
        self.alta_usuario("recepcion1", "recepcion", "clave-rec", "u-1")
        self.alta_usuario("recepcion2", "recepcion", "clave-rec2", "u-2")
        propio = self.cliente_como("recepcion1", "clave-rec")
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (uid2,) = conexion.execute("SELECT id FROM usuarios WHERE nombre = 'recepcion2'").fetchone()
            (uid1,) = conexion.execute("SELECT id FROM usuarios WHERE nombre = 'recepcion1'").fetchone()
        respuesta = propio.post(
            f"/usuarios/{uid2}/clave", json={"clave": "clave-nueva"}, headers={"Idempotency-Key": "cl-ajena"}
        )
        self.assertEqual(respuesta.status_code, 403)
        respuesta = propio.post(
            f"/usuarios/{uid1}/clave", json={"clave": "clave-cambiada"}, headers={"Idempotency-Key": "cl-propia"}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.cliente_como("recepcion1", "clave-cambiada")
        respuesta = self.cliente.post(
            f"/usuarios/{uid2}/clave", json={"clave": "clave-por-admin"}, headers={"Idempotency-Key": "cl-admin"}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.cliente_como("recepcion2", "clave-por-admin")
        self.assertEqual(self.cliente.post("/sesion", json={"usuario": "recepcion2", "clave": "clave-rec2"}).status_code, 401)

    def test_revocacion_de_sesiones_sobre_otro_usuario(self):
        self.alta_usuario("recepcion1", "recepcion", "clave-rec", "u-1")
        cliente = self.cliente_como("recepcion1", "clave-rec")
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (uid,) = conexion.execute("SELECT id FROM usuarios WHERE nombre = 'recepcion1'").fetchone()
            (propio,) = conexion.execute("SELECT id FROM usuarios WHERE nombre = 'admin'").fetchone()
        respuesta = self.cliente.post(f"/usuarios/{uid}/revocacion", json={}, headers={"Idempotency-Key": "rev-1"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertGreaterEqual(respuesta.json()["sesiones_revocadas"], 1)
        self.assertEqual(cliente.get("/sesion").status_code, 401)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (activas,) = conexion.execute(
                "SELECT count(*) FROM sesiones WHERE usuario_id = %s AND revocada_en IS NULL", (uid,)
            ).fetchone()
        self.assertEqual(activas, 0)
        propia = self.cliente.post(f"/usuarios/{propio}/revocacion", json={}, headers={"Idempotency-Key": "rev-2"})
        self.assertEqual(propia.status_code, 409)  # «para cerrar tu sesión usa DELETE /sesion»

    def test_baja_revoca_sesiones_y_bloquea_login(self):
        self.alta_usuario("recepcion1", "recepcion", "clave-rec", "u-1")
        cliente = self.cliente_como("recepcion1", "clave-rec")
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (uid,) = conexion.execute("SELECT id FROM usuarios WHERE nombre = 'recepcion1'").fetchone()
            (admin_id,) = conexion.execute("SELECT id FROM usuarios WHERE nombre = 'admin'").fetchone()
        ultimo = self.cliente.post(f"/usuarios/{admin_id}/baja", json={}, headers={"Idempotency-Key": "baja-admin"})
        self.assertEqual(ultimo.status_code, 409)
        respuesta = self.cliente.post(f"/usuarios/{uid}/baja", json={}, headers={"Idempotency-Key": "baja-1"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.json()["activo"])
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (activo,) = conexion.execute("SELECT activo FROM usuarios WHERE id = %s", (uid,)).fetchone()
            (activas,) = conexion.execute(
                "SELECT count(*) FROM sesiones WHERE usuario_id = %s AND revocada_en IS NULL", (uid,)
            ).fetchone()
        self.assertFalse(activo)
        self.assertEqual(activas, 0)
        self.assertEqual(self.cliente.post("/sesion", json={"usuario": "recepcion1", "clave": "clave-rec"}).status_code, 401)
        self.assertEqual(cliente.get("/sesion").status_code, 401)
        otra_vez = self.cliente.post(f"/usuarios/{uid}/baja", json={}, headers={"Idempotency-Key": "baja-2"})
        self.assertEqual(otra_vez.status_code, 409)
        ajeno = self.cliente.post("/usuarios/USR-NO-EXISTE/baja", json={}, headers={"Idempotency-Key": "baja-3"})
        self.assertEqual(ajeno.status_code, 403)

    # ---- 3. estado de la habitación (las decide el dominio) ----

    def test_turnover_solape_sucia_limpieza_y_siguiente_checkin(self):
        # A [p1,p5) con 4 noches; entrada ocupa la unidad y asienta las noches.
        rid_a = self.reservar("HAB-SINT-101", P1, P5, "Alicia", clave="r-a")
        self.assertEqual(self.pagar(rid_a, 200_000, "cob-a", "pag-a").status_code, 201)
        self.assertEqual(self.entrada(rid_a, "ent-a").status_code, 200)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (operativo,) = conexion.execute(
                "SELECT estado_operativo FROM habitaciones WHERE id = 'HAB-SINT-101'").fetchone()
            (noches,) = conexion.execute(
                "SELECT count(*) FROM cargos WHERE reserva_id = %s AND concepto LIKE 'Alojamiento%%'", (rid_a,)).fetchone()
        self.assertEqual(operativo, "ocupada")
        # V1 (spec-api-v1): el cargo del alojamiento completo nace al confirmar
        self.assertEqual(noches, 1)  # un solo cargo «Alojamiento N noches»
        # B [p5,p7) se crea aunque A esté en estadía (turnover, fuente check_in)
        rid_b = self.reservar("HAB-SINT-101", P5, P7, "Beatriz", clave="r-b")
        # la entrada de B con A todavía en estadía responde 200 (turnover)
        self.assertEqual(self.entrada(rid_b, "ent-b").status_code, 200)
        # C en el rango de B la rechaza el dominio (solape con en_estadia)
        solape = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-SINT-101", "inicio": P5, "fin": P7, "huesped": {"nombre": "C", "documento": "D"}},
            headers={"Idempotency-Key": "r-c"},
        )
        self.assertEqual(solape.status_code, 409)
        # salida de A (saldo 0): la unidad queda sucia y nace la tarea de limpieza
        self.assertEqual(self.salida(rid_a, "sal-a").status_code, 200)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (operativo, preparacion) = conexion.execute(
                "SELECT estado_operativo, estado_preparacion FROM habitaciones WHERE id = 'HAB-SINT-101'"
            ).fetchone()
            (tarea,) = conexion.execute(
                "SELECT id FROM tareas_operativas WHERE habitacion_id = 'HAB-SINT-101' "
                "AND tipo = 'limpieza' AND estado = 'pendiente'"
            ).fetchone()
        self.assertEqual((operativo, preparacion), ("disponible", "sucia"))
        self.assertIsNotNone(tarea)
        # una reserva nueva en la unidad sucia no puede hacer check-in
        rid_c = self.reservar("HAB-SINT-101", P7, P9, "Clara", clave="r-c2")
        self.assertEqual(self.entrada(rid_c, "ent-c").status_code, 409)
        # la limpieza completa la tarea y deja la unidad limpia
        limpieza = self.cliente.post(
            "/hotel/habitaciones/HAB-SINT-101/limpieza", json={}, headers={"Idempotency-Key": "limp-1"}
        )
        self.assertEqual(limpieza.status_code, 200)
        self.assertEqual(limpieza.json()["estado_preparacion"], "limpia")
        # ahora el check-in de C entra
        self.assertEqual(self.entrada(rid_c, "ent-c-2").status_code, 200)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (operativo,) = conexion.execute(
                "SELECT estado_operativo FROM habitaciones WHERE id = 'HAB-SINT-101'").fetchone()
        self.assertEqual(operativo, "ocupada")
        # limpieza sin tarea pendiente: no-op idempotente (200, 0 tareas cerradas)
        otra = self.cliente.post(
            "/hotel/habitaciones/HAB-SINT-101/limpieza", json={}, headers={"Idempotency-Key": "limp-2"}
        )
        self.assertEqual(otra.status_code, 200)
        self.assertEqual(otra.json()["tareas_completadas"], 0)
        self.assertEqual(otra.json()["estado_preparacion"], "limpia")

    def test_mantenimiento_bloquea_entrada_y_sale_de_la_oferta(self):
        rid = self.reservar("HAB-SINT-102", P1, P3, "Carlos", clave="r-mant")
        abrir = self.cliente.post(
            "/hotel/habitaciones/HAB-SINT-102/mantenimiento",
            json={"abierto": True},
            headers={"Idempotency-Key": "m-1"},
        )
        self.assertEqual(abrir.status_code, 200)
        self.assertTrue(abrir.json()["mantenimiento"])
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (flag,) = conexion.execute("SELECT mantenimiento FROM habitaciones WHERE id = 'HAB-SINT-102'").fetchone()
            (tarea,) = conexion.execute(
                "SELECT id FROM tareas_operativas WHERE habitacion_id = 'HAB-SINT-102' "
                "AND tipo = 'mantenimiento' AND estado = 'pendiente'"
            ).fetchone()
        self.assertTrue(flag)
        self.assertIsNotNone(tarea)
        # aunque la preparación siga limpia, check_in lo niega (mantenimiento)
        self.assertEqual(self.entrada(rid, "ent-mant").status_code, 409)
        oferta = self.cliente.get("/hotel/oferta", params={"inicio": FUTURO, "fin": FUTURO_FIN, "personas": 2}
                                  ).json()["oferta"]
        self.assertNotIn("HAB-SINT-102", {i["habitacion_id"] for i in oferta})
        cerrar = self.cliente.post(
            "/hotel/habitaciones/HAB-SINT-102/mantenimiento",
            json={"abierto": False},
            headers={"Idempotency-Key": "m-2"},
        )
        self.assertEqual(cerrar.status_code, 200)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (pendientes,) = conexion.execute(
                "SELECT count(*) FROM tareas_operativas WHERE habitacion_id = 'HAB-SINT-102' "
                "AND tipo = 'mantenimiento' AND estado = 'pendiente'"
            ).fetchone()
        self.assertEqual(pendientes, 0)
        self.assertEqual(self.entrada(rid, "ent-tras-cerrar").status_code, 200)

    def test_limpieza_requiere_rol_recepcion_o_admin(self):
        self.alta_usuario("caja1", "caja", "clave-caja", "u-caja")
        cliente = self.cliente_como("caja1", "clave-caja")
        respuesta = cliente.post(
            "/hotel/habitaciones/HAB-SINT-101/limpieza", json={}, headers={"Idempotency-Key": "limp-rol"}
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_oferta_incluye_unidad_ocupada_cuando_no_solapa(self):
        rid = self.reservar("HAB-SINT-101", P1, P3, "Diana", clave="r-ocu")
        self.assertEqual(self.entrada(rid, "ent-ocu").status_code, 200)
        oferta = self.cliente.get(
            "/hotel/oferta", params={"inicio": FUTURO, "fin": FUTURO_FIN, "personas": 2}
        ).json()["oferta"]
        self.assertIn("HAB-SINT-101", {i["habitacion_id"] for i in oferta})
        solapada = self.cliente.get(
            "/hotel/oferta", params={"inicio": P1, "fin": P3, "personas": 2}
        ).json()["oferta"]
        self.assertNotIn("HAB-SINT-101", {i["habitacion_id"] for i in solapada})

    def test_entrada_no_exige_documento_ni_hora_de_llegada_en_el_contrato(self):
        # spec-api-v1 «Operación de la habitación»: la entrada solo se niega
        # por mantenimiento/disponible/preparación/otra estadía solapada. El
        # documento es nullable y la hora de llegada no es condición HTTP.
        sin_doc = self.reservar("HAB-SINT-103", P1, P3, "Elías", documento=None, clave="r-sd")
        self.assertEqual(self.entrada(sin_doc, "ent-sd").status_code, 200)

    def test_entrada_exige_que_la_reserva_haya_comenzado(self):
        # REQUISITO PROPUESTO 2026-11-03 (v1-issue-07, en ratificación): la
        # entrada exige inicio <= hoy; fuente: regla de llegada del dominio.
        futura = self.reservar("HAB-SINT-102", FUTURO, FUTURO_FIN, "Fito", clave="r-fu")
        respuesta = self.entrada(futura, "ent-fu")
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("día de entrada", respuesta.json()["detail"])
        hoy = HOY.isoformat()
        manana = (HOY + timedelta(days=2)).isoformat()
        actual = self.reservar("HAB-SINT-102", hoy, manana, "Gabi", clave="r-ga")
        self.assertEqual(self.entrada(actual, "ent-ga").status_code, 200)

    # ---- 5. cancelación (decide el dominio, sin reversos) ----

    def test_cancelacion_dentro_de_plazo_sin_penalidad(self):
        rid = self.reservar("HAB-SINT-102", FUTURO, FUTURO_FIN, "Elena", clave="r-eli")
        respuesta = self.cancelar(rid, "can-eli")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["estado"], "cancelada")
        self.assertEqual(respuesta.json()["penalidad_clp"], 0)
        self.assertEqual(respuesta.json()["reembolso"], "no configurado")
        # V1: el alojamiento completo nace al confirmar y la cancelación lo
        # revierte: un cargo + un reverso. Los cargos no se borran.
        cargos = self._cargos_de(rid)
        self.assertEqual(len(cargos), 2)
        tipos = sorted(c[1] for c in cargos)
        self.assertEqual(tipos, ["cargo", "reverso"])
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (estado,) = conexion.execute("SELECT estado FROM reservas WHERE id = %s", (rid,)).fetchone()
        self.assertEqual(estado, "cancelada")
        oferta = self.cliente.get("/hotel/oferta", params={"inicio": FUTURO, "fin": FUTURO_FIN, "personas": 2}
                                  ).json()["oferta"]
        self.assertIn("HAB-SINT-102", {i["habitacion_id"] for i in oferta})
        self.assertEqual(self.cancelar(rid, "can-eli-2").status_code, 409)

    def test_cancelacion_fuera_de_plazo_carga_la_primera_noche(self):
        rid = self.reservar("HAB-SINT-103", P1, P2, "Fabián", clave="r-fab")
        respuesta = self.cancelar(rid, "can-fab")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["penalidad_clp"], 50_000)
        # alojamiento + reverso + penalidad de la primera noche
        cargos = self._cargos_de(rid)
        self.assertEqual(len(cargos), 3)
        penalidad = [c for c in cargos if c[1] == "cargo" and "primera noche" in c[2]]
        self.assertEqual(len(penalidad), 1)
        self.assertEqual(penalidad[0][3], 50_000)

    def test_cancelacion_desde_en_estadia_o_finalizada_da_409(self):
        rid = self.reservar("HAB-SINT-101", P1, P3, "Gloria", clave="r-glo")
        self.pagar(rid, 100_000, "cob-glo", "pag-glo")
        self.entrada(rid, "ent-glo")
        self.assertEqual(self.cancelar(rid, "can-glo-1").status_code, 409)
        self.salida(rid, "sal-glo")
        self.assertEqual(self.cancelar(rid, "can-glo-2").status_code, 409)

    def test_cancelacion_con_saldo_a_favor_se_confirma_sin_reembolso(self):
        rid = self.reservar("HAB-SINT-102", FUTURO, (date.fromisoformat(FUTURO) + timedelta(days=1)).isoformat(),
                            "Héctor", clave="r-hec")
        self.assertEqual(self.pagar(rid, 70_000, "cob-hec", "pag-hec").status_code, 201)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (pagos_antes,) = conexion.execute("SELECT count(*) FROM pagos WHERE reserva_id = %s", (rid,)).fetchone()
        respuesta = self.cancelar(rid, "can-hec")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["estado"], "cancelada")
        self.assertEqual(respuesta.json()["reembolso"], "no configurado")
        # saldo a favor del huésped (pagado > neto) sin reembolso: los pagos no se tocan
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (pagos_despues,) = conexion.execute("SELECT count(*) FROM pagos WHERE reserva_id = %s", (rid,)).fetchone()
            (neto,) = conexion.execute(
                "SELECT COALESCE(SUM(CASE WHEN tipo = 'reverso' THEN -monto_clp ELSE monto_clp END), 0) "
                "FROM cargos WHERE reserva_id = %s", (rid,)).fetchone()
            (pagado,) = conexion.execute(
                "SELECT COALESCE(SUM(monto_clp), 0) FROM pagos WHERE reserva_id = %s", (rid,)).fetchone()
        self.assertEqual(pagos_despues, pagos_antes)
        self.assertLess(neto - pagado, 0)

    def test_cancelacion_idempotente_no_duplica_la_penalizacion(self):
        rid = self.reservar("HAB-SINT-103", P1, P2, "Irene", clave="r-ire")
        primera = self.cancelar(rid, "can-ire")
        segunda = self.cancelar(rid, "can-ire")
        self.assertEqual(primera.status_code, 200)
        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(primera.json(), segunda.json())
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (cargos,) = conexion.execute("SELECT count(*) FROM cargos WHERE reserva_id = %s", (rid,)).fetchone()
        # alojamiento + reverso + penalidad (fuera de plazo), sin duplicar
        self.assertEqual(cargos, 3)

    def test_cancelacion_requiere_rol_recepcion_o_admin(self):
        self.alta_usuario("caja1", "caja", "clave-caja", "u-caja")
        cliente = self.cliente_como("caja1", "clave-caja")
        rid = self.reservar("HAB-SINT-101", FUTURO, FUTURO_FIN, "Jorge", clave="r-jor")
        respuesta = cliente.post(f"/hotel/reservas/{rid}/cancelacion", json={}, headers={"Idempotency-Key": "can-rol"})
        self.assertEqual(respuesta.status_code, 403)

    # ---- 6. cargos de estadía (decide el dominio) ----

    def test_cargo_aparece_en_la_liquidacion_de_salida(self):
        rid = self.reservar("HAB-SINT-101", P1, P3, "Karla", clave="r-kar")
        cargo = self.cliente.post(
            f"/hotel/reservas/{rid}/cargos",
            json={"concepto": "Minibar", "monto_clp": 7_000},
            headers={"Idempotency-Key": "car-1"},
        )
        self.assertEqual(cargo.status_code, 201, cargo.text)
        self.assertEqual(cargo.json()["tipo"], "cargo")
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (tipo, concepto, monto) = conexion.execute(
                "SELECT tipo, concepto, monto_clp FROM cargos WHERE reserva_id = %s AND concepto = 'Minibar'",
                (rid,),
            ).fetchone()
        self.assertEqual((tipo, concepto, monto), ("cargo", "Minibar", 7_000))
        self.pagar(rid, 107_000, "cob-kar", "pag-kar")
        self.entrada(rid, "ent-kar")
        cargo2 = self.cliente.post(
            f"/hotel/reservas/{rid}/cargos",
            json={"concepto": "consumo restaurante", "monto_clp": 3_000},
            headers={"Idempotency-Key": "car-2"},
        )
        self.assertEqual(cargo2.status_code, 201)
        self.pagar(rid, 3_000, "cob-kar-2", "pag-kar-2")
        salida = self.salida(rid, "sal-kar")
        self.assertEqual(salida.status_code, 200)
        self.assertEqual(salida.json()["total_clp"], 110_000)  # 100.000 noches + 10.000 cargos
        self.assertEqual(salida.json()["saldo_clp"], 0)

    def test_cargo_valida_monto_y_estado(self):
        rid = self.reservar("HAB-SINT-102", P1, P2, "Luis", clave="r-lui")
        invalido = self.cliente.post(
            f"/hotel/reservas/{rid}/cargos",
            json={"concepto": "extra", "monto_clp": 0},
            headers={"Idempotency-Key": "car-val"},
        )
        self.assertEqual(invalido.status_code, 422)
        self.pagar(rid, 50_000, "cob-lui", "pag-lui")
        self.entrada(rid, "ent-lui")
        self.salida(rid, "sal-lui")
        finalizada = self.cliente.post(
            f"/hotel/reservas/{rid}/cargos",
            json={"concepto": "extra", "monto_clp": 1_000},
            headers={"Idempotency-Key": "car-fin"},
        )
        self.assertEqual(finalizada.status_code, 409)
        self.assertTrue(all(c[1] == "cargo" for c in self._cargos_de(rid)))

    def test_cargo_rol_caja_y_reserva_ajena(self):
        self.alta_usuario("caja1", "caja", "clave-caja", "u-caja")
        cliente = self.cliente_como("caja1", "clave-caja")
        rid = self.reservar("HAB-SINT-103", FUTURO, FUTURO_FIN, "Mónica", clave="r-mon")
        respuesta = cliente.post(
            f"/hotel/reservas/{rid}/cargos",
            json={"concepto": "consumo", "monto_clp": 5_000},
            headers={"Idempotency-Key": "car-caja"},
        )
        self.assertEqual(respuesta.status_code, 201)
        ajena = cliente.post(
            "/hotel/reservas/RSV-NO-EXISTE/cargos",
            json={"concepto": "consumo", "monto_clp": 5_000},
            headers={"Idempotency-Key": "car-ajena"},
        )
        self.assertEqual(ajena.status_code, 403)

    def test_auditoria_registra_las_mutaciones_nuevas(self):
        rid = self.reservar("HAB-SINT-101", FUTURO, FUTURO_FIN, "Nora", clave="r-nor")
        self.cancelar(rid, "can-nor")
        self.cliente.post(
            "/hotel/habitaciones/HAB-SINT-101/mantenimiento",
            json={"abierto": True},
            headers={"Idempotency-Key": "m-aud"},
        )
        self.alta_usuario("recepcion1", "recepcion", "clave-rec", "u-aud")
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            filas = conexion.execute("SELECT accion, resultado FROM auditoria").fetchall()
        acciones = {(f[0], f[1]) for f in filas}
        self.assertIn(("cancelacion", "cancelada"), acciones)
        self.assertIn(("mantenimiento", "abierto"), acciones)
        self.assertIn(("usuario", "creado"), acciones)


if __name__ == "__main__":
    unittest.main()
