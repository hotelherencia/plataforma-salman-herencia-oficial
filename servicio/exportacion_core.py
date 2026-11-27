"""Exportación financiera de solo lectura para PEI CORE (`core.finance.v1.1`).

Reglas invariantes:
- Solo lectura absoluta: toda consulta corre bajo `SET TRANSACTION READ ONLY`.
- Minimización de PII: jamás exporta `huesped_nombre`, `huesped_documento`, correos,
  teléfonos, `receptor` de factura ni datos sensibles de tarjeta. Cuentas enmascaradas.
- Precisión exacta: importes en enteros exactos en string (`*_minor`) + moneda/escala explícita.
- Consistencia de corte (`as_of`), orden determinista `(source_updated_at ASC, external_id ASC)`
  y paginación por keyset cursor.
- Separación explícita entre datos operacionales (`es_sintetico=False`) y sintéticos (`es_sintetico=True`).
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal

import psycopg

from . import conciliacion_bancaria, iva
from .empresa_titular import EMPRESA_TITULAR, EMPRESA_TITULAR_MARCA, EMPRESA_TITULAR_RUT

SCHEMA_VERSION = "1.1"
SOURCE_SYSTEM = "hotel_herencia"
BUSINESS_UNIT_SLUG = "hotel-herencia"
BUSINESS_UNIT_NAME = EMPRESA_TITULAR_MARCA
TIMEZONE = "America/Santiago"
MAX_PERIOD_DAYS = 92
MAX_PAGE_SIZE = 500
VALID_RESOURCES = frozenset({"reservations", "payments", "bank_movements"})


class ExportacionInvalida(ValueError):
    """422/400: parámetros de exportación fuera de contrato."""


class CursorInvalido(ValueError):
    """400: cursor opaco malformado."""


def _iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_iso_utc(raw: str, campo: str) -> datetime:
    texto = (raw or "").strip()
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(texto)
    except ValueError as err:
        raise ExportacionInvalida(f"{campo} debe ser ISO-8601 con zona horaria") from err
    if dt.tzinfo is None:
        raise ExportacionInvalida(f"{campo} debe incluir zona horaria explícita (ej. Z)")
    return dt.astimezone(timezone.utc)


def _encode_cursor(ts_iso: str, external_id: str) -> str:
    payload = json.dumps({"ts": ts_iso, "id": external_id}, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        obj = json.loads(raw.decode("utf-8"))
        if not isinstance(obj, dict) or not isinstance(obj.get("ts"), str) or not isinstance(obj.get("id"), str):
            raise ValueError("estructura inválida")
        return _parse_iso_utc(obj["ts"], "cursor.ts"), obj["id"]
    except Exception as err:
        raise CursorInvalido("cursor de paginación inválido") from err


def _record_hash(item: dict) -> str:
    canonical = json.dumps(item, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _enmascarar_cuenta(cuenta: str | None) -> str:
    limpia = (cuenta or "").strip()
    if not limpia:
        return "****"
    ultimos = limpia[-4:] if len(limpia) >= 4 else limpia
    return f"****{ultimos}"


def _normalizar_medio(medio: str | None) -> str:
    m = (medio or "").strip().lower()
    if m in ("efectivo", "debito", "credito", "transferencia", "pasarela"):
        return m
    return "efectivo"


def _normalizar_estado_pago(estado: str | None) -> str:
    e = (estado or "").strip().lower()
    if e == "confirmado":
        return "confirmed"
    if e in ("anulado", "reversado", "reversed"):
        return "reversed"
    return "pending"


def _normalizar_documento(doc: str | None) -> str:
    d = (doc or "").strip().lower()
    if d in ("boleta", "factura", "sin_documento", "pendiente"):
        return d
    return "pendiente"


def exportar_pagina(
    conexion: psycopg.Connection,
    *,
    empresa,
    empresa_rut: str | None,
    resource: str,
    from_date: date,
    to_date: date,
    as_of: str | None = None,
    updated_since: str | None = None,
    page_size: int = 100,
    cursor: str | None = None,
) -> dict:
    if resource not in VALID_RESOURCES:
        raise ExportacionInvalida(f"resource inválido: {resource}")
    if to_date < from_date:
        raise ExportacionInvalida("to_date debe ser mayor o igual a from_date")
    if (to_date - from_date).days > MAX_PERIOD_DAYS:
        raise ExportacionInvalida(f"el período máximo de exportación es {MAX_PERIOD_DAYS} días")
    if not isinstance(page_size, int) or page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ExportacionInvalida(f"page_size debe estar entre 1 y {MAX_PAGE_SIZE}")

    as_of_dt = _parse_iso_utc(as_of, "as_of") if as_of else datetime.now(timezone.utc)
    updated_since_dt = _parse_iso_utc(updated_since, "updated_since") if updated_since else None
    cursor_pair = _decode_cursor(cursor) if cursor else None

    # Garantía matemática en PostgreSQL: cero mutaciones durante la exportación.
    conexion.rollback()
    conexion.execute("BEGIN TRANSACTION READ ONLY")
    try:
        if resource == "reservations":
            items, has_more = _exportar_reservas(conexion, empresa.id, from_date, to_date, as_of_dt, updated_since_dt, page_size, cursor_pair)
        elif resource == "payments":
            items, has_more = _exportar_pagos(conexion, empresa.id, from_date, to_date, as_of_dt, updated_since_dt, page_size, cursor_pair)
        else:
            items, has_more = _exportar_movimientos_bancarios(conexion, empresa.id, from_date, to_date, as_of_dt, updated_since_dt, page_size, cursor_pair)
    finally:
        conexion.rollback()

    next_cursor = None
    if has_more and items:
        ultimo = items[-1]
        next_cursor = _encode_cursor(ultimo["source_updated_at"], ultimo["external_id"])

    rut = empresa_rut or (EMPRESA_TITULAR_RUT if not empresa.es_sintetico and empresa.id == EMPRESA_TITULAR.id else "00.000.000-0")
    es_sintetico = bool(empresa.es_sintetico)

    return {
        "schema_version": SCHEMA_VERSION,
        "source_system": SOURCE_SYSTEM,
        "resource": resource,
        "timezone": TIMEZONE,
        "legal_entity": {
            "external_id": empresa.id,
            "name": empresa.nombre,
            "tax_id": rut,
        },
        "business_unit": {
            "slug": BUSINESS_UNIT_SLUG,
            "name": BUSINESS_UNIT_NAME,
            "tipo": "hotel",
        },
        "period": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        },
        "as_of": _iso_utc(as_of_dt),
        "updated_since": _iso_utc(updated_since_dt) if updated_since_dt else None,
        "is_synthetic": es_sintetico,
        "data_origin": "synthetic" if es_sintetico else "operational",
        "currency_defaults": {"currency": "CLP", "decimals": 0},
        "pagination": {
            "page_size": page_size,
            "returned": len(items),
            "has_more": has_more,
            "next_cursor": next_cursor,
        },
        "items": items,
    }


def _exportar_reservas(
    conexion: psycopg.Connection,
    empresa_id: str,
    from_date: date,
    to_date: date,
    as_of_dt: datetime,
    updated_since_dt: datetime | None,
    page_size: int,
    cursor_pair: tuple[datetime, str] | None,
) -> tuple[list[dict], bool]:
    filtros = [
        "r.empresa_id = %s",
        "r.inicio <= %s",
        "r.fin >= %s",
        "GREATEST(r.creado_en, COALESCE(l.creado_en, r.creado_en)) <= %s",
    ]
    params: list = [empresa_id, to_date, from_date, as_of_dt]
    if updated_since_dt is not None:
        filtros.append("GREATEST(r.creado_en, COALESCE(l.creado_en, r.creado_en)) >= %s")
        params.append(updated_since_dt)
    if cursor_pair is not None:
        filtros.append("(GREATEST(r.creado_en, COALESCE(l.creado_en, r.creado_en)), r.id) > (%s, %s)")
        params.extend([cursor_pair[0], cursor_pair[1]])

    params.append(page_size + 1)
    filas = conexion.execute(
        "SELECT r.id, r.canal, r.estado, r.inicio, r.fin, r.tarifa_noche_aceptada_clp, "
        "l.id AS liq_id, l.estado AS liq_estado, l.total_clp AS liq_total_clp, "
        "COALESCE((SELECT SUM(CASE WHEN c.tipo = 'reverso' THEN -ABS(c.monto_clp) ELSE c.monto_clp END) "
        "          FROM cargos c WHERE c.reserva_id = r.id AND c.creado_en <= %s), 0) AS cargos_netos, "
        "GREATEST(r.creado_en, COALESCE(l.creado_en, r.creado_en)) AS updated_at "
        "FROM reservas r "
        "LEFT JOIN liquidaciones l ON l.reserva_id = r.id AND l.creado_en <= %s "
        f"WHERE {' AND '.join(filtros)} "
        "ORDER BY updated_at ASC, r.id ASC "
        "LIMIT %s",
        [as_of_dt, as_of_dt, *params],
    ).fetchall()

    has_more = len(filas) > page_size
    filas = filas[:page_size]
    items: list[dict] = []
    for f in filas:
        res_id, canal, estado, inicio, fin, tarifa_noche, liq_id, liq_estado, liq_total, cargos_netos, upd = f
        noches = max(0, (fin - inicio).days)
        if estado == "cancelada":
            esperado = max(0, int(cargos_netos or 0))
        elif liq_total is not None:
            esperado = max(0, int(liq_total))
        elif int(cargos_netos or 0) > 0:
            esperado = int(cargos_netos)
        else:
            esperado = max(0, int(tarifa_noche or 0) * noches)

        base_item = {
            "external_id": res_id,
            "external_code": res_id,
            "channel": canal or "recepcion",
            "status": estado,
            "service_start_date": inicio.isoformat(),
            "service_end_date": fin.isoformat(),
            "currency": "CLP",
            "currency_decimals": 0,
            "expected_amount_minor": str(esperado),
            "settlement_external_id": liq_id,
            "settlement_status": liq_estado,
            "source_updated_at": _iso_utc(upd),
        }
        base_item["record_hash"] = _record_hash(base_item)
        items.append(base_item)
    return items, has_more


def _exportar_pagos(
    conexion: psycopg.Connection,
    empresa_id: str,
    from_date: date,
    to_date: date,
    as_of_dt: datetime,
    updated_since_dt: datetime | None,
    page_size: int,
    cursor_pair: tuple[datetime, str] | None,
) -> tuple[list[dict], bool]:
    comisiones = conciliacion_bancaria.obtener_comisiones(conexion, empresa_id)
    tasa = iva.tasa(conexion)

    filtros = [
        "r.empresa_id = %s",
        "p.fecha_contable >= %s",
        "p.fecha_contable <= %s",
        "p.creado_en <= %s",
    ]
    params: list = [empresa_id, from_date, to_date, as_of_dt]
    if updated_since_dt is not None:
        filtros.append("p.creado_en >= %s")
        params.append(updated_since_dt)
    if cursor_pair is not None:
        filtros.append("(p.creado_en, p.id) > (%s, %s)")
        params.extend([cursor_pair[0], cursor_pair[1]])

    params.append(page_size + 1)
    filas = conexion.execute(
        "SELECT p.id, p.reserva_id, p.tipo, p.referencia_pago_id, p.medio, p.estado, "
        "p.fecha_contable, ABS(p.monto_clp) AS monto_bruto, "
        "COALESCE(NULLIF(BTRIM(p.comprobante), ''), NULLIF(BTRIM(p.codigo_autorizacion), ''), "
        "  (SELECT NULLIF(BTRIM(cm.comprobante), '') FROM caja_movimientos cm WHERE cm.pago_id = p.id LIMIT 1)) AS ref_code, "
        "p.documento_tipo, p.documento_folio, p.creado_en, "
        "COALESCE((SELECT SUM(cb.monto_asignado_clp) FROM conciliaciones_bancarias cb "
        "          WHERE cb.pago_id = p.id AND cb.creado_en <= %s), 0) AS op_rec_clp "
        "FROM pagos p "
        "JOIN reservas r ON r.id = p.reserva_id "
        f"WHERE {' AND '.join(filtros)} "
        "ORDER BY p.creado_en ASC, p.id ASC "
        "LIMIT %s",
        [as_of_dt, *params],
    ).fetchall()

    has_more = len(filas) > page_size
    filas = filas[:page_size]
    items: list[dict] = []
    for f in filas:
        (
            pago_id, reserva_id, tipo, ref_pago_id, medio, estado,
            fecha_contable, bruto, ref_code, doc_tipo, doc_folio, creado_en, op_rec_clp,
        ) = f
        bruto_int = int(bruto)
        es_reverso = tipo == "reverso"
        medio_norm = _normalizar_medio(medio)
        if es_reverso:
            neto_int, com_int = bruto_int, 0
        else:
            cfg = comisiones.get(medio_norm, {"porcentaje_comision": Decimal("0"), "iva_comision": False})
            neto_int, com_int = conciliacion_bancaria.calcular_abono_esperado(bruto_int, cfg, tasa)

        base_item = {
            "external_id": pago_id,
            "reservation_external_id": reserva_id,
            "payment_type": "reversal" if es_reverso else "payment",
            "reverses_payment_external_id": ref_pago_id if es_reverso else None,
            "method": medio_norm,
            "status": _normalizar_estado_pago(estado),
            "accounting_date": fecha_contable.isoformat(),
            "currency": "CLP",
            "currency_decimals": 0,
            "gross_amount_minor": str(bruto_int),
            "expected_fee_minor": str(com_int),
            "expected_net_minor": str(neto_int),
            "reference_code": ref_code or None,
            "document_type": _normalizar_documento(doc_tipo),
            "document_folio": doc_folio or None,
            "hotel_operational_reconciled_minor": str(int(op_rec_clp or 0)),
            "source_updated_at": _iso_utc(creado_en),
        }
        base_item["record_hash"] = _record_hash(base_item)
        items.append(base_item)
    return items, has_more


def _exportar_movimientos_bancarios(
    conexion: psycopg.Connection,
    empresa_id: str,
    from_date: date,
    to_date: date,
    as_of_dt: datetime,
    updated_since_dt: datetime | None,
    page_size: int,
    cursor_pair: tuple[datetime, str] | None,
) -> tuple[list[dict], bool]:
    filtros = [
        "m.empresa_id = %s",
        "m.fecha_movimiento >= %s",
        "m.fecha_movimiento <= %s",
        "m.creado_en <= %s",
    ]
    params: list = [empresa_id, from_date, to_date, as_of_dt]
    if updated_since_dt is not None:
        filtros.append("m.creado_en >= %s")
        params.append(updated_since_dt)
    if cursor_pair is not None:
        filtros.append("(m.creado_en, m.id) > (%s, %s)")
        params.extend([cursor_pair[0], cursor_pair[1]])

    params.append(page_size + 1)
    filas = conexion.execute(
        "SELECT m.id, m.cartola_id, cb.banco, cb.cuenta, m.fecha_movimiento, m.tipo, cb.moneda, "
        "ABS(m.monto_clp) AS monto, m.referencia, m.descripcion, m.creado_en, "
        "COALESCE((SELECT SUM(c.monto_asignado_clp) FROM conciliaciones_bancarias c "
        "          WHERE c.cartola_movimiento_id = m.id AND c.creado_en <= %s), 0) AS op_rec_clp "
        "FROM cartola_movimientos m "
        "JOIN cartolas_bancarias cb ON cb.id = m.cartola_id "
        f"WHERE {' AND '.join(filtros)} "
        "ORDER BY m.creado_en ASC, m.id ASC "
        "LIMIT %s",
        [as_of_dt, *params],
    ).fetchall()

    has_more = len(filas) > page_size
    filas = filas[:page_size]
    items: list[dict] = []
    for f in filas:
        (
            mov_id, cartola_id, banco, cuenta, fecha_mov, tipo, moneda,
            monto, referencia, descripcion, creado_en, op_rec_clp,
        ) = f
        base_item = {
            "external_id": mov_id,
            "statement_external_id": cartola_id,
            "bank_name": banco,
            "account_mask": _enmascarar_cuenta(cuenta),
            "movement_date": fecha_mov.isoformat(),
            "direction": "credit" if tipo == "abono" else "debit",
            "currency": (moneda or "CLP").strip().upper(),
            "currency_decimals": 0,
            "amount_minor": str(int(monto)),
            "reference_code": (referencia or "").strip() or None,
            "description": (descripcion or "Movimiento bancario")[:240],
            "hotel_operational_reconciled_minor": str(int(op_rec_clp or 0)),
            "source_updated_at": _iso_utc(creado_en),
        }
        base_item["record_hash"] = _record_hash(base_item)
        items.append(base_item)
    return items, has_more
