"""OBS-03: el script que quita el TOTP del admin solo corre contra una base local."""
import importlib.util
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _cargar(nombre: str):
    ruta = RAIZ / "scripts" / f"{nombre}.py"
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class GuardaTotpLocalTest(unittest.TestCase):
    def setUp(self):
        self.mod = _cargar("desactivar_totp_admin_local")

    def test_acepta_destinos_locales(self):
        for url in (
            "postgresql://u:p@127.0.0.1:5432/plataforma_dev",
            "postgresql://u:p@localhost/plataforma_dev",
            "postgresql://u:p@[::1]:5432/db",
            "postgresql:///plataforma_dev?host=/var/run/postgresql",
            "dbname=plataforma_dev host=127.0.0.1",
        ):
            with self.subTest(url=url):
                self.assertTrue(self.mod.es_destino_local(url))

    def test_rechaza_destinos_remotos(self):
        for url in (
            "postgresql://u:p@containers-us-west-1.railway.app:6543/railway",
            "postgresql://u:p@db.example.com/db",
            "postgresql://u:p@127.0.0.1,db.example.com/db",
            "postgresql://u:p@localhost.example.com/db",
            "host=10.0.0.5 dbname=x",
            "no es una url",
        ):
            with self.subTest(url=url):
                self.assertFalse(self.mod.es_destino_local(url))


if __name__ == "__main__":
    unittest.main()
