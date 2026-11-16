#!/usr/bin/env python3
"""Verificación integral LOCAL previa al despliegue (REL-A01, orden del
propietario 2026-11-05: la verificación se hace en local, antes de desplegar;
GitHub Actions no aplica porque bloquea la construcción).

Un solo comando revisa TODO lo que la especificación manda verificar con
hechos antes de publicar:

1. estado del repo (scripts/validar_estado_v1.py: specs, contrato, tablero,
   evidencia, landing, `.env`, CI local);
2. dominio: las 5 raíces de la especificación ejecutable;
3. servicio: la suite completa con **pytest** contra una base DEDICADA
   creada al vuelo (satisface el guard de aislamiento v1-issue-11 sin apoyo
   manual). pytest recoge también las funciones estilo pytest que
   `unittest discover` se saltaba (AI-001 / SEC-010, auditoría 2026-11-16);
4. landing: unitarios del CTA y del formulario de leads;
5. front: build de producción (con API_BASE_URL horneado, como se despliega).

Dependencias: `uv sync --frozen` sobre `uv.lock` (las mismas versiones que
se despliegan; antes se instalaba desde requirements.txt sin lock) más
pytest fijado en PYTEST_VERSION, fuera del lock para no tocar el build de
Vercel.

Uso:  python3 scripts/verificar_local.py            (requiere `uv`)
Salida: resumen por paso y código 0 solo si TODO está en verde. Si algo
falla: revisar, evaluar y corregir antes de desplegar — no publicar en rojo.
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"
BASE = "postgresql://plataforma:plataforma@127.0.0.1:5432"
NOMBRE_BASE = f"verificacion_{int(time.time())}"
PYTEST_VERSION = "9.2.0"
# uv.lock declara requires-python >=3.13; uv descarga ese Python si el
# sistema solo trae otro (Ubuntu 24.04/WSL trae 3.12).
PYTHON_VERSION = "3.13"

fallos: list[str] = []


def paso(nombre: str, comando: list[str], cwd: Path = ROOT, env_extra: dict | None = None) -> bool:
    print(f"\n== {nombre} ==")
    env = os.environ.copy()
    env.update(env_extra or {})
    t0 = time.time()
    r = subprocess.run(comando, cwd=cwd, env=env)
    dur = time.time() - t0
    ok = r.returncode == 0
    print(f"== {nombre}: {'OK' if ok else 'FALLA'} ({dur:.0f}s) ==")
    if not ok:
        fallos.append(nombre)
    return ok


def preparar_entorno() -> bool:
    """`.venv` reproducible desde uv.lock (+ pytest fijado)."""
    uv = shutil.which("uv")
    if uv is None:
        print("FALTA: uv (https://docs.astral.sh/uv/). El verificador instala desde uv.lock.")
        return False
    print("== 0) dependencias: uv sync --frozen ==")
    if subprocess.run([uv, "sync", "--frozen", "--python", PYTHON_VERSION], cwd=ROOT).returncode != 0:
        print("uv sync --frozen falló: uv.lock no coincide con pyproject.toml o falta el Python pedido")
        return False
    instalar = [uv, "pip", "install", "--python", str(PYTHON), f"pytest=={PYTEST_VERSION}"]
    return subprocess.run(instalar, cwd=ROOT).returncode == 0


def main() -> int:
    if not preparar_entorno():
        return 1

    # 0) base dedicada para la suite del servicio
    print(f"== base dedicada: {NOMBRE_BASE} ==")
    subprocess.run(["psql", f"{BASE}/postgres", "-c", f"DROP DATABASE IF EXISTS {NOMBRE_BASE}"],
                   check=False, capture_output=True)
    creada = subprocess.run(
        ["psql", f"{BASE}/postgres", "-c", f"CREATE DATABASE {NOMBRE_BASE} OWNER plataforma"]
    )
    if creada.returncode != 0:
        print("No se pudo crear la base dedicada: ¿PostgreSQL en 127.0.0.1:5432 con rol plataforma?")
        return 1
    url_test = f"{BASE}/{NOMBRE_BASE}"

    try:
        paso("1) estado del repo (validar_estado_v1)",
             [sys.executable, "scripts/validar_estado_v1.py"])
        raices = [
            "core/incremento1",
            "verticales/hotel/incremento1",
            "verticales/cafeteria/incremento1",
            "verticales/inmobiliaria/incremento1",
            "verticales/constructora/incremento1",
        ]
        for raiz in raices:
            paso(f"2) dominio {raiz}",
                 [str(PYTHON), "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                 cwd=ROOT / raiz)
        paso("3) servicio (suite completa con pytest, base dedicada)",
             [str(PYTHON), "-m", "pytest", "servicio/tests", "-q", "-p", "no:cacheprovider"],
             env_extra={"DATABASE_URL_TEST": url_test})
        paso("4) landing unitarios", ["node", "--test", "landing/test/*.test.mjs"])
        env_front = os.environ.copy()
        env_front["API_BASE_URL"] = "http://127.0.0.1:8080"
        paso("5) front build de producción",
             ["bash", "-c", "npm ci --no-audit --no-fund && npm run build"],
             cwd=ROOT / "front", env_extra=env_front)
    finally:
        subprocess.run(["psql", f"{BASE}/postgres", "-c", f"DROP DATABASE IF EXISTS {NOMBRE_BASE} WITH (FORCE)"],
                       check=False, capture_output=True)

    print("\n===== RESUMEN =====")
    if fallos:
        print("FALLÓ:", "; ".join(fallos))
        print("Revisar, evaluar y corregir antes de desplegar. No publicar en rojo.")
        return 1
    print("TODO EN VERDE — la construcción está lista para desplegar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
