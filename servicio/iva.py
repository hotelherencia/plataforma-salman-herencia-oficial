"""IVA de los precios del hotel (Chile; tasa configurable, 19 % por defecto).

Regla única (documentada en docs/arquitectura/spec-api-v1.md):

- La **fuente de verdad es el precio CON IVA** en pesos enteros: es lo que
  paga el huésped y lo que guardan tipos, habitaciones, excepciones y
  reservas.
- neto = redondeo_medio_arriba(precio × 100 / (100 + tasa)); IVA = precio − neto.
  Así neto + IVA == precio siempre.
- Si se ingresa un neto, el precio con IVA = redondeo_medio_arriba(neto ×
  (100 + tasa) / 100); se guarda ese precio y el neto se vuelve a derivar
  (puede diferir en $1 del ingresado por el redondeo).

Aritmética entera (tasa en milésimas de punto) para que el servidor y el
front (front/lib/iva.js) den exactamente lo mismo.
"""
from __future__ import annotations

from decimal import Decimal

import psycopg

CLAVE_TASA = "iva_porcentaje"
TASA_POR_DEFECTO = Decimal("19")
TASA_MAXIMA = Decimal("100")


def _milesimas(tasa: Decimal | float | int) -> int:
    return int((Decimal(str(tasa)) * 1000).to_integral_value())


def _dividir_medio_arriba(a: int, b: int) -> int:
    return (2 * a + b) // (2 * b)


def neto_desde_precio(precio_con_iva: int, tasa) -> int:
    base = 100_000 + _milesimas(tasa)
    return _dividir_medio_arriba(precio_con_iva * 100_000, base)


def precio_desde_neto(neto: int, tasa) -> int:
    return _dividir_medio_arriba(neto * (100_000 + _milesimas(tasa)), 100_000)


def desglose(precio_con_iva: int | None, tasa) -> dict | None:
    if precio_con_iva is None:
        return None
    neto = neto_desde_precio(precio_con_iva, tasa)
    return {"con_iva": precio_con_iva, "neto": neto, "iva": precio_con_iva - neto}


def tasa(conexion: psycopg.Connection) -> Decimal:
    fila = conexion.execute("SELECT valor FROM ajustes_plataforma WHERE clave = %s", (CLAVE_TASA,)).fetchone()
    return Decimal(fila[0]) if fila else TASA_POR_DEFECTO


def fijar_tasa(conexion: psycopg.Connection, nueva: Decimal, actor: str) -> tuple[Decimal, Decimal]:
    anterior = tasa(conexion)
    conexion.execute(
        "INSERT INTO ajustes_plataforma (clave, valor, actualizado_por) VALUES (%s, %s, %s) "
        "ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado_en = clock_timestamp(), "
        "actualizado_por = EXCLUDED.actualizado_por",
        (CLAVE_TASA, nueva, actor),
    )
    return anterior, nueva


def como_texto(valor: Decimal) -> str:
    """19.000 → "19"; 19.500 → "19.5"."""
    return format(valor.normalize(), "f")
