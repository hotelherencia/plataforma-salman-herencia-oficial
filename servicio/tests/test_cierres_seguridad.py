"""Cierres urgentes: documentación de la API apagada en producción y /salud mínimo."""
import unittest

from fastapi.testclient import TestClient

from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion


def _config(**extra) -> Configuracion:
    base = dict(
        host="127.0.0.1",
        puerto=0,
        database_url=None,
        cookie_segura=False,
        origen_front=None,
        admin_usuario=None,
        admin_clave=None,
    )
    base.update(extra)
    return Configuracion(**base)


class DocumentacionHttpTest(unittest.TestCase):
    def test_en_desarrollo_docs_y_openapi_siguen_disponibles(self):
        cliente = TestClient(crear_app())
        self.assertEqual(cliente.get("/docs").status_code, 200)
        self.assertEqual(cliente.get("/redoc").status_code, 200)
        esquema = cliente.get("/openapi.json")
        self.assertEqual(esquema.status_code, 200)
        self.assertTrue(esquema.json()["openapi"].startswith("3."))

    def test_en_produccion_docs_redoc_y_openapi_no_se_exponen(self):
        cliente = TestClient(crear_app(configuracion=_config(cookie_segura=True)))
        for ruta in ("/docs", "/redoc", "/openapi.json", "/docs/", "/redoc/"):
            with self.subTest(ruta=ruta):
                self.assertEqual(cliente.get(ruta).status_code, 404, ruta)


class SaludPublicoTest(unittest.TestCase):
    def test_salud_solo_informa_estado(self):
        cuerpo = TestClient(crear_app()).get("/salud").json()
        self.assertEqual(cuerpo, {"estado": "ok"})
        for clave in ("empresa", "empresa_nombre", "empresa_rut", "es_sintetica", "nucleo", "hotel"):
            self.assertNotIn(clave, cuerpo, clave)
