"""El titular real (Herencia SpA) no es el marcador sintético de las pruebas."""
import unittest

from fastapi.testclient import TestClient

from servicio.aplicacion import crear_app, empresa_desde_config
from servicio.configuracion import Configuracion
from servicio.empresa_titular import EMPRESA_TITULAR, EMPRESA_TITULAR_RUT


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


class EmpresaTitularTest(unittest.TestCase):
    def test_sin_config_sigue_el_marcador_sintetico(self):
        empresa = empresa_desde_config(None)
        self.assertEqual(empresa.id, "EMP-SINTETICA-001")
        self.assertTrue(empresa.es_sintetico)

    def test_empresa_titular_activa_herencia_spa(self):
        empresa = empresa_desde_config(_config(empresa_titular=True))
        self.assertEqual(empresa.id, EMPRESA_TITULAR.id)
        self.assertEqual(empresa.nombre, "Herencia SpA")
        self.assertFalse(empresa.es_sintetico)

    def test_salud_publico_no_expone_datos_internos(self):
        app = crear_app(configuracion=_config(
            empresa_titular=True,
            empresa_rut=EMPRESA_TITULAR_RUT,
        ))
        cuerpo = TestClient(app).get("/salud").json()
        self.assertEqual(cuerpo, {"estado": "ok"})
        self.assertNotIn("empresa_rut", cuerpo)
        self.assertNotIn("empresa", cuerpo)
        self.assertNotIn("empresa_nombre", cuerpo)
        # El titular sigue activo en el núcleo; ya no se publica por /salud.
        self.assertEqual(app.state.aplicacion.nucleo.empresa.id, "EMP-HERENCIA-001")
        self.assertEqual(app.state.aplicacion.nucleo.empresa.nombre, "Herencia SpA")


if __name__ == "__main__":
    unittest.main()
