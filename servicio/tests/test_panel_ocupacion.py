"""Reconciliación ocupación ↔ oferta ↔ panel (spec-hotel-operacion-v1 §4–§5).

Cada prueba recomputa el valor esperado de forma independiente (SQL directo
sobre el mismo dataset sintético) y lo contrasta con la respuesta de la API.
Criterios: CA-OCU-01 (estados por noche y consistencia con la oferta),
CA-HAB-08 (oferta multi-noche ⟺ todas las noches disponibles), CA-IND-01
(indicadores reconponibles desde reservas y habitaciones), y las definiciones
del resumen añadidas a §5 el 2026-11-03. La fecha de corte es la del servidor.
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
H = date.today()  # fecha de corte del servidor (misma regla que la API)


class ReconciliacionBaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        ))

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "TRUNCATE auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "solicitudes, reservas, tarifas, tareas_operativas, sesiones, usuarios, habitaciones "
                "RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.commit()
        self.cliente = TestClient(self.app)
        self.assertEqual(self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)
        self._construir_dataset()

    # ---------- helpers ----------
    def clave(self):
        return f"rec-{uuid.uuid4().hex[:10]}"

    def select(self, sql, parametros=()):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            return conexion.execute(sql, parametros).fetchall()

    def habitacion(self, hab_id, capacidad=2, tipo="doble"):
        r = self.cliente.put(
            f"/hotel/habitaciones/{hab_id}",
            json={"tipo": tipo, "capacidad": capacidad},
            headers={"If-None-Match": "*", "Idempotency-Key": self.clave()},
        )
        self.assertIn(r.status_code, (200, 201), r.text)

    def tarifa(self, hab_id, monto, desde="2026-01-01", hasta="2027-12-31"):
        r = self.cliente.put(
            "/hotel/tarifas",
            json={"habitacion_id": hab_id, "fecha_desde": desde, "fecha_hasta": hasta, "tarifa_noche_clp": monto},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertIn(r.status_code, (200, 201), r.text)

    def reservar(self, hab_id, inicio, fin, nombre="Huésped Rec"):
        r = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": hab_id, "inicio": str(inicio), "fin": str(fin),
                  "huesped": {"nombre": nombre}},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["reserva_id"]

    def entrada(self, reserva_id):
        r = self.cliente.post(f"/hotel/reservas/{reserva_id}/entrada", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(r.status_code, 200, r.text)

    def pagar(self, reserva_id, monto):
        r = self.cliente.post(
            f"/hotel/reservas/{reserva_id}/pagos",
            json={"monto_clp": monto, "clave": f"cobro-{uuid.uuid4().hex[:8]}", "modo": "manual"},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(r.status_code, 201, r.text)

    def salida(self, reserva_id):
        r = self.cliente.post(f"/hotel/reservas/{reserva_id}/salida", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(r.status_code, 200, r.text)

    def cancelar(self, reserva_id):
        r = self.cliente.post(f"/hotel/reservas/{reserva_id}/cancelacion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(r.status_code, 200, r.text)

    def retirar(self, hab_id):
        r = self.cliente.post(
            f"/hotel/habitaciones/{hab_id}/servicio",
            json={"en_servicio": False, "motivo": "revisión anual"},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(r.status_code, 200, r.text)

    def mantenimiento(self, hab_id, abierto=True):
        r = self.cliente.post(
            f"/hotel/habitaciones/{hab_id}/mantenimiento",
            json={"abierto": abierto},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(r.status_code, 200, r.text)

    def _construir_dataset(self):
        """Dataset determinista (una sola empresa, una sola zona horaria: la
        del servidor). Ver descripción en cada test."""
        self.habitacion("OC-101", capacidad=2)                       # doble, tarifa completa
        self.habitacion("OC-102", capacidad=2)                       # tarifa hasta H+5 (luego sin_tarifa)
        self.habitacion("OC-103")                                    # fuera de servicio
        self.habitacion("OC-104")                                    # mantenimiento abierto con reserva previa
        self.habitacion("OC-105", capacidad=3, tipo="suite")         # para filtro por tipo
        self.tarifa("OC-101", 50_000)
        self.tarifa("OC-102", 45_000, hasta=str(H + timedelta(days=5)))
        self.tarifa("OC-103", 55_000)
        self.tarifa("OC-104", 55_000)
        self.tarifa("OC-105", 90_000)
        # R2: estadía finalizada [H-5, H-2) en 101, salida anticipada: la
        # liquidación se fecha H-3 (fin_efectivo = H-3).
        self.r2 = self.reservar("OC-101", H - timedelta(days=5), H - timedelta(days=2), "Finalizada Temprana")
        self.entrada(self.r2)
        self.pagar(self.r2, 150_000)
        self.salida(self.r2)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("UPDATE liquidaciones SET creado_en = %s WHERE reserva_id = %s",
                             (H - timedelta(days=3), self.r2))
            conexion.commit()
        # R1: estadía en curso [H-2, H+1) en 101 (tras la salida de R2 la unidad
        # queda sucia: se completa la limpieza antes del check-in).
        self.r1 = self.reservar("OC-101", H - timedelta(days=2), H + timedelta(days=1), "En Casa")
        self.assertEqual(self.cliente.post(
            "/hotel/habitaciones/OC-101/limpieza", headers={"Idempotency-Key": self.clave()}
        ).status_code, 200)
        self.entrada(self.r1)
        # R3: finalizada hoy [H-4, H+3) en 102 → fin_efectivo = hoy (liquidación
        # real); sus noches futuras quedan libres.
        self.r3 = self.reservar("OC-102", H - timedelta(days=4), H + timedelta(days=3), "Salida Hoy")
        self.entrada(self.r3)
        self.pagar(self.r3, 7 * 45_000)
        self.salida(self.r3)
        # R5: confirmada futura [H+1, H+3) en 104, creada ANTES de abrir el
        # mantenimiento (la reserva gana sobre no_vendible en la celda).
        self.r5 = self.reservar("OC-104", H + timedelta(days=1), H + timedelta(days=3), "Confirmada Mantenimiento")
        self.mantenimiento("OC-104", abierto=True)
        # R6: confirmada futura cancelada [H+10, H+12) en 101.
        self.r6 = self.reservar("OC-101", H + timedelta(days=10), H + timedelta(days=12), "Cancelada")
        self.cancelar(self.r6)
        # OC-103 fuera de servicio (sin reservas).
        self.retirar("OC-103")

    # ---------- API ----------
    def ocupacion(self, desde, hasta):
        r = self.cliente.get("/hotel/ocupacion", params={"desde": str(desde), "hasta": str(hasta)})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def oferta(self, inicio, fin, personas=1):
        r = self.cliente.get("/hotel/oferta", params={"inicio": str(inicio), "fin": str(fin), "personas": personas})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def panel(self, desde, hasta, tipo=None):
        params = {"desde": str(desde), "hasta": str(hasta)}
        if tipo:
            params["tipo"] = tipo
        r = self.cliente.get("/hotel/indicadores", params=params)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    # ---------- reconteo independiente ----------
    def filas_reservas(self):
        """(id, habitacion_id, inicio, fin, estado, fin_efectivo) desde SQL."""
        return [
            (f[0], f[1], f[2], f[3], f[4], min(f[3], f[5].date()) if f[4] == "finalizada" and f[5] else f[3])
            for f in self.select(
                "SELECT r.id, r.habitacion_id, r.inicio, r.fin, r.estado, l.creado_en "
                "FROM reservas r LEFT JOIN liquidaciones l ON l.reserva_id = r.id"
            )
        ]

    def celda(self, datos, hab_id, noche):
        h = next(x for x in datos["habitaciones"] if x["habitacion_id"] == hab_id)
        return next(c for c in h["noches"] if c["fecha"] == str(noche))


class OcupacionOfertaReconciliacionTest(ReconciliacionBaseTest):
    DESDE = H - timedelta(days=7)
    HASTA = H + timedelta(days=10)

    def test_cada_noche_disponible_coincide_con_la_oferta_de_una_noche(self):
        datos = self.ocupacion(self.DESDE, self.HASTA)
        self.assertEqual(datos["fecha_corte"], str(H))
        for noche in [self.DESDE + timedelta(days=i) for i in range((self.HASTA - self.DESDE).days)]:
            ofertadas = {i["habitacion_id"] for i in self.oferta(noche, noche + timedelta(days=1), 1)["oferta"]}
            for h in datos["habitaciones"]:
                celda = self.celda(datos, h["habitacion_id"], noche)
                with self.subTest(habitacion=h["habitacion_id"], noche=noche):
                    if noche >= H:
                        # §5: disponible ⟺ en la oferta (misma noche, personas=1)
                        self.assertEqual(celda["estado"] == "disponible",
                                         h["habitacion_id"] in ofertadas, celda)
                    # §5: confirmada/en_estadia/no_vendible/sin_tarifa nunca en oferta
                    if celda["estado"] in ("confirmada", "en_estadia", "no_vendible", "sin_tarifa"):
                        self.assertNotIn(h["habitacion_id"], ofertadas, celda)

    def test_oferta_multinoche_si_y_solo_si_todas_sus_noches_disponibles(self):
        datos = self.ocupacion(H, H + timedelta(days=8))
        for a, b in ((H, H + timedelta(days=3)), (H + timedelta(days=5), H + timedelta(days=8))):
            ofertadas = {i["habitacion_id"] for i in self.oferta(a, b, 1)["oferta"]}
            noches = [a + timedelta(days=i) for i in range((b - a).days)]
            for h in datos["habitaciones"]:
                todas_disponibles = all(
                    self.celda(datos, h["habitacion_id"], n)["estado"] == "disponible" for n in noches
                )
                with self.subTest(habitacion=h["habitacion_id"], rango=(a, b)):
                    self.assertEqual(h["habitacion_id"] in ofertadas, todas_disponibles)

    def test_capacidad_filtra_la_oferta_pero_no_la_celda(self):
        datos = self.ocupacion(H, H + timedelta(days=2))
        ofertadas_3 = {i["habitacion_id"] for i in self.oferta(H + timedelta(days=1), H + timedelta(days=2), 3)["oferta"]}
        self.assertIn("OC-105", ofertadas_3)          # capacidad 3
        self.assertNotIn("OC-101", ofertadas_3)       # capacidad 2
        # la celda no mide capacidad: 101 (libre esa noche, con tarifa) sigue «disponible»
        self.assertEqual(self.celda(datos, "OC-101", H + timedelta(days=1))["estado"], "disponible")

    def test_salida_anticipada_libera_noches_futuras(self):
        datos = self.ocupacion(H - timedelta(days=5), H + timedelta(days=4))
        # R2 (101) liquidó H-3: solo las noches [H-5, H-3) quedan finalizada.
        self.assertEqual(self.celda(datos, "OC-101", H - timedelta(days=5))["estado"], "finalizada")
        self.assertEqual(self.celda(datos, "OC-101", H - timedelta(days=4))["estado"], "finalizada")
        self.assertEqual(self.celda(datos, "OC-101", H - timedelta(days=3))["estado"], "sin_ocupar")
        # R3 (102) liquidó hoy: sus noches futuras son vendibles.
        for n in (H, H + timedelta(days=1), H + timedelta(days=2)):
            self.assertEqual(self.celda(datos, "OC-102", n)["estado"], "disponible", n)

    def test_la_reserva_gana_sobre_no_vendible_y_la_cancelada_no_pinta(self):
        datos = self.ocupacion(H, H + timedelta(days=12))
        # R5 confirmada sobre 104 en mantenimiento: la celda es confirmada.
        for n in (H + timedelta(days=1), H + timedelta(days=2)):
            celda = self.celda(datos, "OC-104", n)
            self.assertEqual(celda["estado"], "confirmada", celda)
            self.assertEqual(celda["reserva_id"], self.r5)
        # fuera del rango de R5, 104 es no_vendible por mantenimiento.
        self.assertEqual(self.celda(datos, "OC-104", H + timedelta(days=4))["estado"], "no_vendible")
        # R6 cancelada en 101: sus noches quedan disponibles y la reserva se lista.
        for n in (H + timedelta(days=10), H + timedelta(days=11)):
            self.assertEqual(self.celda(datos, "OC-101", n)["estado"], "disponible", n)
        habitacion_101 = next(h for h in datos["habitaciones"] if h["habitacion_id"] == "OC-101")
        canceladas = [r for r in habitacion_101["reservas"] if r["estado"] == "cancelada"]
        self.assertEqual([r["reserva_id"] for r in canceladas], [self.r6])

    def test_resumen_suma_solo_celdas_disponible_ocupada_y_no_vendible(self):
        datos = self.ocupacion(self.DESDE, self.HASTA)
        for fila in datos["resumen"]:
            noche = date.fromisoformat(fila["fecha"])
            estados = {}
            for h in datos["habitaciones"]:
                celda = self.celda(datos, h["habitacion_id"], noche)
                estados[celda["estado"]] = estados.get(celda["estado"], 0) + 1
            with self.subTest(noche=noche):
                self.assertEqual(fila["disponibles"], estados.get("disponible", 0))
                self.assertEqual(fila["ocupadas"], estados.get("confirmada", 0) + estados.get("en_estadia", 0))
                self.assertEqual(fila["no_vendibles"], estados.get("no_vendible", 0))


class PanelReconciliacionTest(ReconciliacionBaseTest):
    DESDE = H - timedelta(days=7)
    HASTA = H + timedelta(days=8)

    def test_situacion_de_hoy_recompone_desde_reservas(self):
        p = self.panel(self.DESDE, self.HASTA)
        self.assertEqual(p["fecha_corte"], str(H))
        filas = self.filas_reservas()
        self.assertEqual(p["hoy"]["llegadas_vencidas"]["valor"],
                         sum(1 for f in filas if f[4] == "confirmada" and f[2] < H))
        self.assertEqual(p["hoy"]["en_casa"]["valor"], sum(1 for f in filas if f[4] == "en_estadia"))
        self.assertEqual(p["hoy"]["salidas_hoy"]["valor"],
                         sum(1 for f in filas if f[4] == "en_estadia" and f[3] == H))
        self.assertEqual(p["hoy"]["habitaciones_total"]["valor"],
                         self.select("SELECT count(*) FROM habitaciones")[0][0])
        self.assertEqual(p["hoy"]["fuera_de_servicio"]["valor"],
                         self.select("SELECT count(*) FROM habitaciones WHERE estado_operativo='fuera_de_servicio'")[0][0])
        self.assertEqual(p["hoy"]["en_mantenimiento"]["valor"],
                         self.select("SELECT count(*) FROM habitaciones WHERE mantenimiento")[0][0])

    def test_periodo_recompone_noche_a_noche_desde_el_dataset(self):
        p = self.panel(self.DESDE, self.HASTA)
        filas = self.filas_reservas()
        creadas = {f[0]: f[1] for f in self.select("SELECT id, creado_en::date FROM habitaciones")}
        esperado_reservadas = esperado_ocupadas = esperado_unidades = 0
        for s in p["serie"]:
            noche = date.fromisoformat(s["fecha"])
            con_noche = [f for f in filas if f[4] in ("confirmada", "en_estadia", "finalizada")
                         and f[2] <= noche < f[5]]
            activas = {h for h, creada in creadas.items() if creada <= noche}
            activas |= {f[1] for f in con_noche}
            self.assertEqual(s["unidades"], len(activas), noche)
            self.assertEqual(s["reservadas"], len({f[1] for f in con_noche}), noche)
            if noche <= H:
                self.assertIsNotNone(s["ocupadas"], noche)
                self.assertEqual(s["ocupadas"], len({f[1] for f in con_noche if f[4] in ("en_estadia", "finalizada")}), noche)
                esperado_ocupadas += s["ocupadas"]
                esperado_unidades += s["unidades"]
            else:
                self.assertIsNone(s["ocupadas"], noche)
            esperado_reservadas += s["reservadas"]
        per = p["periodo_indicadores"]
        self.assertEqual(per["noches_reservadas"]["valor"], esperado_reservadas)
        self.assertEqual(per["noches_ocupadas"]["valor"], esperado_ocupadas)
        self.assertAlmostEqual(per["ocupacion"]["valor"], esperado_ocupadas / esperado_unidades)
        self.assertAlmostEqual(per["ocupacion_reservada"]["valor"], esperado_reservadas / sum(s["unidades"] for s in p["serie"]))

    def test_periodo_todo_futuro_ocupacion_nula_no_cero(self):
        p = self.panel(H + timedelta(days=1), H + timedelta(days=8))
        self.assertIsNone(p["periodo_indicadores"]["ocupacion"]["valor"])
        self.assertTrue(all(s["ocupadas"] is None for s in p["serie"]))
        # las reservadas futuras sí cuentan (prospectivas)
        self.assertGreater(p["periodo_indicadores"]["noches_reservadas"]["valor"], 0)

    def test_canceladas_y_registradas_recomponen(self):
        p = self.panel(self.DESDE, self.HASTA)
        canceladas = [f for f in self.filas_reservas() if f[4] == "cancelada"
                      and f[2] < self.HASTA and f[3] > self.DESDE]
        per = p["periodo_indicadores"]
        self.assertEqual(per["reservas_canceladas"]["valor"], len(canceladas))
        esperadas_noches = sum(
            len([n for n in range((self.HASTA - self.DESDE).days)
                 if self.DESDE + timedelta(days=n) >= f[2] and self.DESDE + timedelta(days=n) < f[3]])
            for f in canceladas
        )
        self.assertEqual(per["reservas_canceladas"]["noches"], esperadas_noches)
        registradas_api = per["reservas_registradas"]["valor"]
        registradas_sql = self.select(
            "SELECT count(*) FROM reservas WHERE creado_en::date >= %s AND creado_en::date < %s",
            (self.DESDE, self.HASTA))[0][0]
        self.assertEqual(registradas_api, registradas_sql)

    def test_filtro_por_tipo_restringe_unidades_y_reservas(self):
        p = self.panel(self.DESDE, self.HASTA, tipo="suite")
        self.assertEqual(p["hoy"]["habitaciones_total"]["valor"], 1)
        self.assertEqual(p["hoy"]["en_casa"]["valor"], 0)
        self.assertEqual(p["hoy"]["llegadas_vencidas"]["valor"], 0)
        self.assertEqual(p["periodo_indicadores"]["reservas_canceladas"]["valor"], 0)

    def test_serie_del_panel_coincide_con_el_resumen_de_ocupacion(self):
        """Métricas distintas con nombres iguales (nota 2026-11-03 en §4.3):
        la serie del panel cuenta en_estadia+finalizada en noches ≤ hoy; el
        resumen de ocupación cuenta confirmada+en_estadia en cualquier noche.
        La reconciliación exige que ambas se recomponen desde las celdas."""
        p = self.panel(self.DESDE, self.HASTA)
        datos = self.ocupacion(self.DESDE, self.HASTA)
        serie = {s["fecha"]: s for s in p["serie"]}
        for fila in datos["resumen"]:
            noche = fila["fecha"]
            estados = {}
            for h in datos["habitaciones"]:
                celda = self.celda(datos, h["habitacion_id"], date.fromisoformat(noche))
                estados[celda["estado"]] = estados.get(celda["estado"], 0) + 1
            with self.subTest(noche=noche):
                self.assertEqual(serie[noche]["reservadas"],
                                 estados.get("confirmada", 0) + estados.get("en_estadia", 0) + estados.get("finalizada", 0))
                if date.fromisoformat(noche) <= H:
                    self.assertEqual(serie[noche]["ocupadas"],
                                     estados.get("en_estadia", 0) + estados.get("finalizada", 0))
