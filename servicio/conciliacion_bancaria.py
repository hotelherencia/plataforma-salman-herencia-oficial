"""Contable 2.6 (#396 / FIN-003, FIN-004, FIN-006): Conciliación bancaria con cartola.

Reglas clave:
- Comisiones y días hábiles de abono por medio (ej. Transbank débito/crédito) viven
  en `comisiones_medios` (configurables por `admin_hotel`, nunca hardcodeadas).
- Importación de cartola CSV con vista previa, hash SHA-256 anti-duplicado, mapeo
  de columnas configurable por banco y reporte explícito de filas rechazadas.
- Cruce automático con retiros para depósito, transferencias y liquidaciones de
  tarjetas descontando comisión y respetando desfase de días hábiles.
- Ventas de un mes cuyo abono cae en el mes siguiente quedan marcadas «en tránsito».
- Conciliación manual muchos-a-muchos: exige justificación >= 10 caracteres,
  audita el emparejamiento y jamás supera el saldo disponible ni del movimiento
  bancario ni del movimiento interno (append-only).
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import uuid
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import psycopg
from psycopg.types.json import Jsonb

from . import contabilidad, iva, roles, seguridad

ROLES_CONCILIACION = roles.con_admin_hotel("caja")
ROLES_COMISIONES = roles.con_admin_hotel()

_COMISIONES_DEFECTO = {
    "efectivo": {"proveedor": "caja", "porcentaje_comision": Decimal("0"), "iva_comision": False, "dias_habiles_abono": 0, "cuenta_deposito": None, "mapeo_columnas": {}},
    "transferencia": {"proveedor": "banco", "porcentaje_comision": Decimal("0"), "iva_comision": False, "dias_habiles_abono": 0, "cuenta_deposito": None, "mapeo_columnas": {}},
    "debito": {"proveedor": "transbank", "porcentaje_comision": Decimal("0"), "iva_comision": True, "dias_habiles_abono": 1, "cuenta_deposito": None, "mapeo_columnas": {}},
    "credito": {"proveedor": "transbank", "porcentaje_comision": Decimal("0"), "iva_comision": True, "dias_habiles_abono": 2, "cuenta_deposito": None, "mapeo_columnas": {}},
}


class ConciliacionInvalida(ValueError):
    """422: datos inválidos de cartola, comisión o emparejamiento."""


class ConciliacionConflicto(Exception):
    """409: cartola duplicada o asignación excede monto disponible."""


def _sumar_dias_habiles(fecha: date, dias: int) -> date:
    actual = fecha
    restantes = max(0, int(dias))
    while restantes > 0:
        actual += timedelta(days=1)
        if actual.weekday() < 5:
            restantes -= 1
    return actual


def _parsear_fecha(texto: str) -> date:
    limpio = (texto or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", limpio):
        return date.fromisoformat(limpio)
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", limpio)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    raise ValueError(f"fecha inválida «{limpio}»")


def _parsear_monto(texto: str) -> int:
    limpio = (texto or "").strip().replace("$", "").replace(" ", "")
    if not limpio:
        raise ValueError("monto vacío")
    if "." in limpio and "," in limpio:
        limpio = limpio.replace(".", "").split(",")[0]
    elif limpio.count(".") >= 1 and re.fullmatch(r"-?\d{1,3}(\.\d{3})+", limpio):
        limpio = limpio.replace(".", "")
    else:
        limpio = limpio.replace(",", "")
    return int(limpio)


# --- Configuración de comisiones y desfase por medio ----------------------------

def _parsear_porcentaje_exacto(valor) -> Decimal:
    """Convierte porcentaje de comisión a Decimal exacto (sin pasar por float), máximo 3 decimales."""
    if isinstance(valor, bool):
        raise ConciliacionInvalida("porcentaje de comisión inválido")
    try:
        dec = valor if isinstance(valor, Decimal) else Decimal(str(valor).strip())
    except (InvalidOperation, ValueError, TypeError) as err:
        raise ConciliacionInvalida("porcentaje de comisión inválido") from err
    if not dec.is_finite():
        raise ConciliacionInvalida("porcentaje de comisión inválido")
    if dec < Decimal("0") or dec > Decimal("30"):
        raise ConciliacionInvalida("el porcentaje de comisión debe estar entre 0 y 30 %")
    return dec.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def obtener_comisiones(conexion: psycopg.Connection, empresa_id: str) -> dict[str, dict]:
    salida = {
        m: {
            "medio": m,
            **cfg,
            "porcentaje_comision": float(cfg["porcentaje_comision"]),
            "porcentaje_comision_exacto": str(cfg["porcentaje_comision"].quantize(Decimal("0.001"))),
        }
        for m, cfg in _COMISIONES_DEFECTO.items()
    }
    for f in conexion.execute(
        "SELECT medio, proveedor, porcentaje_comision, iva_comision, dias_habiles_abono, "
        "cuenta_deposito, mapeo_columnas FROM comisiones_medios WHERE empresa_id = %s",
        (empresa_id,),
    ).fetchall():
        pct_exacto = _parsear_porcentaje_exacto(f[2])
        salida[f[0]] = {
            "medio": f[0],
            "proveedor": f[1],
            "porcentaje_comision": float(pct_exacto),
            "porcentaje_comision_exacto": str(pct_exacto),
            "iva_comision": bool(f[3]),
            "dias_habiles_abono": int(f[4]),
            "cuenta_deposito": f[5],
            "mapeo_columnas": f[6] or {},
        }
    return salida


def guardar_comisiones(
    conexion: psycopg.Connection,
    empresa_id: str,
    items: list[dict],
    actor: str,
) -> dict[str, dict]:
    if not items:
        raise ConciliacionInvalida("indica al menos un medio para configurar")
    with conexion.transaction():
        for it in items:
            medio = it["medio"]
            if medio not in _COMISIONES_DEFECTO:
                raise ConciliacionInvalida(f"medio inválido: {medio}")
            pct = _parsear_porcentaje_exacto(it.get("porcentaje_comision", Decimal("0")))
            dias = int(it.get("dias_habiles_abono", 0))
            if not (0 <= dias <= 30):
                raise ConciliacionInvalida("los días hábiles de abono deben estar entre 0 y 30")
            conexion.execute(
                "INSERT INTO comisiones_medios "
                "(empresa_id, medio, proveedor, porcentaje_comision, iva_comision, dias_habiles_abono, "
                "cuenta_deposito, mapeo_columnas, actualizado_por) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (empresa_id, medio) DO UPDATE SET "
                "proveedor = EXCLUDED.proveedor, porcentaje_comision = EXCLUDED.porcentaje_comision, "
                "iva_comision = EXCLUDED.iva_comision, dias_habiles_abono = EXCLUDED.dias_habiles_abono, "
                "cuenta_deposito = EXCLUDED.cuenta_deposito, mapeo_columnas = EXCLUDED.mapeo_columnas, "
                "actualizado_por = EXCLUDED.actualizado_por, actualizado_en = now()",
                (
                    empresa_id, medio, (it.get("proveedor") or "general").strip()[:60],
                    pct, bool(it.get("iva_comision", True)), dias,
                    (it.get("cuenta_deposito") or "").strip()[:80] or None,
                    Jsonb(it.get("mapeo_columnas") or {}), actor,
                ),
            )
        seguridad.auditar(conexion, actor, "comisiones_medios", empresa_id, f"medios={len(items)}")
    return obtener_comisiones(conexion, empresa_id)


def calcular_abono_esperado(monto_bruto_clp: int, cfg_medio: dict, tasa_iva: Decimal) -> tuple[int, int]:
    """Devuelve (abono_esperado_clp, comision_total_clp) usando aritmética Decimal exacta (sin float)."""
    raw_pct = cfg_medio.get("porcentaje_comision_exacto")
    if raw_pct is None:
        raw_pct = cfg_medio.get("porcentaje_comision")
    pct = raw_pct if isinstance(raw_pct, Decimal) else _parsear_porcentaje_exacto(raw_pct or 0)
    if pct <= Decimal("0"):
        return int(monto_bruto_clp), 0
    tasa = tasa_iva if isinstance(tasa_iva, Decimal) else Decimal(str(tasa_iva))
    comision_neta = (Decimal(int(monto_bruto_clp)) * pct) / Decimal("100")
    if cfg_medio.get("iva_comision", True):
        comision_total = comision_neta * (Decimal("1") + tasa / Decimal("100"))
    else:
        comision_total = comision_neta
    comision_clp = int(comision_total.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return max(0, int(monto_bruto_clp) - comision_clp), comision_clp


# --- Vista previa e importación de cartola CSV ----------------------------------

def parsear_cartola_csv(contenido_csv: str, mapeo: dict | None = None) -> dict:
    """Parsea una cartola bancaria CSV con mapeo de columnas configurable y lista filas rechazadas."""
    if not contenido_csv or not contenido_csv.strip():
        raise ConciliacionInvalida("la cartola CSV está vacía")
    texto = contenido_csv.lstrip("\ufeff")
    sha = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    muestra = texto[:2048]
    delim = ";" if muestra.count(";") > muestra.count(",") else ","
    lector = csv.DictReader(io.StringIO(texto), delimiter=delim)
    cabeceras = [c.strip() for c in (lector.fieldnames or []) if c]
    if not cabeceras:
        raise ConciliacionInvalida("no se detectaron encabezados en la cartola CSV")

    m = {k: (v or "").strip() for k, v in (mapeo or {}).items()}
    col_fecha = m.get("fecha") or next((c for c in cabeceras if "fecha" in c.lower()), None)
    col_desc = m.get("descripcion") or next((c for c in cabeceras if any(p in c.lower() for p in ("desc", "glosa", "detalle", "concepto"))), None)
    col_ref = m.get("referencia") or next((c for c in cabeceras if any(p in c.lower() for p in ("ref", "doc", "comprobante", "operacion"))), None)
    col_monto = m.get("monto") or next((c for c in cabeceras if any(p in c.lower() for p in ("monto", "importe", "abono"))), None)
    col_cargo = m.get("cargo") or next((c for c in cabeceras if "cargo" in c.lower() and c != col_monto), None)

    if not col_fecha or not col_monto:
        raise ConciliacionInvalida("indica o incluye columnas de fecha y monto/abono en la cartola CSV")

    validas = []
    rechazadas = []
    total_filas = 0
    for idx, fila in enumerate(lector, start=2):
        limpia = {k.strip(): (v.strip() if isinstance(v, str) else "") for k, v in fila.items() if k}
        if not any(limpia.values()):
            continue
        total_filas += 1
        try:
            fecha_mov = _parsear_fecha(limpia.get(col_fecha, ""))
            desc = (limpia.get(col_desc or "", "") or "Movimiento bancario")[:200]
            ref = (limpia.get(col_ref or "", "") or "")[:80] or None
            monto_raw = limpia.get(col_monto, "")
            cargo_raw = limpia.get(col_cargo, "") if col_cargo else ""
            if monto_raw:
                monto = _parsear_monto(monto_raw)
            elif cargo_raw:
                monto = -abs(_parsear_monto(cargo_raw))
            else:
                raise ValueError("sin monto ni cargo")
            if monto == 0:
                raise ValueError("monto igual a 0")
            validas.append({
                "linea": idx,
                "fecha_movimiento": fecha_mov.isoformat(),
                "descripcion": desc,
                "referencia": ref,
                "monto_clp": abs(monto),
                "tipo": "abono" if monto > 0 else "cargo",
            })
        except ValueError as err:
            rechazadas.append({"linea": idx, "motivo": str(err)})

    return {
        "sha256": sha,
        "cabeceras": cabeceras,
        "filas_totales": total_filas,
        "filas_validas": len(validas),
        "filas_rechazadas": len(rechazadas),
        "movimientos": validas,
        "rechazadas": rechazadas,
    }


def vista_previa_cartola(
    conexion: psycopg.Connection,
    empresa_id: str,
    contenido_csv: str,
    mapeo: dict | None = None,
) -> dict:
    parsed = parsear_cartola_csv(contenido_csv, mapeo)
    ya_importada = conexion.execute(
        "SELECT id, periodo, creado_en FROM cartolas_bancarias WHERE empresa_id = %s AND sha256 = %s",
        (empresa_id, parsed["sha256"]),
    ).fetchone()
    parsed["duplicada"] = bool(ya_importada)
    parsed["cartola_existente_id"] = ya_importada[0] if ya_importada else None
    return parsed


def _actualizar_estado_mov_cartola(conexion: psycopg.Connection, cartola_mov_id: str) -> str:
    (monto_total,) = conexion.execute(
        "SELECT monto_clp FROM cartola_movimientos WHERE id = %s", (cartola_mov_id,)
    ).fetchone()
    (asignado,) = conexion.execute(
        "SELECT COALESCE(SUM(monto_asignado_clp), 0) FROM conciliaciones_bancarias WHERE cartola_movimiento_id = %s",
        (cartola_mov_id,),
    ).fetchone()
    estado = "conciliado" if asignado >= monto_total else ("parcial" if asignado > 0 else "pendiente")
    conexion.execute("UPDATE cartola_movimientos SET estado = %s WHERE id = %s", (estado, cartola_mov_id))
    return estado


def _candidatos_internos_disponibles(conexion: psycopg.Connection, empresa_id: str) -> list[dict]:
    """Movimientos internos de caja/pagos conciliables con su saldo aún no conciliado."""
    filas = conexion.execute(
        "SELECT m.id, m.fecha_contable, m.tipo, m.medio, ABS(m.monto_clp), m.pago_id, "
        "COALESCE(m.comprobante, p.comprobante, p.codigo_autorizacion), "
        "COALESCE((SELECT SUM(c.monto_asignado_clp + c.comision_clp) FROM conciliaciones_bancarias c "
        "  WHERE c.caja_movimiento_id = m.id), 0) "
        "FROM caja_movimientos m LEFT JOIN pagos p ON p.id = m.pago_id "
        "WHERE m.empresa_id = %s "
        "AND ((m.tipo IN ('cobro', 'cobro_directo') AND m.medio IN ('transferencia', 'debito', 'credito')) "
        "  OR m.tipo = 'retiro_deposito') "
        "ORDER BY m.fecha_contable ASC, m.id ASC",
        (empresa_id,),
    ).fetchall()
    salida = []
    for f in filas:
        bruto = int(f[4])
        ya = int(f[7] or 0)
        disp = max(0, bruto - ya)
        if disp <= 0:
            continue
        salida.append({
            "caja_movimiento_id": f[0],
            "fecha_contable": f[1],
            "tipo": f[2],
            "medio": f[3],
            "monto_bruto_clp": bruto,
            "disponible_clp": disp,
            "pago_id": f[5],
            "comprobante": (f[6] or "").strip().lower(),
        })
    return salida


def importar_y_conciliar_cartola(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    banco: str,
    cuenta: str,
    periodo: str,
    contenido_csv: str,
    mapeo: dict | None = None,
    actor: str = "sistema",
) -> dict:
    """Importa la cartola bancaria (idempotente por SHA-256) y cruza automáticamente
    retiros para depósito, transferencias y liquidaciones de tarjetas según comisiones/desfase."""
    if not banco.strip() or not cuenta.strip():
        raise ConciliacionInvalida("indica banco y número de cuenta")
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", periodo.strip()):
        raise ConciliacionInvalida("periodo debe tener formato YYYY-MM")
    parsed = parsear_cartola_csv(contenido_csv, mapeo)
    if parsed["filas_validas"] == 0:
        raise ConciliacionInvalida("la cartola no contiene movimientos válidos para importar")

    if conexion.execute(
        "SELECT 1 FROM cartolas_bancarias WHERE empresa_id = %s AND sha256 = %s",
        (empresa_id, parsed["sha256"]),
    ).fetchone():
        raise ConciliacionConflicto("esa cartola bancaria ya fue importada anteriormente")

    comisiones = obtener_comisiones(conexion, empresa_id)
    tasa = iva.tasa(conexion)
    cartola_id = f"CRT-{uuid.uuid4().hex[:12]}"
    conciliados_auto = 0

    with conexion.transaction():
        conexion.execute(
            "INSERT INTO cartolas_bancarias "
            "(id, empresa_id, banco, cuenta, periodo, moneda, sha256, filas_totales, filas_importadas, filas_rechazadas, errores, actor) "
            "VALUES (%s,%s,%s,%s,%s,'CLP',%s,%s,%s,%s,%s,%s)",
            (
                cartola_id, empresa_id, banco.strip()[:80], cuenta.strip()[:60], periodo.strip(),
                parsed["sha256"], parsed["filas_totales"], parsed["filas_validas"],
                parsed["filas_rechazadas"], Jsonb(parsed["rechazadas"]), actor,
            ),
        )
        candidatos = _candidatos_internos_disponibles(conexion, empresa_id)
        usados: set[str] = set()

        for mov in parsed["movimientos"]:
            mov_id = f"CMO-{uuid.uuid4().hex[:12]}"
            fecha_mov = date.fromisoformat(mov["fecha_movimiento"])
            conexion.execute(
                "INSERT INTO cartola_movimientos "
                "(id, cartola_id, empresa_id, fecha_movimiento, descripcion, referencia, monto_clp, tipo, estado) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'pendiente')",
                (mov_id, cartola_id, empresa_id, fecha_mov, mov["descripcion"], mov["referencia"],
                 mov["monto_clp"], mov["tipo"]),
            )
            if mov["tipo"] != "abono":
                continue

            # Cruce automático seguro (FIN-006): exige calce por fecha esperada + monto exacto
            # (neto de comisión configurada) Y comprobante/referencia cuando hay ambigüedad.
            ref_mov = (mov["referencia"] or "").strip().lower()
            desc_mov = mov["descripcion"].lower()
            calces = []
            for cand in candidatos:
                if cand["caja_movimiento_id"] in usados:
                    continue
                cfg = comisiones.get(cand["medio"], _COMISIONES_DEFECTO["transferencia"])
                abono_esp, com_clp = calcular_abono_esperado(cand["disponible_clp"], cfg, tasa)
                fecha_esp = _sumar_dias_habiles(cand["fecha_contable"], cfg["dias_habiles_abono"])
                # Tolerancia de +-2 días por feriados bancarios
                if abs((fecha_mov - fecha_esp).days) > 2:
                    continue
                if abono_esp != mov["monto_clp"]:
                    continue
                prioridad_ref = 0
                if cand["comprobante"] and (cand["comprobante"] == ref_mov or cand["comprobante"] in desc_mov):
                    prioridad_ref = 2
                elif cand["medio"] in ("debito", "credito"):
                    prov = (cfg.get("proveedor") or "").strip().lower()
                    if prov and prov != "general" and (prov in desc_mov or prov in ref_mov):
                        prioridad_ref = 1
                calces.append((prioridad_ref, cand, abono_esp, com_clp))

            # Regla FIN-006 endurecida: coincidir solo en monto (prioridad 0) JAMÁS auto-concilia;
            # exige evidencia secundaria (comprobante/autorización o proveedor de adquirente de tarjeta)
            # y unicidad. Cualquier coincidencia solo por monto o ambigua queda pendiente para revisión manual.
            elegido = None
            con_comprobante = [x for x in calces if x[0] == 2]
            con_proveedor = [x for x in calces if x[0] == 1]
            if len(con_comprobante) == 1:
                elegido = con_comprobante[0]
            elif len(con_comprobante) == 0 and len(con_proveedor) == 1 and len(calces) == 1:
                elegido = con_proveedor[0]

            if elegido is not None:
                _p, cand, abono_esp, com_clp = elegido
                conexion.execute(
                    "INSERT INTO conciliaciones_bancarias "
                    "(id, empresa_id, cartola_movimiento_id, caja_movimiento_id, pago_id, "
                    "monto_asignado_clp, comision_clp, modo, justificacion, actor) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,'automatico',%s,%s)",
                    (
                        f"CON-{uuid.uuid4().hex[:12]}", empresa_id, mov_id,
                        cand["caja_movimiento_id"], cand["pago_id"], abono_esp, com_clp,
                        f"Cruce automático ({cand['medio']}, comisión {com_clp} CLP)", actor,
                    ),
                )
                usados.add(cand["caja_movimiento_id"])
                _actualizar_estado_mov_cartola(conexion, mov_id)
                conciliados_auto += 1

        seguridad.auditar(
            conexion, actor, "cartola_importacion", cartola_id,
            f"filas={parsed['filas_validas']},conciliados_auto={conciliados_auto},rechazadas={parsed['filas_rechazadas']}",
        )

    return {
        "cartola_id": cartola_id,
        "banco": banco.strip(),
        "cuenta": cuenta.strip(),
        "periodo": periodo.strip(),
        "filas_totales": parsed["filas_totales"],
        "filas_importadas": parsed["filas_validas"],
        "filas_rechazadas": parsed["filas_rechazadas"],
        "conciliados_automaticamente": conciliados_auto,
        "pendientes": parsed["filas_validas"] - conciliados_auto,
        "rechazadas": parsed["rechazadas"],
    }


def emparejar_manual(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    cartola_movimiento_id: str,
    caja_movimiento_id: str,
    monto_asignado_clp: int,
    comision_clp: int = 0,
    justificacion: str,
    actor: str,
) -> dict:
    """Conciliación manual muchos-a-muchos (FIN-004): nunca supera importes disponibles,
    exige justificación auditada (>= 10 caracteres) y es estrictamente append-only."""
    just = (justificacion or "").strip()
    if len(just) < contabilidad.MIN_JUSTIFICACION:
        raise ConciliacionInvalida("la conciliación manual exige justificación (mínimo 10 caracteres)")
    if monto_asignado_clp <= 0 or comision_clp < 0:
        raise ConciliacionInvalida("monto asignado debe ser > 0 y comisión >= 0")

    cm = conexion.execute(
        "SELECT id, monto_clp, estado FROM cartola_movimientos "
        "WHERE id = %s AND empresa_id = %s FOR UPDATE",
        (cartola_movimiento_id, empresa_id),
    ).fetchone()
    if not cm:
        raise seguridad.ErrorPermiso("acceso denegado")

    (ya_cm,) = conexion.execute(
        "SELECT COALESCE(SUM(monto_asignado_clp), 0) FROM conciliaciones_bancarias WHERE cartola_movimiento_id = %s",
        (cartola_movimiento_id,),
    ).fetchone()
    disp_cm = int(cm[1]) - int(ya_cm or 0)
    if monto_asignado_clp > disp_cm:
        raise ConciliacionConflicto(
            f"el monto asignado ({monto_asignado_clp} CLP) supera el saldo disponible del movimiento bancario ({disp_cm} CLP)"
        )

    im = conexion.execute(
        "SELECT id, ABS(monto_clp), pago_id FROM caja_movimientos "
        "WHERE id = %s AND empresa_id = %s FOR UPDATE",
        (caja_movimiento_id, empresa_id),
    ).fetchone()
    if not im:
        raise seguridad.ErrorPermiso("acceso denegado")

    (ya_im,) = conexion.execute(
        "SELECT COALESCE(SUM(monto_asignado_clp + comision_clp), 0) FROM conciliaciones_bancarias WHERE caja_movimiento_id = %s",
        (caja_movimiento_id,),
    ).fetchone()
    disp_im = int(im[1]) - int(ya_im or 0)
    if monto_asignado_clp + comision_clp > disp_im:
        raise ConciliacionConflicto(
            f"monto + comisión ({monto_asignado_clp + comision_clp} CLP) supera el monto disponible del movimiento interno ({disp_im} CLP)"
        )

    conc_id = f"CON-{uuid.uuid4().hex[:12]}"
    with conexion.transaction():
        conexion.execute(
            "INSERT INTO conciliaciones_bancarias "
            "(id, empresa_id, cartola_movimiento_id, caja_movimiento_id, pago_id, "
            "monto_asignado_clp, comision_clp, modo, justificacion, actor) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,'manual',%s,%s)",
            (conc_id, empresa_id, cartola_movimiento_id, caja_movimiento_id, im[2],
             monto_asignado_clp, comision_clp, just[:400], actor),
        )
        nuevo_estado = _actualizar_estado_mov_cartola(conexion, cartola_movimiento_id)
        seguridad.auditar(
            conexion, actor, "conciliacion_bancaria_manual", conc_id,
            f"cm={cartola_movimiento_id},caja={caja_movimiento_id},monto={monto_asignado_clp},estado={nuevo_estado}",
        )

    return {
        "conciliacion_id": conc_id,
        "cartola_movimiento_id": cartola_movimiento_id,
        "caja_movimiento_id": caja_movimiento_id,
        "monto_asignado_clp": monto_asignado_clp,
        "comision_clp": comision_clp,
        "estado_cartola_movimiento": nuevo_estado,
    }


def estado_conciliacion(
    conexion: psycopg.Connection,
    empresa_id: str,
    periodo: str | None = None,
) -> dict:
    """Lista cartolas, movimientos bancarios (conciliado/parcial/pendiente) y movimientos internos
    pendientes o «en tránsito» (ventas de fin de mes cuyo abono cae en el mes siguiente)."""
    filtros_c = ["empresa_id = %s"]
    params_c: list = [empresa_id]
    if periodo:
        filtros_c.append("periodo = %s")
        params_c.append(periodo)

    cartolas = [
        {
            "cartola_id": r[0], "banco": r[1], "cuenta": r[2], "periodo": r[3],
            "filas_totales": r[4], "filas_importadas": r[5], "filas_rechazadas": r[6],
            "actor": r[7], "creado_en": r[8].isoformat(),
        }
        for r in conexion.execute(
            "SELECT id, banco, cuenta, periodo, filas_totales, filas_importadas, filas_rechazadas, actor, creado_en "
            f"FROM cartolas_bancarias WHERE {' AND '.join(filtros_c)} ORDER BY creado_en DESC LIMIT 50",
            params_c,
        ).fetchall()
    ]

    movs_cartola = [
        {
            "cartola_movimiento_id": r[0], "cartola_id": r[1], "fecha_movimiento": r[2].isoformat(),
            "descripcion": r[3], "referencia": r[4], "monto_clp": int(r[5]), "tipo": r[6],
            "estado": r[7], "asignado_clp": int(r[8] or 0), "pendiente_clp": max(0, int(r[5]) - int(r[8] or 0)),
        }
        for r in conexion.execute(
            "SELECT m.id, m.cartola_id, m.fecha_movimiento, m.descripcion, m.referencia, m.monto_clp, m.tipo, m.estado, "
            "COALESCE((SELECT SUM(c.monto_asignado_clp) FROM conciliaciones_bancarias c WHERE c.cartola_movimiento_id = m.id), 0) "
            "FROM cartola_movimientos m JOIN cartolas_bancarias cb ON cb.id = m.cartola_id "
            f"WHERE {' AND '.join(f.replace('empresa_id', 'm.empresa_id').replace('periodo', 'cb.periodo') for f in filtros_c)} "
            "ORDER BY m.fecha_movimiento DESC, m.id DESC LIMIT 500",
            params_c,
        ).fetchall()
    ]

    comisiones = obtener_comisiones(conexion, empresa_id)
    internos = _candidatos_internos_disponibles(conexion, empresa_id)
    en_transito = []
    pendientes_internos = []
    for cand in internos:
        cfg = comisiones.get(cand["medio"], _COMISIONES_DEFECTO["transferencia"])
        fecha_abono = _sumar_dias_habiles(cand["fecha_contable"], cfg["dias_habiles_abono"])
        cruza_mes = (fecha_abono.year, fecha_abono.month) != (cand["fecha_contable"].year, cand["fecha_contable"].month)
        item = {
            "caja_movimiento_id": cand["caja_movimiento_id"],
            "fecha_contable": cand["fecha_contable"].isoformat(),
            "fecha_abono_esperada": fecha_abono.isoformat(),
            "tipo": cand["tipo"],
            "medio": cand["medio"],
            "monto_bruto_clp": cand["monto_bruto_clp"],
            "pendiente_clp": cand["disponible_clp"],
            "comprobante": cand["comprobante"] or None,
            "en_transito": cruza_mes,
        }
        if cruza_mes:
            en_transito.append(item)
        pendientes_internos.append(item)

    return {
        "periodo": periodo,
        "cartolas": cartolas,
        "movimientos_cartola": movs_cartola,
        "internos_pendientes": pendientes_internos,
        "en_transito": en_transito,
        "resumen": {
            "conciliados": sum(1 for m in movs_cartola if m["estado"] == "conciliado"),
            "parciales": sum(1 for m in movs_cartola if m["estado"] == "parcial"),
            "pendientes_cartola": sum(1 for m in movs_cartola if m["estado"] == "pendiente"),
            "en_transito_cantidad": len(en_transito),
            "en_transito_clp": sum(i["pendiente_clp"] for i in en_transito),
        },
    }
