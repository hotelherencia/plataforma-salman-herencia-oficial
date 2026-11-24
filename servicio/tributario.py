"""Contable 2.7 (#397 / TAX-002, TAX-003): Conciliación tributaria mensual y borrador F29.

Reglas clave:
- Resume boletas, facturas y notas de crédito/reversos por mes calendario:
  neto, IVA (tasa vigente desde `ajustes_plataforma`, nunca hardcodeada) y total.
- Ventas con tarjeta de fin de mes cuyo abono bancario cae en el mes siguiente
  suman al débito fiscal del **mes de la venta** y se detallan explícitamente como
  «en tránsito» respecto de la cartola del mes siguiente.
- Las notas de crédito / reversos restan en el mes correspondiente.
- Crédito fiscal referencial proveniente de facturas y notas de crédito de proveedores
  (`documentos_proveedor` cargadas/aplicadas del mes).
- **Sin emisión electrónica ni conexión ni envío al SII** (regla obligatoria AGENTS.md).
"""
from __future__ import annotations

import calendar
import csv
import io
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import psycopg

from . import conciliacion_bancaria, contabilidad, facturas_proveedor, iva, roles

ROLES_TRIBUTARIO = roles.con_admin_hotel("caja")


def _desglose(bruto: int, tasa: Decimal) -> tuple[int, int]:
    """Devuelve (neto_clp, iva_clp) exactos al peso (neto + iva == bruto)."""
    if bruto == 0:
        return 0, 0
    signo = -1 if bruto < 0 else 1
    abs_b = abs(bruto)
    neto = int((Decimal(abs_b) / (Decimal(1) + tasa / Decimal(100))).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return signo * neto, signo * (abs_b - neto)


def resumen_tributario_mensual(
    conexion: psycopg.Connection,
    empresa_id: str,
    anio: int,
    mes: int,
) -> dict:
    """Conciliación tributaria mensual (borrador F29) — solo lectura, sin envío al SII."""
    if not (2020 <= anio <= 2100) or not (1 <= mes <= 12):
        raise contabilidad.DatosCajaInvalidos("indica un año (2020–2100) y mes (1–12) válidos")
    dias_mes = calendar.monthrange(anio, mes)[1]
    desde = date(anio, mes, 1)
    hasta = desde + timedelta(days=dias_mes)
    tasa = iva.tasa(conexion)
    comisiones = conciliacion_bancaria.obtener_comisiones(conexion, empresa_id)

    # 1. Ventas/cobros con documento (pagos de reservas + movimientos directos cobrados)
    filas_ventas = conexion.execute(
        "SELECT fecha_contable, documento_tipo, tipo_doc_op, medio, monto_clp, folio, ref_id FROM ("
        "  SELECT p.fecha_contable, p.documento_tipo, "
        "    CASE WHEN p.tipo = 'reverso' THEN 'nota_credito' ELSE 'venta' END AS tipo_doc_op, "
        "    p.medio, CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END AS monto_clp, "
        "    p.documento_folio AS folio, p.id AS ref_id "
        "  FROM pagos p JOIN reservas r ON r.id = p.reserva_id "
        "  WHERE r.empresa_id = %s AND p.estado = 'confirmado' "
        "  AND p.fecha_contable >= %s AND p.fecha_contable < %s "
        "  UNION ALL "
        "  SELECT d.fecha_contable, d.documento_tipo, "
        "    CASE WHEN d.tipo = 'reverso_directo' THEN 'nota_credito' ELSE 'venta' END AS tipo_doc_op, "
        "    d.medio, CASE WHEN d.tipo = 'reverso_directo' THEN -d.monto_clp ELSE d.monto_clp END AS monto_clp, "
        "    d.documento_folio AS folio, d.id AS ref_id "
        "  FROM movimientos_directos d LEFT JOIN movimientos_directos o ON o.id = d.referencia_id "
        "  WHERE d.empresa_id = %s AND d.fecha_contable >= %s AND d.fecha_contable < %s "
        "  AND (d.tipo = 'cargo_directo' OR (d.tipo = 'reverso_directo' AND o.tipo = 'cargo_directo'))"
        ") v ORDER BY fecha_contable ASC, ref_id ASC",
        (empresa_id, desde, hasta, empresa_id, desde, hasta),
    ).fetchall()

    por_documento = {
        "boleta": {"cantidad": 0, "total_clp": 0, "neto_clp": 0, "iva_clp": 0},
        "factura": {"cantidad": 0, "total_clp": 0, "neto_clp": 0, "iva_clp": 0},
        "nota_credito": {"cantidad": 0, "total_clp": 0, "neto_clp": 0, "iva_clp": 0},
        "sin_documento": {"cantidad": 0, "total_clp": 0, "neto_clp": 0, "iva_clp": 0},
        "pendiente": {"cantidad": 0, "total_clp": 0, "neto_clp": 0, "iva_clp": 0},
    }
    diario: dict[str, dict] = {}
    ventas_en_transito = []

    for fecha_c, doc_tipo, tipo_op, medio, monto, folio, ref_id in filas_ventas:
        monto_i = int(monto)
        clave = "nota_credito" if tipo_op == "nota_credito" else (doc_tipo if doc_tipo in por_documento else "pendiente")
        neto_i, iva_i = _desglose(monto_i, tasa)
        bucket = por_documento[clave]
        bucket["cantidad"] += 1
        bucket["total_clp"] += monto_i
        bucket["neto_clp"] += neto_i
        bucket["iva_clp"] += iva_i

        f_iso = fecha_c.isoformat()
        dia = diario.setdefault(f_iso, {"fecha": f_iso, "total_clp": 0, "neto_clp": 0, "iva_clp": 0, "documentos": 0})
        dia["total_clp"] += monto_i
        dia["neto_clp"] += neto_i
        dia["iva_clp"] += iva_i
        dia["documentos"] += 1

        # Venta con tarjeta/medio diferido cuyo abono cae en el mes siguiente:
        # suma al débito fiscal del mes de la venta y figura «en tránsito» para conciliación bancaria.
        if tipo_op == "venta" and medio in comisiones:
            fecha_abono = conciliacion_bancaria._sumar_dias_habiles(fecha_c, comisiones[medio]["dias_habiles_abono"])
            if (fecha_abono.year, fecha_abono.month) != (anio, mes):
                ventas_en_transito.append({
                    "referencia_id": ref_id,
                    "fecha_venta": f_iso,
                    "fecha_abono_estimada": fecha_abono.isoformat(),
                    "medio": medio,
                    "documento_tipo": doc_tipo,
                    "folio": folio,
                    "total_clp": monto_i,
                    "neto_clp": neto_i,
                    "iva_clp": iva_i,
                })

    # Débito fiscal F29: boletas + facturas + notas de crédito (restan) + pendientes/sin_documento como referencia
    total_afecto_ventas = sum(por_documento[k]["total_clp"] for k in ("boleta", "factura", "nota_credito"))
    neto_afecto_ventas = sum(por_documento[k]["neto_clp"] for k in ("boleta", "factura", "nota_credito"))
    debito_fiscal_clp = sum(por_documento[k]["iva_clp"] for k in ("boleta", "factura", "nota_credito"))

    total_ventas_con_pendientes = sum(b["total_clp"] for b in por_documento.values())

    # 2. Crédito fiscal referencial de compras de proveedores (0040 + 0062).
    # #469: el grupo factura a varias sociedades y el IVA crédito de una no se imputa a otra. Solo suma
    # lo emitido al RUT de esta empresa (EMPRESA_RUT); lo emitido a otro RUT se informa aparte y no
    # resta del IVA. Los documentos sin receptor registrado cuentan, pero se avisan para que se completen.
    rut_empresa = facturas_proveedor.rut_hotel()

    def _compras(clase: str, estado: str) -> tuple:
        filtro, parametros = ("", [])
        if rut_empresa:
            filtro, parametros = (" AND receptor_rut IS NOT NULL AND receptor_rut <> %s", [rut_empresa])
        propias = conexion.execute(
            "SELECT COUNT(*), COALESCE(SUM(monto_neto_clp), 0), COALESCE(SUM(iva_clp), 0), COALESCE(SUM(monto_total_clp), 0), "
            "COUNT(*) FILTER (WHERE receptor_rut IS NULL) "
            "FROM documentos_proveedor WHERE clase = %s AND estado = %s "
            "AND fecha_emision >= %s AND fecha_emision < %s"
            + (" AND (receptor_rut IS NULL OR receptor_rut = %s)" if rut_empresa else ""),
            [clase, estado, desde, hasta] + ([rut_empresa] if rut_empresa else []),
        ).fetchone()
        ajenas = (0, 0)
        if rut_empresa:
            ajenas = conexion.execute(
                "SELECT COUNT(*), COALESCE(SUM(iva_clp), 0) FROM documentos_proveedor WHERE clase = %s AND estado = %s "
                "AND fecha_emision >= %s AND fecha_emision < %s" + filtro,
                [clase, estado, desde, hasta] + parametros,
            ).fetchone()
        return propias, ajenas

    (compras_facturas, facturas_otro_rut) = _compras("factura", "cargada")
    (compras_nc, nc_otro_rut) = _compras("nota_credito", "aplicada")
    credito_fiscal_clp = int(compras_facturas[2] or 0) - int(compras_nc[2] or 0)
    sin_receptor = int(compras_facturas[4] or 0) + int(compras_nc[4] or 0)

    # Caja cobrada efectivamente en el mes (para explicar diferencia vs ventas tributarias)
    (caja_mes_clp,) = conexion.execute(
        "SELECT COALESCE(SUM(monto_clp), 0) FROM caja_movimientos "
        "WHERE empresa_id = %s AND fecha_contable >= %s AND fecha_contable < %s "
        "AND tipo IN ('cobro', 'reverso_cobro', 'cobro_directo', 'reverso_directo')",
        (empresa_id, desde, hasta),
    ).fetchone()

    return {
        "periodo": f"{anio:04d}-{mes:02d}",
        "anio": anio,
        "mes": mes,
        "iva_pct": float(tasa),
        "integracion_sii": False,
        "nota_legal": "Borrador interno de conciliación tributaria (F29). No realiza emisión ni envío al SII.",
        "por_documento": por_documento,
        "diario": [diario[k] for k in sorted(diario)],
        "ventas_en_transito": ventas_en_transito,
        "compras_credito_fiscal": {
            "facturas_cantidad": int(compras_facturas[0] or 0),
            "facturas_neto_clp": int(compras_facturas[1] or 0),
            "facturas_iva_clp": int(compras_facturas[2] or 0),
            "facturas_total_clp": int(compras_facturas[3] or 0),
            "notas_credito_cantidad": int(compras_nc[0] or 0),
            "notas_credito_iva_clp": int(compras_nc[2] or 0),
            "credito_fiscal_neto_clp": credito_fiscal_clp,
            "rut_empresa": rut_empresa,
            "excluidas_otro_receptor": {
                "facturas_cantidad": int(facturas_otro_rut[0] or 0),
                "facturas_iva_clp": int(facturas_otro_rut[1] or 0),
                "notas_credito_cantidad": int(nc_otro_rut[0] or 0),
                "notas_credito_iva_clp": int(nc_otro_rut[1] or 0),
            },
            "sin_receptor_cantidad": sin_receptor,
        },
        "borrador_f29": {
            "ventas_tributarias_neto_clp": neto_afecto_ventas,
            "debito_fiscal_clp": debito_fiscal_clp,
            "ventas_tributarias_total_clp": total_afecto_ventas,
            "credito_fiscal_clp": credito_fiscal_clp,
            "iva_determinado_clp": debito_fiscal_clp - credito_fiscal_clp,
            "ventas_en_transito_total_clp": sum(v["total_clp"] for v in ventas_en_transito),
            "ventas_en_transito_iva_clp": sum(v["iva_clp"] for v in ventas_en_transito),
            "caja_cobrada_mes_clp": int(caja_mes_clp or 0),
            "diferencia_ventas_vs_caja_clp": total_ventas_con_pendientes - int(caja_mes_clp or 0),
        },
    }


def exportar_tributario_csv(datos: dict) -> str:
    """Exporta el resumen tributario mensual (borrador F29) a CSV UTF-8 con BOM."""
    buf = io.StringIO()
    buf.write("\ufeff")
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Borrador Conciliación Tributaria (F29)", datos["periodo"], f"IVA {datos['iva_pct']}%", "Sin envío SII"])
    w.writerow([])
    w.writerow(["Tipo documento", "Cantidad", "Neto (CLP)", "IVA (CLP)", "Total (CLP)"])
    for tipo, b in datos["por_documento"].items():
        w.writerow([tipo, b["cantidad"], b["neto_clp"], b["iva_clp"], b["total_clp"]])
    w.writerow([])
    f29 = datos["borrador_f29"]
    w.writerow(["Resumen F29", "Monto (CLP)"])
    w.writerow(["Débito fiscal (IVA ventas)", f29["debito_fiscal_clp"]])
    w.writerow(["Crédito fiscal (IVA compras)", f29["credito_fiscal_clp"]])
    w.writerow(["IVA determinado (débito - crédito)", f29["iva_determinado_clp"]])
    w.writerow(["Ventas con tarjeta en tránsito (mes siguiente)", f29["ventas_en_transito_total_clp"]])
    w.writerow(["Caja cobrada del mes", f29["caja_cobrada_mes_clp"]])
    return buf.getvalue()
