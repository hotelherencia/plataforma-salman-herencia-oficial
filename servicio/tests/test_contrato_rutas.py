"""DOC-W16 (auditoría 2026-11-16): la tabla de operaciones de spec-api-v1
coincide con las rutas que expone el código (ni más ni menos)."""
import re
import unittest
from pathlib import Path

from servicio.aplicacion import crear_app

RAIZ = Path(__file__).resolve().parents[2]
_PATRON = re.compile(
    r"## Operaciones de esta versión \((\d+)\)\n\n\| Operación \| Efecto \|\n\|---\|---\|\n(.*?)(?=\n## )", re.S
)


def _normalizar(operacion: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", operacion.split("?")[0].strip())


class ContratoRutasTest(unittest.TestCase):
    def test_tabla_de_operaciones_igual_a_las_rutas(self):
        spec = (RAIZ / "docs/arquitectura/spec-api-v1.md").read_text(encoding="utf-8")
        m = _PATRON.search(spec)
        self.assertIsNotNone(m, "tabla de operaciones no localizable")
        tabla = {
            _normalizar(f)
            for f in re.findall(r"^\| `((?:GET|POST|PUT|DELETE) [^`]+)`", m.group(2), re.M)
        }
        codigo = {
            _normalizar(f"{metodo.upper()} {ruta}")
            for ruta, ops in crear_app().openapi()["paths"].items()
            for metodo in ops
        }
        self.assertEqual(sorted(codigo - tabla), [], "rutas sin fila en spec-api-v1")
        self.assertEqual(sorted(tabla - codigo), [], "filas de spec-api-v1 sin ruta")
        self.assertEqual(int(m.group(1)), len(codigo))


if __name__ == "__main__":
    unittest.main()
