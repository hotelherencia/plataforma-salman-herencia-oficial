"""V1-ISSUE-39 — regla RES-TARIFA-NOCHES (spec-hotel-operacion-v1 §2.8, CA-HAB-08).

Oferta y reserva exigen tarifa vigente en cada noche de la estadía, igual que
`/hotel/ocupacion`, que pinta `sin_tarifa` la noche descubierta. El precio de
una estadía que cruza tarifas no se fija aquí (D-TAR-02, v1-issue-17): solo
se exige que el total confirmado sea el ofrecido. HTTP contra PostgreSQL
real; datos 100% sintéticos. Archivo propio para no tocar suites que otro
trabajo está editando en paralelo."""
import os
import unittest
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
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


class TarifaCadaNocheTest(unittest.TestCase):
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
            seguridad.crear_usuario(conexion, EMPRESA, "recepcion1", "recepcion", "clave-recepcion")
            conexion.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                "VALUES ('HAB-T-1', 'EST-SINT-001', 'doble', 2)"
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

    def tarifa(self, desde, hasta, monto, hid="HAB-T-1"):
        respuesta = self.admin.put(
            "/hotel/tarifas",
            json={"habitacion_id": hid, "fecha_desde": iso(desde), "fecha_hasta": iso(hasta), "tarifa_noche_clp": monto},
            headers=self.clave("tar"),
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)

    def oferta(self, inicio, fin, personas=2):
        respuesta = self.recepcion.get(
            "/hotel/oferta", params={"inicio": iso(inicio), "fin": iso(fin), "personas": personas}
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return {item["habitacion_id"]: item for item in respuesta.json()["oferta"]}

    def reservar(self, inicio, fin, hid="HAB-T-1"):
        return self.recepcion.post(
            "/hotel/reservas",
            json={"habitacion_id": hid, "inicio": iso(inicio), "fin": iso(fin), "huesped": {"nombre": "Huésped Sintético"}},
            headers=self.clave("rsv"),
        )

    def efectos(self):
        (reservas,) = self.sql("SELECT count(*) FROM reservas")[0]
        (cargos,) = self.sql("SELECT count(*) FROM cargos")[0]
        (auditoria,) = self.sql("SELECT count(*) FROM auditoria WHERE accion = 'reserva'")[0]
        return reservas, cargos, auditoria

    # ---- CA-HAB-08 ----

    def test_estadia_con_noche_sin_tarifa_no_se_ofrece(self):
        self.tarifa(5, 10, 40000)  # cubre las noches 5..9
        self.assertIn("HAB-T-1", self.oferta(6, 9))  # todas cubiertas
        self.assertNotIn("HAB-T-1", self.oferta(8, 12))  # noches 10 y 11 sin tarifa

    def test_reserva_con_noche_sin_tarifa_responde_409_sin_efectos(self):
        self.tarifa(5, 10, 40000)
        respuesta = self.reservar(8, 12)
        self.assertEqual(respuesta.status_code, 409, respuesta.text)
        self.assertIn("sin tarifa vigente", respuesta.json()["detail"])
        self.assertIn(iso(10), respuesta.json()["detail"])  # primera noche descubierta
        self.assertEqual(self.efectos(), (0, 0, 0))

    def test_noche_intermedia_sin_tarifa_tambien_bloquea(self):
        self.tarifa(5, 8, 40000)
        self.tarifa(9, 15, 40000)  # hueco en la noche 8
        self.assertNotIn("HAB-T-1", self.oferta(6, 11))
        self.assertEqual(self.reservar(6, 11).status_code, 409)
        self.assertEqual(self.efectos(), (0, 0, 0))

    def test_tarifas_contiguas_se_ofrecen_y_el_total_confirmado_es_el_ofrecido(self):
        self.tarifa(5, 10, 40000)
        self.tarifa(10, 20, 60000)
        ofrecida = self.oferta(8, 12)["HAB-T-1"]
        respuesta = self.reservar(8, 12)
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        reserva = respuesta.json()
        self.assertEqual(reserva["total_clp"], ofrecida["total_clp"])
        self.assertEqual(reserva["tarifa_noche_aceptada_clp"], ofrecida["tarifa_noche_clp"])
        (cargo,) = self.sql("SELECT monto_clp FROM cargos WHERE reserva_id = %s", (reserva["reserva_id"],))[0]
        self.assertEqual(cargo, ofrecida["total_clp"])

    def test_oferta_coincide_con_las_noches_disponibles_de_ocupacion(self):
        """§5: la unidad está en la oferta de [inicio, fin) sii todas sus noches son `disponible`."""
        self.tarifa(3, 7, 40000)
        self.tarifa(8, 12, 50000)  # noche 7 sin tarifa
        self.assertEqual(self.reservar(10, 11).status_code, 201)  # noche 10 ocupada
        respuesta = self.recepcion.get("/hotel/ocupacion", params={"desde": iso(1), "hasta": iso(14)})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        (fila,) = [h for h in respuesta.json()["habitaciones"] if h["habitacion_id"] == "HAB-T-1"]
        disponible = {n["fecha"]: n["estado"] == "disponible" for n in fila["noches"]}
        for inicio in range(1, 13):
            for fin in range(inicio + 1, 14):
                esperado = all(disponible[iso(d)] for d in range(inicio, fin))
                with self.subTest(inicio=inicio, fin=fin):
                    self.assertEqual("HAB-T-1" in self.oferta(inicio, fin), esperado)


if __name__ == "__main__":
    unittest.main()
