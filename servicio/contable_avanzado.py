"""Contabilidad fases 2.3, 2.4 y 2.5 (#393, #394, #395 / KPI-002).

- 2.3 (#393): Cuadratura diaria de ocupación, noches devengadas, imputaciones y abonos (anticipos).
- 2.4 (#394): Cierre mensual congelado + matriz habitaciones × días (equivalente automatizado a «Ocupación 2026»)
  con exportación CSV lista para Excel.
- 2.5 (#395 / KPI-002): Indicadores ejecutivos reales calculados exclusivamente en el servidor
  (ocupación, ADR, RevPAR), devolviendo `None` («sin muestra») cuando no hay muestra — nunca cero inventado.
"""
from __future__ import annotations

import calendar
import csv
import io
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import psycopg
from psycopg.types.json import Json

from . import contabilidad, iva, panel, roles

ROLES_CUADRATURA = roles.con_admin_hotel("caja")
ROLES_EJECUTIVOS = roles.con_admin_hotel()
ROLES_REAPERTURA_MENSUAL = roles.con_admin_hotel()

_CODIGOS_CELDA = {
    "en_estadia": "OC",
    "finalizada": "FN",
    "confirmada": "CF",
    "mantenimiento": "MT",
    "fuera_de_servicio": "FS",
    "libre": "",
}


def _neto(bruto: int, tasa: Decimal) -> int:
    return int((Decimal(bruto) / (1 + tasa / 100)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _rango_mes(anio: int, mes: int) -> tuple[date, date, int]:
    if not (2020 <= anio <= 2100) or not (1 <= mes <= 12):
        raise contabilidad.DatosCajaInvalidos("indica un año (2020–2100) y mes (1–12) válidos")
    dias_mes = calendar.monthrange(anio, mes)[1]
    desde = date(anio, mes, 1)
    hasta = desde + timedelta(days=dias_mes)
    return desde, hasta, dias_mes


def _precios_noche_reservas(
    conexion: psycopg.Connection,
    reserva_ids: list[str],
    desde: date,
    hasta: date,
) -> dict[tuple[str, date], int]:
    if not reserva_ids:
        return {}
    return {
        (f[0], f[1]): int(f[2])
        for f in conexion.execute(
            "SELECT reserva_id, noche, precio_clp FROM reserva_noches "
            "WHERE reserva_id = ANY(%s) AND noche >= %s AND noche < %s",
            (reserva_ids, desde, hasta),
        ).fetchall()
    }


def _imputado_por_reserva_noche(
    conexion: psycopg.Connection,
    reserva_ids: list[str],
    desde: date,
    hasta: date,
) -> dict[tuple[str, date], int]:
    if not reserva_ids:
        return {}
    return {
        (f[0], f[1]): int(f[2])
        for f in conexion.execute(
            "SELECT reserva_id, noche, COALESCE(SUM(monto_clp), 0) "
            "FROM imputaciones_pago "
            "WHERE reserva_id = ANY(%s) AND noche >= %s AND noche < %s "
            "AND tipo IN ('consumo', 'aplicacion_anticipo', 'ajuste') "
            "GROUP BY reserva_id, noche",
            (reserva_ids, desde, hasta),
        ).fetchall()
    }


def _cargos_noche_asentados(
    conexion: psycopg.Connection,
    reserva_ids: list[str],
    noche: date,
) -> dict[str, int]:
    if not reserva_ids:
        return {}
    ref = f"noche:{noche.isoformat()}"
    return {
        f[0]: int(f[1])
        for f in conexion.execute(
            "SELECT c.reserva_id, COALESCE(SUM(c.monto_clp), 0) "
            "FROM cargos c "
            "WHERE c.reserva_id = ANY(%s) AND c.tipo = 'cargo' AND c.concepto = 'Noche' "
            "AND c.referencia = %s "
            "AND NOT EXISTS (SELECT 1 FROM cargos r WHERE r.reserva_id = c.reserva_id "
            "  AND r.tipo = 'reverso' AND r.referencia = c.id) "
            "GROUP BY c.reserva_id",
            (reserva_ids, ref),
        ).fetchall()
    }


# --- 2.3 (#393): Cuadratura diaria de ocupación, noches y abonos -----------------

def cuadratura_diaria(
    conexion: psycopg.Connection,
    empresa_id: str,
    fecha: date,
    solo_inventario_real: bool = False,
) -> dict:
    """Cruza la ocupación de la noche `fecha` contra noches devengadas, cargos asentados,
    imputaciones de pago, anticipos (abonos) y caja del día."""
    habitaciones = panel._habitaciones(conexion, None, solo_inventario_real=solo_inventario_real)
    ids = [h["habitacion_id"] for h in habitaciones]
    tasa = iva.tasa(conexion)

    reservas = conexion.execute(
        "SELECT r.id, r.habitacion_id, r.huesped_nombre, r.estado, r.inicio, r.fin, r.tarifa_noche_aceptada_clp "
        "FROM reservas r "
        "WHERE r.empresa_id = %s AND r.estado IN ('confirmada', 'en_estadia', 'finalizada') "
        "AND r.inicio <= %s AND r.fin > %s AND r.habitacion_id = ANY(%s) "
        "ORDER BY r.habitacion_id, r.id",
        (empresa_id, fecha, fecha, ids),
    ).fetchall()
    rids = [r[0] for r in reservas]
    precios_noche = _precios_noche_reservas(conexion, rids, fecha, fecha + timedelta(days=1))
    imputado_noche = _imputado_por_reserva_noche(conexion, rids, fecha, fecha + timedelta(days=1))
    cargos_noche = _cargos_noche_asentados(conexion, rids, fecha)

    # Anticipos por reserva (saldo de abono sin aplicar)
    abonos_reserva: dict[str, int] = {}
    if rids:
        for rid, libre in conexion.execute(
            "SELECT reserva_id, "
            "COALESCE(SUM(monto_clp) FILTER (WHERE tipo = 'anticipo'), 0) "
            "- COALESCE(SUM(monto_clp) FILTER (WHERE tipo = 'aplicacion_anticipo'), 0) "
            "FROM imputaciones_pago WHERE reserva_id = ANY(%s) GROUP BY reserva_id",
            (rids,),
        ).fetchall():
            abonos_reserva[rid] = int(libre or 0)

    disponibles = sum(1 for h in habitaciones if h["en_servicio"])
    fuera_servicio = sum(1 for h in habitaciones if not h["en_servicio"])
    ocupadas_estadia = 0
    confirmadas_sin_llegada = 0
    devengado_alojamiento = 0
    cargos_noche_total = 0
    imputado_noche_total = 0
    detalle_habitaciones = []
    diferencias: list[dict] = []

    por_hab = {r[1]: r for r in reservas}
    for h in habitaciones:
        hid = h["habitacion_id"]
        r = por_hab.get(hid)
        if r is None:
            continue
        rid, _hid, huesped, estado, ini, fin, tarifa_base = r
        precio = precios_noche.get((rid, fecha), int(tarifa_base or 0))
        asentado = cargos_noche.get(rid, 0)
        imputado = max(0, imputado_noche.get((rid, fecha), 0))
        abono_libre = max(0, abonos_reserva.get(rid, 0))
        pendiente_noche = max(0, precio - imputado)

        if estado == "confirmada":
            confirmadas_sin_llegada += 1
            diferencias.append({
                "tipo": "confirmada_sin_llegada",
                "habitacion_id": hid,
                "reserva_id": rid,
                "detalle": f"{hid}: reserva confirmada sin Llegada registrada para la noche {fecha.isoformat()}",
                "monto_clp": precio,
            })
        else:
            ocupadas_estadia += 1
            devengado_alojamiento += precio
            cargos_noche_total += asentado
            imputado_noche_total += min(imputado, precio)
            if asentado != precio:
                diferencias.append({
                    "tipo": "cargo_noche_distinto",
                    "habitacion_id": hid,
                    "reserva_id": rid,
                    "detalle": f"{hid}: precio congelado {precio} CLP vs cargo Noche asentado {asentado} CLP",
                    "monto_clp": precio - asentado,
                })
            if pendiente_noche > 0:
                diferencias.append({
                    "tipo": "noche_pendiente_pago",
                    "habitacion_id": hid,
                    "reserva_id": rid,
                    "detalle": f"{hid}: noche con saldo pendiente de {pendiente_noche} CLP",
                    "monto_clp": pendiente_noche,
                })

        detalle_habitaciones.append({
            "habitacion_id": hid,
            "tipo_habitacion": h["tipo"],
            "reserva_id": rid,
            "huesped_nombre": huesped,
            "estado_reserva": estado,
            "inicio": ini.isoformat(),
            "fin": fin.isoformat(),
            "precio_noche_clp": precio,
            "cargo_noche_asentado_clp": asentado,
            "imputado_noche_clp": imputado,
            "pendiente_noche_clp": pendiente_noche,
            "abono_sin_aplicar_clp": abono_libre,
        })

    # Movimientos de abonos (anticipos) en la fecha (hora Chile)
    (anticipos_recibidos_dia, anticipos_aplicados_dia) = conexion.execute(
        "SELECT "
        "COALESCE(SUM(i.monto_clp) FILTER (WHERE i.tipo = 'anticipo'), 0), "
        "COALESCE(SUM(i.monto_clp) FILTER (WHERE i.tipo = 'aplicacion_anticipo'), 0) "
        "FROM imputaciones_pago i JOIN reservas r ON r.id = i.reserva_id "
        "WHERE r.empresa_id = %s AND (i.creado_en AT TIME ZONE 'America/Santiago')::date = %s",
        (empresa_id, fecha),
    ).fetchone()

    # Saldo acumulado de abonos vigentes (pasivo) al cierre de `fecha`
    (saldo_anticipos_vigentes,) = conexion.execute(
        "SELECT COALESCE(SUM(i.monto_clp) FILTER (WHERE i.tipo = 'anticipo'), 0) "
        "- COALESCE(SUM(i.monto_clp) FILTER (WHERE i.tipo = 'aplicacion_anticipo'), 0) "
        "FROM imputaciones_pago i JOIN reservas r ON r.id = i.reserva_id "
        "WHERE r.empresa_id = %s AND (i.creado_en AT TIME ZONE 'America/Santiago')::date <= %s",
        (empresa_id, fecha),
    ).fetchone()

    # Cruce con pagos del día y caja del día
    (pagos_reservas_dia,) = conexion.execute(
        "SELECT COALESCE(SUM(CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END), 0) "
        "FROM pagos p JOIN reservas r ON r.id = p.reserva_id "
        "WHERE r.empresa_id = %s AND p.fecha_contable = %s AND p.estado = 'confirmado'",
        (empresa_id, fecha),
    ).fetchone()
    (directos_cobrados_dia,) = conexion.execute(
        "SELECT COALESCE(SUM(CASE "
        "  WHEN d.tipo = 'cargo_directo' AND d.estado_cobro = 'cobrado' THEN d.monto_clp "
        "  WHEN d.tipo = 'reverso_directo' AND o.tipo = 'cargo_directo' AND o.estado_cobro = 'cobrado' THEN -d.monto_clp "
        "  ELSE 0 END), 0) "
        "FROM movimientos_directos d LEFT JOIN movimientos_directos o ON o.id = d.referencia_id "
        "WHERE d.empresa_id = %s AND d.fecha_contable = %s",
        (empresa_id, fecha),
    ).fetchone()
    (caja_cobros_dia,) = conexion.execute(
        "SELECT COALESCE(SUM(monto_clp), 0) FROM caja_movimientos "
        "WHERE empresa_id = %s AND fecha_contable = %s "
        "AND tipo IN ('cobro', 'reverso_cobro', 'cobro_directo', 'reverso_directo')",
        (empresa_id, fecha),
    ).fetchone()
    # Pagos históricos sin movimiento en caja (no_informado sin turno)
    (pagos_sin_caja,) = conexion.execute(
        "SELECT COALESCE(SUM(CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END), 0) "
        "FROM pagos p JOIN reservas r ON r.id = p.reserva_id "
        "WHERE r.empresa_id = %s AND p.fecha_contable = %s AND p.estado = 'confirmado' "
        "AND NOT EXISTS (SELECT 1 FROM caja_movimientos m WHERE m.pago_id = p.id)",
        (empresa_id, fecha),
    ).fetchone()
    total_libro_cobros = int(pagos_reservas_dia) + int(directos_cobrados_dia)
    total_caja_equivalente = int(caja_cobros_dia) + int(pagos_sin_caja)
    dif_caja_libro = total_libro_cobros - total_caja_equivalente
    if dif_caja_libro != 0:
        diferencias.append({
            "tipo": "diferencia_caja_vs_libro",
            "habitacion_id": None,
            "reserva_id": None,
            "detalle": f"Diferencia entre cobros del libro ({total_libro_cobros} CLP) y caja ({total_caja_equivalente} CLP)",
            "monto_clp": dif_caja_libro,
        })

    ocupacion_ratio = (ocupadas_estadia / disponibles) if disponibles > 0 else None
    adr_clp = round(devengado_alojamiento / ocupadas_estadia) if ocupadas_estadia > 0 else None
    revpar_clp = round(devengado_alojamiento / disponibles) if disponibles > 0 else None

    return {
        "fecha": fecha.isoformat(),
        "ocupacion": {
            "habitaciones_disponibles": disponibles,
            "habitaciones_fuera_de_servicio": fuera_servicio,
            "noches_ocupadas": ocupadas_estadia,
            "confirmadas_sin_llegada": confirmadas_sin_llegada,
            "ocupacion_proporcion": round(ocupacion_ratio, 4) if ocupacion_ratio is not None else None,
            "ocupacion_pct": round(ocupacion_ratio * 100, 1) if ocupacion_ratio is not None else None,
        },
        "noches": {
            "devengado_alojamiento_clp": devengado_alojamiento,
            "devengado_alojamiento_neto_clp": _neto(devengado_alojamiento, tasa),
            "cargos_noche_asentados_clp": cargos_noche_total,
            "imputado_noche_clp": imputado_noche_total,
            "pendiente_noche_clp": max(0, devengado_alojamiento - imputado_noche_total),
            "adr_clp": adr_clp,
            "revpar_clp": revpar_clp,
            "iva_pct": float(tasa),
        },
        "abonos": {
            "recibidos_dia_clp": int(anticipos_recibidos_dia or 0),
            "aplicados_dia_clp": int(anticipos_aplicados_dia or 0),
            "saldo_vigente_clp": int(saldo_anticipos_vigentes or 0),
        },
        "cobros": {
            "pagos_reservas_dia_clp": int(pagos_reservas_dia or 0),
            "directos_cobrados_dia_clp": int(directos_cobrados_dia or 0),
            "total_libro_clp": total_libro_cobros,
            "total_caja_clp": total_caja_equivalente,
            "diferencia_clp": dif_caja_libro,
        },
        "detalle_habitaciones": detalle_habitaciones,
        "diferencias": diferencias,
        "cuadra": len(diferencias) == 0,
    }


# --- 2.4 (#394): Matriz mensual habitaciones × días y cierre mensual -------------

def matriz_mensual(
    conexion: psycopg.Connection,
    empresa_id: str,
    anio: int,
    mes: int,
    solo_inventario_real: bool = False,
    hoy: date | None = None,
) -> dict:
    """Construye la matriz habitaciones × días del mes (equivalente a «Ocupación 2026»)
    con totales por habitación, totales por día y KPIs reales del mes."""
    desde, hasta, dias_mes = _rango_mes(anio, mes)
    hoy = hoy or contabilidad.hoy_chile()
    tasa = iva.tasa(conexion)
    dias = [desde + timedelta(days=i) for i in range(dias_mes)]

    habitaciones = panel._habitaciones(conexion, None, solo_inventario_real=solo_inventario_real)
    ids = [h["habitacion_id"] for h in habitaciones]
    reservas = panel._reservas_del_periodo(conexion, empresa_id, desde, hasta, ids)
    rids = [r["reserva_id"] for r in reservas]

    tarifas_base = {}
    if rids:
        for rid, tbase in conexion.execute(
            "SELECT id, tarifa_noche_aceptada_clp FROM reservas WHERE id = ANY(%s)", (rids,)
        ).fetchall():
            tarifas_base[rid] = int(tbase or 0)
    precios_noche = _precios_noche_reservas(conexion, rids, desde, hasta)
    imputado_noche = _imputado_por_reserva_noche(conexion, rids, desde, hasta)

    totales_dia = {
        d: {"fecha": d.isoformat(), "dia": d.day, "disponibles": 0, "ocupadas": 0, "confirmadas": 0,
            "mantenimiento": 0, "fuera_de_servicio": 0, "ingreso_alojamiento_clp": 0, "imputado_clp": 0}
        for d in dias
    }

    filas_matriz = []
    total_unidades_mes = 0
    total_ocupadas_mes = 0
    total_confirmadas_mes = 0
    total_ingreso_mes = 0
    total_imputado_mes = 0

    for h in habitaciones:
        hid = h["habitacion_id"]
        propias = [r for r in reservas if r["habitacion_id"] == hid]
        celdas = []
        occ_hab = 0
        conf_hab = 0
        disp_hab = 0
        ing_hab = 0
        imp_hab = 0

        for d in dias:
            estadia = next(
                (r for r in propias if r["estado"] in ("en_estadia", "finalizada") and panel._contiene(r, d)),
                None,
            )
            confirmada = next(
                (r for r in propias if r["estado"] == "confirmada" and panel._contiene(r, d)),
                None,
            )
            en_servicio = h["en_servicio"]
            if en_servicio:
                disp_hab += 1
                totales_dia[d]["disponibles"] += 1
                total_unidades_mes += 1
            else:
                totales_dia[d]["fuera_de_servicio"] += 1

            if estadia:
                precio = precios_noche.get((estadia["reserva_id"], d), tarifas_base.get(estadia["reserva_id"], 0))
                pag = min(max(0, imputado_noche.get((estadia["reserva_id"], d), 0)), precio)
                estado = estadia["estado"]
                occ_hab += 1
                ing_hab += precio
                imp_hab += pag
                totales_dia[d]["ocupadas"] += 1
                totales_dia[d]["ingreso_alojamiento_clp"] += precio
                totales_dia[d]["imputado_clp"] += pag
                total_ocupadas_mes += 1
                total_ingreso_mes += precio
                total_imputado_mes += pag
                celdas.append({
                    "fecha": d.isoformat(),
                    "dia": d.day,
                    "estado": estado,
                    "codigo": _CODIGOS_CELDA[estado],
                    "reserva_id": estadia["reserva_id"],
                    "tarifa_clp": precio,
                    "imputado_clp": pag,
                    "pendiente_clp": max(0, precio - pag),
                })
            elif confirmada:
                precio = precios_noche.get((confirmada["reserva_id"], d), tarifas_base.get(confirmada["reserva_id"], 0))
                conf_hab += 1
                totales_dia[d]["confirmadas"] += 1
                total_confirmadas_mes += 1
                celdas.append({
                    "fecha": d.isoformat(),
                    "dia": d.day,
                    "estado": "confirmada",
                    "codigo": _CODIGOS_CELDA["confirmada"],
                    "reserva_id": confirmada["reserva_id"],
                    "tarifa_clp": precio,
                    "imputado_clp": 0,
                    "pendiente_clp": precio,
                })
            elif not en_servicio:
                celdas.append({"fecha": d.isoformat(), "dia": d.day, "estado": "fuera_de_servicio", "codigo": "FS"})
            elif panel._mantenimiento_en(h, d, hoy):
                totales_dia[d]["mantenimiento"] += 1
                celdas.append({"fecha": d.isoformat(), "dia": d.day, "estado": "mantenimiento", "codigo": "MT"})
            else:
                celdas.append({"fecha": d.isoformat(), "dia": d.day, "estado": "libre", "codigo": ""})

        filas_matriz.append({
            "habitacion_id": hid,
            "tipo": h["tipo"],
            "en_servicio": h["en_servicio"],
            "celdas": celdas,
            "totales": {
                "noches_disponibles": disp_hab,
                "noches_ocupadas": occ_hab,
                "noches_confirmadas": conf_hab,
                "ocupacion_pct": round(100 * occ_hab / disp_hab, 1) if disp_hab > 0 else None,
                "ingreso_alojamiento_clp": ing_hab,
                "imputado_clp": imp_hab,
                "pendiente_clp": max(0, ing_hab - imp_hab),
            },
        })

    # Completar ocupación % por día
    resumen_diario = []
    for d in dias:
        td = totales_dia[d]
        td["ocupacion_pct"] = round(100 * td["ocupadas"] / td["disponibles"], 1) if td["disponibles"] > 0 else None
        resumen_diario.append(td)

    # Cobros percibidos y egresos del mes (contabilidad por fecha_contable)
    (cobros_reservas_mes,) = conexion.execute(
        "SELECT COALESCE(SUM(CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END), 0) "
        "FROM pagos p JOIN reservas r ON r.id = p.reserva_id "
        "WHERE r.empresa_id = %s AND p.estado = 'confirmado' AND p.fecha_contable >= %s AND p.fecha_contable < %s",
        (empresa_id, desde, hasta),
    ).fetchone()
    (ingresos_directos_mes, egresos_directos_mes) = conexion.execute(
        "SELECT "
        "COALESCE(SUM(CASE WHEN d.tipo = 'cargo_directo' THEN d.monto_clp "
        "  WHEN d.tipo = 'reverso_directo' AND o.tipo = 'cargo_directo' THEN -d.monto_clp ELSE 0 END), 0), "
        "COALESCE(SUM(CASE WHEN d.tipo = 'egreso_operacional' THEN d.monto_clp "
        "  WHEN d.tipo = 'reverso_directo' AND o.tipo = 'egreso_operacional' THEN -d.monto_clp ELSE 0 END), 0) "
        "FROM movimientos_directos d LEFT JOIN movimientos_directos o ON o.id = d.referencia_id "
        "WHERE d.empresa_id = %s AND d.fecha_contable >= %s AND d.fecha_contable < %s",
        (empresa_id, desde, hasta),
    ).fetchone()
    (consumos_reserva_mes,) = conexion.execute(
        "SELECT COALESCE(SUM(CASE WHEN c.tipo = 'reverso' THEN -c.monto_clp ELSE c.monto_clp END), 0) "
        "FROM cargos c JOIN reservas r ON r.id = c.reserva_id "
        "WHERE r.empresa_id = %s AND (c.creado_en AT TIME ZONE 'America/Santiago')::date >= %s "
        "AND (c.creado_en AT TIME ZONE 'America/Santiago')::date < %s "
        "AND c.concepto <> 'Noche' AND NOT (c.tipo = 'reverso' AND EXISTS ("
        "  SELECT 1 FROM cargos o WHERE o.id = c.referencia AND o.concepto = 'Noche'))",
        (empresa_id, desde, hasta),
    ).fetchone()

    # Verificar cierres diarios del mes (hasta hoy o último día del mes)
    corte_cierres = min(hasta - timedelta(days=1), hoy)
    dias_exigibles = [d for d in dias if d <= corte_cierres]
    cerrados = {
        f[0] for f in conexion.execute(
            "SELECT fecha FROM cierres_diarios "
            "WHERE empresa_id = %s AND estado = 'cerrado' AND fecha >= %s AND fecha < %s",
            (empresa_id, desde, hasta),
        ).fetchall()
    }
    dias_sin_cerrar = [d.isoformat() for d in dias_exigibles if d not in cerrados]
    alertas = []
    if dias_sin_cerrar:
        alertas.append(f"Hay {len(dias_sin_cerrar)} día(s) del mes sin cierre diario cerrado")

    ocupacion_ratio = (total_ocupadas_mes / total_unidades_mes) if total_unidades_mes > 0 else None
    adr_clp = round(total_ingreso_mes / total_ocupadas_mes) if total_ocupadas_mes > 0 else None
    revpar_clp = round(total_ingreso_mes / total_unidades_mes) if total_unidades_mes > 0 else None
    total_devengado_mes = total_ingreso_mes + int(consumos_reserva_mes or 0) + int(ingresos_directos_mes or 0)

    cierre = conexion.execute(
        "SELECT estado, cerrado_por, cerrado_en, nota, reabierto_por, motivo_reapertura "
        "FROM cierres_mensuales WHERE empresa_id = %s AND anio = %s AND mes = %s",
        (empresa_id, anio, mes),
    ).fetchone()

    return {
        "periodo": f"{anio:04d}-{mes:02d}",
        "anio": anio,
        "mes": mes,
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "dias": [d.isoformat() for d in dias],
        "matriz": filas_matriz,
        "totales_por_dia": resumen_diario,
        "resumen": {
            "unidades_noche": total_unidades_mes,
            "noches_ocupadas": total_ocupadas_mes,
            "noches_confirmadas": total_confirmadas_mes,
            "ocupacion_proporcion": round(ocupacion_ratio, 4) if ocupacion_ratio is not None else None,
            "ocupacion_pct": round(ocupacion_ratio * 100, 1) if ocupacion_ratio is not None else None,
            "ingreso_alojamiento_clp": total_ingreso_mes,
            "ingreso_alojamiento_neto_clp": _neto(total_ingreso_mes, tasa),
            "ingreso_consumos_reserva_clp": int(consumos_reserva_mes or 0),
            "ingreso_directo_clp": int(ingresos_directos_mes or 0),
            "total_devengado_clp": total_devengado_mes,
            "total_devengado_neto_clp": _neto(total_devengado_mes, tasa),
            "egresos_operacionales_clp": int(egresos_directos_mes or 0),
            "cobros_reservas_clp": int(cobros_reservas_mes or 0),
            "imputado_alojamiento_clp": total_imputado_mes,
            "adr_clp": adr_clp,
            "adr_neto_clp": _neto(adr_clp, tasa) if adr_clp is not None else None,
            "revpar_clp": revpar_clp,
            "revpar_neto_clp": _neto(revpar_clp, tasa) if revpar_clp is not None else None,
            "iva_pct": float(tasa),
            "dias_cerrados": len(cerrados),
            "dias_sin_cerrar": len(dias_sin_cerrar),
        },
        "alertas": alertas,
        "cierre": (
            {
                "estado": cierre[0],
                "cerrado_por": cierre[1],
                "cerrado_en": cierre[2].isoformat(),
                "nota": cierre[3],
                "reabierto_por": cierre[4],
                "motivo_reapertura": cierre[5],
            }
            if cierre
            else None
        ),
    }


def exportar_matriz_mensual_csv(datos: dict) -> str:
    """Exporta la matriz habitaciones × días a CSV (UTF-8 con BOM para Excel), equivalente a «Ocupación 2026»."""
    buf = io.StringIO()
    buf.write("\ufeff")
    escritor = csv.writer(buf, delimiter=";")
    dias_headers = [d[-2:] for d in datos["dias"]]
    escritor.writerow([
        "Habitación", "Tipo", *dias_headers,
        "Noches ocupadas", "Ocupación %", "Ingreso alojamiento (CLP)", "Imputado (CLP)", "Pendiente (CLP)",
    ])
    for fila in datos["matriz"]:
        tot = fila["totales"]
        escritor.writerow([
            fila["habitacion_id"],
            fila["tipo"],
            *[c["codigo"] for c in fila["celdas"]],
            tot["noches_ocupadas"],
            "" if tot["ocupacion_pct"] is None else f"{tot['ocupacion_pct']:.1f}".replace(".", ","),
            tot["ingreso_alojamiento_clp"],
            tot["imputado_clp"],
            tot["pendiente_clp"],
        ])
    res = datos["resumen"]
    escritor.writerow([
        "TOTAL OCUPADAS", "",
        *[td["ocupadas"] for td in datos["totales_por_dia"]],
        res["noches_ocupadas"],
        "" if res["ocupacion_pct"] is None else f"{res['ocupacion_pct']:.1f}".replace(".", ","),
        res["ingreso_alojamiento_clp"],
        res["imputado_alojamiento_clp"],
        max(0, res["ingreso_alojamiento_clp"] - res["imputado_alojamiento_clp"]),
    ])
    escritor.writerow([
        "DISPONIBLES", "",
        *[td["disponibles"] for td in datos["totales_por_dia"]],
        res["unidades_noche"], "", "", "", "",
    ])
    escritor.writerow([
        "INGRESO DIARIO (CLP)", "",
        *[td["ingreso_alojamiento_clp"] for td in datos["totales_por_dia"]],
        res["ingreso_alojamiento_clp"], "", "", "", "",
    ])
    return buf.getvalue()


def obtener_cierre_mensual(
    conexion: psycopg.Connection,
    empresa_id: str,
    anio: int,
    mes: int,
    solo_inventario_real: bool = False,
) -> dict:
    """Mes cerrado: devuelve el cierre congelado. Mes abierto/reabierto: calcula en vivo."""
    _rango_mes(anio, mes)
    fila = conexion.execute(
        "SELECT resumen, estado, cerrado_por, cerrado_en, nota, reabierto_por, motivo_reapertura "
        "FROM cierres_mensuales WHERE empresa_id = %s AND anio = %s AND mes = %s",
        (empresa_id, anio, mes),
    ).fetchone()
    if fila and fila[1] == "cerrado":
        return {
            **fila[0],
            "cierre": {
                "estado": fila[1],
                "cerrado_por": fila[2],
                "cerrado_en": fila[3].isoformat(),
                "nota": fila[4],
                "reabierto_por": fila[5],
                "motivo_reapertura": fila[6],
            },
            "congelada": True,
        }
    vivo = matriz_mensual(conexion, empresa_id, anio, mes, solo_inventario_real=solo_inventario_real)
    return {**vivo, "congelada": False}


def cerrar_mes(
    conexion: psycopg.Connection,
    empresa_id: str,
    anio: int,
    mes: int,
    usuario_id: str,
    actor: str,
    nota: str | None = None,
    confirmar_alertas: bool = False,
    solo_inventario_real: bool = False,
    hoy: date | None = None,
) -> dict:
    desde, _hasta, _dias = _rango_mes(anio, mes)
    hoy = hoy or contabilidad.hoy_chile()
    if desde > hoy:
        raise contabilidad.OperacionCajaInvalida("no se puede cerrar un mes que aún no comienza")
    conexion.execute("SELECT pg_advisory_xact_lock(hashtext('cierre_mensual'), hashtext(%s))", (empresa_id,))
    existente = conexion.execute(
        "SELECT estado FROM cierres_mensuales WHERE empresa_id = %s AND anio = %s AND mes = %s",
        (empresa_id, anio, mes),
    ).fetchone()
    if existente and existente[0] == "cerrado":
        raise contabilidad.OperacionCajaInvalida(f"el mes {anio:04d}-{mes:02d} ya está cerrado")
    datos = matriz_mensual(conexion, empresa_id, anio, mes, solo_inventario_real=solo_inventario_real, hoy=hoy)
    if datos["alertas"] and not confirmar_alertas:
        raise contabilidad.OperacionCajaInvalida("revisa las alertas del mes (días sin cierre diario) y confirma el cierre")
    nota_limpia = (nota or "").strip()[:1000] or None
    snapshot = {k: v for k, v in datos.items() if k != "cierre"}
    conexion.execute(
        "INSERT INTO cierres_mensuales (empresa_id, anio, mes, estado, usuario_id, cerrado_por, nota, resumen) "
        "VALUES (%s, %s, %s, 'cerrado', %s, %s, %s, %s) "
        "ON CONFLICT (empresa_id, anio, mes) DO UPDATE SET estado = 'cerrado', usuario_id = EXCLUDED.usuario_id, "
        "cerrado_por = EXCLUDED.cerrado_por, cerrado_en = now(), nota = EXCLUDED.nota, resumen = EXCLUDED.resumen",
        (empresa_id, anio, mes, usuario_id, actor, nota_limpia, Json(snapshot)),
    )
    return {
        "periodo": f"{anio:04d}-{mes:02d}",
        "anio": anio,
        "mes": mes,
        "estado": "cerrado",
        "cerrado_por": actor,
        "resumen": snapshot["resumen"],
    }


def reabrir_mes(
    conexion: psycopg.Connection,
    empresa_id: str,
    anio: int,
    mes: int,
    actor: str,
    motivo: str,
) -> dict:
    _rango_mes(anio, mes)
    motivo_limpio = (motivo or "").strip()
    if len(motivo_limpio) < contabilidad.MIN_JUSTIFICACION:
        raise contabilidad.DatosCajaInvalidos("explica el motivo de la reapertura mensual (mínimo 10 caracteres)")
    fila = conexion.execute(
        "SELECT estado FROM cierres_mensuales WHERE empresa_id = %s AND anio = %s AND mes = %s",
        (empresa_id, anio, mes),
    ).fetchone()
    if not fila or fila[0] != "cerrado":
        raise contabilidad.OperacionCajaInvalida(f"el mes {anio:04d}-{mes:02d} no está cerrado")
    conexion.execute(
        "UPDATE cierres_mensuales SET estado = 'reabierto', reabierto_por = %s, reabierto_en = now(), "
        "motivo_reapertura = %s WHERE empresa_id = %s AND anio = %s AND mes = %s",
        (actor, motivo_limpio[:500], empresa_id, anio, mes),
    )
    return {"periodo": f"{anio:04d}-{mes:02d}", "anio": anio, "mes": mes, "estado": "reabierto", "reabierto_por": actor}


# --- 2.5 (#395 / KPI-002): Indicadores ejecutivos reales -------------------------

def indicadores_ejecutivos(
    conexion: psycopg.Connection,
    empresa_id: str,
    desde: date,
    hasta: date,
    hoy: date,
    tipo: str | None = None,
    *,
    solo_inventario_real: bool = False,
) -> dict:
    """Indicadores ejecutivos reales (ocupación, ADR y RevPAR) calculados en el servidor.

    Regla estricta de veracidad (`KPI-002`):
    - Sin muestra (unidades-noche == 0 o noches ocupadas == 0 para ADR) → `None`, NUNCA cero inventado.
    - Base de alojamiento: noches realmente alojadas (`en_estadia`/`finalizada`) con fecha <= `hoy`,
      valoradas al precio congelado en `reserva_noches` (respaldo `tarifa_noche_aceptada_clp`),
      informando valor con IVA incluido y neto según tasa vigente.
    """
    noches = panel.validar_periodo(desde, hasta, panel.MAX_NOCHES_INDICADORES)
    habitaciones = panel._habitaciones(conexion, tipo, solo_inventario_real=solo_inventario_real)
    ids = [h["habitacion_id"] for h in habitaciones]
    reservas = panel._reservas_del_periodo(conexion, empresa_id, desde, hasta, ids)
    rids = [r["reserva_id"] for r in reservas]

    tarifas_base = {}
    if rids:
        for rid, tbase in conexion.execute(
            "SELECT id, tarifa_noche_aceptada_clp FROM reservas WHERE id = ANY(%s)", (rids,)
        ).fetchall():
            tarifas_base[rid] = int(tbase or 0)
    precios_noche = _precios_noche_reservas(conexion, rids, desde, hasta)
    tasa = iva.tasa(conexion)

    unidades_pasadas = 0
    noches_ocupadas = 0
    ingreso_alojamiento = 0
    serie = []

    for noche in noches:
        con_noche = [r for r in reservas if r["estado"] in panel.ESTADOS_CON_NOCHES and panel._contiene(r, noche)]
        activas = {
            h["habitacion_id"] for h in habitaciones
            if h["registrada_el"] <= noche and h["estado_operativo"] != "fuera_de_servicio"
        }
        activas |= {r["habitacion_id"] for r in con_noche}
        n_activas = len(activas)
        if noche <= hoy:
            estadias_noche = [r for r in con_noche if r["estado"] in ("en_estadia", "finalizada")]
            por_hab: dict[str, int] = {}
            for r in estadias_noche:
                por_hab[r["habitacion_id"]] = precios_noche.get(
                    (r["reserva_id"], noche), tarifas_base.get(r["reserva_id"], 0)
                )
            occ = len(por_hab)
            ing = sum(por_hab.values())
            unidades_pasadas += n_activas
            noches_ocupadas += occ
            ingreso_alojamiento += ing
            serie.append({
                "fecha": noche.isoformat(),
                "unidades": n_activas,
                "noches_ocupadas": occ,
                "ocupacion": round(occ / n_activas, 4) if n_activas > 0 else None,
                "ingreso_alojamiento_clp": ing,
                "adr_clp": round(ing / occ) if occ > 0 else None,
                "revpar_clp": round(ing / n_activas) if n_activas > 0 else None,
            })
        else:
            serie.append({
                "fecha": noche.isoformat(),
                "unidades": n_activas,
                "noches_ocupadas": None,
                "ocupacion": None,
                "ingreso_alojamiento_clp": None,
                "adr_clp": None,
                "revpar_clp": None,
            })

    ocupacion = (noches_ocupadas / unidades_pasadas) if unidades_pasadas > 0 else None
    adr_clp = round(ingreso_alojamiento / noches_ocupadas) if noches_ocupadas > 0 else None
    revpar_clp = round(ingreso_alojamiento / unidades_pasadas) if unidades_pasadas > 0 else None
    ingreso_val = ingreso_alojamiento if unidades_pasadas > 0 else None

    return {
        "fecha_corte": hoy.isoformat(),
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "noches": len(noches)},
        "filtros": {"tipo": tipo},
        "iva_pct": float(tasa),
        "unidades_noche_pasadas": unidades_pasadas,
        "noches_ocupadas": noches_ocupadas,
        "ocupacion": round(ocupacion, 4) if ocupacion is not None else None,
        "ingreso_alojamiento_clp": ingreso_val,
        "ingreso_alojamiento_neto_clp": _neto(ingreso_val, tasa) if ingreso_val is not None else None,
        "adr_clp": adr_clp,
        "adr_neto_clp": _neto(adr_clp, tasa) if adr_clp is not None else None,
        "revpar_clp": revpar_clp,
        "revpar_neto_clp": _neto(revpar_clp, tasa) if revpar_clp is not None else None,
        "serie": serie,
    }
