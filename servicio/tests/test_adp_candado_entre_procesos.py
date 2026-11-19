"""El dominio vive en memoria de cada proceso y numera sus ids sobre lo que lee de la base. Dos instancias que
operan a la vez podrían numerar igual y chocar en la clave primaria. Un candado de PostgreSQL por transacción
serializa las operaciones del hotel entre procesos: la segunda recarga ya con lo que la primera confirmó."""
import os
import unittest

import psycopg

from servicio import hotel_sql, migracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)


class CandadoEntreProcesosTest(unittest.TestCase):
    def setUp(self):
        migracion.aplicar_migraciones(URL_TEST)

    def intentar(self, conexion) -> bool:
        return conexion.execute("SELECT pg_try_advisory_xact_lock(%s)", (hotel_sql.CLAVE_BLOQUEO,)).fetchone()[0]

    def test_mientras_una_transaccion_opera_otra_no_entra_y_al_confirmar_si(self):
        with psycopg.connect(URL_TEST) as a, psycopg.connect(URL_TEST) as b:
            hotel_sql.bloquear(a)
            self.assertFalse(self.intentar(b))
            b.rollback()
            a.commit()
            self.assertTrue(self.intentar(b))

    def test_es_reentrante_en_la_misma_transaccion(self):
        with psycopg.connect(URL_TEST) as a:
            hotel_sql.bloquear(a)
            hotel_sql.bloquear(a)  # no se bloquea a sí misma


if __name__ == "__main__":
    unittest.main()
