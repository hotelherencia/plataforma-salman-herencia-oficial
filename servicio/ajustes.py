"""Ajustes operativos editables desde Configuración (#348, 2026-11-18).

Cada ajuste tiene un valor por defecto y un validador; lo guardado en la
tabla `ajustes` reemplaza al defecto. Hoy:

- `tope_solicitudes_cliente`: un mismo cliente (correo o teléfono
  normalizado) puede tener como máximo `max_solicitudes` solicitudes
  recibidas o convertidas en los últimos `dias` días. Decisión del
  propietario (opción C de #348). Valor inicial: 3 en 7 días, activo.
"""
from __future__ import annotations

import copy
import json

import psycopg

from . import roles

ROLES_EDICION = roles.con_admin_hotel()


class AjusteInvalido(Exception):
    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


def _entero(valor, campo, minimo, maximo) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or not minimo <= valor <= maximo:
        raise AjusteInvalido(f"{campo} debe ser un entero entre {minimo} y {maximo}")
    return valor


def _validar_tope(valor: dict) -> dict:
    if not isinstance(valor, dict) or set(valor) - {"activo", "max_solicitudes", "dias"}:
        raise AjusteInvalido("campos permitidos: activo, max_solicitudes, dias")
    actual = {**DEFECTOS["tope_solicitudes_cliente"], **valor}
    if not isinstance(actual["activo"], bool):
        raise AjusteInvalido("activo debe ser verdadero o falso")
    return {"activo": actual["activo"],
            "max_solicitudes": _entero(actual["max_solicitudes"], "max_solicitudes", 1, 100),
            "dias": _entero(actual["dias"], "dias", 1, 365)}


DEFECTOS: dict[str, dict] = {
    "tope_solicitudes_cliente": {"activo": True, "max_solicitudes": 3, "dias": 7},
}
_VALIDADORES = {"tope_solicitudes_cliente": _validar_tope}


def leer(conexion: psycopg.Connection, empresa_id: str, clave: str) -> dict:
    fila = conexion.execute(
        "SELECT valor FROM ajustes WHERE empresa_id = %s AND clave = %s", (empresa_id, clave)
    ).fetchone()
    return {**copy.deepcopy(DEFECTOS[clave]), **(fila[0] if fila else {})}


def todos(conexion: psycopg.Connection, empresa_id: str) -> dict:
    return {clave: leer(conexion, empresa_id, clave) for clave in DEFECTOS}


def guardar(conexion: psycopg.Connection, empresa_id: str, clave: str, valor: dict, actor: str) -> dict:
    if clave not in DEFECTOS:
        raise AjusteInvalido(f"ajuste desconocido: {clave}")
    limpio = _VALIDADORES[clave](valor)
    conexion.execute(
        "INSERT INTO ajustes (empresa_id, clave, valor, actualizado_por) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (empresa_id, clave) DO UPDATE SET valor = EXCLUDED.valor, "
        "actualizado_por = EXCLUDED.actualizado_por, actualizado_en = now()",
        (empresa_id, clave, json.dumps(limpio), actor),
    )
    return limpio
