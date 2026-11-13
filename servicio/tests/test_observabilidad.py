"""Observabilidad: logs JSON correlacionados, 500 controlado y detector de
intentos de vulneración. Sin base de datos (app mínima con `instalar`)."""
import json
import logging
import unittest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from servicio import observabilidad
from servicio.observabilidad import DetectorAmenazas, FormatoJson


def _app(umbral=20, bloquear=False) -> FastAPI:
    app = FastAPI()

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.get("/privado")
    def privado():
        raise HTTPException(status_code=401, detail="sin sesión")

    @app.get("/roto")
    def roto():
        raise ValueError("secreto-que-no-debe-salir")

    observabilidad.instalar(app)
    app.state.detector_amenazas = DetectorAmenazas(umbral=umbral, ventana_segundos=300, bloquear=bloquear)
    return app


class DetectorTest(unittest.TestCase):
    def test_alerta_una_vez_por_ventana(self):
        d = DetectorAmenazas(umbral=3, ventana_segundos=60)
        self.assertFalse(d.registrar("1.1.1.1", ahora=0))
        self.assertFalse(d.registrar("1.1.1.1", ahora=1))
        self.assertTrue(d.registrar("1.1.1.1", ahora=2))
        self.assertFalse(d.registrar("1.1.1.1", ahora=3))  # ya alertado
        self.assertTrue(d.sospechosa("1.1.1.1", ahora=3))
        self.assertFalse(d.sospechosa("1.1.1.1", ahora=100))  # ventana vencida

    def test_ips_independientes(self):
        d = DetectorAmenazas(umbral=2, ventana_segundos=60)
        d.registrar("a", ahora=0)
        self.assertFalse(d.registrar("b", ahora=0))


class MiddlewareTest(unittest.TestCase):
    def test_request_id_en_cabecera_y_respeta_entrante_valido(self):
        c = TestClient(_app())
        r = c.get("/ok", headers={"X-Request-ID": "abc-123"})
        self.assertEqual(r.headers["X-Request-ID"], "abc-123")
        r = c.get("/ok", headers={"X-Request-ID": "<script>alert(1)</script>"})
        self.assertNotIn("<", r.headers["X-Request-ID"])
        self.assertNotEqual(r.headers["X-Request-ID"], "<script>alert(1)</script>")

    def test_500_controlado_sin_filtrar_detalle(self):
        c = TestClient(_app(), raise_server_exceptions=False)
        with self.assertLogs("servicio.http", level="ERROR") as logs:
            r = c.get("/roto")
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("secreto-que-no-debe-salir", r.text)
        self.assertEqual(r.json()["request_id"], r.headers["X-Request-ID"])
        self.assertTrue(any("error_no_controlado" in l for l in logs.output))

    def test_ruta_sonda_y_alerta_posible_ataque(self):
        c = TestClient(_app(umbral=6))
        with self.assertLogs("servicio.seguridad", level="WARNING") as logs:
            c.get("/.env")  # sonda: peso 5
            c.get("/privado")  # 401: peso 1 -> cruza 6
        texto = "\n".join(logs.output)
        self.assertIn("ruta_sonda", texto)
        self.assertIn("posible_ataque", texto)

    def test_bloqueo_opcional(self):
        c = TestClient(_app(umbral=2, bloquear=True))
        c.get("/privado")
        c.get("/privado")
        self.assertEqual(c.get("/ok").status_code, 429)
        self.assertEqual(c.get("/salud").status_code, 404)  # /salud nunca se bloquea

    def test_no_registra_query_string(self):
        c = TestClient(_app())
        with self.assertLogs("servicio.http", level="INFO") as logs:
            c.get("/ok?code=SECRETO_OAUTH&state=x")
        self.assertNotIn("SECRETO_OAUTH", "\n".join(logs.output))
        registro = logs.records[-1]
        self.assertEqual(registro.ruta, "/ok")


class FormatoJsonTest(unittest.TestCase):
    def test_linea_json_con_campos_extra(self):
        registro = logging.makeLogRecord({"name": "servicio.x", "levelname": "WARNING", "msg": "evt", "ip": "1.2.3.4"})
        datos = json.loads(FormatoJson().format(registro))
        self.assertEqual(datos["mensaje"], "evt")
        self.assertEqual(datos["ip"], "1.2.3.4")
        self.assertIn("request_id", datos)


if __name__ == "__main__":
    unittest.main()
