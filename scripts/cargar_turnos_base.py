#!/usr/bin/env python3
"""Genera la plantilla de turnos desde la hoja `Horario` y carga turnos semanales (#467).

  # 1) plantilla (sin base de datos; salida fuera del repo)
  python scripts/cargar_turnos_base.py plantilla "<libro>.xlsx" --salida /ruta/turnos_base.csv \
      --fin-contrato Maite=2026-12-31
  # 2) completar la columna `usuario` (nombre de cuenta en la plataforma), luego validar y cargar
  python scripts/cargar_turnos_base.py cargar /ruta/turnos_base.csv --desde 2026-12-01 --semanas 8 [--aplicar]

`cargar` necesita PYTHONPATH con core/incremento1 (igual que cargar_apertura_operativa.py) y valida por defecto (dry-run) y solo escribe con `--aplicar`. Nunca lee `Personal Vigente` ni `.env`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from servicio import turnos_base  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="orden", required=True)
    a = sub.add_parser("plantilla")
    a.add_argument("xlsx", type=Path)
    a.add_argument("--salida", type=Path, required=True)
    a.add_argument("--fin-contrato", action="append", default=[], metavar="NOMBRE=AAAA-MM-DD")
    b = sub.add_parser("cargar")
    b.add_argument("csv", type=Path)
    b.add_argument("--desde", type=date.fromisoformat, required=True)
    b.add_argument("--semanas", type=int, default=8)
    b.add_argument("--aplicar", action="store_true")
    b.add_argument("--empresa-id", default=None, help="Por defecto, la empresa titular.")
    b.add_argument("--actor", default="migracion_apertura")
    b.add_argument("--database-url", default=None)
    args = p.parse_args(argv)
    if args.orden == "plantilla":
        if RAIZ in args.salida.resolve().parents:
            print("Error: la salida no debe estar dentro del repositorio.", file=sys.stderr)
            return 2
        fines = dict(x.split("=", 1) for x in args.fin_contrato)
        filas = turnos_base.plantilla(args.xlsx, fines)
        turnos_base.escribir_plantilla(filas, args.salida)
        print(f"plantilla escrita: {len(filas)} turnos base; completa la columna `usuario`.")
        return 0
    url = args.database_url or os.environ.get("DATABASE_URL")
    if not url:
        print("Error: define DATABASE_URL o pasa --database-url.", file=sys.stderr)
        return 2
    import psycopg  # noqa: E402  (solo `cargar` necesita la base y el núcleo en el path)

    from servicio import migracion
    from servicio.empresa_titular import EMPRESA_TITULAR

    args.empresa_id = args.empresa_id or EMPRESA_TITULAR.id
    migracion.aplicar_migraciones(url)
    with psycopg.connect(url) as c:
        acta = turnos_base.cargar_turnos_csv(c, args.empresa_id, args.csv, args.desde, args.semanas,
                                             aplicar=args.aplicar, actor=args.actor)
        if args.aplicar and acta["aprobado"]:
            c.commit()
    print(json.dumps(acta, ensure_ascii=False, indent=2))
    return 0 if acta["aprobado"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
