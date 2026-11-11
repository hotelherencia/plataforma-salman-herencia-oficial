"""Verifica conteos documentales en DATABASE_URL (.env). Sin secretos en salida."""
from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def main() -> int:
    for line in (RAIZ / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("DATABASE_URL="):
            os.environ["DATABASE_URL"] = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
    import psycopg

    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=20) as c:
        print("migraciones", c.execute("SELECT count(*) FROM schema_migrations").fetchone()[0])
        print(
            "doc_hab_tar_ocu",
            c.execute("SELECT count(*) FROM doc_habitacion").fetchone()[0],
            c.execute("SELECT count(*) FROM doc_tarifa").fetchone()[0],
            c.execute("SELECT count(*) FROM doc_ocupacion_reportada").fetchone()[0],
        )
        print(
            "doc_control_reg",
            c.execute("SELECT count(*) FROM doc_control_ocupacion").fetchone()[0],
            c.execute("SELECT count(*) FROM doc_registro").fetchone()[0],
        )
        reales = c.execute(
            "SELECT id, tipo, capacidad, estado_operativo FROM habitaciones "
            "WHERE id NOT LIKE 'HAB-SINT-%' ORDER BY id"
        ).fetchall()
        print("operativo_reales_n", len(reales))
        print("operativo_reales", reales)
        print(
            "sinteticas",
            c.execute(
                "SELECT id, estado_operativo FROM habitaciones WHERE id LIKE 'HAB-SINT-%' ORDER BY id"
            ).fetchall(),
        )
        print(
            "tarifas_doc",
            c.execute(
                "SELECT tarifa_id, tipo_comercial, monto_clp, aprobada_2027, publicar_activa "
                "FROM doc_tarifa ORDER BY tarifa_id"
            ).fetchall(),
        )
        print(
            "ocu_ene",
            c.execute(
                "SELECT habitacion_id, valor_reportado FROM doc_ocupacion_reportada "
                "WHERE periodo='2026-01' ORDER BY habitacion_id"
            ).fetchall(),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
