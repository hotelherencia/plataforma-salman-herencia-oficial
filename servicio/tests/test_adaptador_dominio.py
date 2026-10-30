"""Pruebas de estupidez del adaptador ADP (2026-10-30): fallan si alguna ruta
hotelera vuelve a decidir la regla en SQL o si el dominio queda de adorno.

1. Parchear un método de `ServicioHotelInventario` para que lance propaga el
   fallo por el HTTP y no deja la habitación `ocupada` (igual con cancelar,
   check_out, asentar_cargo y consultar_oferta).
2. En `servicio/cobro.py` y `servicio/reservas.py` no quedan los literales de
   la política de 48 horas ni condiciones de mantenimiento, preparación o
   solape que decidan el check-in (esos archivos persisten y traducen HTTP).
3. Reserva, check-in, tarea de limpieza y cancelación fuera de plazo siguen
   en la base tras construir la app de nuevo contra la misma DATABASE_URL; la
   segunda entrada a la misma reserva responde 409 porque check_in lo niega,
   también en el proceso recién arrancado.
4. Arranque contra una base sin habitaciones: la oferta no contiene
   HAB-SINT-101.
"""
import os
import unittest
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.migracion import aplicar_migraciones

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()
P1 = (HOY - timedelta(days=9)).isoformat()
P5 = (HOY - timedelta(days=5)).isoformat()

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def sembrar(conexion):
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


class AdaptadorDominioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            sembrar(conexion)
        self.cliente = TestClient(self.app)
        self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})

    def reservar(self, inicio=P1, fin=P5, clave="res-1"):
        respuesta = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-SINT-101", "inicio": inicio, "fin": fin,
                  "huesped": {"nombre": "Huésped", "documento": "DOC-1"}},
            headers={"Idempotency-Key": clave},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()["reserva_id"]

    def test_1_el_fallo_del_dominio_propaga_y_no_ocupa(self):
        from hotel_inventario import servicio as servicio_dominio

        class FalloProp(Exception):
            pass

        metodos = {
            "check_in": ("entrada", lambda rid: self.cliente.post(
                f"/hotel/reservas/{rid}/entrada", json={}, headers={"Idempotency-Key": "ent-x"})),
            "cancelar": ("cancelacion", lambda rid: self.cliente.post(
                f"/hotel/reservas/{rid}/cancelacion", json={}, headers={"Idempotency-Key": "can-x"})),
            "check_out": ("salida", lambda rid: self.cliente.post(
                f"/hotel/reservas/{rid}/salida", json={}, headers={"Idempotency-Key": "sal-x"})),
            "asentar_cargo": ("cargos", lambda rid: self.cliente.post(
                f"/hotel/reservas/{rid}/cargos", json={"concepto": "x", "monto_clp": 1000},
                headers={"Idempotency-Key": "car-x"})),
        }
        original = servicio_dominio.ServicioHotelInventario.check_in
        for desplazamiento, (nombre, (_ruta, llamar)) in enumerate(metodos.items()):
            with self.subTest(metodo=nombre):
                metodo_original = getattr(servicio_dominio.ServicioHotelInventario, nombre)

                def fallo(self_h, *args, _m=metodo_original, **kwargs):
                    raise FalloProp("el dominio se niega")

                setattr(servicio_dominio.ServicioHotelInventario, nombre, fallo)
                try:
                    base = date.fromisoformat(P1) + timedelta(days=desplazamiento * 20)
                    rid = self.reservar(
                        inicio=base.isoformat(),
                        fin=(base + timedelta(days=2)).isoformat(),
                        clave=f"stp-{nombre}",
                    )
                    with self.assertRaises(FalloProp):
                        llamar(rid)
                    with psycopg.connect(URL_TEST) as conexion:
                        (operativo,) = conexion.execute(
                            "SELECT estado_operativo FROM habitaciones WHERE id = 'HAB-SINT-101'"
                        ).fetchone()
                    self.assertNotEqual(operativo, "ocupada")
                finally:
                    setattr(servicio_dominio.ServicioHotelInventario, nombre, metodo_original)
        servicio_dominio.ServicioHotelInventario.check_in = original

        # consultar_oferta: si el dominio lanza, el HTTP propaga el fallo
        def fallo_oferta(self_h, *args, **kwargs):
            raise FalloProp("el dominio se niega")

        metodo_original = servicio_dominio.ServicioHotelInventario.consultar_oferta
        servicio_dominio.ServicioHotelInventario.consultar_oferta = fallo_oferta
        try:
            with self.assertRaises(FalloProp):
                self.cliente.get("/hotel/oferta", params={"inicio": P1, "fin": P5, "personas": 2})
        finally:
            servicio_dominio.ServicioHotelInventario.consultar_oferta = metodo_original

    def test_2_sin_reglas_de_negocio_en_el_sql(self):
        prohibidos = [
            "HORA_LLEGADA", "LIMITE_CANCELACION", "reservas_sin_solape",
            "estado_preparacion", "daterange", "48 horas", "primera noche",
        ]
        for relativo in ("servicio/cobro.py", "servicio/reservas.py"):
            ruta = os.path.join(RAIZ, relativo)
            with self.subTest(archivo=relativo):
                texto = open(ruta, encoding="utf-8").read()
                for palabra in prohibidos:
                    self.assertNotIn(palabra, texto, f"{relativo} decide la regla en SQL: «{palabra}»")

    def test_3_estado_perdura_y_la_segunda_entrada_la_niega_el_dominio(self):
        rid = self.reservar()
        self.cliente.post(f"/hotel/reservas/{rid}/pagos",
                          json={"monto_clp": 200_000, "clave": "cob-1", "modo": "manual"},
                          headers={"Idempotency-Key": "pag-1"})
        self.assertEqual(self.cliente.post(
            f"/hotel/reservas/{rid}/entrada", json={}, headers={"Idempotency-Key": "ent-1"}).status_code, 200)
        self.assertEqual(self.cliente.post(
            f"/hotel/reservas/{rid}/salida", json={}, headers={"Idempotency-Key": "sal-1"}).status_code, 200)
        # proceso nuevo contra la misma base: todo sigue y check_in niega la reentrada
        app2 = crear_app(configuracion=self.config)
        cliente2 = TestClient(app2)
        cliente2.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        with psycopg.connect(URL_TEST) as conexion:
            (reservas,) = conexion.execute("SELECT count(*) FROM reservas").fetchone()
            (tareas,) = conexion.execute("SELECT count(*) FROM tareas_operativas WHERE estado = 'pendiente'").fetchone()
            (cargos,) = conexion.execute("SELECT count(*) FROM cargos").fetchone()
            (pagos,) = conexion.execute("SELECT count(*) FROM pagos").fetchone()
        self.assertEqual((reservas, tareas, cargos, pagos), (1, 1, 4, 1))
        respuesta = cliente2.post(f"/hotel/reservas/{rid}/entrada", json={}, headers={"Idempotency-Key": "ent-2"})
        self.assertEqual(respuesta.status_code, 409)
        with psycopg.connect(URL_TEST) as conexion:
            (operativo,) = conexion.execute(
                "SELECT estado_operativo FROM habitaciones WHERE id = 'HAB-SINT-101'").fetchone()
        self.assertEqual(operativo, "disponible")  # la salida dejó la unidad sucia, no ocupada

    def test_4_arranque_sin_habitaciones_no_oferta_la_semillada(self):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute(
                "TRUNCATE tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.commit()
        app = crear_app(configuracion=self.config)
        cliente = TestClient(app)
        cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        respuesta = cliente.get("/hotel/oferta", params={"inicio": P1, "fin": P5, "personas": 2})
        self.assertEqual(respuesta.status_code, 200)
        ids = {i["habitacion_id"] for i in respuesta.json()["oferta"]}
        self.assertNotIn("HAB-SINT-101", ids)
        self.assertEqual(ids, set())
        with psycopg.connect(URL_TEST) as conexion:
            sembrar(conexion)


if __name__ == "__main__":
    unittest.main()
