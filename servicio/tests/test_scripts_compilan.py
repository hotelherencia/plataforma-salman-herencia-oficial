"""Los scripts operativos deben al menos compilar: un `from __future__`
fuera de lugar dejó inutilizable la carga documental puntual (W16-A02)."""
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


class ScriptsCompilanTest(unittest.TestCase):
    def test_todos_los_scripts_compilan(self):
        for ruta in sorted((RAIZ / "scripts").glob("*.py")):
            with self.subTest(script=ruta.name):
                compile(ruta.read_text(encoding="utf-8"), str(ruta), "exec")


if __name__ == "__main__":
    unittest.main()
