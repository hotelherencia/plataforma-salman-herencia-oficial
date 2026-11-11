"""En la BD local del .env: deja al admin sin TOTP de app (solo clave).

La plataforma de producción no se toca desde aquí. Sirve para integrar y
consultar /hotel/documental con el ADMIN del .env.
"""
from __future__ import annotations

import os
from pathlib import Path

import psycopg

RAIZ = Path(__file__).resolve().parents[1]


def main() -> int:
    env: dict[str, str] = {}
    for line in (RAIZ / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    admin = env["ADMIN_USUARIO"]
    with psycopg.connect(env["DATABASE_URL"], connect_timeout=15) as c:
        c.execute(
            "UPDATE usuarios SET totp_activado = FALSE, totp_secreto = NULL, "
            "totp_secreto_pendiente = NULL WHERE nombre = %s",
            (admin,),
        )
        c.commit()
        fila = c.execute(
            "SELECT nombre, totp_activado FROM usuarios WHERE nombre = %s", (admin,)
        ).fetchone()
        print("admin_totp", fila)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
