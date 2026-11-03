"""Guard de aislamiento para los tests del servicio (v1-issue-11).

Antes de truncar la base de pruebas, exige que no haya otras conexiones
activas a la misma base: si otro proceso escribe concurrentemente (otro
trabajo en el mismo árbol, un backend E2E apuntado a la misma base), los
tests fallan de forma flaky y difícil de diagnosticar. Con el guard, el
fallo es temprano y con mensaje claro; la corrida formal usa una base
dedicada (ver e2e/README.md).
"""
import psycopg


def exigir_base_libre(conexion: psycopg.Connection) -> None:
    """Lanza RuntimeError si hay otras conexiones activas a esta base de datos."""
    (otras,) = conexion.execute(
        "SELECT count(*) FROM pg_stat_activity "
        "WHERE datname = current_database() AND pid <> pg_backend_pid() AND state IS NOT NULL"
    ).fetchone()
    if otras > 0:
        raise RuntimeError(
            f"la base de pruebas tiene {otras} otra(s) conexión(es) activa(s): "
            "aislar la corrida con una base dedicada (DATABASE_URL_TEST) o detener "
            "al otro proceso antes de truncar (v1-issue-11)"
        )
