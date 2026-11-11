from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import psycopg

RAIZ = Path(__file__).resolve().parents[1]


def env() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (RAIZ / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> int:
    e = env()
    base = "http://127.0.0.1:8080"
    body = json.dumps({"usuario": e["ADMIN_USUARIO"], "clave": e["ADMIN_CLAVE"]}).encode()
    req = urllib.request.Request(
        base + "/sesion", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print("login_ok", r.read().decode()[:300])
    except Exception as err:
        print("login_fail", getattr(err, "code", type(err).__name__))
        if hasattr(err, "read"):
            print(err.read().decode()[:500])
    with psycopg.connect(e["DATABASE_URL"], connect_timeout=15) as c:
        print("usuarios", c.execute("SELECT nombre, rol, empresa_id, activo FROM usuarios ORDER BY nombre").fetchall())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
