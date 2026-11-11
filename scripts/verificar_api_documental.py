"""Login local y verifica /hotel/documental/* usando .env (sin imprimir secretos)."""
from __future__ import annotations

import json
import http.cookiejar
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def main() -> int:
    env: dict[str, str] = {}
    for line in (RAIZ / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    base = "http://127.0.0.1:8080"
    print("salud", urllib.request.urlopen(base + "/salud", timeout=10).read().decode())
    print("ready", urllib.request.urlopen(base + "/readiness", timeout=10).read().decode())
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    cuerpo = {"usuario": env["ADMIN_USUARIO"], "clave": env["ADMIN_CLAVE"]}
    secreto = env.get("ADMIN_TOTP_SECRETO") or ""
    if secreto:
        import sys
        from pathlib import Path as _P

        sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
        from servicio import totp as totp_mod

        cuerpo["totp"] = totp_mod.codigo(secreto)
    req = urllib.request.Request(
        base + "/sesion",
        data=json.dumps(cuerpo).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with op.open(req, timeout=15) as r:
        print("login", r.status, r.read().decode()[:240])

    def get(path: str):
        cookie = "; ".join(f"{c.name}={c.value}" for c in cj)
        with op.open(
            urllib.request.Request(
                base + path,
                headers={"Accept": "application/json", "Cookie": cookie},
            ),
            timeout=20,
        ) as r:
            return json.loads(r.read().decode())

    resumen = get("/hotel/documental/resumen")
    print("resumen", resumen.get("cargado"), resumen.get("conteos"))
    habs = get("/hotel/documental/habitaciones")["habitaciones"]
    print("doc_habitaciones", len(habs), habs[0]["habitacion_id"], habs[0]["tipo_salman"])
    tars = get("/hotel/documental/tarifas")
    print("doc_tarifas", len(tars["tarifas"]), "publicar", tars.get("publicar_activas"))
    ocu = get("/hotel/documental/ocupacion?periodo=2026-01")
    print("doc_ocupacion_ene", len(ocu["ocupacion"]), "kpi", ocu.get("es_kpi"))
    op_h = get("/hotel/habitaciones")["habitaciones"]
    reales = [h for h in op_h if not str(h.get("habitacion_id") or h.get("id") or "").startswith("HAB-SINT")]
    print("operativo_listado", len(op_h), "sin_sint", len(reales))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
