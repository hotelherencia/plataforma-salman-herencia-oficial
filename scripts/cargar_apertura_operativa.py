#!/usr/bin/env python3
"""CLI idempotente de carga inicial operativa y migración de apertura (F20 / MIG-002..006).

Uso:
  python scripts/cargar_apertura_operativa.py --dry-run \
      --inventarios docs/operacion/migracion-apertura/inventario_inicial_ejemplo.csv \
      --incidencias docs/operacion/migracion-apertura/incidencias_iniciales_ejemplo.csv \
      --reservas docs/operacion/migracion-apertura/reservas_y_anticipos_corte_2026_12_31_plantilla.csv

  python scripts/cargar_apertura_operativa.py --aplicar ...

Reglas de seguridad:
- Por defecto corre en `--dry-run` (nunca modifica la BD si no se pasa `--aplicar` explícitamente).
- Nunca imprime valores de variables de entorno ni credenciales.
- La auditoría no persiste PII.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import psycopg  # noqa: E402

from servicio import aplicacion, carga_apertura, migracion  # noqa: E402
from servicio.empresa_titular import EMPRESA_TITULAR  # noqa: E402


def parsear_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Carga inicial operativa idempotente (F20 / MIG-002..006) con acta de validación."
    )
    grupo_modo = parser.add_mutually_exclusive_group()
    grupo_modo.add_argument("--dry-run", action="store_true", help="Valida los CSV y emite acta sin escribir (por defecto).")
    grupo_modo.add_argument("--aplicar", action="store_true", help="Aplica los CSV validados de forma idempotente.")
    parser.add_argument("--inventarios", type=Path, default=None, help="Ruta a CSV saneado de inventarios iniciales (0055).")
    parser.add_argument("--incidencias", type=Path, default=None, help="Ruta a CSV saneado de incidencias iniciales (0059).")
    parser.add_argument("--reservas", type=Path, default=None, help="Ruta a CSV saneado de reservas futuras y anticipos al 31-12-2026.")
    parser.add_argument("--empresa-id", default=EMPRESA_TITULAR.id, help="Identificador de la empresa en la BD.")
    parser.add_argument("--actor", default="migracion_apertura", help="Actor registrado en auditoría.")
    parser.add_argument("--database-url", default=None, help="URL PostgreSQL explícita (si se omite usa DATABASE_URL).")
    parser.add_argument("--acta-salida", type=Path, default=None, help="Ruta opcional para guardar el acta JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parsear_args(argv)
    if not (args.inventarios or args.incidencias or args.reservas):
        print("Error: indica al menos un archivo (--inventarios, --incidencias o --reservas).", file=sys.stderr)
        return 2
    db_url = args.database_url or os.environ.get("DATABASE_URL")
    if not db_url:
        print("Error: define DATABASE_URL o pasa --database-url.", file=sys.stderr)
        return 2

    migracion.aplicar_migraciones(db_url)
    app_dom = aplicacion.construir_aplicacion()
    from servicio import hotel_sql
    hotel_sql.registrar(app_dom.hotel)

    with psycopg.connect(db_url) as conexion:
        acta = carga_apertura.ejecutar_apertura(
            conexion,
            args.empresa_id,
            inventarios_csv=args.inventarios,
            incidencias_csv=args.incidencias,
            reservas_csv=args.reservas,
            aplicar=bool(args.aplicar),
            actor=args.actor,
            nucleo=app_dom.nucleo,
            hotel=app_dom.hotel,
        )
        if args.aplicar and acta["aprobado"]:
            conexion.commit()
        else:
            conexion.rollback()

    salida_json = json.dumps(acta, ensure_ascii=False, indent=2)
    if args.acta_salida:
        args.acta_salida.parent.mkdir(parents=True, exist_ok=True)
        args.acta_salida.write_text(salida_json + "\n", encoding="utf-8")
    print(salida_json)
    return 0 if acta["aprobado"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
