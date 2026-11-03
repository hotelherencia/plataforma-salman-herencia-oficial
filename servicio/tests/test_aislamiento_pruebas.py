"""Guard de aislamiento de la base de pruebas (v1-issue-11, 2026-11-03).

Los tests de servicio truncan y siembran una base compartida. Si otro
proceso escribe en la misma base al mismo tiempo (otro trabajo en el mismo
árbol, un backend E2E apuntado a la misma base), los fallos son flaky y
caros de diagnosticar (deadlocks TRUNCATE, 401 «sesión inválida», usuarios
borrados a mitad de prueba). Este guard convierte esa condición en un error
claro y temprano: antes de truncar, exige no haber otras conexiones activas
a la base de pruebas.
"""
import os
import unittest

import psycopg

from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)


class AislamientoDePruebasTest(unittest.TestCase):
    def test_pasa_cuando_solo_esta_la_conexion_propia(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)  # no debe lanzar

    def test_falla_con_mensaje_claro_si_hay_otro_cliente(self):
        conexion_propia = psycopg.connect(URL_TEST)
        otra = psycopg.connect(URL_TEST)
        try:
            with self.assertRaises(RuntimeError) as contexto:
                exigir_base_libre(conexion_propia)
            self.assertIn("aislar", str(contexto.exception))
        finally:
            otra.close()
            conexion_propia.close()

    def test_no_cuenta_conexiones_de_otras_bases(self):
        # Una conexión a otra base no debe disparar el guard.
        url_base = URL_TEST.rsplit("/", 1)[0] + "/postgres"
        with psycopg.connect(url_base) as otra_base, psycopg.connect(URL_TEST) as propia:
            exigir_base_libre(propia)  # no debe lanzar


if __name__ == "__main__":
    unittest.main()
