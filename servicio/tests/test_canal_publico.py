"""Canal público (V1-ISSUE-22 y V1-ISSUE-24, spec-api-v1 «Canal público»).

Sin sesión: disponibilidad con la misma regla de la oferta interna y
solicitud persistida (recibida/landing) con idempotencia propia, freno por
IP y CORS del origen de la landing solo en /publico/*. Conversión interna
trazable por recepción o administrador. Datos 100 % sintéticos; la regresión
se corre con base dedicada (exigir_base_libre).
"""
import hashlib
import json
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
OTRA_EMPRESA = "EMP-OTRA-001"
ADMIN = ("admin", "clave-admin-sintetica")
LANDING = "https://landing.test"
HOY = date.today()
MANANA = HOY + timedelta(days=1)
EN_3 = HOY + timedelta(days=3)


class CanalPublicoBaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front="http://localhost:3000", origen_landing=LANDING,
            admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "TRUNCATE auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "solicitudes, reservas, tarifas, tareas_operativas, sesiones, usuarios, habitaciones "
                "RESTART IDENTITY CASCADE"
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
        self.app.state.freno_solicitudes.max_por_minuto = 1000  # el freno se ejercita aparte
        self.cliente = TestClient(self.app)
        self.assertEqual(self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)
        self.anonima = TestClient(self.app)

    def clave(self):
        return f"pub-{uuid.uuid4().hex[:10]}"

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

    def select(self, sql, parametros=()):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            return conexion.execute(sql, parametros).fetchall()

    def cuerpo_solicitud(self, habitacion="HAB-SINT-101", inicio=str(MANANA), fin=str(EN_3), personas=2):
        return {
            "habitacion_id": habitacion, "inicio": inicio, "fin": fin, "personas": personas,
            "huesped_nombre": "Visitante Sintético", "huesped_contacto": "visitante@example.test",
        }

    def crear_solicitud(self, **kwargs):
        clave = kwargs.pop("clave", self.clave())
        respuesta = self.anonima.post(
            "/publico/solicitudes", json=self.cuerpo_solicitud(**kwargs),
            headers={"Idempotency-Key": clave},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()["solicitud_id"]


class DisponibilidadPublicaTest(CanalPublicoBaseTest):
    def test_cp01_disponibilidad_sin_sesion_200_sin_datos_personales(self):
        respuesta = self.anonima.get(
            "/publico/disponibilidad", params={"inicio": str(MANANA), "fin": str(EN_3), "personas": 2}
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        cuerpo = respuesta.json()
        self.assertIn("HAB-SINT-101", {i["habitacion_id"] for i in cuerpo["oferta"]})
        self.assertIn("tarifa_noche_clp", cuerpo["oferta"][0])
        self.assertNotIn("huesped", json.dumps(cuerpo).lower())

    def test_cp01b_rechaza_parametros_ajenos_y_fechas_mal_formadas(self):
        base = {"inicio": str(MANANA), "fin": str(EN_3), "personas": 2}
        ajeno = self.anonima.get("/publico/disponibilidad", params={**base, "correo": "a@b.test"})
        self.assertEqual(ajeno.status_code, 422, ajeno.text)
        mala = self.anonima.get("/publico/disponibilidad", params={**base, "inicio": "09-11-2026"})
        self.assertEqual(mala.status_code, 422, mala.text)

    def test_cp02_disponibilidad_valida_fechas_y_personas(self):
        for params in (
            {"inicio": str(EN_3), "fin": str(MANANA), "personas": 2},      # fin <= inicio
            {"inicio": str(HOY - timedelta(days=2)), "fin": str(MANANA), "personas": 2},  # pasado
            {"inicio": str(MANANA), "fin": str(MANANA + timedelta(days=31)), "personas": 2},  # >30 noches
            {"inicio": str(MANANA), "fin": str(EN_3), "personas": 0},
            {"inicio": str(MANANA), "fin": str(EN_3), "personas": 31},
        ):
            with self.subTest(params=params):
                respuesta = self.anonima.get("/publico/disponibilidad", params=params)
                self.assertIn(respuesta.status_code, (400, 422), respuesta.text)

    def test_cp03_disponibilidad_respeta_misma_regla_de_oferta(self):
        # mantenimiento abierto excluye la unidad (idéntico a /hotel/oferta)
        self.assertEqual(self.cliente.post(
            "/hotel/habitaciones/HAB-SINT-101/mantenimiento", json={"abierto": True},
            headers={"Idempotency-Key": self.clave()}).status_code, 200)
        respuesta = self.anonima.get(
            "/publico/disponibilidad", params={"inicio": str(MANANA), "fin": str(EN_3), "personas": 2}
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertNotIn("HAB-SINT-101", {i["habitacion_id"] for i in respuesta.json()["oferta"]})

    def test_cp04_rutas_internas_siguen_pidiendo_sesion(self):
        respuesta = self.anonima.get(
            "/hotel/oferta", params={"inicio": str(MANANA), "fin": str(EN_3), "personas": 2}
        )
        self.assertEqual(respuesta.status_code, 401)


class CorsPublicoTest(CanalPublicoBaseTest):
    def test_cp10_preflight_landing_sin_credenciales(self):
        respuesta = self.anonima.options("/publico/disponibilidad", headers={
            "Origin": LANDING, "Access-Control-Request-Method": "GET"})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.headers.get("access-control-allow-origin"), LANDING)
        self.assertIsNone(respuesta.headers.get("access-control-allow-credentials"))

    def test_cp11_cors_solo_publico_y_solo_origen_landing(self):
        params = {"inicio": str(MANANA), "fin": str(EN_3), "personas": 2}
        con_origen = self.anonima.get("/publico/disponibilidad", params=params, headers={"Origin": LANDING})
        self.assertEqual(con_origen.headers.get("access-control-allow-origin"), LANDING)
        self.assertIsNone(con_origen.headers.get("access-control-allow-credentials"))
        ajeno = self.anonima.get("/publico/disponibilidad", params=params,
                                 headers={"Origin": "https://otro.example"})
        self.assertIsNone(ajeno.headers.get("access-control-allow-origin"))

    def test_cp12_origen_landing_no_entra_a_lo_interno(self):
        params = {"inicio": str(MANANA), "fin": str(EN_3), "personas": 2}
        lectura = self.anonima.get("/hotel/oferta", params=params, headers={"Origin": LANDING})
        self.assertEqual(lectura.status_code, 401)
        mutacion = self.anonima.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-SINT-101", "inicio": str(MANANA), "fin": str(EN_3),
                  "huesped": {"nombre": "X"}},
            headers={"Origin": LANDING, "Idempotency-Key": self.clave()})
        self.assertEqual(mutacion.status_code, 403)

    def test_cp13_solicitud_con_origen_landing_permitida(self):
        respuesta = self.anonima.post(
            "/publico/solicitudes", json=self.cuerpo_solicitud(),
            headers={"Idempotency-Key": self.clave(), "Origin": LANDING})
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        self.assertEqual(respuesta.headers.get("access-control-allow-origin"), LANDING)


class SolicitudesPublicasTest(CanalPublicoBaseTest):
    def test_cp20_solicitud_crea_recibida_auditada(self):
        respuesta = self.anonima.post(
            "/publico/solicitudes", json=self.cuerpo_solicitud(),
            headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["estado"], "recibida")
        self.assertEqual(cuerpo["origen"], "landing")
        solicitud_id = cuerpo["solicitud_id"]
        fila = self.select("SELECT estado, origen, empresa_id, huesped_nombre FROM solicitudes WHERE id=%s",
                           (solicitud_id,))
        self.assertEqual(fila[0][:4], ("recibida", "landing", EMPRESA, "Visitante Sintético"))
        auditoria = self.select("SELECT actor, accion FROM auditoria WHERE recurso=%s", (solicitud_id,))
        self.assertTrue(any(a[0] == f"publico:{solicitud_id}" for a in auditoria), auditoria)

    def test_cp21_reintento_misma_clave_mismo_cuerpo(self):
        clave = self.clave()
        cuerpo = self.cuerpo_solicitud()
        r1 = self.anonima.post("/publico/solicitudes", json=cuerpo, headers={"Idempotency-Key": clave})
        self.assertEqual(r1.status_code, 201, r1.text)
        r2 = self.anonima.post("/publico/solicitudes", json=cuerpo, headers={"Idempotency-Key": clave})
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertTrue(r2.json()["reintento"])
        self.assertEqual(r1.json()["solicitud_id"], r2.json()["solicitud_id"])
        self.assertEqual(self.select("SELECT count(*) FROM solicitudes")[0][0], 1)

    def test_cp22_misma_clave_otro_cuerpo_409(self):
        clave = self.clave()
        r1 = self.anonima.post("/publico/solicitudes", json=self.cuerpo_solicitud(),
                               headers={"Idempotency-Key": clave})
        self.assertEqual(r1.status_code, 201, r1.text)
        r2 = self.anonima.post("/publico/solicitudes", json=self.cuerpo_solicitud(habitacion="HAB-SINT-102"),
                               headers={"Idempotency-Key": clave})
        self.assertEqual(r2.status_code, 409, r2.text)
        self.assertEqual(self.select("SELECT count(*) FROM solicitudes")[0][0], 1)

    def test_cp23_sin_cupo_409_y_nada_persiste(self):
        respuesta = self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-SINT-101", "inicio": str(MANANA), "fin": str(EN_3),
                  "huesped": {"nombre": "Ocupante Interno"}},
            headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        respuesta = self.anonima.post(
            "/publico/solicitudes", json=self.cuerpo_solicitud(),
            headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 409, respuesta.text)
        self.assertEqual(self.select("SELECT count(*) FROM solicitudes")[0][0], 0)

    def test_cp24_sin_tarifa_409_legible(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("UPDATE tarifas SET fecha_hasta=%s WHERE habitacion_id='HAB-SINT-101'",
                             (HOY + timedelta(days=10),))
            conexion.commit()
        respuesta = self.anonima.post(
            "/publico/solicitudes",
            json=self.cuerpo_solicitud(inicio=str(HOY + timedelta(days=12)), fin=str(HOY + timedelta(days=14))),
            headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 409, respuesta.text)
        self.assertIn("sin tarifa vigente", respuesta.json()["detail"])
        self.assertEqual(self.select("SELECT count(*) FROM solicitudes")[0][0], 0)

    def test_cp25_sin_clave_de_idempotencia_422(self):
        respuesta = self.anonima.post("/publico/solicitudes", json=self.cuerpo_solicitud())
        self.assertEqual(respuesta.status_code, 422, respuesta.text)

    def test_cp26_validaciones_de_la_solicitud(self):
        casos = (
            self.cuerpo_solicitud(personas=0),
            self.cuerpo_solicitud(inicio=str(HOY - timedelta(days=1))),
            {**self.cuerpo_solicitud(), "huesped_nombre": " "},
            {**self.cuerpo_solicitud(), "huesped_contacto": ""},
        )
        for cuerpo in casos:
            with self.subTest(cuerpo=cuerpo):
                respuesta = self.anonima.post("/publico/solicitudes", json=cuerpo,
                                              headers={"Idempotency-Key": self.clave()})
                self.assertEqual(respuesta.status_code, 422, respuesta.text)

    def test_cp27_cuerpo_muy_grande_413(self):
        respuesta = self.anonima.post(
            "/publico/solicitudes", json={**self.cuerpo_solicitud(), "nota": "x" * 9000},
            headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 413, respuesta.text)

    def test_cp28_freno_de_abuso_por_ip(self):
        config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, origen_landing=LANDING,
            admin_usuario=ADMIN[0], admin_clave=ADMIN[1], publico_max_por_minuto=2,
        )
        app = crear_app(configuracion=config)
        app.state.freno_solicitudes.max_por_minuto = 2
        anonima = TestClient(app)
        estados = [
            anonima.post("/publico/solicitudes", json=self.cuerpo_solicitud(),
                         headers={"Idempotency-Key": self.clave()}).status_code
            for _ in range(3)
        ]
        self.assertEqual(estados[:2], [201, 201])
        self.assertEqual(estados[2], 429)


class BandejaSolicitudesTest(CanalPublicoBaseTest):
    def test_bn30_bandeja_conversion_trazable(self):
        solicitud_id = self.crear_solicitud()
        self.crear_usuario("recepcion1", "recepcion")
        recepcion = self.login("recepcion1", "clave-usuario-1")
        bandeja = recepcion.get("/hotel/solicitudes")
        self.assertEqual(bandeja.status_code, 200, bandeja.text)
        self.assertIn(solicitud_id, {s["solicitud_id"] for s in bandeja.json()["solicitudes"]})
        conversion = recepcion.post(
            f"/hotel/solicitudes/{solicitud_id}/conversion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(conversion.status_code, 201, conversion.text)
        cuerpo = conversion.json()
        self.assertEqual(cuerpo["estado"], "convertida")
        reserva_id = cuerpo["reserva_id"]
        fila = self.select("SELECT estado, reserva_id FROM solicitudes WHERE id=%s", (solicitud_id,))[0]
        self.assertEqual(fila, ("convertida", reserva_id))
        detalle = recepcion.get(f"/hotel/reservas/{reserva_id}")
        self.assertEqual(detalle.status_code, 200, detalle.text)
        self.assertEqual(detalle.json()["estado"], "confirmada")
        auditoria = self.select("SELECT accion FROM auditoria WHERE recurso=%s", (solicitud_id,))
        self.assertTrue(any("conversion" in a[0] for a in auditoria), auditoria)
        # doble conversión → 409
        otra = recepcion.post(
            f"/hotel/solicitudes/{solicitud_id}/conversion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(otra.status_code, 409, otra.text)

    def test_bn31_conversion_aplica_la_misma_carrera_por_la_ultima_unidad(self):
        solicitud_id = self.crear_solicitud()
        # otro huésped interno toma el rango antes de la conversión
        self.assertEqual(self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": "HAB-SINT-101", "inicio": str(MANANA), "fin": str(EN_3),
                  "huesped": {"nombre": "Ocupante Rápido"}},
            headers={"Idempotency-Key": self.clave()}).status_code, 201)
        conversion = self.cliente.post(
            f"/hotel/solicitudes/{solicitud_id}/conversion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(conversion.status_code, 409, conversion.text)
        self.assertEqual(
            self.select("SELECT estado FROM solicitudes WHERE id=%s", (solicitud_id,))[0][0], "recibida")

    def test_bn32_bandeja_y_conversion_son_de_recepcion_o_administrador(self):
        solicitud_id = self.crear_solicitud()
        self.crear_usuario("caja1", "caja")
        caja = self.login("caja1", "clave-usuario-1")
        self.assertEqual(caja.get("/hotel/solicitudes").status_code, 403)
        self.assertEqual(caja.post(
            f"/hotel/solicitudes/{solicitud_id}/conversion",
            headers={"Idempotency-Key": self.clave()}).status_code, 403)

    def test_bn33_bandeja_filtra_por_estado(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                "VALUES ('TAR-102', 'HAB-SINT-102', '2026-01-01', '2027-12-31', 60000)"
            )
            conexion.commit()
        una = self.crear_solicitud()
        dos = self.crear_solicitud(habitacion="HAB-SINT-102")
        self.assertEqual(self.cliente.post(
            f"/hotel/solicitudes/{una}/conversion", headers={"Idempotency-Key": self.clave()}).status_code, 201)
        recibidas = self.cliente.get("/hotel/solicitudes", params={"estado": "recibida"})
        self.assertEqual({s["solicitud_id"] for s in recibidas.json()["solicitudes"]}, {dos})
        convertidas = self.cliente.get("/hotel/solicitudes", params={"estado": "convertida"})
        self.assertEqual({s["solicitud_id"] for s in convertidas.json()["solicitudes"]}, {una})

    def test_bn34_rechazo_marca_motivo_y_bloquea_conversion(self):
        solicitud_id = self.crear_solicitud()
        rechazo = self.cliente.post(
            f"/hotel/solicitudes/{solicitud_id}/rechazo", json={"motivo": "sin cupo real"},
            headers={"Idempotency-Key": self.clave()})
        self.assertEqual(rechazo.status_code, 200, rechazo.text)
        fila = self.select("SELECT estado, rechazo_motivo FROM solicitudes WHERE id=%s", (solicitud_id,))[0]
        self.assertEqual(fila, ("rechazada", "sin cupo real"))
        conversion = self.cliente.post(
            f"/hotel/solicitudes/{solicitud_id}/conversion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(conversion.status_code, 409, conversion.text)

    def test_bn35_solicitud_ajena_o_inexistente_403(self):
        respuesta = self.cliente.post(
            "/hotel/solicitudes/SOL-NO-EXISTE/conversion", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(respuesta.status_code, 403, respuesta.text)
