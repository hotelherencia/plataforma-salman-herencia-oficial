"""Auditoría de seguridad 2026-11-17 — SA-MH-01: el adaptador HTTP del modelo
no sigue redirecciones (urllib reenviaba Authorization con la API key al nuevo
host), exige https fuera de loopback y acota el tamaño de la respuesta."""
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from servicio.modelo_http import ModeloHttp
from servicio.modelo_lenguaje import ModeloFallo

MB = 1024 * 1024


class _Destino(BaseHTTPRequestHandler):
    vistos: list = []

    def do_GET(self):
        _Destino.vistos.append(self.headers.get("Authorization"))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"choices":[{"message":{"content":"{\\"herramienta\\":\\"x\\",\\"argumentos\\":{}}"}}]}')

    do_POST = do_GET

    def log_message(self, *a):
        pass


class _Redirige(BaseHTTPRequestHandler):
    destino = ""

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(302)
        self.send_header("Location", _Redirige.destino)
        self.end_headers()

    def log_message(self, *a):
        pass


class _Gigante(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(200)
        self.end_headers()
        try:
            self.wfile.write(
                b'{"choices":[{"message":{"content":"{\\"herramienta\\":\\"x\\",\\"argumentos\\":{}}"}}]}'
                + b" " * (3 * MB))
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *a):
        pass


def _servir(manejador):
    s = HTTPServer(("127.0.0.1", 0), manejador)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


class ModeloHttpEndurecidoTest(unittest.TestCase):
    def test_mh01_no_sigue_redirecciones_ni_filtra_la_clave(self):
        _Destino.vistos = []
        destino = _servir(_Destino)
        _Redirige.destino = f"http://localhost:{destino.server_address[1]}/robado"
        origen = _servir(_Redirige)
        try:
            modelo = ModeloHttp(f"http://127.0.0.1:{origen.server_address[1]}", "clave-secreta-de-prueba")
            with self.assertRaises(ModeloFallo):
                modelo.decidir([{"rol": "user", "texto": "hola"}], ["x"])
            self.assertEqual(_Destino.vistos, [], "la redirección no debe seguirse")
        finally:
            origen.shutdown(); destino.shutdown()

    def test_mh01_exige_https_fuera_de_loopback(self):
        with self.assertRaises(ValueError):
            ModeloHttp("http://api.proveedor.example/v1", "k")
        ModeloHttp("https://api.proveedor.example/v1", "k")  # válido
        ModeloHttp("http://127.0.0.1:9/v1", "k")  # loopback de pruebas

    def test_mh01_respuesta_gigante_es_fallo(self):
        s = _servir(_Gigante)
        try:
            modelo = ModeloHttp(f"http://127.0.0.1:{s.server_address[1]}", "k")
            with self.assertRaises(ModeloFallo):
                modelo.decidir([{"rol": "user", "texto": "hola"}], ["x"])
        finally:
            s.shutdown()


if __name__ == "__main__":
    unittest.main()
