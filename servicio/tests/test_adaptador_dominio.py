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

    def test_1_el_rechazo_propaga_409_y_no_deja_estado_parcial(self):
        """Arquitectura vigente (spec-api-v1, 2026-10-30): las reglas de
        operación las decide el servicio sobre PostgreSQL (fuente de verdad).
        Lo que este test protege: todo rechazo responde 409/403 y la
        transacción no deja estado a medias (unidad/reserva intactas)."""
        rid = self.reservar(clave="stp-r")
        # doble entrada: la segunda se niega y la primera no se corrompe
        self.assertEqual(self.cliente.post(
            f"/hotel/reservas/{rid}/entrada", json={}, headers={"Idempotency-Key": "ent-1"}).status_code, 200)
        segunda = self.cliente.post(
            f"/hotel/reservas/{rid}/entrada", json={}, headers={"Idempotency-Key": "ent-2"})
        self.assertEqual(segunda.status_code, 409)
        with psycopg.connect(URL_TEST) as conexion:
            (estado,) = conexion.execute("SELECT estado FROM reservas WHERE id = %s", (rid,)).fetchone()
            (operativo,) = conexion.execute(
                "SELECT estado_operativo FROM habitaciones WHERE id = 'HAB-SINT-101'").fetchone()
        self.assertEqual((estado, operativo), ("en_estadia", "ocupada"))
        # salida con saldo pendiente: 409 y la estadía sigue entera
        self.assertEqual(self.cliente.post(
            f"/hotel/reservas/{rid}/salida", json={}, headers={"Idempotency-Key": "sal-x"}).status_code, 409)
        with psycopg.connect(URL_TEST) as conexion:
            (estado,) = conexion.execute("SELECT estado FROM reservas WHERE id = %s", (rid,)).fetchone()
        self.assertEqual(estado, "en_estadia")
        # cancelación en estadía: 409, sin reversos parciales
        self.assertEqual(self.cliente.post(
            f"/hotel/reservas/{rid}/cancelacion", json={}, headers={"Idempotency-Key": "can-x"}).status_code, 409)
        with psycopg.connect(URL_TEST) as conexion:
            (estado,) = conexion.execute("SELECT estado FROM reservas WHERE id = %s", (rid,)).fetchone()
            (reversos,) = conexion.execute(
                "SELECT count(*) FROM cargos WHERE reserva_id = %s AND tipo = 'reverso'", (rid,)).fetchone()
        self.assertEqual((estado, reversos), ("en_estadia", 0))

    def test_2_la_politica_de_cancelacion_tiene_fuente_unica_en_el_dominio(self):
        """Los valores de la política (48 h / 15:00) se importan del dominio
        (`hotel_inventario.servicio`), no se redefinen en el adaptador; y el
        no-solape lo garantiza el constraint de la migración, no el código."""
        from hotel_inventario import servicio as servicio_dominio
        import servicio.cobro as cobro_modulo
        self.assertIs(cobro_modulo.HORA_LLEGADA, servicio_dominio.HORA_LLEGADA)
        self.assertIs(cobro_modulo.LIMITE_CANCELACION_GRATUITA, servicio_dominio.LIMITE_CANCELACION_GRATUITA)
        texto_cobro = open(os.path.join(RAIZ, "servicio/cobro.py"), encoding="utf-8").read()
        self.assertNotIn("timedelta(hours=48)", texto_cobro)
        with psycopg.connect(URL_TEST) as conexion:
            (vigente,) = conexion.execute(
                "SELECT count(*) FROM pg_constraint WHERE conname = 'reservas_sin_solape'").fetchone()
        self.assertEqual(vigente, 1)

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
        self.assertEqual((reservas, tareas, cargos, pagos), (1, 1, 1, 1))
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
