"""Contacto y leads de la landing (V1-ISSUE-20 punto 8, spec-api-v1
«Contacto y leads de la landing»).

Formulario propio de la landing: el lead (prospección) se persiste en la
plataforma con idempotencia propia, freno por IP y CORS del origen de la
landing solo en /publico/*; recepción o administrador lo gestionan por la
bandeja interna (contactado/cerrado con nota y auditoría). Los datos de
contacto se guardan tal cual (son el objeto de la gestión comercial). Datos
100 % sintéticos; la regresión se corre con base dedicada (exigir_base_libre).
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
OTRA_EMPRESA = "EMP-OTRA-001"
ADMIN = ("admin", "clave-admin-sintetica")
LANDING = "https://landing.test"
HOY = date.today()
MANANA = HOY + timedelta(days=1)
EN_3 = HOY + timedelta(days=3)


class LeadsBaseTest(unittest.TestCase):
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
                "TRUNCATE auditoria, claves_idempotencia, leads, solicitudes, reservas, tarifas, "
                "sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
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
        return f"lead-{uuid.uuid4().hex[:10]}"

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

    def cuerpo_lead(self, nombre="Visitante Sintético", correo="visitante@example.test",
                    telefono="+56 9 5555 5555", huespedes=2, check_in=str(MANANA),
                    check_out=str(EN_3), mensaje="Consulta sobre disponibilidad"):
        return {
            "nombre": nombre, "correo": correo, "telefono": telefono,
            "huespedes": huespedes, "check_in": check_in, "check_out": check_out,
            "mensaje": mensaje,
        }

    def crear_lead(self, **kwargs):
        clave = kwargs.pop("clave", self.clave())
        respuesta = self.anonima.post(
            "/publico/leads", json=self.cuerpo_lead(**kwargs),
            headers={"Idempotency-Key": clave},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()["lead"]["id"]


class LeadsPublicosTest(LeadsBaseTest):
    def test_ld01_crear_lead_sin_sesion_201_auditado(self):
        respuesta = self.anonima.post(
            "/publico/leads", json=self.cuerpo_lead(), headers={"Idempotency-Key": self.clave()}
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["lead"]["estado"], "nuevo")
        self.assertIn("creado_en", cuerpo["lead"])
        lead_id = cuerpo["lead"]["id"]
        # CA-LEAD-01: la respuesta no lleva datos del lead ni de terceros
        self.assertNotIn("correo", cuerpo["lead"])
        filas = self.select(
            "SELECT empresa_id, nombre, correo, telefono, estado, origen FROM leads WHERE id = %s", (lead_id,)
        )
        self.assertEqual(len(filas), 1)
        empresa_id, nombre, correo, telefono, estado, origen = filas[0]
        self.assertEqual(empresa_id, EMPRESA)
        self.assertEqual(nombre, "Visitante Sintético")
        # los datos de contacto se guardan tal cual: son la agenda de seguimiento
        self.assertEqual(correo, "visitante@example.test")
        self.assertEqual(telefono, "+56 9 5555 5555")
        self.assertEqual(estado, "nuevo")
        self.assertEqual(origen, "landing")
        auditoria = self.select("SELECT actor FROM auditoria WHERE actor = %s", (f"publico:{lead_id}",))
        self.assertEqual(len(auditoria), 1)

    def test_ld02_reintento_misma_clave_mismo_cuerpo(self):
        clave = self.clave()
        primera = self.anonima.post(
            "/publico/leads", json=self.cuerpo_lead(), headers={"Idempotency-Key": clave}
        )
        segunda = self.anonima.post(
            "/publico/leads", json=self.cuerpo_lead(), headers={"Idempotency-Key": clave}
        )
        self.assertEqual(primera.status_code, 201, primera.text)
        self.assertEqual(segunda.status_code, 200, segunda.text)
        self.assertTrue(segunda.json()["reintento"])
        self.assertEqual(primera.json()["lead"]["id"], segunda.json()["lead"]["id"])
        self.assertEqual(self.select("SELECT count(*) FROM leads")[0][0], 1)

    def test_ld03_misma_clave_otro_cuerpo_409(self):
        clave = self.clave()
        self.assertEqual(self.anonima.post(
            "/publico/leads", json=self.cuerpo_lead(), headers={"Idempotency-Key": clave}
        ).status_code, 201)
        respuesta = self.anonima.post(
            "/publico/leads", json=self.cuerpo_lead(nombre="Otro Nombre"),
            headers={"Idempotency-Key": clave},
        )
        self.assertEqual(respuesta.status_code, 409, respuesta.text)
        self.assertEqual(self.select("SELECT count(*) FROM leads")[0][0], 1)

    def test_ld04_sin_clave_de_idempotencia_422(self):
        respuesta = self.anonima.post("/publico/leads", json=self.cuerpo_lead())
        self.assertEqual(respuesta.status_code, 422, respuesta.text)

    def test_ld05_validaciones_del_lead(self):
        casos = [
            {**self.cuerpo_lead(), "nombre": ""},
            {**self.cuerpo_lead(), "correo": "no-es-correo"},
            {**self.cuerpo_lead(), "telefono": ""},
            {**self.cuerpo_lead(), "huespedes": 0},
            {**self.cuerpo_lead(), "huespedes": 31},
            {**self.cuerpo_lead(), "check_out": str(MANANA)},  # fin == inicio
            {**self.cuerpo_lead(), "check_in": None, "check_out": str(EN_3)},  # fecha suelta
            {**self.cuerpo_lead(), "mensaje": "x" * 2001},
        ]
        for i, cuerpo in enumerate(casos):
            respuesta = self.anonima.post(
                "/publico/leads", json=cuerpo, headers={"Idempotency-Key": self.clave()}
            )
            self.assertEqual(respuesta.status_code, 422, f"caso {i}: {respuesta.text}")
        self.assertEqual(self.select("SELECT count(*) FROM leads")[0][0], 0)

    def test_ld06_cuerpo_muy_grande_413(self):
        # el tope de 8 KB se ejerce antes del modelo: Pydantic ignora campos
        # extra, así que el cuerpo grande llega al chequeo de content-length
        respuesta = self.anonima.post(
            "/publico/leads", json={**self.cuerpo_lead(), "relleno": "x" * 9000},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(respuesta.status_code, 413, respuesta.text)

    def test_ld07_freno_de_abuso_por_ip(self):
        config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, origen_landing=LANDING,
            admin_usuario=ADMIN[0], admin_clave=ADMIN[1], publico_max_por_minuto=2,
        )
        app = crear_app(configuracion=config)
        app.state.freno_solicitudes.max_por_minuto = 2
        anonima = TestClient(app)
        estados = [
            anonima.post("/publico/leads", json=self.cuerpo_lead(),
                         headers={"Idempotency-Key": self.clave()}).status_code
            for _ in range(3)
        ]
        self.assertEqual(estados[:2], [201, 201])
        self.assertEqual(estados[2], 429)


class LeadsCorsTest(LeadsBaseTest):
    def test_ld10_cors_solo_publico_y_solo_origen_landing(self):
        con_origen = self.anonima.post(
            "/publico/leads", json=self.cuerpo_lead(),
            headers={"Idempotency-Key": self.clave(), "Origin": LANDING},
        )
        self.assertEqual(con_origen.status_code, 201, con_origen.text)
        self.assertEqual(con_origen.headers.get("access-control-allow-origin"), LANDING)
        self.assertIsNone(con_origen.headers.get("access-control-allow-credentials"))
        ajeno = self.anonima.post(
            "/publico/leads", json=self.cuerpo_lead(),
            headers={"Idempotency-Key": self.clave(), "Origin": "https://otro.example"},
        )
        self.assertIsNone(ajeno.headers.get("access-control-allow-origin"))

    def test_ld11_origen_landing_no_entra_a_la_bandeja_interna(self):
        lectura = self.anonima.get("/hotel/leads", headers={"Origin": LANDING})
        self.assertEqual(lectura.status_code, 401)
        lead_id = self.crear_lead()
        mutacion = self.cliente.post(
            f"/hotel/leads/{lead_id}/estado", json={"estado": "contactado"},
            headers={"Idempotency-Key": self.clave(), "Origin": LANDING},
        )
        self.assertEqual(mutacion.status_code, 403)


class BandejaLeadsTest(LeadsBaseTest):
    def test_ld20_bandeja_con_datos_de_contacto_y_orden(self):
        primero = self.crear_lead(nombre="Primero")
        segundo = self.crear_lead(nombre="Segundo")
        respuesta = self.cliente.get("/hotel/leads")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        leads = respuesta.json()["leads"]
        self.assertEqual({l["id"] for l in leads}, {primero, segundo})
        creados = [l["creado_en"] for l in leads]
        self.assertEqual(creados, sorted(creados, reverse=True))  # creado_en DESC
        por_id = {l["id"]: l for l in leads}
        self.assertEqual(por_id[segundo]["nombre"], "Segundo")
        self.assertEqual(por_id[segundo]["correo"], "visitante@example.test")
        self.assertEqual(por_id[segundo]["telefono"], "+56 9 5555 5555")
        self.assertEqual(por_id[segundo]["mensaje"], "Consulta sobre disponibilidad")
        self.assertEqual(por_id[segundo]["estado"], "nuevo")

    def test_ld21_bandeja_exige_rol_de_gestion(self):
        self.crear_lead()
        self.assertEqual(self.anonima.get("/hotel/leads").status_code, 401)
        self.crear_usuario("caja1", "caja")
        caja = self.login("caja1", "clave-usuario-1")
        self.assertEqual(caja.get("/hotel/leads").status_code, 403)

    def test_ld22_bandeja_filtra_por_estado(self):
        uno = self.crear_lead(nombre="Uno")
        dos = self.crear_lead(nombre="Dos")
        self.assertEqual(self.cliente.post(
            f"/hotel/leads/{uno}/estado", json={"estado": "contactado", "nota": "Llamado"},
            headers={"Idempotency-Key": self.clave()},
        ).status_code, 200)
        nuevos = self.cliente.get("/hotel/leads", params={"estado": "nuevo"})
        self.assertEqual({l["id"] for l in nuevos.json()["leads"]}, {dos})
        contactados = self.cliente.get("/hotel/leads", params={"estado": "contactado"})
        self.assertEqual({l["id"] for l in contactados.json()["leads"]}, {uno})

    def test_ld23_gestion_marca_estado_nota_y_auditoria(self):
        lead_id = self.crear_lead()
        respuesta = self.cliente.post(
            f"/hotel/leads/{lead_id}/estado", json={"estado": "contactado", "nota": "Llamado, pide cotización"},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        fila = self.select(
            "SELECT estado, gestion_por, gestion_en, nota FROM leads WHERE id = %s", (lead_id,)
        )[0]
        self.assertEqual(fila[0], "contactado")
        self.assertEqual(fila[1], ADMIN[0])
        self.assertIsNotNone(fila[2])
        self.assertEqual(fila[3], "Llamado, pide cotización")
        auditoria = self.select("SELECT actor FROM auditoria WHERE actor = %s", (ADMIN[0],))
        self.assertGreaterEqual(len(auditoria), 1)

    def test_ld24_transiciones_invalidas_409_y_ajeno_403(self):
        lead_id = self.crear_lead()
        self.assertEqual(self.cliente.post(
            f"/hotel/leads/{lead_id}/estado", json={"estado": "cerrado"},
            headers={"Idempotency-Key": self.clave()},
        ).status_code, 200)  # nuevo → cerrado es válida
        self.assertEqual(self.cliente.post(
            f"/hotel/leads/{lead_id}/estado", json={"estado": "contactado"},
            headers={"Idempotency-Key": self.clave()},
        ).status_code, 409)  # cerrado → contactado no
        self.assertEqual(self.cliente.post(
            "/hotel/leads/LEAD-NO-EXISTE/estado", json={"estado": "contactado"},
            headers={"Idempotency-Key": self.clave()},
        ).status_code, 403)
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "INSERT INTO leads (id, empresa_id, nombre, correo, telefono, estado, origen, "
                "idempotency_key, cuerpo_hash) VALUES ('LEAD-AJENA', %s, 'Ajeno', 'a@b.test', "
                "'123', 'nuevo', 'landing', 'clave-ajena', 'hash')", (OTRA_EMPRESA,)
            )
            conexion.commit()
        self.assertEqual(self.cliente.post(
            "/hotel/leads/LEAD-AJENA/estado", json={"estado": "contactado"},
            headers={"Idempotency-Key": self.clave()},
        ).status_code, 403)
        # CA-LEAD-03: la bandeja nunca muestra leads de otra empresa
        self.assertNotIn("LEAD-AJENA", {l["id"] for l in self.cliente.get("/hotel/leads").json()["leads"]})

    def test_ld25_gestion_idempotente_por_clave_interna(self):
        lead_id = self.crear_lead()
        clave = self.clave()
        cuerpo = {"estado": "contactado", "nota": "Primer intento"}
        primera = self.cliente.post(f"/hotel/leads/{lead_id}/estado", json=cuerpo,
                                    headers={"Idempotency-Key": clave})
        self.assertEqual(primera.status_code, 200, primera.text)
        gestion_en = self.select("SELECT gestion_en FROM leads WHERE id = %s", (lead_id,))[0][0]
        segunda = self.cliente.post(f"/hotel/leads/{lead_id}/estado", json=cuerpo,
                                    headers={"Idempotency-Key": clave})
        self.assertEqual(segunda.status_code, 200, segunda.text)
        # CA-LEAD-04: no reescribe gestion_en
        self.assertEqual(self.select("SELECT gestion_en FROM leads WHERE id = %s", (lead_id,))[0][0], gestion_en)
        self.assertEqual(self.cliente.post(
            f"/hotel/leads/{lead_id}/estado", json=cuerpo
        ).status_code, 400)  # sin clave interna: la compuerta de mutaciones responde 400

    def test_ld26_cierre_guarda_nota_y_bloquea_reapertura(self):
        lead_id = self.crear_lead()
        self.assertEqual(self.cliente.post(
            f"/hotel/leads/{lead_id}/estado", json={"estado": "contactado"},
            headers={"Idempotency-Key": self.clave()},
        ).status_code, 200)
        self.assertEqual(self.cliente.post(
            f"/hotel/leads/{lead_id}/estado", json={"estado": "cerrado", "nota": "Reservó por teléfono"},
            headers={"Idempotency-Key": self.clave()},
        ).status_code, 200)
        fila = self.select("SELECT estado, nota FROM leads WHERE id = %s", (lead_id,))[0]
        self.assertEqual(fila, ("cerrado", "Reservó por teléfono"))
        self.assertEqual(self.cliente.post(
            f"/hotel/leads/{lead_id}/estado", json={"estado": "nuevo"},
            headers={"Idempotency-Key": self.clave()},
        ).status_code, 409)


if __name__ == "__main__":
    unittest.main()
