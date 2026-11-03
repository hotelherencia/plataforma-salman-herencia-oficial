import os
import unittest
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.tests.aislamiento import exigir_base_libre
from servicio.aplicacion import Aplicacion, construir_aplicacion, crear_app
from servicio.configuracion import Configuracion
from nucleo.servicio import AccesoDenegado as AccesoNucleo
from nucleo.servicio import Nucleo

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
RANGO = {"inicio": str(date.today() - timedelta(days=20)), "fin": str(date.today() - timedelta(days=18))}


class NucleoRechaza(Nucleo):
    def aplicar_resultado_pago(self, empresa_id, clave, estado, monto_clp):
        raise AccesoNucleo("empresa desconocida")


class CobroEstadiaTest(unittest.TestCase):
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
                "TRUNCATE claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            from servicio.reservas import sembrar_habitaciones

            sembrar_habitaciones(conexion)
            conexion.execute(
                "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                "VALUES ('TAR-FIJA', 'HAB-SINT-101', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()
        self.cliente = TestClient(self.app)
        self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})

    def reservar(self, clave="res-1", habitacion_id="HAB-SINT-101"):
        respuesta = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": habitacion_id, **RANGO, "huesped": {"nombre": "Huésped"}},
            headers={"Idempotency-Key": clave},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()["reserva_id"]

    def pagar(self, reserva_id, monto=100_000, clave="cob-1", modo="manual", idem="pag-1"):
        return self.cliente.post(
            f"/hotel/reservas/{reserva_id}/pagos",
            json={"monto_clp": monto, "clave": clave, "modo": modo},
            headers={"Idempotency-Key": idem},
        )

    def test_pago_misma_clave_distinto_monto_o_modo_es_409(self):
        # V1-ISSUE-32: deduplicar por (reserva_id, clave) solo es reintento si
        # el pago es idéntico; con monto distinto es un conflicto 409.
        # (modo=pasarela se resuelve antes como 503 «no configurada».)
        rid = self.reservar()
        primera = self.pagar(rid, 50_000, clave="abono-1", idem="p1")
        self.assertEqual(primera.status_code, 201, primera.text)
        otra_clave = self.pagar(rid, 70_000, clave="abono-1", idem="p2")
        self.assertEqual(otra_clave.status_code, 409, otra_clave.text)
        # el pago original queda intacto: un solo pago de 50000
        detalle = self.cliente.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(detalle["cuenta"]["pagado_clp"], 50_000)

    def test_pago_reintento_identico_repite_201_con_reintento(self):
        rid = self.reservar()
        primera = self.pagar(rid, 50_000, clave="abono-1", idem="p1")
        repetida = self.pagar(rid, 50_000, clave="abono-1", idem="p2")
        self.assertEqual(primera.status_code, 201, primera.text)
        self.assertEqual(repetida.status_code, 201, repetida.text)
        self.assertTrue(repetida.json()["reintento"])
        self.assertEqual(repetida.json()["pago_id"], primera.json()["pago_id"])

    def test_pago_manual_deja_efecto_en_el_nucleo_y_pago_en_la_base(self):
        rid = self.reservar()
        respuesta = self.pagar(rid)
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["estado"], "confirmado")
        self.assertTrue(cuerpo["efecto_nucleo_id"])
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (efectos,) = conexion.execute("SELECT count(*) FROM efectos_nucleo WHERE clave = %s", (f"{rid}:cob-1",)).fetchone()
            (pagos,) = conexion.execute("SELECT count(*) FROM pagos WHERE reserva_id = %s", (rid,)).fetchone()
        self.assertEqual(efectos, 1)
        self.assertEqual(pagos, 1)

    def test_si_el_nucleo_rechaza_no_hay_pago(self):
        rid = self.reservar()
        nucleo_rechaza = NucleoRechaza()
        app = crear_app(
            aplicacion=Aplicacion(nucleo=nucleo_rechaza, hotel=construir_hotel_para(nucleo_rechaza)),
            configuracion=self.config,
        )
        cliente = TestClient(app)
        cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        respuesta = cliente.post(
            f"/hotel/reservas/{rid}/pagos",
            json={"monto_clp": 100_000, "clave": "cob-x", "modo": "manual"},
            headers={"Idempotency-Key": "pag-x"},
        )
        self.assertEqual(respuesta.status_code, 403)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (pagos,) = conexion.execute("SELECT count(*) FROM pagos WHERE reserva_id = %s", (rid,)).fetchone()
            (efectos,) = conexion.execute("SELECT count(*) FROM efectos_nucleo").fetchone()
        self.assertEqual(pagos, 0)
        self.assertEqual(efectos, 0)

    def test_modo_pasarela_responde_503_y_nada_queda_cobrado(self):
        rid = self.reservar()
        respuesta = self.pagar(rid, modo="pasarela", clave="web-1", idem="pag-web")
        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(respuesta.json()["estado"], "pendiente")
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (pagos,) = conexion.execute("SELECT count(*) FROM pagos").fetchone()
        self.assertEqual(pagos, 0)

    def test_idempotencia_del_pago_no_duplica_efecto(self):
        rid = self.reservar()
        cuerpo = {"monto_clp": 100_000, "clave": "cob-1", "modo": "manual"}
        primera = self.cliente.post(
            f"/hotel/reservas/{rid}/pagos", json=cuerpo, headers={"Idempotency-Key": "pag-1"}
        )
        segunda = self.cliente.post(
            f"/hotel/reservas/{rid}/pagos", json=cuerpo, headers={"Idempotency-Key": "pag-1"}
        )
        self.assertEqual(primera.status_code, 201)
        self.assertEqual(segunda.status_code, 201)
        self.assertEqual(primera.json()["pago_id"], segunda.json()["pago_id"])
        conflicto = self.cliente.post(
            f"/hotel/reservas/{rid}/pagos",
            json={**cuerpo, "monto_clp": 200_000},
            headers={"Idempotency-Key": "pag-1"},
        )
        self.assertEqual(conflicto.status_code, 409)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (pagos,) = conexion.execute("SELECT count(*) FROM pagos WHERE reserva_id = %s", (rid,)).fetchone()
        self.assertEqual(pagos, 1)

    def test_caja_del_dia_ligada_a_reserva(self):
        rid = self.reservar()
        self.pagar(rid, monto=100_000, clave="cob-1", idem="pag-1")
        hoy = date.today().isoformat()
        respuesta = self.cliente.get("/hotel/caja", params={"fecha": hoy})
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["total_clp"], 100_000)
        self.assertEqual(cuerpo["pagos"][0]["reserva_id"], rid)
        self.assertEqual(cuerpo["pagos"][0]["habitacion_id"], "HAB-SINT-101")

    def test_caja_requiere_rol_caja_o_admin(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            seguridad.crear_usuario(conexion, EMPRESA, "recepcion", "recepcion", "clave-rec")
            conexion.commit()
        self.cliente.post("/sesion", json={"usuario": "recepcion", "clave": "clave-rec"})
        respuesta = self.cliente.get("/hotel/caja", params={"fecha": date.today().isoformat()})
        self.assertEqual(respuesta.status_code, 403)

    def test_entrada_exige_habitacion_lista(self):
        rid = self.reservar()
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("UPDATE habitaciones SET estado_preparacion = 'sucia' WHERE id = 'HAB-SINT-101'")
            conexion.commit()
        respuesta = self.cliente.post(
            f"/hotel/reservas/{rid}/entrada", headers={"Idempotency-Key": "ent-1"}
        )
        self.assertEqual(respuesta.status_code, 409)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("UPDATE habitaciones SET estado_preparacion = 'limpia' WHERE id = 'HAB-SINT-101'")
            conexion.commit()
        respuesta = self.cliente.post(
            f"/hotel/reservas/{rid}/entrada", headers={"Idempotency-Key": "ent-2"}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["estado"], "en_estadia")

    def test_salida_liquida_la_cuenta_saldada(self):
        rid = self.reservar()
        self.pagar(rid)
        self.cliente.post(f"/hotel/reservas/{rid}/entrada", headers={"Idempotency-Key": "ent-1"})
        respuesta = self.cliente.post(f"/hotel/reservas/{rid}/salida", headers={"Idempotency-Key": "sal-1"})
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["total_clp"], 100_000)
        self.assertEqual(cuerpo["saldo_clp"], 0)
        self.assertEqual(cuerpo["estado"], "liquidada")

    def test_salida_con_saldo_pendiente_responde_409(self):
        rid = self.reservar()
        self.cliente.post(f"/hotel/reservas/{rid}/entrada", headers={"Idempotency-Key": "ent-1"})
        respuesta = self.cliente.post(f"/hotel/reservas/{rid}/salida", headers={"Idempotency-Key": "sal-1"})
        self.assertEqual(respuesta.status_code, 409)

    def test_reserva_ajena_o_inexistente_responde_403(self):
        respuesta = self.cliente.post(
            "/hotel/reservas/RSV-NO-EXISTE/pagos",
            json={"monto_clp": 100_000, "clave": "k", "modo": "manual"},
            headers={"Idempotency-Key": "pag-ne"},
        )
        self.assertEqual(respuesta.status_code, 403)


def construir_hotel_para(nucleo):
    from hotel_inventario.dominio import EstadoUnidad, Establecimiento, Unidad
    from servicio.aplicacion import construir_hotel

    establecimiento = Establecimiento(id="EST-SINT-001", empresa_id=nucleo.empresa.id, nombre="Hotel Herencia sintético")
    unidades = tuple(Unidad(f"HAB-SINT-10{n}", establecimiento.id, 2, 50_000, EstadoUnidad.LIMPIA) for n in range(1, 4))
    return construir_hotel(nucleo, establecimiento, unidades)


if __name__ == "__main__":
    unittest.main()
