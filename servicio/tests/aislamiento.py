"""Guard de aislamiento para los tests del servicio (v1-issue-11).

Antes de truncar la base de pruebas, exige que no haya otras conexiones
activas a la misma base: si otro proceso escribe concurrentemente (otro
trabajo en el mismo árbol, un backend E2E apuntado a la misma base), los
tests fallan de forma flaky y difícil de diagnosticar. Con el guard, el
fallo es temprano y con mensaje claro; la corrida formal usa una base
dedicada (ver e2e/README.md).
"""
import gc
import time

import psycopg

# Gracia para conexiones del propio proceso que aún no se cierran (un
# TestClient o una conexión sin `with` del módulo anterior, liberada por el
# recolector). Un proceso ajeno que escribe de verdad sigue conectado mucho
# más que esto, así que el guard no se debilita (flaky visto el 2026-11-16).
GRACIA_SEGUNDOS = 3.0


def _otras_conexiones(conexion: psycopg.Connection) -> int:
    (otras,) = conexion.execute(
        "SELECT count(*) FROM pg_stat_activity "
        "WHERE datname = current_database() AND pid <> pg_backend_pid() AND state IS NOT NULL"
    ).fetchone()
    return otras


def exigir_base_libre(conexion: psycopg.Connection) -> None:
    """Lanza RuntimeError si hay otras conexiones activas a esta base de datos."""
    limite = time.monotonic() + GRACIA_SEGUNDOS
    otras = _otras_conexiones(conexion)
    while otras > 0 and time.monotonic() < limite:
        gc.collect()
        time.sleep(0.1)
        otras = _otras_conexiones(conexion)
    if otras > 0:
        raise RuntimeError(
            f"la base de pruebas tiene {otras} otra(s) conexión(es) activa(s): "
            "aislar la corrida con una base dedicada (DATABASE_URL_TEST) o detener "
            "al otro proceso antes de truncar (v1-issue-11)"
        )
