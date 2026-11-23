"""#452 mensajes preformateados al huésped y #454 datos que faltan."""
import os
import unittest
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import mensajes_huesped, migracion, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_mensajes452")
HOY = date.today()


class BuzonFalso:
    def __init__(self, falla=False):
        self.enviados, self.falla = [], falla

    def enviar(self, asunto, cuerpo, destinos=None, html=None):
        if self.falla:
            raise RuntimeError("smtp caído")
        self.enviados.append((asunto, cuerpo, destinos))


class MensajesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario="admin_m", admin_clave="Clave123!"))
        cls.cm = TestClient(cls.app)
        cls.cm.__enter__()
        cls._n = 0

    @classmethod
    def tearDownClass(cls):
        cls.cm.__exit__(None, None, None)

    def setUp(self):
        h = seguridad.hashear_clave("Clave123!")
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "TRUNCATE freno_solicitudes_eventos, mensajes_huesped_envios, reserva_huespedes, huespedes, clientes, reasignaciones, "
                "liquidaciones, pagos, cargos, reserva_noches, reservas, solicitudes, tarifas, excepciones_precio, "
                "habitaciones, politicas_hotel, claves_idempotencia, auditoria, sesiones, usuarios CASCADE")
            c.execute("INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                      "('USR-M-RECEP', 'recep_m', %s, 'recepcion', 'EMP-SINTETICA-001', true), "
                      "('USR-M-CAJA', 'caja_m', %s, 'caja', 'EMP-SINTETICA-001', true)", (h, h))
            c.execute("INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, "
                      "estado_preparacion, en_inventario) VALUES ('HAB-M1', 'EST-1', 'doble', 3, 'disponible', "
                      "'limpia', true)")
            c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, "
                      "motivo, activa) VALUES ('EXC-M1', 'HAB-M1', %s, %s, 55000, 'base', true)",
                      (HOY, HOY + timedelta(days=60)))
            c.commit()
        self.app.state.freno_solicitudes.max_por_minuto = 1000  # el freno se ejercita en test_canal_publico
        self.recep, self.caja = self._login("recep_m"), self._login("caja_m")

    def _login(self, u):
        c = TestClient(self.app)
        self.assertEqual(c.post("/sesion", json={"usuario": u, "clave": "Clave123!"}).status_code, 200)
        return c

    def _h(self):
        self.__class__._n += 1
        return {"Idempotency-Key": f"msg-452-{self._n}-xxxxxxxxxxxx"}

    def _reservar(self, **huesped):
        r = self.recep.post("/hotel/reservas", headers=self._h(), json={
            "habitacion_id": "HAB-M1", "inicio": str(HOY + timedelta(days=3)), "fin": str(HOY + timedelta(days=5)),
            "personas": 2, "huesped": {"nombre": "Ana Prueba", "documento": "12.345.678-5",
                                       "documento_tipo": "rut", **huesped}})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["reserva_id"]

    def test_reserva_con_contacto_arma_mensajes_con_whatsapp_y_correo(self):
        rid = self._reservar(correo="Ana@Example.com", telefono="9 1234 5678")
        m = self.recep.get(f"/hotel/reservas/{rid}/mensajes").json()
        self.assertEqual(m["contacto"], {"correo": "ana@example.com", "telefono": "+56912345678"})
        self.assertEqual(m["datos_faltantes"], [])
        self.assertIsNone(m["alerta"])
        conf = next(x for x in m["mensajes"] if x["plantilla"] == "confirmacion")
        self.assertIn("Llegada:", conf["texto"])
        self.assertIn("$110.000", conf["texto"])
        self.assertTrue(conf["whatsapp"].startswith("https://wa.me/56912345678?text="))
        self.assertTrue(conf["puede_correo"])
        self.assertEqual({x["plantilla"] for x in m["mensajes"]},
                         {"confirmacion", "recordatorio", "solicitar_datos", "cancelacion", "gracias"})

    def test_sin_contacto_alerta_y_datos_faltantes_en_la_ficha(self):
        rid = self._reservar()
        m = self.recep.get(f"/hotel/reservas/{rid}/mensajes").json()
        self.assertIn("Sin forma de contactar", m["alerta"])
        self.assertIn("un correo o un teléfono de contacto", m["datos_faltantes"])
        self.assertIsNone(next(x for x in m["mensajes"] if x["plantilla"] == "gracias")["whatsapp"])
        ficha = self.recep.get(f"/hotel/reservas/{rid}").json()
        self.assertIn("un correo o un teléfono de contacto", ficha["datos_faltantes"])
        r = self.recep.post(f"/hotel/reservas/{rid}/mensajes", headers=self._h(),
                            json={"plantilla": "confirmacion", "canal": "whatsapp"})
        self.assertEqual(r.status_code, 409, r.text)

    def test_contacto_invalido_se_rechaza(self):
        r = self.recep.post("/hotel/reservas", headers=self._h(), json={
            "habitacion_id": "HAB-M1", "inicio": str(HOY + timedelta(days=3)), "fin": str(HOY + timedelta(days=5)),
            "huesped": {"nombre": "Ana", "correo": "no-es-correo"}})
        self.assertEqual(r.status_code, 422)

    def test_whatsapp_manual_queda_en_el_historial_sin_el_numero_completo(self):
        rid = self._reservar(telefono="+56 9 1234 5678")
        r = self.recep.post(f"/hotel/reservas/{rid}/mensajes", headers=self._h(),
                            json={"plantilla": "recordatorio", "canal": "whatsapp"})
        self.assertEqual(r.status_code, 200, r.text)
        h = self.recep.get(f"/hotel/reservas/{rid}/mensajes").json()["historial"]
        self.assertEqual(h[0]["canal"], "whatsapp_manual")
        self.assertNotIn("912345678", h[0]["destino"])

    def test_correo_sin_buzon_configurado_es_409(self):
        rid = self._reservar(correo="ana@example.com")
        r = self.recep.post(f"/hotel/reservas/{rid}/mensajes", headers=self._h(),
                            json={"plantilla": "confirmacion", "canal": "correo"})
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("buzón", r.json()["detail"])

    def test_envio_por_correo_con_buzon_registra_enviado_y_fallido(self):
        rid = self._reservar(correo="ana@example.com")
        with psycopg.connect(URL_TEST) as c:
            ok, mal = BuzonFalso(), BuzonFalso(falla=True)
            r1 = mensajes_huesped.enviar_por_correo(c, "EMP-SINTETICA-001", rid, "confirmacion", "recep_m", buzon=ok)
            r2 = mensajes_huesped.enviar_por_correo(c, "EMP-SINTETICA-001", rid, "gracias", "recep_m", buzon=mal)
            c.commit()
            estados = [f[0] for f in c.execute(
                "SELECT estado FROM mensajes_huesped_envios WHERE reserva_id = %s ORDER BY creado_en", (rid,))]
        self.assertEqual((r1["estado"], r2["estado"]), ("enviado", "fallido"))
        self.assertEqual(estados, ["enviado", "fallido"])
        self.assertEqual(ok.enviados[0][2], ["ana@example.com"])
        self.assertIn("a***@example.com", mensajes_huesped.enmascarar("ana@example.com"))

    def test_roles_y_reserva_ajena(self):
        rid = self._reservar(correo="ana@example.com")
        self.assertEqual(self.caja.get(f"/hotel/reservas/{rid}/mensajes").status_code, 403)
        self.assertEqual(self.recep.get("/hotel/reservas/RSV-NO-EXISTE/mensajes").status_code, 403)

    def test_conversion_de_solicitud_pasa_el_contacto_al_titular(self):
        r = TestClient(self.app).post("/publico/solicitudes", headers={"Idempotency-Key": "pub-452-conv-xxxxxxxxxxxx"}, json={
            "tipo": "doble", "inicio": str(HOY + timedelta(days=5)), "fin": str(HOY + timedelta(days=7)),
            "personas": 2, "huesped_nombre": "Luis Web",
            "huesped_contacto": "luis@example.com · Tel: 9 8765 4321"})
        self.assertEqual(r.status_code, 201, r.text)
        sid = r.json()["solicitud_id"]
        c = self.recep.post(f"/hotel/solicitudes/{sid}/conversion", headers=self._h(), json={})
        self.assertEqual(c.status_code, 201, c.text)
        m = self.recep.get(f"/hotel/reservas/{c.json()['reserva_id']}/mensajes").json()
        self.assertEqual(m["contacto"], {"correo": "luis@example.com", "telefono": "+56987654321"})


if __name__ == "__main__":
    unittest.main()
