"""Valida login productivo con ADMIN_* del .env (sin imprimir secretos)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://plataforma-salman-herencia-oficial.vercel.app/api"
ORIGEN = "https://plataforma-salman-herencia-oficial.vercel.app"


def leer_env(ruta: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def principal() -> int:
    env = leer_env(ROOT / ".env")
    usuario = env.get("ADMIN_USUARIO")
    clave = env.get("ADMIN_CLAVE")
    if not usuario or not clave:
        print("FALTA ADMIN_USUARIO/ADMIN_CLAVE en .env")
        return 2

    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def call(method: str, path: str, body: dict | None = None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            BASE + path,
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "Origin": ORIGEN,
                "Accept": "application/json",
                "Referer": ORIGEN + "/login",
            },
        )
        try:
            with opener.open(req, timeout=30) as resp:
                return resp.status, resp.read().decode(), dict(resp.headers.items())
        except urllib.error.HTTPError as err:
            return err.code, err.read().decode(), dict(err.headers.items())

    s0, b0, _ = call("GET", "/sesion")
    print(f"GET_sin_cookie={s0} body={b0[:120]}")

    s1, b1, h1 = call("POST", "/sesion", {"usuario": usuario, "clave": clave})
    print(f"POST_login={s1} body={b1[:220]}")
    set_cookie = h1.get("Set-Cookie") or h1.get("set-cookie") or ""
    print(f"set_cookie_presente={bool(set_cookie)}")
    if set_cookie:
        attrs = [parte.strip().split("=", 1)[0] for parte in set_cookie.split(";")]
        print("set_cookie_attrs=" + ",".join(attrs))
    cookies = [(c.name, c.secure, c.path) for c in jar]
    print(f"cookies={cookies}")

    s2, b2, _ = call("GET", "/sesion")
    print(f"GET_con_cookie={s2} body={b2[:220]}")

    s3, b3, _ = call("GET", "/salud")
    print(f"GET_salud={s3} body={b3[:220]}")

    salud = {}
    try:
        salud = json.loads(b3) if b3 else {}
    except json.JSONDecodeError:
        pass
    login = {}
    try:
        login = json.loads(b1) if b1 else {}
    except json.JSONDecodeError:
        pass
    if (
        s1 == 200
        and login.get("empresa_id")
        and salud.get("empresa")
        and login["empresa_id"] != salud["empresa"]
    ):
        print(
            "diagnostico=nucleo_distinto_de_sesion "
            f"login_empresa={login['empresa_id']} salud_empresa={salud['empresa']}"
        )

    ok = (
        s1 == 200
        and s2 == 200
        and any(c.name == "sid" for c in jar)
        and salud.get("empresa") == login.get("empresa_id")
        and not salud.get("es_sintetica", True)
    )
    print("resultado=" + ("OK" if ok else "FALLA"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(principal())
