"""Lista las variables de despliegue tomando valores del `.env` local.

Se ejecuta en la máquina del propietario (el agente nunca lee `.env`,
política de secretos). Imprime pares CLAVE=valor listos para pegar en el
dashboard de Vercel/Railway y marca lo que parece del entorno local
(localhost/127.0.0.1) o lo que falta en `.env`.

Uso (desde la raíz del repo):
  python scripts/mapear_variables_despliegue.py t4b --dominio https://<dominio>
  python scripts/mapear_variables_despliegue.py t4 --railway https://<api> --front https://<front>

La salida contiene secretos: no compartirla ni capturarla.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

LOCAL = re.compile(r"localhost|127\.0\.0\.1", re.IGNORECASE)


def leer_env(ruta: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    if not ruta.is_file():
        return valores
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def principal() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modo", choices=["t4", "t4b"])
    parser.add_argument("--env", default=".env", help="ruta del .env local")
    parser.add_argument("--dominio", help="https://<dominio> del front (t4b)")
    parser.add_argument("--railway", help="https://<url-api> del backend (t4)")
    parser.add_argument("--front", help="https://<url-front> en Vercel (t4)")
    args = parser.parse_args()

    if args.modo == "t4b" and not args.dominio:
        parser.error("t4b exige --dominio")
    if args.modo == "t4" and not (args.railway and args.front):
        parser.error("t4 exige --railway y --front")

    env = leer_env(Path(args.env))
    filas: list[tuple[str, str | None, str]] = []

    def tomar(clave: str, produccion: str | None = None, nota: str = "") -> None:
        filas.append((clave, produccion if produccion is not None else env.get(clave), nota))

    tomar("DATABASE_URL", nota="PostgreSQL del entorno (externo en t4b)")
    tomar("ADMIN_USUARIO")
    tomar("ADMIN_CLAVE", nota="rotar tras el primer login productivo")
    tomar("ADMIN_EMAIL")
    tomar("GOOGLE_CLIENT_ID")
    tomar("GOOGLE_CLIENT_SECRET")
    tomar("COOKIE_SEGURA", produccion="1")
    if "SESSION_HORAS" in env:
        tomar("SESSION_HORAS")

    if args.modo == "t4b":
        print("# Proyecto Vercel canónico (t4b: front y API en el mismo dominio)")
        tomar("API_BASE_URL", produccion="/api", nota="variable de build del front")
        tomar("GOOGLE_REDIRECT_URI", produccion=f"{args.dominio}/api/auth/google/callback",
              nota="registrarla también en Cloud Console")
        tomar("FRONT_URL", produccion=args.dominio)
    else:
        print("# Servicio en Railway (t4)")
        tomar("GOOGLE_REDIRECT_URI", produccion=f"{args.railway}/auth/google/callback",
              nota="registrarla también en Cloud Console")
        tomar("SERVICIO_HOST", produccion="0.0.0.0")
        tomar("ORIGEN_FRONT", produccion=args.front)
        tomar("FRONT_URL", produccion=args.front)

    for clave, valor, nota in filas:
        if valor is None or valor == "":
            marca = "FALTA EN .ENV"
        elif LOCAL.search(valor):
            marca = "¡REVISAR! parece local; no copiar tal cual a producción"
        else:
            marca = ""
        detalle = " | ".join(p for p in (nota, marca) if p)
        print(f"{clave}={valor or ''}" + (f"   # {detalle}" if detalle else ""))

    if args.modo == "t4":
        print("\n# Front en Vercel (variable de build, en el proyecto del front)")
        print(f"API_BASE_URL={args.railway}")

    print("\n# Recordatorio: la salida de este script contiene secretos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
