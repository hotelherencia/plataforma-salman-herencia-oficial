"""Prueba local de facturas en foto/PDF: timbre SII (PDF417) y lectura con IA.

Uso (la clave nunca se imprime ni se guarda):
    GEMINI_API_KEY="$(cat /ruta/gemini.key)" .venv/bin/python scripts/probar_facturas_fotos.py fotos/*.jpg
    .venv/bin/python scripts/probar_facturas_fotos.py --sin-ia fotos/*.jpg      # solo timbre
    ... --json resultado.json                                                   # además, JSON

Para cada archivo informa:
  * timbre leído en la foto original y en la versión reducida como la sube el
    celular (lado mayor 3200 px, JPEG 0,9);
  * clase, cabecera y líneas leídas por la IA, y los avisos de cuadratura
    (suma de líneas vs neto, neto+IVA vs total, total vs MNT del timbre).
No escribe en la base de datos ni copia las fotos.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servicio import ted, vision  # noqa: E402
from servicio.facturas_proveedor import tipo_real  # noqa: E402


def reducida(contenido: bytes) -> bytes | None:
    from PIL import Image, ImageOps

    img = ImageOps.exif_transpose(Image.open(io.BytesIO(contenido))).convert("RGB")
    mayor = max(img.size)
    if mayor > 3200:
        f = 3200 / mayor
        img = img.resize((round(img.width * f), round(img.height * f)), Image.LANCZOS)
    salida = io.BytesIO()
    img.save(salida, "JPEG", quality=90)
    return salida.getvalue()


def pesos(n) -> str:
    return "—" if n is None else "$" + f"{int(round(n)):,}".replace(",", ".")


def probar(ruta: Path, con_ia: bool) -> dict:
    contenido = ruta.read_bytes()
    mime = tipo_real(contenido)
    r: dict = {"archivo": ruta.name, "tipo": mime, "bytes": len(contenido)}
    t0 = time.monotonic()
    r["timbre"] = ted.leer_timbre(contenido, mime) if mime else None
    r["timbre_segundos"] = round(time.monotonic() - t0, 1)
    if mime and mime.startswith("image/"):
        from PIL import Image

        r["pixeles"] = "x".join(map(str, Image.open(io.BytesIO(contenido)).size))
        chica = reducida(contenido)
        r["timbre_reducida"] = ted.leer_timbre(chica, "image/jpeg")
    if con_ia and mime:
        proveedor = vision.proveedor_configurado()
        t0 = time.monotonic()
        try:
            extraido = vision.normalizar(proveedor.extraer(contenido, mime))
            r["ia_modelo"] = getattr(proveedor, "modelo_usado", None) or getattr(proveedor, "modelo", None)
            r["ia"] = extraido
            r["avisos"] = vision.validar(extraido["documento"], extraido["lineas"], r["timbre"],
                                         os.environ.get("EMPRESA_RUT"))
        except Exception as error:  # noqa: BLE001 — se informa y se sigue con la próxima foto
            r["ia_error"] = f"{type(error).__name__}: {str(error)[:200]}"
        r["ia_segundos"] = round(time.monotonic() - t0, 1)
    return r


def imprimir(r: dict) -> None:
    print(f"\n=== {r['archivo']}  ({r['tipo']}, {r.get('pixeles', '')}, {r['bytes'] // 1024} KB)")
    t = r["timbre"]
    if t:
        print(f"  Timbre: RE {t['emisor_rut']} · TD {t['tipo_dte']} ({t['tipo_nombre']}) · F {t['folio']} · "
              f"FE {t['fecha_emision']} · MNT {pesos(t['monto_total_clp'])} · IT1 «{t['primer_item']}»  [{r['timbre_segundos']} s]")
    else:
        print(f"  Timbre: no se pudo leer  [{r['timbre_segundos']} s]")
    if "timbre_reducida" in r:
        print(f"  Timbre en la foto reducida a 3200 px: {'sí' if r['timbre_reducida'] else 'no'}")
    if "ia_error" in r:
        print(f"  IA: falló ({r['ia_error']})")
    elif "ia" in r:
        d, lineas = r["ia"]["documento"], r["ia"]["lineas"]
        print(f"  IA ({r.get('ia_modelo')}, {r['ia_segundos']} s): {r['ia']['clase']} · {d.get('emisor_razon_social')} "
              f"{d.get('emisor_rut')} · folio {d.get('folio')} · neto {pesos(d.get('monto_neto_clp'))} · "
              f"IVA {pesos(d.get('iva_clp'))} · total {pesos(d.get('monto_total_clp'))}")
        for i, l in enumerate(lineas, 1):
            nota = f"  nota a mano: «{l['nota']}»" if l.get("nota") else ""
            print(f"   {i:>2}. {l.get('codigo') or '':<10} {l['nombre'][:48]:<48} {l.get('cantidad')!s:>7} "
                  f"{l.get('unidad') or '':<5} costo {pesos(l.get('costo_unitario_clp'))} total {pesos(l.get('monto_neto_clp'))}{nota}")
        suma = sum(l.get("monto_neto_clp") or 0 for l in lineas)
        print(f"  Suma de líneas {pesos(suma)} · neto {pesos(d.get('monto_neto_clp'))} · "
              f"MNT timbre {pesos((r['timbre'] or {}).get('monto_total_clp'))}")
        for a in r.get("avisos", []):
            print(f"  ! {a['mensaje']}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("archivos", nargs="+", type=Path)
    p.add_argument("--sin-ia", action="store_true")
    p.add_argument("--json", type=Path)
    a = p.parse_args()
    con_ia = not a.sin_ia and vision.estado()["activa"]
    if not a.sin_ia and not con_ia:
        print("Lectura con IA desactivada (falta GEMINI_API_KEY): solo se prueba el timbre.")
    resultados = []
    for ruta in a.archivos:
        r = probar(ruta, con_ia)
        imprimir(r)
        resultados.append(r)
    leidos = sum(1 for r in resultados if r["timbre"])
    print(f"\nTimbre leído en {leidos} de {len(resultados)} archivos.")
    if a.json:
        a.json.write_text(json.dumps(resultados, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
