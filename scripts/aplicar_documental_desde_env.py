"""Aplica migraciones y siembra el paquete documental usando DATABASE_URL del .env.

No imprime secretos. Pensado para correrse en el mismo host que alcanza Postgres
(WSL si la URL es 127.0.0.1 y el motor vive ahí).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (RAIZ, RAIZ / "core" / "incremento1", RAIZ / "verticales" / "hotel" / "incremento1"):
    s = str(ruta)
    if s not in sys.path:
        sys.path.insert(0, s)


def cargar_env(ruta: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for linea in ruta.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not linea or linea.lstrip().startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> int:
    env = cargar_env(RAIZ / ".env")
    for k, v in env.items():
        os.environ.setdefault(k, v)

    # Forzar titular + documental en esta corrida (también escritos en .env).
    os.environ["EMPRESA_TITULAR"] = "1"
    os.environ["INVENTARIO_DOCUMENTAL"] = "1"
    os.environ.setdefault("EMPRESA_ES_SINTETICA", "0")
    os.environ.setdefault("EMPRESA_RUT", "76.707.504-9")

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("FALTA DATABASE_URL")
        return 2

    import psycopg
    from servicio.migracion import aplicar_migraciones
    from servicio import documental, inventario_documental

    print("aplicando_migraciones...")
    nuevas = aplicar_migraciones(url)
    print("migraciones_nuevas", nuevas or ["ninguna"])

    with psycopg.connect(url, connect_timeout=20) as conexion:
        n_mig = conexion.execute("SELECT count(*) FROM schema_migrations").fetchone()[0]
        print("total_migraciones", n_mig)

        r_inv = inventario_documental.sembrar_inventario_documental(
            conexion,
            establecimiento_id=inventario_documental.ESTABLECIMIENTO_HERENCIA,
        )
        print("inventario", r_inv)

        r_doc = documental.sembrar_paquete_documental(conexion)
        print("documental", {k: r_doc[k] for k in r_doc if k != "ya_cargado"}, "ya_cargado", r_doc.get("ya_cargado"))

        # Reetiquetado titular (idempotente; equivalente a 0017)
        for tabla in (
            "usuarios",
            "sesiones",
            "reservas",
            "claves_idempotencia",
            "solicitudes",
            "leads",
            "consultas_agente",
            "politica_agente",
            "mensajes_whatsapp",
        ):
            existe = conexion.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name=%s", (tabla,)
            ).fetchone()
            if existe:
                conexion.execute(
                    f"UPDATE {tabla} SET empresa_id = 'EMP-HERENCIA-001' "
                    "WHERE empresa_id = 'EMP-SINTETICA-001'"
                )

        resumen = documental.resumen(conexion)
        print("resumen_cargado", resumen.get("cargado"))
        print("conteos", resumen.get("conteos"))
        habs = conexion.execute(
            "SELECT count(*) FROM habitaciones WHERE id LIKE 'HAB-%' AND id NOT LIKE 'HAB-SINT-%'"
        ).fetchone()[0]
        sint = conexion.execute(
            "SELECT count(*) FROM habitaciones WHERE id LIKE 'HAB-SINT-%' AND estado_operativo='fuera_de_servicio'"
        ).fetchone()[0]
        print("habitaciones_reales", habs, "sinteticas_fuera", sint)
        conexion.commit()

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
