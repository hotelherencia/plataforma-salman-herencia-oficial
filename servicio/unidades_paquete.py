"""Envases y unidades de facturas de proveedores (2026-11-19).

Los proveedores facturan por envase: «Caja x 18», «Bebida 350 ml X 12 UN»,
«Pack 6». El inventario del hotel cuenta unidades. Estas reglas proponen
cuántas unidades trae cada envase a partir del texto; la administración lo
confirma o corrige y la plataforma lo recuerda por proveedor + ítem.

También se lee la nota manuscrita típica de las facturas de pastelería
(«166und x 690»: 166 unidades a $690 c/u) cuando la IA la transcribe.
"""
from __future__ import annotations

import re
import unicodedata

_MEDIDA = r"(?:ml|cc|lt|lts|l|gr|grs|g|kg|kgs|mg|cm|mm|mt|mts|m|oz|w|v)"
_ENVASE = r"(?:caja|cajas|cj|cja|pack|pck|pqte|paquete|display|disp|bandeja|bolsa|fardo|bulto|set|tira|blister|sixpack|six pack)"

_PATRONES = [
    # «Caja x 18», «PACK DE 6», «Display 24», «cj x12»
    re.compile(rf"\b{_ENVASE}\s*(?:de\s*|x\s*|c/\s*|con\s*)?(\d{{1,4}})\b(?!\s*{_MEDIDA}\b)"),
    # «X 12 UN», «x24 unid», «12 x 1 un»
    re.compile(r"\bx\s*(\d{1,4})\s*(?:u|un|und|unid|unids|unidades|uds|ud)\b"),
    # «12 UN x 350 ml», «24 unidades»
    re.compile(r"\b(\d{1,4})\s*(?:un|und|unid|unids|unidades|uds)\b(?!\s*[x×*]\s*\$?\s*\d{3})"),
    # «12x350ml», «6 x 1,5 lt»: cantidad × medida
    re.compile(rf"\b(\d{{1,3}})\s*[x×]\s*\d+(?:[.,]\d+)?\s*{_MEDIDA}\b"),
    # «Bebida x 6» al final (sin medida después)
    re.compile(r"\bx\s*(\d{{1,4}})\s*$"),
]

# Nota «166und x 690» (unidades × precio): no es un envase.
_NOTA_CON_UNIDAD = re.compile(r"\d{1,5}\s*(?:u|un|und|unid|unidades|uds)\.?\s*[x×*]\s*\$?\s*[\d.]+")
_NOTA = re.compile(r"(\d{1,5})\s*(?:u|un|und|unid|unidades|uds)?\.?\s*[x×*]\s*\$?\s*(\d{1,3}(?:[.\s]\d{3})+|\d{2,7})\b")


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto or "") if not unicodedata.combining(c))
    return " ".join(sin_tildes.lower().split())


def unidades_por_paquete(*textos: str | None) -> int | None:
    """Unidades por envase sugeridas por el texto (descripción, unidad), o
    None si no hay una indicación clara. Nunca devuelve 1 (no aporta)."""
    for texto in textos:
        t = _NOTA_CON_UNIDAD.sub(" ", _normalizar(texto or ""))
        if not t.strip():
            continue
        for patron in _PATRONES:
            m = patron.search(t)
            if m:
                n = int(m.group(1))
                if 2 <= n <= 10000:
                    return n
    return None


def leer_nota_cantidad(nota: str | None) -> dict | None:
    """«166und x 690» → {"unidades": 166, "precio_unitario": 690}."""
    t = _normalizar(nota or "")
    m = _NOTA.search(t)
    if not m:
        return None
    unidades = int(m.group(1))
    precio = int(re.sub(r"[.\s]", "", m.group(2)))
    if unidades <= 0 or precio <= 0:
        return None
    return {"unidades": unidades, "precio_unitario": precio}


def clave_item(codigo: str | None, descripcion: str | None) -> str:
    """Clave estable de un ítem del proveedor: su código, o la descripción
    normalizada si no trae código."""
    if codigo and codigo.strip():
        return "cod:" + codigo.strip().lower()[:60]
    t = re.sub(r"[^a-z0-9]+", " ", _normalizar(descripcion or "")).strip()
    return "txt:" + t[:120]
