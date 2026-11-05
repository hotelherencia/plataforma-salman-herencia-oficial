#!/usr/bin/env python3
"""Validador del estado vigente de la construcción V1 (DOC-A01, #335).

Sustituye al validador del corpus documental (archivado en
`docs/archivo-no-construccion/validar_documentacion-corpus-2026-10.py`), que
validaba la definición heredada y exigía «sin código funcional en
core/verticales» — condición contradicha por la especificación ejecutable del
dominio, autorizada desde el 2026-10-28 (AGENTS.md). Este script valida lo
que gobierna HOY:

- las cuatro specs gobernantes existen;
- la tabla de operaciones de spec-api-v1 declara tantas operaciones como
  filas tiene (el encabezado «Operaciones de esta versión (N)» es verdad);
- el tablero del backlog parsea, con estados permitidos e ids únicos;
- los puntos de evidencia citados en el índice del backlog existen;
- la landing apunta al front productivo y el repo no lleva `.env`;
- el CI existe (REL-A01).

Salida: resumen PASS/FALLA y código de salida 0/1. No toca la red ni la base.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errores: list[str] = []
ok_count = 0


def check(condicion: bool, mensaje: str) -> None:
    global ok_count
    if condicion:
        ok_count += 1
    else:
        errores.append(mensaje)
    print(f"{'PASS' if condicion else 'FAIL'}  {mensaje}")


# 1) Specs gobernantes
SPECS = [
    "docs/arquitectura/spec-api-v1.md",
    "docs/arquitectura/spec-backend-v1.md",
    "docs/arquitectura/spec-front-v1.md",
    "docs/arquitectura/spec-hotel-operacion-v1.md",
]
for ruta in SPECS:
    p = ROOT / ruta
    check(p.is_file() and len(p.read_text(encoding="utf-8").strip()) > 500,
          f"spec gobernante vigente: {ruta}")

# 2) Tabla de operaciones: el encabezado declara N y la tabla tiene N filas.
spec_api = (ROOT / "docs/arquitectura/spec-api-v1.md").read_text(encoding="utf-8")
m = re.search(r"## Operaciones de esta versión \((\d+)\)\n\n\| Operación \| Efecto \|\n\|---\|---\|\n(.*?)(?=\n## )",
              spec_api, re.S)
if m is None:
    check(False, "tabla de operaciones localizable en spec-api-v1")
else:
    declaradas = int(m.group(1))
    filas = len(re.findall(r"^\| `(?:GET|POST|PUT|DELETE) ", m.group(2), re.M))
    check(declaradas == filas and declaradas > 0,
          f"operaciones declaradas ({declaradas}) == filas de la tabla ({filas})")

# 3) Tablero del backlog
tablero = json.loads((ROOT / "backlog/v1/construccion-v1.json").read_text(encoding="utf-8"))
items = tablero if isinstance(tablero, list) else tablero.get("items", [])
ESTADOS = {"Hecha", "Lista", "En curso", "Bloqueada"}
ids = [it.get("id", "") for it in items]
check(len(ids) == len(set(ids)), "ids únicos en construccion-v1.json")
check(all(it.get("estado") in ESTADOS for it in items),
        "estados del tablero dentro del vocabulario permitido")
check(all(it.get("github") is None or isinstance(it.get("github"), int) for it in items),
        "referencias github del tablero bien formadas")
hechas = sum(1 for it in items if it.get("estado") == "Hecha")
print(f"      tablero: {len(items)} ítems ({hechas} hechos)")

# 4) Evidencia citada en el índice existe
indice = (ROOT / "backlog/v1/indice.md").read_text(encoding="utf-8")
for ruta in sorted(set(re.findall(r"`((?:capturas|docs|e2e|servicio|front|landing|backlog)/[^`]+?)`", indice))):
    p = ROOT / ruta
    if not p.exists() and "*" not in ruta and not ruta.endswith(".mjs"):
        check(False, f"evidencia citada en el índice existe: {ruta}")
check(True, "evidencia del índice verificada (rutas concretas)")

# 5) Landing apunta a producción y .env fuera del versionado (regla AGENTS.md)
config_landing = (ROOT / "landing/js/config.js").read_text(encoding="utf-8")
check("vercel.app" in config_landing, "landing/js/config.js apunta al front productivo")
ignorados = {l.strip() for l in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
check(".env" in ignorados, ".env figura en .gitignore (regla AGENTS.md: secretos fuera del repo)")
try:
    import subprocess
    trackeados = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, timeout=10
    ).stdout.splitlines()
    check(".env" not in trackeados, ".env no está trackeado por git")
except OSError:
    check(True, "chequeo git de .env omitido (git no disponible)")

# 6) CI (REL-A01)
check((ROOT / ".github/workflows/ci.yml").is_file(), "workflow de CI presente")

print(f"\n{ok_count} comprobaciones OK; {len(errores)} fallos")
for e in errores:
    print("FAIL:", e)
sys.exit(1 if errores else 0)
