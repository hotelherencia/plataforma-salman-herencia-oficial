"""Adaptador HTTP genérico del modelo del agente (#319): contrato decidir()
contra un endpoint OpenAI-compatible, con un servidor HTTP LOCAL de stub —
sin red externa (NFR-A04). Cubre: payload (model/messages/autorización),
parseo de la decisión, y los caminos de fallo (HTTP != 200, cuerpo inválido,
JSON sin la forma exigida, tipos inválidos, servidor caído/timeout).
"""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from servicio.modelo_http import ModeloHttp
from servicio.modelo_lenguaje import ModeloFallo


class ServidorStub:
    """Servidor HTTP de un solo uso: responde lo que se le programa y
    registra la última petición para afirmar el contrato del request."""

    def __init__(self, status=200, payload=None, latencia_seg=0.0):
        self.status = status
        self.payload = payload
        self.latencia = latencia_seg
        self.ultima = None
        manejador = self._fabrica()
        self.servidor = HTTPServer(("127.0.0.1", 0), manejador)
        self.puerto = self.servidor.server_address[1]
        self.hilo = threading.Thread(target=self.servidor.serve_forever, daemon=True)

    def _fabrica(self):
        stub = self

        class Manejador(BaseHTTPRequestHandler):
            def do_POST(self):
                largo = int(self.headers.get("Content-Length", 0))
                cuerpo = self.rfile.read(largo)
                stub.ultima = {
                    "ruta": self.path,
                    "authorization": self.headers.get("Authorization"),
                    "cuerpo": json.loads(cuerpo.decode("utf-8")) if cuerpo else None,
                }
                if stub.latencia:
                    import time
                    time.sleep(stub.latencia)
                self.send_response(stub.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if stub.payload is not None:
                    self.wfile.write(json.dumps(stub.payload).encode("utf-8"))

            def log_message(self, *args):
                pass

        return Manejador

    def __enter__(self):
        self.hilo.start()
        return self

    def __exit__(self, *args):
        self.servidor.shutdown()
        self.servidor.server_close()

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.puerto}"


def payload_openai(contenido):
    return {"choices": [{"message": {"role": "assistant", "content": contenido}}]}


class ModeloHttpTest(unittest.TestCase):
    def test_payload_y_decision_parseada(self):
        decision = {"herramienta": "cotizar", "argumentos": {"inicio": "2026-12-01"}}
        with ServidorStub(payload=payload_openai(json.dumps(decision))) as stub:
            modelo = ModeloHttp(stub.base_url, api_key="clave-de-prueba", modelo="prueba")
            resultado = modelo.decidir(
                [{"role": "user", "content": "contexto del turno"}],
                ["cotizar", "escalar"],
            )
        self.assertEqual(resultado, decision)
        self.assertEqual(stub.ultima["ruta"], "/chat/completions")
        self.assertEqual(stub.ultima["authorization"], "Bearer clave-de-prueba")
        cuerpo = stub.ultima["cuerpo"]
        self.assertEqual(cuerpo["model"], "prueba")
        self.assertEqual(cuerpo["temperature"], 0)
        roles = [m["role"] for m in cuerpo["messages"]]
        self.assertEqual(roles[0], "system")
        self.assertEqual(roles[1], "user")
        self.assertIn("cotizar", cuerpo["messages"][0]["content"])

    def test_http_500_es_modelo_fallo(self):
        with ServidorStub(status=500, payload={"error": "boom"}) as stub:
            modelo = ModeloHttp(stub.base_url, api_key="k")
            with self.assertRaises(ModeloFallo):
                modelo.decidir([{"role": "user", "content": "x"}], ["cotizar"])

    def test_json_invalido_en_el_contenido(self):
        with ServidorStub(payload=payload_openai("no soy json")) as stub:
            modelo = ModeloHttp(stub.base_url, api_key="k")
            with self.assertRaises(ModeloFallo):
                modelo.decidir([{"role": "user", "content": "x"}], ["cotizar"])

    def test_json_sin_la_forma_exigida(self):
        with ServidorStub(payload=payload_openai(json.dumps({"otra": "cosa"}))) as stub:
            modelo = ModeloHttp(stub.base_url, api_key="k")
            with self.assertRaises(ModeloFallo):
                modelo.decidir([{"role": "user", "content": "x"}], ["cotizar"])

    def test_tipos_invalidos(self):
        with ServidorStub(payload=payload_openai(json.dumps({"herramienta": 1, "argumentos": []}))) as stub:
            modelo = ModeloHttp(stub.base_url, api_key="k")
            with self.assertRaises(ModeloFallo):
                modelo.decidir([{"role": "user", "content": "x"}], ["cotizar"])

    def test_timeout_es_modelo_fallo(self):
        with ServidorStub(payload=payload_openai("{}"), latencia_seg=0.4) as stub:
            modelo = ModeloHttp(stub.base_url, api_key="k", timeout_seg=1)
            with self.assertRaises(ModeloFallo):
                modelo.decidir([{"role": "user", "content": "x"}], ["cotizar"])

    def test_servidor_caido_es_modelo_fallo(self):
        with ServidorStub(payload=payload_openai("{}")) as stub:
            base = stub.base_url
        modelo = ModeloHttp(base, api_key="k")
        with self.assertRaises(ModeloFallo):
            modelo.decidir([{"role": "user", "content": "x"}], ["cotizar"])


class SeleccionDeModeloTest(unittest.TestCase):
    """crear_app elige el puerto: guion (pruebas) > http (configurado) >
    SinAdaptador (503 por defecto, D-AGT-02 pendiente)."""

    def _config(self, **extra):
        from servicio.configuracion import Configuracion
        base = dict(host="127.0.0.1", puerto=0, database_url=None,
                    cookie_segura=False, origen_front=None,
                    admin_usuario=None, admin_clave=None)
        base.update(extra)
        return Configuracion(**base)

    def test_sin_configuracion_es_sin_adaptador(self):
        from servicio.aplicacion import crear_app
        app = crear_app(configuracion=self._config())
        self.assertEqual(app.state.modelo_agente.nombre, "sin_adaptador")

    def test_con_modelo_http_configurado(self):
        from servicio.aplicacion import crear_app
        app = crear_app(configuracion=self._config(
            modelo_base_url="http://127.0.0.1:9", modelo_api_key="k", modelo_nombre="m"))
        self.assertEqual(app.state.modelo_agente.nombre, "http")

    def test_el_guion_manda_sobre_http(self):
        from servicio.aplicacion import crear_app
        app = crear_app(configuracion=self._config(
            agente_guion_json="[]",
            modelo_base_url="http://127.0.0.1:9", modelo_api_key="k"))
        self.assertEqual(app.state.modelo_agente.nombre, "guionado")


if __name__ == "__main__":
    unittest.main()
