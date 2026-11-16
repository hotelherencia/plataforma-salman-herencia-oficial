"""Normalización de texto que llega por el canal público (landing, /reservar).

Se aplica ANTES de validar, hashear (idempotencia) y persistir:
- Unicode NFC (la misma palabra no queda guardada con dos codificaciones).
- Sin caracteres de control C0/C1, DEL ni marcas bidi/ancho cero (evitan
  texto que se ve distinto de lo que dice y la inyección de saltos en logs).
- Saltos y tabulaciones solo en campos multilínea; espacios repetidos colapsan.

El SQL del servicio siempre va parametrizado (psycopg `%s`); esta capa no
"escapa" nada para SQL ni HTML: el front pinta texto (React) y la base recibe
parámetros. Su fin es la calidad del dato y que los topes de largo se midan
sobre lo que realmente se guarda.
"""
from __future__ import annotations

import re
import unicodedata

_CONTROLES = re.compile(
    "[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f"
    "\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]"
)
_ESPACIOS = re.compile(r"[ \u00a0]{2,}")
_RE_TELEFONO = re.compile(r"^[+\d\s().-]+$")


def limpiar_texto(valor: str | None, multilinea: bool = False) -> str:
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFC", str(valor))
    texto = _CONTROLES.sub("", texto)
    if multilinea:
        texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    else:
        texto = re.sub(r"[\r\n\t]+", " ", texto)
    return _ESPACIOS.sub(" ", texto).strip()


def telefono_con_formato(telefono: str) -> bool:
    """Solo dígitos, espacios, +, paréntesis, punto y guion (sin letras ni HTML)."""
    return bool(_RE_TELEFONO.fullmatch(telefono or ""))
