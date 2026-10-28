"""Runner de migraciones SQL numeradas sobre PostgreSQL.

Cada archivo `NNNN_nombre.sql` de `servicio/migraciones/` se aplica una sola
vez, en orden, dentro de una transacción; el avance queda en
`schema_migrations`. Nada se interpola: las migraciones son SQL fijo y los
valores van con parámetros.
"""
from pathlib import Path

import psycopg

DIRECTORIO_MIGRACIONES = Path(__file__).resolve().parent / "migraciones"


def aplicar_migraciones(database_url: str, directorio: Path = DIRECTORIO_MIGRACIONES) -> list[str]:
    archivos = sorted(directorio.glob("*.sql"))
    with psycopg.connect(database_url) as conexion:
        conexion.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, "
            "aplicada_en TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        aplicadas = {fila[0] for fila in conexion.execute("SELECT version FROM schema_migrations").fetchall()}
        nuevas: list[str] = []
        for ruta in archivos:
            version = ruta.stem
            if version in aplicadas:
                continue
            conexion.execute(ruta.read_text(encoding="utf-8"))
            conexion.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            nuevas.append(version)
        conexion.commit()
    return nuevas
