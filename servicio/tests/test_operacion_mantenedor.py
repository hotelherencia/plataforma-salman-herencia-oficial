"""Mantenedor de habitaciones, consulta de reservas, ocupación e indicadores
(2026-11-03, spec-hotel-operacion-v1 §6). HTTP contra PostgreSQL real con el
mismo aislamiento que test_h6; datos 100% sintéticos y fechas relativas a hoy.
Cada prueba lleva el criterio de aceptación que ejerce (CA-*)."""
import os
import unittest
from datetime import date, datetime, time, timedelta

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


def d(dias: int) -> date:
    return HOY + timedelta(days=dias)


def iso(dias: int) -> str:
    return d(dias).isoformat()


def _vaciar(conexion):
    conexion.execute(
        "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
        "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
    )
    seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
    seguridad.crear_usuario(conexion, EMPRESA, "recepcion1", "recepcion", "clave-recepcion")
    seguridad.crear_usuario(conexion, EMPRESA, "caja1", "caja", "clave-caja")


def _habitacion(conexion, hid, tipo="doble", capacidad=2, tarifa=45000, registrada_hace=30, **columnas):
    conexion.execute(
        "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, creado_en) "
        "VALUES (%s, 'EST-SINT-001', %s, %s, now() - make_interval(days => %s))",
        (hid, tipo, capacidad, registrada_hace),
    )
    for columna, valor in columnas.items():
        conexion.execute(f"UPDATE habitaciones SET {columna} = %s WHERE id = %s", (valor, hid))
    if tarifa:
        conexion.execute(
            "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
            "VALUES (%s, %s, %s, %s, %s)",
            (f"TAR-{hid}", hid, d(-400), d(400), tarifa),
        )


def _reserva(conexion, rid, hid, inicio, fin, estado, tarifa=45000, liquidada_el=None, documento="DOC-SINT"):
    conexion.execute(
        "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, "
        "tarifa_noche_aceptada_clp, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (rid, EMPRESA, hid, inicio, fin, f"Huésped {rid}", documento, tarifa, estado),
    )
    if liquidada_el is not None:
        conexion.execute(
            "INSERT INTO liquidaciones (id, reserva_id, total_clp, pagado_clp, saldo_clp, creado_en) "
            "VALUES (%s, %s, 0, 0, 0, %s)",
            (f"LQ-{rid}", rid, datetime.combine(liquidada_el, time(11, 0)).astimezone()),
        )


class BaseOperacion(unittest.TestCase):
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
            _vaciar(conexion)
            self.semilla(conexion)
        self.admin = self.login(*ADMIN)
        self._n = 0

    def semilla(self, conexion):
        pass

    def login(self, usuario, clave):
        cliente = TestClient(self.app)
        respuesta = cliente.post("/sesion", json={"usuario": usuario, "clave": clave})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return cliente

    def clave(self, prefijo="k"):
        self._n += 1
        return {"Idempotency-Key": f"{prefijo}-{self._n}"}

    def sql(self, consulta, parametros=()):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            return conexion.execute(consulta, parametros).fetchall()

    def reservar(self, hid, inicio, fin, cliente=None):
        respuesta = (cliente or self.admin).post(
            "/hotel/reservas",
            json={"habitacion_id": hid, "inicio": inicio, "fin": fin,
                  "huesped": {"nombre": "Huésped Sintético", "documento": "11.111.111-1"}},
            headers=self.clave("rsv"),
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()

    def oferta_ids(self, inicio, fin, personas=1):
        respuesta = self.admin.get(f"/hotel/oferta?inicio={inicio}&fin={fin}&personas={personas}")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return {u["habitacion_id"]: u for u in respuesta.json()["oferta"]}


class MantenedorHabitacionesTest(BaseOperacion):
    def semilla(self, conexion):
        _habitacion(conexion, "HAB-M-1")

    def test_ca_hab_01_alta_solo_crea_con_if_none_match(self):
        r = self.admin.put("/hotel/habitaciones/HAB-M-NUEVA", json={"tipo": "  suite ", "capacidad": 3},
                           headers={**self.clave(), "If-None-Match": "*"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["creada"])
        self.assertEqual(r.json()["tipo"], "suite")
        # repetir el alta (otra clave) sobre una existente: 409 y nada cambia
        r = self.admin.put("/hotel/habitaciones/HAB-M-NUEVA", json={"tipo": "doble", "capacidad": 1},
                           headers={**self.clave(), "If-None-Match": "*"})
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(self.sql("SELECT tipo, capacidad FROM habitaciones WHERE id = 'HAB-M-NUEVA'"),
                         [("suite", 3)])
        self.assertIn(("habitacion", "creada tipo=suite capacidad=3"),
                      {(a, b) for a, b in self.sql("SELECT accion, resultado FROM auditoria "
                                                   "WHERE recurso = 'HAB-M-NUEVA'")})
        # nace sin tarifa: no se ofrece hasta tener una
        self.assertNotIn("HAB-M-NUEVA", self.oferta_ids(iso(10), iso(12)))

    def test_ca_hab_01_validaciones_de_alta(self):
        for ruta, cuerpo in (("/hotel/habitaciones/HAB.1", {"tipo": "doble", "capacidad": 2}),
                             ("/hotel/habitaciones/HAB-OK", {"tipo": "   ", "capacidad": 2}),
                             ("/hotel/habitaciones/HAB-OK", {"tipo": "doble", "capacidad": 0}),
                             ("/hotel/habitaciones/HAB-OK", {"tipo": "doble", "capacidad": 31})):
            with self.subTest(ruta=ruta, cuerpo=cuerpo):
                self.assertEqual(self.admin.put(ruta, json=cuerpo, headers=self.clave()).status_code, 422)
        self.assertEqual(self.sql("SELECT count(*) FROM habitaciones WHERE id IN ('HAB.1', 'HAB-OK')"), [(0,)])

    def test_ca_hab_02_edicion_con_reserva_previa_no_toca_la_reserva(self):
        reserva = self.reservar("HAB-M-1", iso(5), iso(8))
        antes = self.sql("SELECT habitacion_id, inicio, fin, estado, tarifa_noche_aceptada_clp FROM reservas")
        r = self.admin.put("/hotel/habitaciones/HAB-M-1", json={"tipo": "suite", "capacidad": 4},
                           headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertFalse(r.json()["creada"])
        self.assertEqual(r.json()["cambios"], {"tipo": ["doble", "suite"], "capacidad": [2, 4]})
        self.assertEqual(self.sql("SELECT habitacion_id, inicio, fin, estado, tarifa_noche_aceptada_clp "
                                  "FROM reservas"), antes)
        self.assertEqual(self.admin.get(f"/hotel/reservas/{reserva['reserva_id']}").json()["cuenta"]["cargos_netos_clp"],
                         3 * 45000)
        auditoria = [f[0] for f in self.sql("SELECT resultado FROM auditoria WHERE accion = 'habitacion'")]
        self.assertIn("editada tipo: doble→suite; capacidad: 2→4", auditoria)
        # el mismo cuerpo otra vez (otra clave): sin cambios, también auditado
        r = self.admin.put("/hotel/habitaciones/HAB-M-1", json={"tipo": "suite", "capacidad": 4},
                           headers=self.clave())
        self.assertEqual(r.json()["cambios"], {})

    def test_ca_hab_03_tarifa_nueva_cambia_la_venta_y_no_la_reserva(self):
        reserva = self.reservar("HAB-M-1", iso(5), iso(7))
        self.assertEqual(reserva["tarifa_noche_aceptada_clp"], 45000)
        # misma fecha_desde que la vigente: gana la registrada más recientemente
        r = self.admin.put("/hotel/tarifas", json={"habitacion_id": "HAB-M-1", "fecha_desde": d(-400).isoformat(),
                                                   "fecha_hasta": d(400).isoformat(), "tarifa_noche_clp": 60000},
                           headers=self.clave())
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self.oferta_ids(iso(10), iso(11))["HAB-M-1"]["tarifa_noche_clp"], 60000)
        # tramo específico de fecha_desde posterior gana sobre el rango amplio
        self.admin.put("/hotel/tarifas", json={"habitacion_id": "HAB-M-1", "fecha_desde": iso(20),
                                               "fecha_hasta": iso(22), "tarifa_noche_clp": 80000},
                       headers=self.clave())
        self.assertEqual(self.oferta_ids(iso(20), iso(21))["HAB-M-1"]["tarifa_noche_clp"], 80000)
        self.assertEqual(self.oferta_ids(iso(22), iso(23))["HAB-M-1"]["tarifa_noche_clp"], 60000)
        # la reserva conserva su tarifa y su cargo
        detalle = self.admin.get(f"/hotel/reservas/{reserva['reserva_id']}").json()
        self.assertEqual(detalle["tarifa_noche_aceptada_clp"], 45000)
        self.assertEqual(detalle["cuenta"]["cargos_netos_clp"], 90000)
        # historial completo en la ficha, con la vigente de hoy marcada
        ficha = self.admin.get("/hotel/habitaciones/HAB-M-1").json()
        self.assertEqual(len(ficha["tarifas"]), 3)
        vigentes = [t for t in ficha["tarifas"] if t["vigente_hoy"]]
        self.assertEqual([t["tarifa_noche_clp"] for t in vigentes], [60000])
        self.assertEqual(ficha["tarifa_vigente_hoy_clp"], 60000)
        self.assertEqual(len([a for a in ficha["auditoria"] if a["accion"] == "tarifa"]), 2)

    def test_ca_hab_04_retiro_baja_logica_y_reincorporacion(self):
        reserva = self.reservar("HAB-M-1", iso(5), iso(7))
        # sin motivo: 422
        r = self.admin.post("/hotel/habitaciones/HAB-M-1/servicio", json={"en_servicio": False},
                            headers=self.clave())
        self.assertEqual(r.status_code, 422, r.text)
        # con reserva vigente: 409 con la lista y nada cambia
        r = self.admin.post("/hotel/habitaciones/HAB-M-1/servicio",
                            json={"en_servicio": False, "motivo": "remodelación"}, headers=self.clave())
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(r.json()["reservas_vigentes"], [reserva["reserva_id"]])
        self.assertEqual(self.sql("SELECT estado_operativo FROM habitaciones WHERE id = 'HAB-M-1'"),
                         [("disponible",)])
        # cancelada la reserva, el retiro procede
        self.assertEqual(self.admin.post(f"/hotel/reservas/{reserva['reserva_id']}/cancelacion", json={},
                                         headers=self.clave()).status_code, 200)
        r = self.admin.post("/hotel/habitaciones/HAB-M-1/servicio",
                            json={"en_servicio": False, "motivo": "remodelación"}, headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["estado_operativo"], r.json()["en_servicio"], r.json()["cambio"]),
                         ("fuera_de_servicio", False, True))
        self.assertNotIn("HAB-M-1", self.oferta_ids(iso(10), iso(12)))
        # historial intacto: reserva cancelada, cargos y tarifa siguen ahí
        ficha = self.admin.get("/hotel/habitaciones/HAB-M-1").json()
        self.assertEqual(ficha["motivo_fuera_de_servicio"], "remodelación")
        self.assertEqual([x["estado"] for x in ficha["reservas"]], ["cancelada"])
        self.assertEqual(len(ficha["tarifas"]), 1)
        self.assertGreater(self.sql("SELECT count(*) FROM cargos")[0][0], 0)
        # retirar otra vez: sin cambios
        r = self.admin.post("/hotel/habitaciones/HAB-M-1/servicio",
                            json={"en_servicio": False, "motivo": "remodelación"}, headers=self.clave())
        self.assertFalse(r.json()["cambio"])
        # reincorporar: vuelve a la oferta
        r = self.admin.post("/hotel/habitaciones/HAB-M-1/servicio", json={"en_servicio": True},
                            headers=self.clave())
        self.assertEqual((r.json()["estado_operativo"], r.json()["motivo"]), ("disponible", None))
        self.assertIn("HAB-M-1", self.oferta_ids(iso(10), iso(12)))
        resultados = [f[0] for f in self.sql("SELECT resultado FROM auditoria WHERE accion = 'habitacion-servicio' "
                                             "ORDER BY creado_en")]
        self.assertEqual(resultados, ["retirada: remodelación", "sin cambios", "reincorporada"])

    def test_ca_hab_04_estadia_en_curso_impide_el_retiro(self):
        reserva = self.reservar("HAB-M-1", iso(0), iso(2))
        self.admin.post(f"/hotel/reservas/{reserva['reserva_id']}/entrada", json={}, headers=self.clave())
        r = self.admin.post("/hotel/habitaciones/HAB-M-1/servicio",
                            json={"en_servicio": False, "motivo": "daño"}, headers=self.clave())
        self.assertEqual(r.status_code, 409, r.text)

    def test_ca_hab_05_no_hay_borrado_fisico(self):
        esquema = self.admin.get("/openapi.json").json()
        for ruta, operaciones in esquema["paths"].items():
            if ruta.startswith("/hotel/habitaciones"):
                self.assertNotIn("delete", operaciones, ruta)
        self.assertEqual(self.admin.delete("/hotel/habitaciones/HAB-M-1").status_code, 405)
        self.reservar("HAB-M-1", iso(5), iso(7))
        with psycopg.connect(URL_TEST) as conexion, self.assertRaises(psycopg.errors.ForeignKeyViolation):
            conexion.execute("DELETE FROM habitaciones WHERE id = 'HAB-M-1'")

    def test_ca_hab_06_permisos_por_rol(self):
        for usuario, clave in (("recepcion1", "clave-recepcion"), ("caja1", "clave-caja")):
            cliente = self.login(usuario, clave)
            with self.subTest(rol=usuario):
                self.assertEqual(cliente.put("/hotel/habitaciones/HAB-M-1", json={"tipo": "x", "capacidad": 1},
                                             headers=self.clave()).status_code, 403)
                self.assertEqual(cliente.put("/hotel/tarifas", json={"habitacion_id": "HAB-M-1",
                                                                     "fecha_desde": iso(1), "fecha_hasta": iso(2),
                                                                     "tarifa_noche_clp": 1},
                                             headers=self.clave()).status_code, 403)
                self.assertEqual(cliente.post("/hotel/habitaciones/HAB-M-1/servicio",
                                              json={"en_servicio": False, "motivo": "abc"},
                                              headers=self.clave()).status_code, 403)
                ficha = cliente.get("/hotel/habitaciones/HAB-M-1")
                self.assertEqual(ficha.status_code, 200)
                self.assertNotIn("auditoria", ficha.json())
        self.assertIn("auditoria", self.admin.get("/hotel/habitaciones/HAB-M-1").json())
        self.assertEqual(self.admin.get("/hotel/habitaciones/HAB-NO-EXISTE").status_code, 403)
        self.assertEqual(TestClient(self.app).get("/hotel/habitaciones/HAB-M-1").status_code, 401)

    def test_inventario_declara_servicio_y_tarifa_de_hoy(self):
        item = self.admin.get("/hotel/habitaciones").json()["habitaciones"][0]
        self.assertEqual((item["en_servicio"], item["tarifa_vigente_hoy_clp"], item["tarifa_noche_clp"]),
                         (True, 45000, 45000))


class ConsultaReservasTest(BaseOperacion):
    def semilla(self, conexion):
        _habitacion(conexion, "HAB-C-1")
        _habitacion(conexion, "HAB-C-2")
        _reserva(conexion, "RSV-C-A", "HAB-C-1", d(1), d(3), "confirmada")
        _reserva(conexion, "RSV-C-B", "HAB-C-2", d(2), d(6), "confirmada")
        _reserva(conexion, "RSV-C-C", "HAB-C-1", d(10), d(12), "cancelada")

    def ids(self, consulta, cliente=None):
        r = (cliente or self.admin).get(f"/hotel/reservas?{consulta}")
        self.assertEqual(r.status_code, 200, r.text)
        return [x["reserva_id"] for x in r.json()["reservas"]]

    def test_ca_res_01_periodo_y_habitacion(self):
        self.assertEqual(self.ids(f"desde={iso(3)}&hasta={iso(11)}"), ["RSV-C-B", "RSV-C-C"])
        self.assertEqual(self.ids(f"desde={iso(0)}&hasta={iso(2)}"), ["RSV-C-A"])
        self.assertEqual(self.ids(f"hasta={iso(2)}"), ["RSV-C-A"])
        self.assertEqual(self.ids(f"desde={iso(5)}"), ["RSV-C-B", "RSV-C-C"])
        self.assertEqual(self.ids("habitacion_id=HAB-C-1"), ["RSV-C-A", "RSV-C-C"])
        self.assertEqual(self.ids(f"habitacion_id=HAB-C-1&estado=confirmada&desde={iso(0)}&hasta={iso(30)}"),
                         ["RSV-C-A"])
        self.assertEqual(self.admin.get(f"/hotel/reservas?desde={iso(3)}&hasta={iso(3)}").status_code, 422)
        item = self.admin.get("/hotel/reservas?habitacion_id=HAB-C-2").json()["reservas"][0]
        self.assertEqual(item["noches"], 4)

    def test_ca_res_02_detalle_con_cuenta_y_saldo_de_la_salida(self):
        reserva = self.reservar("HAB-C-2", iso(0), iso(2))
        rid = reserva["reserva_id"]
        self.admin.post(f"/hotel/reservas/{rid}/pagos", json={"monto_clp": 50000, "clave": "p1", "modo": "manual"},
                        headers=self.clave())
        self.admin.post(f"/hotel/reservas/{rid}/entrada", json={}, headers=self.clave())
        self.admin.post(f"/hotel/reservas/{rid}/cargos", json={"concepto": "minibar", "monto_clp": 7000},
                        headers=self.clave())
        detalle = self.admin.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(detalle["cuenta"], {"cargos_netos_clp": 97000, "pagado_clp": 50000, "saldo_clp": 47000})
        self.assertEqual([c["concepto"] for c in detalle["cargos"]], ["Alojamiento 2 noches", "minibar"])
        self.assertEqual(detalle["huesped_documento"], "11.111.111-1")
        salida = self.admin.post(f"/hotel/reservas/{rid}/salida", json={}, headers=self.clave())
        self.assertEqual(salida.status_code, 409)
        self.assertIn("47000", salida.json()["detail"])
        self.admin.post(f"/hotel/reservas/{rid}/pagos", json={"monto_clp": 47000, "clave": "p2", "modo": "manual"},
                        headers=self.clave())
        self.assertEqual(self.admin.get(f"/hotel/reservas/{rid}").json()["cuenta"]["saldo_clp"], 0)
        self.assertEqual(self.admin.post(f"/hotel/reservas/{rid}/salida", json={},
                                         headers=self.clave()).status_code, 200)
        detalle = self.admin.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual((detalle["estado"], detalle["liquidacion"]["saldo_clp"]), ("finalizada", 0))
        caja = self.login("caja1", "clave-caja").get(f"/hotel/reservas/{rid}")
        self.assertEqual(caja.status_code, 200)
        self.assertNotIn("huesped_documento", caja.json())
        self.assertEqual(self.admin.get("/hotel/reservas/RSV-NO-EXISTE").status_code, 403)


class OcupacionTest(BaseOperacion):
    def semilla(self, conexion):
        _habitacion(conexion, "HAB-O-1")
        _habitacion(conexion, "HAB-O-2")
        _habitacion(conexion, "HAB-O-3", mantenimiento=True)
        _habitacion(conexion, "HAB-O-4", tarifa=None)
        _habitacion(conexion, "HAB-O-5", estado_operativo="fuera_de_servicio")
        _reserva(conexion, "RSV-O-FIN", "HAB-O-1", d(-3), d(-1), "finalizada", liquidada_el=d(-1))
        _reserva(conexion, "RSV-O-EST", "HAB-O-1", d(-1), d(1), "en_estadia")
        _reserva(conexion, "RSV-O-CON", "HAB-O-2", d(1), d(3), "confirmada")
        _reserva(conexion, "RSV-O-CAN", "HAB-O-2", d(3), d(5), "cancelada")

    def test_ca_ocu_01_estado_por_noche(self):
        r = self.admin.get(f"/hotel/ocupacion?desde={iso(-2)}&hasta={iso(4)}")
        self.assertEqual(r.status_code, 200, r.text)
        cuerpo = r.json()
        self.assertEqual(cuerpo["fecha_corte"], HOY.isoformat())
        filas = {h["habitacion_id"]: [n["estado"] for n in h["noches"]] for h in cuerpo["habitaciones"]}
        self.assertEqual(filas["HAB-O-1"], ["finalizada", "en_estadia", "en_estadia", "disponible", "disponible",
                                            "disponible"])
        self.assertEqual(filas["HAB-O-2"], ["sin_ocupar", "sin_ocupar", "disponible", "confirmada", "confirmada",
                                            "disponible"])
        self.assertEqual(filas["HAB-O-3"][2:], ["no_vendible"] * 4)
        self.assertEqual(filas["HAB-O-4"][2:], ["sin_tarifa"] * 4)
        self.assertEqual(filas["HAB-O-5"][2:], ["no_vendible"] * 4)
        motivos = {h["habitacion_id"]: h["noches"][3].get("motivo") for h in cuerpo["habitaciones"]}
        self.assertEqual((motivos["HAB-O-3"], motivos["HAB-O-5"]), ("mantenimiento", "fuera_de_servicio"))
        # la cancelada se lista y no pinta noches
        reservas_2 = {x["reserva_id"]: x["estado"] for x in
                      next(h for h in cuerpo["habitaciones"] if h["habitacion_id"] == "HAB-O-2")["reservas"]}
        self.assertEqual(reservas_2, {"RSV-O-CON": "confirmada", "RSV-O-CAN": "cancelada"})
        hoy = next(x for x in cuerpo["resumen"] if x["fecha"] == HOY.isoformat())
        self.assertEqual(hoy, {"fecha": HOY.isoformat(), "disponibles": 1, "ocupadas": 1, "no_vendibles": 2})

    def test_ca_ocu_01_consistente_con_la_oferta(self):
        cuerpo = self.admin.get(f"/hotel/ocupacion?desde={iso(0)}&hasta={iso(5)}").json()
        for habitacion in cuerpo["habitaciones"]:
            for noche in habitacion["noches"]:
                inicio = date.fromisoformat(noche["fecha"])
                ofrecidas = self.oferta_ids(inicio.isoformat(), (inicio + timedelta(days=1)).isoformat())
                with self.subTest(habitacion=habitacion["habitacion_id"], noche=noche["fecha"]):
                    self.assertEqual(noche["estado"] == "disponible", habitacion["habitacion_id"] in ofrecidas)
                    if noche["estado"] == "disponible":
                        self.assertEqual(noche["tarifa_noche_clp"],
                                         ofrecidas[habitacion["habitacion_id"]]["tarifa_noche_clp"])

    def test_periodo_invalido(self):
        self.assertEqual(self.admin.get(f"/hotel/ocupacion?desde={iso(0)}&hasta={iso(0)}").status_code, 422)
        self.assertEqual(self.admin.get(f"/hotel/ocupacion?desde={iso(0)}&hasta={iso(63)}").status_code, 422)
        self.assertEqual(self.login("caja1", "clave-caja").get(
            f"/hotel/ocupacion?desde={iso(0)}&hasta={iso(7)}").status_code, 200)
        por_defecto = self.admin.get("/hotel/ocupacion").json()["periodo"]
        self.assertEqual(por_defecto, {"desde": HOY.isoformat(), "hasta": iso(14), "noches": 14})


class IndicadoresTest(BaseOperacion):
    """Conjunto calculado a mano (spec-hotel-operacion-v1 §4.3), periodo de
    cuatro noches [hoy-2, hoy+2) con tres habitaciones registradas hace 30 días:
      noche   hoy-2  hoy-1  hoy   hoy+1
      ocup.   1(FIN) 2(EST,ANT) 1(EST)  —     → 4 / 9 unidades-noche pasadas
      reserv. 1      2      2(EST,CON) 1(CON) → 6 / 12
    ANT es una finalizada con salida anticipada: [hoy-1, hoy+2) liquidada hoy."""

    def semilla(self, conexion):
        _habitacion(conexion, "HAB-I-1", estado_preparacion="sucia")
        _habitacion(conexion, "HAB-I-2", estado_operativo="ocupada")
        _habitacion(conexion, "HAB-I-3", tipo="suite", mantenimiento=True)
        conexion.execute("INSERT INTO tareas_operativas (id, habitacion_id, tipo) VALUES ('T-I', 'HAB-I-1', 'limpieza')")
        _reserva(conexion, "RSV-I-FIN", "HAB-I-1", d(-3), d(-1), "finalizada", liquidada_el=d(-1))
        _reserva(conexion, "RSV-I-ANT", "HAB-I-1", d(-1), d(2), "finalizada", liquidada_el=d(0))
        _reserva(conexion, "RSV-I-EST", "HAB-I-2", d(-1), d(1), "en_estadia")
        _reserva(conexion, "RSV-I-CON", "HAB-I-3", d(0), d(2), "confirmada")
        _reserva(conexion, "RSV-I-CAN", "HAB-I-1", d(0), d(3), "cancelada")
        _reserva(conexion, "RSV-I-VEN", "HAB-I-3", d(-3), d(-2), "confirmada")

    def indicadores(self, consulta, cliente=None):
        r = (cliente or self.admin).get(f"/hotel/indicadores?{consulta}")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_ca_ind_01_valores_y_definiciones(self):
        cuerpo = self.indicadores(f"desde={iso(-2)}&hasta={iso(2)}")
        p = cuerpo["periodo_indicadores"]
        self.assertEqual(p["unidades_noche"]["valor"], 12)
        self.assertEqual(p["noches_ocupadas"]["valor"], 4)
        self.assertAlmostEqual(p["ocupacion"]["valor"], 4 / 9)
        self.assertEqual(p["noches_reservadas"]["valor"], 6)
        self.assertAlmostEqual(p["ocupacion_reservada"]["valor"], 0.5)
        self.assertEqual((p["reservas_canceladas"]["valor"], p["reservas_canceladas"]["noches"]), (1, 2))
        self.assertEqual(p["reservas_registradas"]["valor"], 6)
        for nombre, indicador in {**p, **cuerpo["hoy"]}.items():
            with self.subTest(indicador=nombre):
                for campo in ("valor", "unidad", "formula", "fuente", "limitaciones"):
                    self.assertIn(campo, indicador)
        h = cuerpo["hoy"]
        self.assertEqual(h["llegadas_hoy"]["reservas"], ["RSV-I-CON"])
        self.assertEqual(h["llegadas_vencidas"]["reservas"], ["RSV-I-VEN"])
        self.assertEqual((h["salidas_hoy"]["valor"], h["en_casa"]["valor"]), (0, 1))
        self.assertEqual((h["habitaciones_total"]["valor"], h["habitaciones_ocupadas"]["valor"],
                          h["habitaciones_vendibles"]["valor"], h["habitaciones_sucias"]["valor"],
                          h["limpiezas_pendientes"]["valor"], h["en_mantenimiento"]["valor"]), (3, 1, 2, 1, 1, 1))
        self.assertEqual([s["ocupadas"] for s in cuerpo["serie"]], [1, 2, 1, None])
        self.assertEqual([s["reservadas"] for s in cuerpo["serie"]], [1, 2, 2, 1])

    def test_ca_ind_01_filtro_por_tipo(self):
        p = self.indicadores(f"desde={iso(-2)}&hasta={iso(2)}&tipo=doble")["periodo_indicadores"]
        self.assertEqual(p["unidades_noche"]["valor"], 8)
        self.assertAlmostEqual(p["ocupacion"]["valor"], 4 / 6)
        self.assertAlmostEqual(p["ocupacion_reservada"]["valor"], 4 / 8)

    def test_ca_ind_01_sin_muestra_es_null(self):
        p = self.indicadores(f"desde={iso(1)}&hasta={iso(3)}")["periodo_indicadores"]
        self.assertIsNone(p["ocupacion"]["valor"])
        self.assertAlmostEqual(p["ocupacion_reservada"]["valor"], 1 / 6)
        vacio = self.indicadores(f"desde={iso(-2)}&hasta={iso(2)}&tipo=inexistente")["periodo_indicadores"]
        self.assertIsNone(vacio["ocupacion"]["valor"])
        self.assertIsNone(vacio["ocupacion_reservada"]["valor"])

    def test_ca_ind_02_financieros_no_publicados_y_roles(self):
        cuerpo = self.indicadores("")
        self.assertEqual(cuerpo["periodo"], {"desde": HOY.isoformat(), "hasta": iso(1), "noches": 1})
        self.assertTrue(any("ADR" in x["indicador"] for x in cuerpo["no_disponibles"]))
        texto = str(cuerpo["periodo_indicadores"]) + str(cuerpo["hoy"])
        self.assertNotIn("_clp", texto)
        for usuario, clave in (("recepcion1", "clave-recepcion"), ("caja1", "clave-caja")):
            self.indicadores("", self.login(usuario, clave))
        self.assertEqual(TestClient(self.app).get("/hotel/indicadores").status_code, 401)
        self.assertEqual(self.admin.get(f"/hotel/indicadores?desde={iso(0)}&hasta={iso(93)}").status_code, 422)


if __name__ == "__main__":
    unittest.main()
