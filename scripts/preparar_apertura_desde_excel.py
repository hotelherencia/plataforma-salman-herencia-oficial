#!/usr/bin/env python3
"""Convierte el Excel de levantamiento del hotel en CSV saneados para `cargar_apertura_operativa.py` (#468).

Uso:
  python scripts/preparar_apertura_desde_excel.py "Informacion General ... .xlsx" --salida /ruta/fuera/del/repo
  python scripts/cargar_apertura_operativa.py --dry-run --inventarios .../inventario_inicial.csv \
      --incidencias .../incidencias_iniciales.csv --activos .../activos_iniciales.csv
  # Revisar el acta; solo entonces, con autorización: repetir con --aplicar.

Este script no toca la base de datos y no lee la hoja `Redes`. Deja la salida fuera del repositorio:
los CSV llevan precios de proveedores y estado interno del hotel.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from servicio import apertura_excel  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("xlsx", type=Path)
    parser.add_argument("--salida", type=Path, required=True, help="Carpeta donde dejar los CSV (fuera del repo).")
    parser.add_argument("--proxima-mantencion", default="2026-12-15", help="Fecha ISO de la primera mantención anual.")
    args = parser.parse_args(argv)
    if RAIZ in args.salida.resolve().parents or args.salida.resolve() == RAIZ:
        print("Error: la salida no debe estar dentro del repositorio.", file=sys.stderr)
        return 2
    cuentas = apertura_excel.generar(args.xlsx, args.salida, args.proxima_mantencion)
    print(", ".join(f"{k}={v}" for k, v in cuentas.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
