"""Hallazgos de recepción del propietario (2026-11-18): documento obligatorio
y validado (#367), mover al huésped de habitación (#361) y confirmar la
unidad en la entrada (#360). HTTP contra PostgreSQL real, datos sintéticos.
"""
import os
import unittest
import uuid
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests.apoyo_huespedes import registrar_acompanantes
from servicio.tests.reloj import a_las
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


class RecepcionHallazgosTest(unittest.TestCase):
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
                "TRUNCATE auditoria, reasignaciones, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
                "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            for n, capacidad in ((1, 2), (2, 2), (3, 1)):
                conexion.execute(
                    "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_preparacion) "
                    "VALUES (%s, 'EST-SINT-001', 'doble', %s, 'limpia')",
                    (f"HAB-REC-{n}", capacidad),
                )
                conexion.execute(
                    "INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                    "VALUES (%s, %s, '2026-01-01', '2027-12-31', 50000)",
                    (f"TAR-REC-{n}", f"HAB-REC-{n}"),
                )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        self.assertEqual(self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)

    def idem(self):
        return {"Idempotency-Key": f"k-{uuid.uuid4().hex[:10]}"}

    def reservar(self, habitacion="HAB-REC-1", inicio=HOY, noches=2, huesped=None, personas=2, esperado=201):
        r = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": habitacion, "inicio": str(inicio), "fin": str(inicio + timedelta(days=noches)),
                  "personas": personas,
                  "huesped": huesped or {"nombre": "Pedro Recepción", "documento": "12.345.678-5", "documento_tipo": "rut"}},
            headers=self.idem(),
        )
        self.assertEqual(r.status_code, esperado, r.text)
        return r.json().get("reserva_id") if esperado == 201 else r

    def mover(self, rid, destino, motivo="cliente pidió cambio"):
        return self.cliente.post(f"/hotel/reservas/{rid}/habitacion",
                                 json={"habitacion_id": destino, "motivo": motivo}, headers=self.idem())

    def habitacion(self, hid):
        return next(h for h in self.cliente.get("/hotel/habitaciones").json()["habitaciones"] if h["habitacion_id"] == hid)

    # --- #367: documento obligatorio y validado ---
    def test_367_rut_valido_se_normaliza_y_guarda_tipo(self):
        rid = self.reservar(huesped={"nombre": "Ana", "documento": "123456785", "documento_tipo": "rut"})
        detalle = self.cliente.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(detalle["huesped_documento"], "12.345.678-5")
        with psycopg.connect(URL_TEST) as c:
            self.assertEqual(c.execute("SELECT huesped_documento_tipo FROM reservas WHERE id=%s", (rid,)).fetchone()[0], "rut")

    def test_367_rut_con_digito_incorrecto_422(self):
        r = self.reservar(huesped={"nombre": "Ana", "documento": "12.345.678-9", "documento_tipo": "rut"}, esperado=422)
        self.assertIn("dígito verificador", r.text)

    def test_367_pasaporte_valido_y_documento_vacio_con_tipo_422(self):
        rid = self.reservar(huesped={"nombre": "John", "documento": "ab 123456", "documento_tipo": "pasaporte"})
        self.assertEqual(self.cliente.get(f"/hotel/reservas/{rid}").json()["huesped_documento"], "AB123456")
        self.reservar(habitacion="HAB-REC-2", huesped={"nombre": "Sin doc", "documento_tipo": "rut"}, esperado=422)
        self.reservar(habitacion="HAB-REC-2", huesped={"nombre": "Mal", "documento": "A-1", "documento_tipo": "pasaporte"},
                      esperado=422)

    # --- #361: mover al huésped ---
    def test_361_mover_reserva_confirmada_conserva_tarifa_y_deja_historial(self):
        rid = self.reservar(inicio=HOY + timedelta(days=5))
        antes = self.cliente.get(f"/hotel/reservas/{rid}").json()
        r = self.mover(rid, "HAB-REC-2")
        self.assertEqual(r.status_code, 200, r.text)
        despues = self.cliente.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(despues["habitacion_id"], "HAB-REC-2")
        self.assertEqual(despues["cuenta"], antes["cuenta"])
        self.assertEqual([(a["desde_habitacion_id"], a["hacia_habitacion_id"]) for a in despues["reasignaciones"]],
                         [("HAB-REC-1", "HAB-REC-2")])

    def test_361_destino_ocupado_en_el_rango_409(self):
        rid = self.reservar(inicio=HOY + timedelta(days=5))
        self.reservar(habitacion="HAB-REC-2", inicio=HOY + timedelta(days=6))
        r = self.mover(rid, "HAB-REC-2")
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(self.cliente.get(f"/hotel/reservas/{rid}").json()["habitacion_id"], "HAB-REC-1")

    def test_361_destino_sin_capacidad_o_misma_unidad_409(self):
        rid = self.reservar(inicio=HOY + timedelta(days=5))
        self.assertEqual(self.mover(rid, "HAB-REC-3").status_code, 409)  # capacidad 1 < 2 personas
        self.assertEqual(self.mover(rid, "HAB-REC-1").status_code, 409)
        self.assertEqual(self.mover(rid, "HAB-NO-EXISTE").status_code, 409)

    @a_las(HOY)  # ADP-5: la entrada exige la hora de llegada (15:00 del día de inicio)
    def test_361_en_estadia_destino_ocupada_y_origen_queda_sucia_con_tarea(self):
        rid = self.reservar()
        registrar_acompanantes(self.cliente, rid, 1, self.idem)
        e = self.cliente.post(f"/hotel/reservas/{rid}/entrada", json={}, headers=self.idem())
        self.assertEqual(e.status_code, 200, e.text)
        r = self.mover(rid, "HAB-REC-2", motivo="ruido en la habitación")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.habitacion("HAB-REC-2")["estado_operativo"], "ocupada")
        origen = self.habitacion("HAB-REC-1")
        self.assertEqual((origen["estado_operativo"], origen["estado_preparacion"], origen["limpieza_pendiente"]),
                         ("disponible", "sucia", True))

    def test_361_caja_no_puede_mover(self):
        rid = self.reservar(inicio=HOY + timedelta(days=5))
        self.assertEqual(self.cliente.post("/usuarios", json={"nombre": "caja2", "rol": "caja", "clave": "clave-caja-2"},
                                           headers=self.idem()).status_code, 201)
        caja = TestClient(self.app)
        caja.post("/sesion", json={"usuario": "caja2", "clave": "clave-caja-2"})
        r = caja.post(f"/hotel/reservas/{rid}/habitacion", json={"habitacion_id": "HAB-REC-2", "motivo": "xxx"},
                      headers=self.idem())
        self.assertEqual(r.status_code, 403, r.text)

    # --- #360: unidad confirmada en la entrada ---
    @a_las(HOY)  # ADP-5: la entrada exige la hora de llegada (15:00 del día de inicio)
    def test_360_entrada_con_otra_unidad_reasigna_y_ocupa_la_nueva(self):
        rid = self.reservar()
        registrar_acompanantes(self.cliente, rid, 1, self.idem)
        e = self.cliente.post(f"/hotel/reservas/{rid}/entrada", json={"habitacion_id": "HAB-REC-2"}, headers=self.idem())
        self.assertEqual(e.status_code, 200, e.text)
        self.assertEqual(e.json()["habitacion_id"], "HAB-REC-2")
        self.assertEqual(self.habitacion("HAB-REC-2")["estado_operativo"], "ocupada")
        self.assertNotEqual(self.habitacion("HAB-REC-1")["estado_operativo"], "ocupada")

    @a_las(HOY)  # ADP-5: la entrada exige la hora de llegada (15:00 del día de inicio)
    def test_360_entrada_captura_documento_validado(self):
        rid = self.reservar(huesped={"nombre": "Sin doc"})
        registrar_acompanantes(self.cliente, rid, 1, self.idem)
        malo = self.cliente.post(f"/hotel/reservas/{rid}/entrada",
                                 json={"documento": "12.345.678-9", "documento_tipo": "rut"}, headers=self.idem())
        self.assertEqual(malo.status_code, 422, malo.text)
        ok = self.cliente.post(f"/hotel/reservas/{rid}/entrada",
                               json={"documento": "12345678-5", "documento_tipo": "rut"}, headers=self.idem())
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(self.cliente.get(f"/hotel/reservas/{rid}").json()["huesped_documento"], "12.345.678-5")


if __name__ == "__main__":
    unittest.main()
