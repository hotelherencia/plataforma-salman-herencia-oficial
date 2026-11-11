"""Sincroniza variables de producción desde .env sin imprimir secretos.

Topología actual (T4 proxy): front en Vercel → /api/* → Railway.
Uso (raíz del repo):
  python scripts/sincronizar_env_despliegue.py
  python scripts/sincronizar_env_despliegue.py --front-url https://plataforma-salman-herencia-oficial.vercel.app
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def leer_env(ruta: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def correr(cmd: list[str], env: dict[str, str], stdin: str | None = None) -> None:
    resultado = subprocess.run(
        cmd, env=env, input=stdin, capture_output=True, text=True
    )
    if resultado.returncode != 0:
        err = (resultado.stderr or resultado.stdout or "").strip()
        raise SystemExit(f"falló {' '.join(cmd[:4])}…: {err[:400]}")


def principal() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=".env")
    parser.add_argument(
        "--front-url",
        default="https://plataforma-salman-herencia-oficial.vercel.app",
    )
    parser.add_argument("--railway-service", default="")
    parser.add_argument("--skip-vercel", action="store_true")
    args = parser.parse_args()

    env_local = leer_env(Path(args.env))
    front = args.front_url.rstrip("/")
    faltan = [
        k
        for k in (
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "ADMIN_USUARIO",
            "ADMIN_CLAVE",
            "ADMIN_EMAIL",
        )
        if not env_local.get(k)
    ]
    if faltan:
        raise SystemExit(f"faltan en .env: {', '.join(faltan)}")

    railway_vars = {
        "COOKIE_SEGURA": "1",
        "SESSION_HORAS": env_local.get("SESSION_HORAS", "12"),
        "ORIGEN_FRONT": front,
        "FRONT_URL": front,
        "GOOGLE_REDIRECT_URI": f"{front}/api/auth/google/callback",
        "GOOGLE_CLIENT_ID": env_local["GOOGLE_CLIENT_ID"],
        "GOOGLE_CLIENT_SECRET": env_local["GOOGLE_CLIENT_SECRET"],
        "ADMIN_USUARIO": env_local["ADMIN_USUARIO"],
        "ADMIN_CLAVE": env_local["ADMIN_CLAVE"],
        "ADMIN_EMAIL": env_local["ADMIN_EMAIL"],
        "SERVICIO_HOST": "0.0.0.0",
    }

    entorno = os.environ.copy()
    token = env_local.get("RAILWAY_TOKEN") or os.environ.get("RAILWAY_TOKEN")
    if token:
        entorno["RAILWAY_TOKEN"] = token

    print(f"Railway: fijando {len(railway_vars)} variables (valores omitidos)")
    for clave, valor in railway_vars.items():
        cmd = ["railway", "variable", "set", f"{clave}={valor}", "--skip-deploys"]
        if args.railway_service:
            cmd.extend(["--service", args.railway_service])
        correr(cmd, entorno)
        print(f"  ok {clave}")

    if args.skip_vercel:
        print("Vercel: omitido")
        return 0

    vercel_token = env_local.get("VERCEL_TOKEN") or os.environ.get("VERCEL_TOKEN")
    if not vercel_token:
        print("VERCEL_TOKEN ausente: se omite sync del front")
        return 0

    entorno["VERCEL_TOKEN"] = vercel_token
    print("Vercel front: API_BASE_URL=/api (production)")
    # Actualiza si existe; si no, agrega. Sin echo del valor en logs propios.
    actualizar = subprocess.run(
        [
            "vercel",
            "env",
            "update",
            "API_BASE_URL",
            "production",
            "--token",
            vercel_token,
            "--cwd",
            "front",
            "--yes",
        ],
        env=entorno,
        input="/api\n",
        capture_output=True,
        text=True,
    )
    if actualizar.returncode != 0:
        correr(
            [
                "vercel",
                "env",
                "add",
                "API_BASE_URL",
                "production",
                "--token",
                vercel_token,
                "--cwd",
                "front",
                "--yes",
            ],
            entorno,
            stdin="/api\n",
        )
    print("  ok API_BASE_URL")
    print("listo (sin secretos en stdout)")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
