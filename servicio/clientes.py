"""Clientes (contabilidad fase 2.1): un RUT es una sola persona o empresa.

El RUT se guarda solo con números y dígito verificador, sin puntos ni guion (`123456785`); la pantalla lo
formatea. El mismo RUT con otro nombre se rechaza: el nombre se compara sin tildes, mayúsculas ni espacios de más.
"""
from __future__ import annotations

import re
import unicodedata
import uuid

import psycopg


class RutInvalido(ValueError):
    """422: el RUT no cumple el formato o el dígito verificador."""


class ClienteConflicto(Exception):
    """409: el RUT ya existe con otro nombre."""


def _digito_verificador(cuerpo: int) -> str:
    suma, factor = 0, 2
    for digito in reversed(str(cuerpo)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return "0" if resto == 11 else "K" if resto == 10 else str(resto)


def rut_clave(texto: str) -> str:
    """RUT como se guarda: números y dígito verificador, sin puntos, guion ni espacios."""
    limpio = re.sub(r"[.\s-]", "", (texto or "").strip()).upper()
    if not re.fullmatch(r"\d{7,8}[0-9K]", limpio):
        raise RutInvalido("RUT inválido: usa el formato 12.345.678-5")
    if _digito_verificador(int(limpio[:-1])) != limpio[-1]:
        raise RutInvalido("RUT inválido: el dígito verificador no corresponde")
    return limpio


def rut_visible(clave: str | None) -> str | None:
    """`123456785` → `12.345.678-5` (solo para mostrar)."""
    if not clave:
        return None
    return f"{int(clave[:-1]):,}".replace(",", ".") + f"-{clave[-1]}"


def nombre_clave(nombre: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", nombre or "") if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def buscar(conexion: psycopg.Connection, rut_normalizado: str) -> tuple | None:
    return conexion.execute(
        "SELECT id, nombre, nombre_clave FROM clientes WHERE rut = %s", (rut_normalizado,)
    ).fetchone()


def exigir_nombre_coherente(conexion: psycopg.Connection, rut_normalizado: str, nombre: str) -> None:
    existente = buscar(conexion, rut_normalizado)
    if existente is not None and existente[2] != nombre_clave(nombre):
        raise ClienteConflicto(
            f"el RUT {rut_visible(rut_normalizado)} ya está registrado a nombre de «{existente[1]}»; "
            "revisa el RUT o el nombre"
        )


def asegurar(conexion: psycopg.Connection, rut: str, nombre: str, actor: str, *, giro: str | None = None,
             direccion: str | None = None, comuna: str | None = None, correo: str | None = None,
             tipo: str = "empresa") -> str:
    """Id del cliente de ese RUT; lo crea si no existe. Mismo RUT con otro nombre → `ClienteConflicto`."""
    clave = rut_clave(rut)
    nombre = " ".join((nombre or "").split())
    exigir_nombre_coherente(conexion, clave, nombre)
    existente = buscar(conexion, clave)
    if existente is not None:
        return existente[0]
    cliente_id = f"CLI-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO clientes (id, tipo, rut, nombre, nombre_clave, giro, direccion, comuna, correo, creado_por) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (cliente_id, tipo, clave, nombre, nombre_clave(nombre), giro or None, direccion or None, comuna or None,
         correo or None, actor),
    )
    return cliente_id
