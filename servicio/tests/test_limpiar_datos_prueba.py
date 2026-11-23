from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import limpiar_datos_prueba as script  # noqa: E402


@dataclass
class _Desc:
    name: str


class _FakeCursor:
    def __init__(self, state: dict) -> None:
        self._state = state
        self._last_rows: list[tuple] = []
        self.description: list[_Desc] = []

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: object) -> None:
        sql_txt = query.as_string(None) if hasattr(query, "as_string") else str(query)
        self._state["queries"].append(sql_txt)
        if "information_schema.tables" in sql_txt:
            self._last_rows = [(t,) for t in self._state["tables"]]
            self.description = [_Desc("table_name")]
        elif sql_txt.startswith("SELECT COUNT(*) FROM "):
            tabla = sql_txt.split('"')[1]
            self._last_rows = [(len(self._state["data"].get(tabla, [])),)]
            self.description = [_Desc("count")]
        elif sql_txt.startswith("SELECT * FROM "):
            tabla = sql_txt.split('"')[1]
            filas = self._state["data"].get(tabla, [])
            cols = list(filas[0].keys()) if filas else ["id"]
            self.description = [_Desc(c) for c in cols]
            self._last_rows = [tuple(f[c] for c in cols) for f in filas]
        elif sql_txt.startswith("TRUNCATE TABLE "):
            self._state["truncated"].append(sql_txt)
            self._last_rows = []
            self.description = []

    def fetchall(self) -> list[tuple]:
        return self._last_rows

    def fetchone(self) -> tuple:
        return self._last_rows[0]


class _FakeConn:
    def __init__(self, tables: list[str], data: dict[str, list[dict]]) -> None:
        self.state = {"tables": tables, "data": data, "queries": [], "truncated": [], "committed": False}

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self.state)

    def commit(self) -> None:
        self.state["committed"] = True


def test_listas_sin_solapamiento_y_config_protegida() -> None:
    overlap = set(script.TABLAS_DEPURAR) & set(script.TABLAS_CONSERVAR)
    assert not overlap, f"Tablas duplicadas en ambas listas: {overlap}"
    for esencial in ("schema_migrations", "usuarios", "habitaciones", "tipos_habitacion", "tarifas", "politicas_hotel", "productos"):
        assert esencial in script.TABLAS_CONSERVAR
        assert esencial not in script.TABLAS_DEPURAR


def test_ejecutar_requiere_confirmacion_exacta() -> None:
    rc = script.main(["--ejecutar", "--database-url", "postgresql://fake"])
    assert rc == 2


def test_dry_run_no_trunca_ni_respalda(tmp_path: Path) -> None:
    fake = _FakeConn(
        tables=["usuarios", "reservas", "caja_movimientos"],
        data={"usuarios": [{"id": 1}], "reservas": [{"id": 10}], "caja_movimientos": [{"id": 20}]},
    )
    with patch.object(script.psycopg, "connect", return_value=fake):
        rc = script.main(["--database-url", "postgresql://fake", "--respaldo-dir", str(tmp_path / "bkp")])
    assert rc == 0
    assert fake.state["truncated"] == []
    assert not (tmp_path / "bkp").exists()


def test_ejecutar_respalda_json_y_trunca_solo_operativas(tmp_path: Path) -> None:
    fake = _FakeConn(
        tables=["usuarios", "reservas", "pagos", "caja_movimientos"],
        data={
            "usuarios": [{"id": 1, "correo": "admin@hotel.cl"}],
            "reservas": [{"id": 10, "estado": "confirmada"}],
            "pagos": [{"id": 5, "monto": 50000}],
            "caja_movimientos": [],
        },
    )
    bkp_dir = tmp_path / "respaldo"
    with patch.object(script.psycopg, "connect", return_value=fake):
        rc = script.main([
            "--ejecutar",
            "--confirmar",
            script.CONFIRMACION_REQUERIDA,
            "--database-url",
            "postgresql://fake",
            "--respaldo-dir",
            str(bkp_dir),
        ])
    assert rc == 0
    assert fake.state["committed"] is True
    assert len(fake.state["truncated"]) == 1
    truncate_sql = fake.state["truncated"][0]
    assert '"reservas"' in truncate_sql
    assert '"pagos"' in truncate_sql
    assert '"caja_movimientos"' in truncate_sql
    assert '"usuarios"' not in truncate_sql
    assert (bkp_dir / "reservas.json").exists()
    assert (bkp_dir / "pagos.json").exists()
