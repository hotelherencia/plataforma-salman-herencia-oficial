#!/usr/bin/env python3
"""
Ejecutor de pruebas de base de datos PostgreSQL para Plataforma Salman.
Aplica esquemas DDL, comprueba RLS, restricciones CHECK/UNIQUE y concurrencia.
"""
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PRUEBAS_DIR = ROOT / "docs/arquitectura/pruebas"
RES_DIR = PRUEBAS_DIR / "resultados"
RES_DIR.mkdir(parents=True, exist_ok=True)

CONTAINER = "salman_pg_tmp"

test_files = [
    ("Inicializacion de Roles y Extensiones", PRUEBAS_DIR / "sql/00_init_roles_schemas.sql"),
    ("DDL Core", PRUEBAS_DIR / "sql/01_core.sql"),
    ("DDL Cafeteria", PRUEBAS_DIR / "sql/02_cafeteria.sql"),
    ("DDL Hotel", PRUEBAS_DIR / "sql/03_hotel.sql"),
    ("DDL Inmobiliaria", PRUEBAS_DIR / "sql/04_inmobiliaria.sql"),
    ("DDL Constructora", PRUEBAS_DIR / "sql/05_constructora.sql"),
    ("Pruebas de Integridad y Restricciones CHECK", PRUEBAS_DIR / "integridad/test_constraints_fks.sql"),
    ("Pruebas de Aislamiento Tenant y RLS (app_user)", PRUEBAS_DIR / "aislamiento-tenant/test_rls_policies.sql"),
    ("Pruebas de Concurrencia y Control Optimista", PRUEBAS_DIR / "concurrencia/test_concurrency_locks.sql"),
]

log_lines = []
all_passed = True

print(f"Iniciando ejecucion de pruebas en contenedor Docker '{CONTAINER}'...")

for label, fpath in test_files:
    if not fpath.is_file():
        msg = f"[FAIL] Archivo no encontrado: {fpath}"
        print(msg)
        log_lines.append(msg)
        all_passed = False
        continue

    content = fpath.read_text()
    proc = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-v", "ON_ERROR_STOP=1"],
        input=content,
        text=True,
        capture_output=True
    )
    
    if proc.returncode == 0:
        msg = f"[PASS] {label}"
        print(msg)
        log_lines.append(msg)
        if proc.stdout.strip():
            log_lines.append("STDOUT:\n" + proc.stdout.strip())
        if proc.stderr.strip():
            log_lines.append("STDERR:\n" + proc.stderr.strip())
    else:
        msg = f"[FAIL] {label} (exit code: {proc.returncode})"
        print(msg)
        print("STDERR:\n", proc.stderr)
        log_lines.append(msg)
        log_lines.append("ERROR:\n" + proc.stderr)
        all_passed = False

log_file = RES_DIR / "ejecucion_postgresql.log"
log_file.write_text("\n".join(log_lines) + "\n")
print(f"Log detallado guardado en: {log_file}")

if not all_passed:
    sys.exit(1)
print("Todas las pruebas de esquema, restricciones, RLS y concurrencia PASARON exitosamente.")
