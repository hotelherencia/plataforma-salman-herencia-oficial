import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import servicio.aplicacion as aplicacion_modulo
from servicio.aplicacion import (
    ErrorArranque,
    construir_aplicacion,
    construir_hotel,
    crear_app,
    main,
)
from servicio.configuracion import Configuracion
from servicio.migracion import DIRECTORIO_MIGRACIONES

from hotel_inventario.dominio import EstadoUnidad, Establecimiento, Unidad
from nucleo.empresa import Empresa
from nucleo.servicio import Nucleo

EMPRESA_DEL_NUCLEO = "EMP-SINTETICA-001"


class ArranqueTest(unittest.TestCase):
    def test_arranca_con_nucleo_y_hotel_de_la_misma_empresa(self):
        app = crear_app()
        cliente = TestClient(app)
        respuesta = cliente.get("/salud")

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["nucleo"], "cargado")
        self.assertEqual(cuerpo["hotel"], "cargado")
        self.assertEqual(cuerpo["empresa"], EMPRESA_DEL_NUCLEO)
        self.assertEqual(app.state.aplicacion.hotel.empresa.id, app.state.aplicacion.nucleo.empresa.id)

    def test_no_arranca_si_el_hotel_trae_otra_empresa(self):
        nucleo = Nucleo()
        ajeno = Establecimiento(id="EST-OTRO-001", empresa_id="EMP-OTRA", nombre="Ajeno")
        unidades = (Unidad("HAB-OTRA-1", ajeno.id, 2, 50_000, EstadoUnidad.LIMPIA),)

        with self.assertRaises(ErrorArranque):
            construir_hotel(nucleo, ajeno, unidades)

    def test_el_proceso_termina_si_la_construccion_falla(self):
        configuracion = Configuracion(host="127.0.0.1", puerto=0, database_url=None, cookie_segura=False, origen_front=None, admin_usuario=None, admin_clave=None)
        with patch.object(aplicacion_modulo, "construir_aplicacion", side_effect=ErrorArranque("empresa ajena")):
            with self.assertRaises(SystemExit):
                main(configuracion)

    def test_construir_aplicacion_queda_atada_a_la_empresa_del_nucleo(self):
        otra = Nucleo(empresa=Empresa(id="EMP-SEGUNDA", nombre="Segunda", es_sintetico=True))
        app = aplicacion_modulo.crear_app(aplicacion_modulo.construir_aplicacion(otra))
        self.assertEqual(app.state.aplicacion.hotel.empresa.id, "EMP-SEGUNDA")
        self.assertEqual(app.state.aplicacion.nucleo.empresa.id, "EMP-SEGUNDA")


class MigracionesTest(unittest.TestCase):
    def test_las_migraciones_son_sql_numerado_en_orden(self):
        archivos = sorted(DIRECTORIO_MIGRACIONES.glob("*.sql"))
        self.assertGreaterEqual(len(archivos), 1)
        self.assertTrue(archivos[0].name.startswith("0001_"))
        for ruta in archivos:
            self.assertRegex(ruta.stem, r"^\d{4}_[a-z_]+$")
            self.assertTrue(ruta.read_text(encoding="utf-8").strip().endswith(";"))

    def test_la_migracion_inicial_crea_el_registro_de_versiones(self):
        contenido = (DIRECTORIO_MIGRACIONES / "0001_schema_migrations.sql").read_text(encoding="utf-8")
        self.assertIn("schema_migrations", contenido)


if __name__ == "__main__":
    unittest.main()
