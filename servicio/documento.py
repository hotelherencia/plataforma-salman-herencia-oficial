"""Documento de identidad del huésped (#367): RUT chileno o pasaporte.

El RUT se valida por su dígito verificador (módulo 11) y se guarda con el
formato `12.345.678-5`. El pasaporte se guarda en mayúsculas, sin espacios,
alfanumérico de 6 a 12 caracteres. Nada de esto toca la base: es puro.
"""
from __future__ import annotations

import re

TIPOS = ("rut", "pasaporte")


class DocumentoInvalido(ValueError):
    """422: el documento no cumple el formato de su tipo."""


def digito_verificador(cuerpo: int) -> str:
    suma, factor = 0, 2
    for digito in reversed(str(cuerpo)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return "0" if resto == 11 else "K" if resto == 10 else str(resto)


def normalizar_rut(texto: str) -> str:
    limpio = re.sub(r"[.\s-]", "", (texto or "").strip()).upper()
    if not re.fullmatch(r"\d{7,8}[0-9K]", limpio):
        raise DocumentoInvalido("RUT inválido: usa el formato 12.345.678-5")
    cuerpo, dv = int(limpio[:-1]), limpio[-1]
    if digito_verificador(cuerpo) != dv:
        raise DocumentoInvalido("RUT inválido: el dígito verificador no corresponde")
    return f"{cuerpo:,}".replace(",", ".") + f"-{dv}"


def normalizar_pasaporte(texto: str) -> str:
    limpio = re.sub(r"\s", "", (texto or "").strip()).upper()
    if not re.fullmatch(r"[A-Z0-9]{6,12}", limpio):
        raise DocumentoInvalido("pasaporte inválido: de 6 a 12 letras o números, sin símbolos")
    return limpio


def normalizar(tipo: str, numero: str) -> str:
    if tipo == "rut":
        return normalizar_rut(numero)
    if tipo == "pasaporte":
        return normalizar_pasaporte(numero)
    raise DocumentoInvalido("tipo de documento debe ser rut o pasaporte")
