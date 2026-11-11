#!/usr/bin/env bash
set -euo pipefail
ROOT="/mnt/f/Code/plataforma-salman-herencia-oficial-main/plataforma-salman-herencia-oficial-main"
cd "$ROOT"

# Carga .env a entorno (sin imprimir)
set -a
# shellcheck disable=SC1091
source <(python3 - <<'PY'
from pathlib import Path
for line in Path(".env").read_text(encoding="utf-8", errors="ignore").splitlines():
    if not line or line.lstrip().startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    k = k.strip()
    v = v.strip().strip('"').strip("'").replace("'", "'\\''")
    print(f"export {k}='{v}'")
PY
)
set +a

export EMPRESA_TITULAR=1
export INVENTARIO_DOCUMENTAL=1
export EMPRESA_ES_SINTETICA=0
export EMPRESA_RUT="${EMPRESA_RUT:-76.707.504-9}"
export PYTHONPATH="$ROOT"
export SERVICIO_HOST="${SERVICIO_HOST:-127.0.0.1}"
export SERVICIO_PUERTO="${SERVICIO_PUERTO:-8080}"

exec python3 -m servicio
