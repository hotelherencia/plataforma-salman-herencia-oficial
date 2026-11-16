"""En la BD local del .env: deja al admin sin TOTP de app (solo clave).

La plataforma de producción no se toca desde aquí. Sirve para integrar y
consultar /hotel/documental con el ADMIN del .env.

OBS-03 (auditoría 2026-11-16): guarda de destino. El script se niega a
correr si DATABASE_URL no apunta a un Postgres local (127.0.0.1, localhost,
::1 o socket Unix) y exige `--confirmar`. Así un .env con la URL de Railway
no puede dejar sin segundo factor al admin de producción.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

RAIZ = Path(__file__).resolve().parents[1]
HOSTS_LOCALES = frozenset({"127.0.0.1", "localhost", "::1"})


def es_destino_local(database_url: str) -> bool:
    """True solo si todos los hosts de la conexión son locales o sockets Unix."""
    try:
        datos = conninfo_to_dict(database_url)
    except psycopg.ProgrammingError:
        return False
    hosts = [h.strip() for h in (datos.get("host") or "").split(",")]
    hostaddr = [h.strip() for h in (datos.get("hostaddr") or "").split(",") if h.strip()]
    for host in hosts + hostaddr:
        if host == "" or host.startswith("/"):
            continue  # socket Unix local
        if host.lower() not in HOSTS_LOCALES:
            return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Quita el TOTP del admin en la base LOCAL")
    parser.add_argument("--confirmar", action="store_true", help="obligatorio: confirma la operación")
    args = parser.parse_args(argv)
    env: dict[str, str] = {}
    for line in (RAIZ / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    url = env.get("DATABASE_URL") or ""
    if not url or not es_destino_local(url):
        print("RECHAZADO: DATABASE_URL no es una base local; este script nunca toca producción", file=sys.stderr)
        return 3
    if not args.confirmar:
        print("Falta --confirmar (quita el segundo factor del admin en la base local)", file=sys.stderr)
        return 2
    admin = env["ADMIN_USUARIO"]
    with psycopg.connect(url, connect_timeout=15) as c:
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
