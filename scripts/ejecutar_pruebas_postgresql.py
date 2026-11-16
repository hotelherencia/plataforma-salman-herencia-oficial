#!/usr/bin/env python3
"""OBSOLETO (NEW-02, auditoría 2026-11-16).

Este script ejecutaba SQL de `docs/arquitectura/pruebas/` dentro de un
contenedor Docker `salman_pg_tmp`. Esa carpeta ya no existe en el
repositorio (el modelo multi-vertical de prueba se retiró), así que el
script fallaba siempre y daba la falsa impresión de una verificación de
base de datos.

La verificación vigente contra PostgreSQL real es:

    python3 scripts/verificar_local.py

que crea una base dedicada, aplica las migraciones de `servicio/migraciones/`
y corre la suite completa del servicio con pytest.
"""
import sys

if __name__ == "__main__":
    print(__doc__.strip(), file=sys.stderr)
    sys.exit(2)
