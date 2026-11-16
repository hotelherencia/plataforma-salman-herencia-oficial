"""Comando explícito de migraciones (NEW-01): `python -m servicio.migrar`.

Aplica las migraciones pendientes contra DATABASE_URL (variable de entorno o
.env local ignorado por git) y termina. No crea usuarios ni siembra
inventario. Pensado para el pre-deploy de Railway o para correrlo a mano
antes de poner `MIGRAR_AL_ARRANCAR=0` en Vercel. No imprime secretos.
"""
import argparse
import sys

from .configuracion import cargar_desde_entorno
from .migracion import aplicar_migraciones, migraciones_pendientes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revisar", action="store_true", help="solo lista las pendientes, sin aplicar")
    args = parser.parse_args(argv)
    config = cargar_desde_entorno()
    if not config.database_url:
        print("FALTA DATABASE_URL", file=sys.stderr)
        return 2
    if args.revisar:
        pendientes = migraciones_pendientes(config.database_url)
        print("pendientes", pendientes or ["ninguna"])
        return 1 if pendientes else 0
    nuevas = aplicar_migraciones(config.database_url)
    print("migraciones_nuevas", nuevas or ["ninguna"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
