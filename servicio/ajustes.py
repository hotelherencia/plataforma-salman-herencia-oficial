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


def _validar_revision(valor: dict) -> dict:
    if not isinstance(valor, dict) or set(valor) - {"activo", "intervalo_minutos", "registrar_buzon"}:
        raise AjusteInvalido("campos permitidos: activo, intervalo_minutos, registrar_buzon")
    actual = {**DEFECTOS["revision_correo"], **valor}
    for campo in ("activo", "registrar_buzon"):
        if not isinstance(actual[campo], bool):
            raise AjusteInvalido(f"{campo} debe ser verdadero o falso")
    return {"activo": actual["activo"], "registrar_buzon": actual["registrar_buzon"],
            "intervalo_minutos": _entero(actual["intervalo_minutos"], "intervalo_minutos", 5, 1440)}


MEDIOS_CAJA = ("efectivo", "debito", "credito", "transferencia")
DOCUMENTOS_CAJA = ("boleta", "factura", "sin_documento")
# Billetes y monedas en circulación en Chile (Banco Central), editables.
DENOMINACIONES_CLP = [20000, 10000, 5000, 2000, 1000, 500, 100, 50, 10]


def _validar_caja(valor: dict) -> dict:
    """Parámetros de caja (fase 1 contable). Todo editable por admin_hotel."""
    permitidos = set(DEFECTOS["caja"])
    if not isinstance(valor, dict) or set(valor) - permitidos:
        raise AjusteInvalido("campos permitidos: " + ", ".join(sorted(permitidos)))
    actual = {**copy.deepcopy(DEFECTOS["caja"]), **valor}
    medios_in = actual["medios"]
    if not isinstance(medios_in, dict) or set(medios_in) - set(MEDIOS_CAJA):
        raise AjusteInvalido("medios: solo efectivo, debito, credito y transferencia")
    medios = {}
    for medio in MEDIOS_CAJA:
        m = {**DEFECTOS["caja"]["medios"][medio], **(medios_in.get(medio) or {})}
        if set(m) - {"activo", "comision_pct", "dias_abono"} or not isinstance(m["activo"], bool):
            raise AjusteInvalido(f"medios.{medio}: activo (sí/no), comision_pct y dias_abono")
        comision = m["comision_pct"]
        if isinstance(comision, bool) or not isinstance(comision, (int, float)) or not 0 <= comision <= 15:
            raise AjusteInvalido(f"medios.{medio}.comision_pct debe estar entre 0 y 15")
        medios[medio] = {"activo": m["activo"], "comision_pct": round(float(comision), 2),
                         "dias_abono": _entero(m["dias_abono"], f"medios.{medio}.dias_abono", 0, 30)}
    if not any(m["activo"] for m in medios.values()):
        raise AjusteInvalido("deja al menos un medio de pago activo")
    denominaciones = actual["denominaciones"]
    if (not isinstance(denominaciones, list) or not 1 <= len(denominaciones) <= 20
            or any(isinstance(d, bool) or not isinstance(d, int) or not 1 <= d <= 100000 for d in denominaciones)
            or len(set(denominaciones)) != len(denominaciones)):
        raise AjusteInvalido("denominaciones: lista de 1 a 20 valores enteros distintos")
    if actual["documento_por_defecto"] not in DOCUMENTOS_CAJA:
        raise AjusteInvalido("documento_por_defecto: boleta, factura o sin_documento")
    for campo in ("exigir_turno_efectivo", "exigir_documento"):
        if not isinstance(actual[campo], bool):
            raise AjusteInvalido(f"{campo} debe ser verdadero o falso")
    banco = actual["banco_deposito"]
    if not isinstance(banco, str) or len(banco) > 120:
        raise AjusteInvalido("banco_deposito: texto de hasta 120 caracteres")
    return {
        "medios": medios,
        "fondo_fijo_clp": _entero(actual["fondo_fijo_clp"], "fondo_fijo_clp", 0, 10_000_000),
        "tolerancia_diferencia_clp": _entero(actual["tolerancia_diferencia_clp"], "tolerancia_diferencia_clp", 0, 100_000),
        "denominaciones": sorted(denominaciones, reverse=True),
        "exigir_turno_efectivo": actual["exigir_turno_efectivo"],
        "exigir_documento": actual["exigir_documento"],
        "documento_por_defecto": actual["documento_por_defecto"],
        "banco_deposito": banco.strip(),
    }


DEFECTOS: dict[str, dict] = {
    "tope_solicitudes_cliente": {"activo": True, "max_solicitudes": 3, "dias": 7},
    # #355: revisión de enviados cada 15 minutos; la nota registra el buzón,
    # no la persona (decisión del propietario 2026-11-18).
    "revision_correo": {"activo": True, "intervalo_minutos": 15, "registrar_buzon": True},
    # Fase 1 contable (2026-11-19): valores iniciales, no reglas fijas. La
    # comisión y los días de abono de cada medio salen del contrato con el
    # adquirente (Transbank u otro): la administración los completa.
    "caja": {
        "medios": {
            "efectivo": {"activo": True, "comision_pct": 0, "dias_abono": 0},
            "debito": {"activo": True, "comision_pct": 0, "dias_abono": 1},
            "credito": {"activo": True, "comision_pct": 0, "dias_abono": 2},
            "transferencia": {"activo": True, "comision_pct": 0, "dias_abono": 0},
        },
        "fondo_fijo_clp": 0,
        "tolerancia_diferencia_clp": 0,
        "denominaciones": DENOMINACIONES_CLP,
        "exigir_turno_efectivo": True,
        "exigir_documento": False,
        "documento_por_defecto": "boleta",
        "banco_deposito": "",
    },
}
_VALIDADORES = {"tope_solicitudes_cliente": _validar_tope, "revision_correo": _validar_revision,
                "caja": _validar_caja}


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
