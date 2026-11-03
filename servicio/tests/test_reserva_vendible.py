"""V1-ISSUE-12 — regla RES-VENDIBLE (spec-hotel-operacion-v1 §2.7, CA-HAB-07).

`POST /hotel/reservas` aplica la misma regla de cupo que la oferta y que el
dominio (`ServicioHotelInventario.reservar` → ESTADO_NO_VENDIBLE): una unidad
con mantenimiento abierto, `bloqueada` o `fuera_de_servicio` no recibe una
reserva nueva. HTTP contra PostgreSQL real; datos 100% sintéticos. Archivo
propio para no tocar suites que otro trabajo está editando en paralelo."""
import os
import threading
import time
import unittest
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


def iso(dias: int) -> str:
    return (HOY + timedelta(days=dias)).isoformat()


class ReservaVendibleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute(
                "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
                "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            seguridad.crear_usuario(conexion, EMPRESA, "recepcion1", "recepcion", "clave-recepcion")
            for hid in ("HAB-V-1", "HAB-V-2"):
                conexion.execute(
                    "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                    "VALUES (%s, 'EST-SINT-001', 'doble', 2)",
                    (hid,),
                )
                conexion.execute(
                    "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                    "VALUES (%s, %s, %s, %s, 45000)",
                    (f"TAR-{hid}", hid, iso(-30), iso(400)),
                )
        self.admin = self.login(*ADMIN)
        self.recepcion = self.login("recepcion1", "clave-recepcion")
        self._n = 0

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
            return conexion.execute(consulta, parametros).fetchall()

    def reservar(self, hid, inicio=5, fin=7, cliente=None, cabeceras=None):
        return (cliente or self.recepcion).post(
            "/hotel/reservas",
            json={"habitacion_id": hid, "inicio": iso(inicio), "fin": iso(fin),
                  "huesped": {"nombre": "Huésped Sintético", "documento": "11.111.111-1"}},
            headers=cabeceras or self.clave("rsv"),
        )

    def servicio(self, hid, cuerpo):
        respuesta = self.admin.post(f"/hotel/habitaciones/{hid}/servicio", json=cuerpo, headers=self.clave("srv"))
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return respuesta.json()

    def efectos(self, hid):
        """(reservas, cargos, auditorías de reserva) que existen para la habitación."""
        (reservas,) = self.sql("SELECT count(*) FROM reservas WHERE habitacion_id = %s", (hid,))[0]
        (cargos,) = self.sql(
            "SELECT count(*) FROM cargos c JOIN reservas r ON r.id = c.reserva_id WHERE r.habitacion_id = %s", (hid,)
        )[0]
        (auditoria,) = self.sql("SELECT count(*) FROM auditoria WHERE accion = 'reserva'")[0]
        return reservas, cargos, auditoria

    # ---- CA-HAB-07 ----

    def test_ca_hab_07_retirada_rechaza_la_reserva_y_reincorporada_la_acepta(self):
        self.servicio("HAB-V-1", {"en_servicio": False, "motivo": "remodelación"})
        respuesta = self.reservar("HAB-V-1")
        self.assertEqual(respuesta.status_code, 409, respuesta.text)
        self.assertIn("detail", respuesta.json())
        self.assertEqual(self.efectos("HAB-V-1"), (0, 0, 0))
        # releída desde la base: sigue retirada y sin reservas vigentes
        self.assertEqual(
            self.sql("SELECT estado_operativo FROM habitaciones WHERE id = 'HAB-V-1'"), [("fuera_de_servicio",)]
        )
        self.servicio("HAB-V-1", {"en_servicio": True})
        self.assertEqual(self.reservar("HAB-V-1").status_code, 201)
        self.assertEqual(self.efectos("HAB-V-1"), (1, 1, 1))

    def test_ca_hab_07_bloqueada_y_mantenimiento_rechazan_para_cualquier_rol(self):
        self.sql_mutar("UPDATE habitaciones SET estado_operativo = 'bloqueada' WHERE id = 'HAB-V-1'")
        self.sql_mutar("UPDATE habitaciones SET mantenimiento = true WHERE id = 'HAB-V-2'")
        for cliente in (self.admin, self.recepcion):
            for hid in ("HAB-V-1", "HAB-V-2"):
                with self.subTest(hid=hid):
                    self.assertEqual(self.reservar(hid, cliente=cliente).status_code, 409)
        self.assertEqual(self.efectos("HAB-V-1"), (0, 0, 0))
        self.assertEqual(self.efectos("HAB-V-2")[:2], (0, 0))

    def test_ocupada_y_sucia_siguen_vendibles_en_otras_fechas(self):
        # HECHO (ESTADOS_VENDIBLES): ocupación y limpieza no sacan del cupo
        self.sql_mutar(
            "UPDATE habitaciones SET estado_operativo = 'ocupada', estado_preparacion = 'sucia' WHERE id = 'HAB-V-1'"
        )
        self.assertEqual(self.reservar("HAB-V-1").status_code, 201)

    def test_el_409_queda_asociado_a_su_clave(self):
        self.servicio("HAB-V-1", {"en_servicio": False, "motivo": "remodelación"})
        cabeceras = self.clave("rep")
        primera = self.reservar("HAB-V-1", cabeceras=cabeceras)
        self.servicio("HAB-V-1", {"en_servicio": True})
        repetida = self.reservar("HAB-V-1", cabeceras=cabeceras)
        self.assertEqual((primera.status_code, repetida.status_code), (409, 409))
        self.assertEqual(primera.json(), repetida.json())
        self.assertEqual(self.efectos("HAB-V-1")[0], 0)

    def test_retiro_y_reserva_concurrentes_no_dejan_reserva_en_unidad_retirada(self):
        # Un retiro en curso (fila bloqueada y aún sin commit) obliga a la reserva
        # a esperar; al confirmarse el retiro, la reserva ve el estado nuevo.
        retiro = psycopg.connect(URL_TEST)
        try:
            retiro.execute("SELECT 1 FROM habitaciones WHERE id = 'HAB-V-1' FOR UPDATE")
            retiro.execute(
                "UPDATE habitaciones SET estado_operativo = 'fuera_de_servicio', "
                "motivo_fuera_de_servicio = 'concurrencia', fuera_de_servicio_desde = now() WHERE id = 'HAB-V-1'"
            )
            resultado = {}
            hilo = threading.Thread(target=lambda: resultado.update(r=self.reservar("HAB-V-1")))
            hilo.start()
            time.sleep(0.8)
            self.assertTrue(hilo.is_alive(), "la reserva debía esperar el cerrojo de la habitación")
            retiro.commit()
            hilo.join(timeout=10)
            self.assertFalse(hilo.is_alive())
        finally:
            retiro.close()
        self.assertEqual(resultado["r"].status_code, 409, resultado["r"].text)
        self.assertEqual(
            self.sql("SELECT count(*) FROM reservas WHERE habitacion_id = 'HAB-V-1' "
                     "AND estado IN ('confirmada', 'en_estadia')"),
            [(0,)],
        )

    def sql_mutar(self, consulta):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute(consulta)


if __name__ == "__main__":
    unittest.main()
