#!/usr/bin/env bash
set -euo pipefail
ROOT="/mnt/f/Code/plataforma-salman-herencia-oficial-main/plataforma-salman-herencia-oficial-main"
ENV_FILE="$ROOT/.env"
cd "$ROOT"

# Extrae DATABASE_URL del .env sin eco
URL="$(python3 - <<'PY'
from pathlib import Path
for line in Path(".env").read_text(encoding="utf-8", errors="ignore").splitlines():
    if line.startswith("DATABASE_URL="):
        print(line.split("=", 1)[1].strip().strip('"').strip("'"))
        break
PY
)"
if [[ -z "${URL}" ]]; then
  echo "FALTA DATABASE_URL"
  exit 2
fi

export DATABASE_URL="$URL"
export EMPRESA_TITULAR=1
export INVENTARIO_DOCUMENTAL=1
export EMPRESA_ES_SINTETICA=0
export EMPRESA_RUT=76.707.504-9

pg_isready -h 127.0.0.1 -p 5432

# Asegura rol/base de desarrollo (idempotente)
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='plataforma'" | grep -q 1; then
  sudo -u postgres createuser -s plataforma || true
fi
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='plataforma_dev'" | grep -q 1; then
  sudo -u postgres createdb -O plataforma plataforma_dev || sudo -u postgres createdb plataforma_dev
fi

python3 -c 'import psycopg' 2>/dev/null || pip3 install --user 'psycopg[binary]' -q

export PYTHONPATH="$ROOT"
python3 scripts/aplicar_documental_desde_env.py
