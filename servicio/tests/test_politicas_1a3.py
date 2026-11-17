"""Entrega 1A.3 — políticas del hotel, recargos en la cotización y agente."""
import os
import pathlib
import unittest
from datetime import date, time, timedelta
from decimal import Decimal

import psycopg
from fastapi.testclient import TestClient

from servicio import agente, politicas, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.modelo_lenguaje import ModeloGuionado
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


def iso(dias: int) -> str:
    return (HOY + timedelta(days=dias)).isoformat()


def _limpiar(conexion):
    exigir_base_libre(conexion)
    conexion.execute(
        "TRUNCATE politica_agente, trazas_agente, borradores_agente, consultas_agente, "
        "auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
        "solicitudes, reservas, tarifas, tareas_operativas, sesiones, usuarios, habitaciones "
        "RESTART IDENTITY CASCADE"
    )
    conexion.execute("DELETE FROM tipos_habitacion WHERE id LIKE 't13%%'")
    conexion.execute("DELETE FROM politicas_hotel WHERE empresa_id = %s", (EMPRESA,))
    conexion.execute("UPDATE ajustes_plataforma SET valor = 19 WHERE clave = 'iva_porcentaje'")


class PoliticasDominioTest(unittest.TestCase):
    def test_inicial_marca_pendientes_sin_inventar(self):
        cuerpo = politicas.inicial()
        self.assertEqual(cuerpo["llegada_salida"]["hora_llegada_desde"], "14:00")
        self.assertEqual(cuerpo["llegada_salida"]["hora_salida_hasta"], "12:00")
        self.assertEqual(cuerpo["llegada_salida"]["confirmacion"], politicas.PENDIENTE)
        self.assertEqual(cuerpo["cancelacion"]["confirmacion"], politicas.PENDIENTE)
        self.assertEqual(cuerpo["cancelacion"]["horas_antelacion_gratis"], 48)
        self.assertIn("48 horas", politicas.texto_cancelacion(cuerpo))
        self.assertEqual(cuerpo["no_show"]["confirmacion"], politicas.NO_DEFINIDO)
        self.assertIsNone(cuerpo["no_show"]["penalidad_tipo"])
        self.assertEqual(cuerpo["mascotas"]["confirmacion"], politicas.NO_DEFINIDO)
        self.assertIsNone(cuerpo["mascotas"]["se_aceptan"])
        self.assertIsNone(cuerpo["estacionamiento"]["con_costo"])
        self.assertTrue(cuerpo["desayuno"]["incluido"])
        self.assertEqual(cuerpo["medios_pago"]["medios"], ["efectivo", "tarjeta", "transferencia"])
        self.assertGreaterEqual(len(cuerpo["faq"]), 14)
        rutas = {p["ruta"] for p in politicas.pendientes(cuerpo)}
        self.assertTrue(any(r == "cancelacion" or r.startswith("cancelacion.") for r in rutas))
        self.assertTrue(any(r == "llegada_salida" or r.startswith("llegada_salida.") for r in rutas))

    def test_recargo_llegada_anticipada_por_hora(self):
        cuerpo = politicas.inicial()
        calc = politicas.calcular_recargos(
            cuerpo, 55000, 2, {"hora_llegada": "11:00", "hora_salida": "12:00"}
        )
        self.assertEqual(calc["total_recargos_clp"], 30_000)
        self.assertEqual(calc["recargos"][0]["concepto"], "llegada_anticipada")
        self.assertEqual(calc["recargos"][0]["horas"], 3)
        self.assertEqual([r["concepto"] for r in calc["recargos"]], ["llegada_anticipada"])

    def test_recargo_salida_tardia_y_desglose(self):
        cuerpo = politicas.inicial()
        item = politicas.enriquecer_item(
            {"habitacion_id": "HAB-X", "tipo": "doble", "tarifa_noche_clp": 55000, "total_clp": 110000},
            cuerpo, {"hora_salida": "15:00"}, Decimal("19"), 2,
        )
        self.assertEqual(item["subtotal_noches_clp"], 110000)
        self.assertEqual(item["total_recargos_clp"], 30_000)
        self.assertEqual(item["total_clp"], 140000)
        self.assertEqual(item["desglose"]["con_iva"], 140000)
        self.assertEqual(item["desglose"]["neto"] + item["desglose"]["iva"], 140000)
        self.assertEqual(item["cancelacion_confirmacion"], politicas.PENDIENTE)

    def test_horas_iniciadas(self):
        self.assertEqual(politicas._horas_iniciadas(time(11, 0), time(14, 0), True), 3)
        self.assertEqual(politicas._horas_iniciadas(time(11, 1), time(14, 0), True), 3)
        self.assertEqual(politicas._horas_iniciadas(time(14, 0), time(14, 0), True), 0)
        self.assertEqual(politicas._horas_iniciadas(time(15, 0), time(12, 0), False), 3)

    def test_minimo_de_noches(self):
        cuerpo = politicas.inicial()
        cuerpo["minimo_noches"]["confirmacion"] = "confirmado"
        cuerpo["minimo_noches"]["noches"] = 3
        calc = politicas.calcular_recargos(cuerpo, 55000, 2, None)
        self.assertFalse(calc["cumple_minimo"])
        calc2 = politicas.calcular_recargos(cuerpo, 55000, 3, None)
        self.assertTrue(calc2["cumple_minimo"])

    def test_cama_adicional_sin_precio_no_inventa(self):
        cuerpo = politicas.inicial()
        calc = politicas.calcular_recargos(cuerpo, 55000, 2, {"cama_adicional": True})
        self.assertEqual(calc["total_recargos_clp"], 0)
        self.assertEqual(calc["avisos"][0]["motivo"], "pendiente_de_confirmar")

    def test_publica_oculta_pasos_internos(self):
        vista = politicas.vista_publica({
            "empresa_id": EMPRESA, "version": 0, "actualizada_en": None, "cuerpo": politicas.inicial(),
        })
        self.assertNotIn("pasos", vista["politicas"].get("registro_llegada", {}))
        self.assertTrue(all(d.get("publico") for d in vista["politicas"]["registro_llegada"]["datos"]))
        self.assertNotIn("registro_salida", vista["politicas"])

    def test_reservas_ya_no_tiene_politica_hardcodeada(self):
        fuente = (pathlib.Path(__file__).resolve().parents[1] / "reservas.py").read_text(encoding="utf-8")
        self.assertNotIn("POLITICA_CANCELACION", fuente)
        self.assertNotIn("15:00", fuente)


class PoliticasHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        ))

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            _limpiar(conexion)
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
        self.cliente = TestClient(self.app)
        self._n = 0

    def tearDown(self):
        with psycopg.connect(URL_TEST) as conexion:
            _limpiar(conexion)

    def clave(self):
        self._n += 1
        return {"Idempotency-Key": f"t13-{self._n}"}

    def _sesion(self, nombre, clave, rol=None):
        if rol and rol != "administrador":
            with psycopg.connect(URL_TEST) as conexion:
                seguridad.crear_usuario(conexion, EMPRESA, nombre, rol, clave)
        r = self.cliente.post("/sesion", json={"usuario": nombre, "clave": clave})
        self.assertEqual(r.status_code, 200, r.text)
        return r

    def test_get_publico_sin_sesion(self):
        r = self.cliente.get("/publico/politicas")
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertEqual(cuerpo["politicas"]["llegada_salida"]["hora_llegada_desde"], "14:00")
        self.assertEqual(cuerpo["politicas"]["cancelacion"]["confirmacion"], "pendiente_confirmar")
        self.assertNotIn("registro_salida", cuerpo["politicas"])
        self.assertTrue(cuerpo["pendientes"])

    def test_put_solo_admin_hotel(self):
        self._sesion("recep", "clave-recepcion-xx", "recepcion")
        r = self.cliente.get("/hotel/politicas")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["puede_editar"])
        cuerpo = r.json()["cuerpo"]
        cuerpo["desayuno"]["horario_desde"] = "08:00"
        r = self.cliente.put("/hotel/politicas", json={"cuerpo": cuerpo}, headers=self.clave())
        self.assertEqual(r.status_code, 403)
        self.cliente.delete("/sesion")
        self._sesion("plataforma", "clave-plataforma-x", "admin_plataforma")
        r = self.cliente.put("/hotel/politicas", json={"cuerpo": cuerpo}, headers=self.clave())
        self.assertEqual(r.status_code, 403)
        self.cliente.delete("/sesion")
        self._sesion(*ADMIN)
        r = self.cliente.put("/hotel/politicas", json={"cuerpo": cuerpo}, headers=self.clave())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["cuerpo"]["desayuno"]["horario_desde"], "08:00")
        self.assertEqual(r.json()["version"], 1)

    def test_oferta_y_reserva_aplican_recargos_y_snapshot(self):
        self._sesion(*ADMIN)
        alta = self.cliente.post("/hotel/tipos", json={
            "tipo_id": "t13_dbl", "nombre": "Doble 1A3", "capacidad_base": 2,
            "precio_base_clp": 55000, "precio_en": "con_iva",
        }, headers=self.clave())
        self.assertEqual(alta.status_code, 201, alta.text)
        lote = self.cliente.post("/hotel/habitaciones/lote", json={
            "tipo_id": "t13_dbl", "cantidad": 1, "prefijo": "T13-", "desde_numero": 1,
        }, headers=self.clave())
        self.assertEqual(lote.status_code, 201, lote.text)
        hid = lote.json()["habitaciones"][0]
        oferta = self.cliente.get(
            f"/hotel/oferta?inicio={iso(3)}&fin={iso(5)}&personas=2&hora_llegada=11:00&hora_salida=12:00"
        )
        self.assertEqual(oferta.status_code, 200, oferta.text)
        item = next(i for i in oferta.json()["oferta"] if i["habitacion_id"] == hid)
        self.assertEqual(item["subtotal_noches_clp"], 110000)
        self.assertEqual(item["total_recargos_clp"], 30000)
        self.assertEqual(item["total_clp"], 140000)
        self.assertEqual(item["desglose"]["con_iva"], 140000)
        self.assertEqual(item["cancelacion_confirmacion"], "pendiente_confirmar")
        reserva = self.cliente.post("/hotel/reservas", json={
            "habitacion_id": hid, "inicio": iso(3), "fin": iso(5),
            "huesped": {"nombre": "Huésped 1A3"}, "personas": 2,
            "hora_llegada": "11:00",
        }, headers=self.clave())
        self.assertEqual(reserva.status_code, 201, reserva.text)
        self.assertEqual(reserva.json()["total_clp"], 140000)
        self.assertEqual(reserva.json()["subtotal_noches_clp"], 110000)
        self.assertEqual(len(reserva.json()["recargos"]), 1)
        with psycopg.connect(URL_TEST) as conexion:
            fila = conexion.execute(
                "SELECT total_aceptado_clp, politica_snapshot, recargos FROM reservas WHERE id = %s",
                (reserva.json()["reserva_id"],),
            ).fetchone()
        self.assertEqual(fila[0], 140000)
        self.assertIn("48 horas", fila[1]["texto_cancelacion"])
        self.assertEqual(fila[2][0]["monto_clp"], 30000)

    def test_simulacion_con_precio_de_ejemplo(self):
        self._sesion(*ADMIN)
        r = self.cliente.post("/hotel/politicas/simulacion", json={
            "inicio": iso(3), "fin": iso(5), "hora_llegada": "11:00",
            "precio_noche_clp": 55000,
        })
        self.assertEqual(r.status_code, 200, r.text)
        s = r.json()["simulacion"]
        self.assertEqual(r.json()["noches"], 2)
        self.assertEqual(s["total_clp"], 140000)

    def test_agente_consulta_politicas(self):
        with psycopg.connect(URL_TEST) as conexion:
            _limpiar(conexion)
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            agente.asegurar_agente_servicio(conexion, EMPRESA)
            consulta = agente.registrar_consulta(conexion, EMPRESA, "manual", "¿A qué hora es la llegada?", "admin")
            modelo = ModeloGuionado([
                {"herramienta": "consultar_politicas", "argumentos": {"tema": "horarios"}},
                {"herramienta": "proponer_borrador", "argumentos": {
                    "plantilla": "informacion", "campos": {}, "saludo": "Hola",
                }},
            ])
            agente.procesar(conexion, consulta, modelo, agente.politica_de(conexion, EMPRESA))
            conexion.commit()
            detalle = agente.detalle_consulta(conexion, EMPRESA, consulta["consulta_id"])
        self.assertEqual(detalle["estado"], "procesada")
        texto = detalle["borradores"][-1]["texto_compuesto"]
        self.assertIn("14:00", texto)
        self.assertIn("12:00", texto)
        veredicto = agente.verificar(
            {"plantilla": "informacion", "campos": {}, "saludo": "Llegada desde las 14:00"},
            {"consultar_politicas": politicas.conocimiento(politicas.inicial(), "horarios")},
        )
        self.assertEqual(veredicto, "ok")
        self.assertEqual(
            agente.verificar({"plantilla": "informacion", "campos": {}, "saludo": "Hola"}, {}),
            "rechazo:sin_politicas_del_turno",
        )
        self.assertEqual(
            agente.verificar(
                {"plantilla": "informacion", "campos": {}, "saludo": "El recargo es $99999"},
                {"consultar_politicas": politicas.conocimiento(politicas.inicial(), "horarios")},
            ),
            "rechazo:cifra_en_texto_libre",
        )
