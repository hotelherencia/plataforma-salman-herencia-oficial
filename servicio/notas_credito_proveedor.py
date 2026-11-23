"""Notas de crédito de proveedor vinculadas a facturas y Cuenta por Pagar (#402 / PUR-004).

Reglas clave:
- Toda factura de proveedor confirmada (`cargada`) genera (de forma idempotente) su
  cuenta por pagar en `cuentas_por_pagar` con un primer asiento append-only
  `cargo_factura` en `cxp_movimientos`.
- Una nota de crédito (DTE 61, `clase = 'nota_credito'`) en estado `pendiente`
  puede aplicarse una sola vez contra una factura `cargada` del mismo proveedor:
  1. Rebaja stock en `core_stock_bodega` + `productos.stock` (migración 0055) con
     movimiento append-only `tipo = 'reverso'` en `movimientos_stock` para cada línea
     con devolución física (sin dejar stock negativo → 409).
  2. Registra asiento negativo append-only `tipo = 'nota_credito'` en `cxp_movimientos`
     con clave única `nc:{nc_documento_id}` (idempotente, sin duplicar rebajas ni
     superar el saldo pendiente de la factura).
  3. Marca la nota de crédito como `aplicada` vinculada vía `factura_referencia_id`.
- Los pagos a proveedor se registran también de forma append-only en `cxp_movimientos`
  (`tipo = 'pago_proveedor'`), sin duplicados y sin sobrepasar el saldo pendiente.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import psycopg

from core.incremento1.nucleo import stock as stock_core
from . import facturas_proveedor as fp
from . import productos as productos_db


def _id(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:12]}"


def _saldo_y_totales_cxp(conexion: psycopg.Connection, cxp_id: str) -> dict:
    filas = conexion.execute(
        "SELECT tipo, monto_clp FROM cxp_movimientos WHERE cxp_id = %s ORDER BY creado_en, id",
        (cxp_id,),
    ).fetchall()
    cargos = sum(int(m) for t, m in filas if t == "cargo_factura")
    notas_credito = sum(-int(m) for t, m in filas if t == "nota_credito")
    pagos = sum(-int(m) for t, m in filas if t == "pago_proveedor")
    reversos = sum(int(m) for t, m in filas if t == "reverso")
    saldo = cargos - notas_credito - pagos + reversos
    return {
        "cargos_clp": cargos,
        "notas_credito_clp": notas_credito,
        "pagado_clp": pagos,
        "saldo_pendiente_clp": saldo,
    }


def _recalcular_estado_cxp(conexion: psycopg.Connection, cxp_id: str) -> tuple[str, dict]:
    tot = _saldo_y_totales_cxp(conexion, cxp_id)
    saldo = tot["saldo_pendiente_clp"]
    if saldo <= 0:
        estado = "anulada" if tot["pagado_clp"] == 0 and tot["notas_credito_clp"] > 0 else "pagada"
    elif tot["notas_credito_clp"] > 0 or tot["pagado_clp"] > 0:
        estado = "parcial"
    else:
        estado = "abierta"
    conexion.execute(
        "UPDATE cuentas_por_pagar SET estado = %s, actualizado_en = now() WHERE id = %s",
        (estado, cxp_id),
    )
    return estado, tot


def asegurar_cxp_para_factura(
    conexion: psycopg.Connection,
    documento_id: str,
    actor: str,
    dias_vencimiento: int = 30,
) -> dict:
    """Crea (si aún no existe) la cuenta por pagar de una factura de proveedor cargada."""
    existente = conexion.execute(
        "SELECT id FROM cuentas_por_pagar WHERE documento_id = %s FOR UPDATE",
        (documento_id,),
    ).fetchone()
    if existente:
        return obtener_cxp(conexion, existente[0])

    fila = conexion.execute(
        "SELECT id, clase, estado, emisor_rut, emisor_razon_social, tipo_dte, folio, fecha_emision, "
        "COALESCE(monto_total_clp, COALESCE(monto_neto_clp, 0) + COALESCE(monto_exento_clp, 0) + COALESCE(iva_clp, 0), 0) "
        "FROM documentos_proveedor WHERE id = %s",
        (documento_id,),
    ).fetchone()
    if not fila:
        raise fp.DocumentoNoEncontrado("No existe esa factura de proveedor.")
    if fila[1] != "factura" or fila[2] != "cargada":
        raise fp.DocumentoEnConflicto("Solo una factura de proveedor cargada genera cuenta por pagar.", documento_id)

    monto = int(fila[8] or 0)
    fecha_emision: date | None = fila[7]
    fecha_venc = (fecha_emision + timedelta(days=dias_vencimiento)) if fecha_emision else None
    cxp_id = _id("CXP")
    conexion.execute(
        "INSERT INTO cuentas_por_pagar "
        "(id, documento_id, emisor_rut, emisor_razon_social, tipo_dte, folio, fecha_emision, fecha_vencimiento, "
        "monto_original_clp, estado, actor) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'abierta',%s) "
        "ON CONFLICT (documento_id) DO NOTHING",
        (cxp_id, documento_id, fila[3] or "", fila[4], fila[5], fila[6] or "", fecha_emision, fecha_venc, monto, actor),
    )
    real_id = conexion.execute(
        "SELECT id FROM cuentas_por_pagar WHERE documento_id = %s", (documento_id,)
    ).fetchone()[0]
    conexion.execute(
        "INSERT INTO cxp_movimientos (id, cxp_id, tipo, monto_clp, documento_id, motivo, clave_idempotencia, actor) "
        "VALUES (%s, %s, 'cargo_factura', %s, %s, %s, %s, %s) "
        "ON CONFLICT (clave_idempotencia) DO NOTHING",
        (_id("CXM"), real_id, monto, documento_id, f"Factura DTE {fila[5] or 33} folio {fila[6]}", f"fac:{documento_id}", actor),
    )
    _recalcular_estado_cxp(conexion, real_id)
    return obtener_cxp(conexion, real_id)


def obtener_cxp(conexion: psycopg.Connection, cxp_id: str) -> dict:
    f = conexion.execute(
        "SELECT id, documento_id, emisor_rut, emisor_razon_social, tipo_dte, folio, "
        "fecha_emision, fecha_vencimiento, monto_original_clp, estado, actor, creado_en, actualizado_en "
        "FROM cuentas_por_pagar WHERE id = %s",
        (cxp_id,),
    ).fetchone()
    if not f:
        raise fp.DocumentoNoEncontrado("No existe esa cuenta por pagar.")
    tot = _saldo_y_totales_cxp(conexion, cxp_id)
    movs = [
        {
            "movimiento_id": m[0],
            "tipo": m[1],
            "monto_clp": int(m[2]),
            "documento_id": m[3],
            "medio": m[4],
            "comprobante": m[5],
            "motivo": m[6],
            "actor": m[7],
            "registrado_en": m[8].isoformat(),
        }
        for m in conexion.execute(
            "SELECT id, tipo, monto_clp, documento_id, medio, comprobante, motivo, actor, creado_en "
            "FROM cxp_movimientos WHERE cxp_id = %s ORDER BY creado_en ASC, id ASC",
            (cxp_id,),
        ).fetchall()
    ]
    return {
        "cxp_id": f[0],
        "documento_id": f[1],
        "emisor_rut": f[2],
        "emisor_razon_social": f[3],
        "tipo_dte": f[4],
        "folio": f[5],
        "fecha_emision": f[6].isoformat() if f[6] else None,
        "fecha_vencimiento": f[7].isoformat() if f[7] else None,
        "monto_original_clp": int(f[8]),
        "estado": f[9],
        **tot,
        "movimientos": movs,
        "actor": f[10],
        "creado_en": f[11].isoformat(),
        "actualizado_en": f[12].isoformat(),
    }


def listar_cxp(
    conexion: psycopg.Connection,
    estado: str | None = None,
    emisor_rut: str | None = None,
    limite: int = 100,
) -> list[dict]:
    filtros, params = [], []
    if estado and estado != "todos":
        if estado == "pendientes":
            filtros.append("estado IN ('abierta', 'parcial')")
        else:
            filtros.append("estado = %s")
            params.append(estado)
    if emisor_rut:
        filtros.append("emisor_rut = %s")
        params.append(emisor_rut)
    where = (" WHERE " + " AND ".join(filtros)) if filtros else ""
    ids = [
        r[0] for r in conexion.execute(
            f"SELECT id FROM cuentas_por_pagar{where} ORDER BY creado_en DESC, id DESC LIMIT %s",
            (*params, limite),
        ).fetchall()
    ]
    return [obtener_cxp(conexion, cid) for cid in ids]


def sugerir_factura_para_nc(conexion: psycopg.Connection, emisor_rut: str | None, referencias: list[dict]) -> dict | None:
    if not emisor_rut:
        return None
    folios_ref = [str(r.get("folio")) for r in (referencias or []) if r.get("folio")]
    fila = conexion.execute(
        "SELECT id, folio, fecha_emision, monto_total_clp FROM documentos_proveedor "
        "WHERE clase = 'factura' AND estado = 'cargada' AND emisor_rut = %s "
        "ORDER BY (folio = ANY(%s)) DESC, creado_en DESC LIMIT 1",
        (emisor_rut, folios_ref),
    ).fetchone()
    if not fila:
        return None
    return {
        "documento_id": fila[0],
        "folio": fila[1],
        "fecha_emision": fila[2].isoformat() if fila[2] else None,
        "monto_total_clp": int(fila[3]) if fila[3] is not None else None,
    }


def aplicar_nota_credito(
    conexion: psycopg.Connection,
    nc_documento_id: str,
    factura_id: str,
    lineas_stock: list[dict],
    actor: str,
    monto_rebaja_clp: int | None = None,
    motivo: str | None = None,
) -> dict:
    """Vincula una nota de crédito de proveedor (DTE 61) a su factura cargada,
    rebajando stock (0055) y cuenta por pagar (PUR-004) de forma atómica,
    append-only e idempotente."""
    nc = fp._vista(fp._fila(conexion, nc_documento_id, bloquear=True))
    if nc["clase"] != "nota_credito":
        raise fp.DocumentoEnConflicto("Solo una nota de crédito puede aplicarse con esta operación.", nc_documento_id)
    if nc["estado"] != "pendiente":
        raise fp.DocumentoEnConflicto(
            f"Esta nota de crédito ya está en estado «{nc['estado']}» y no puede aplicarse dos veces.",
            nc_documento_id,
        )

    factura = fp._vista(fp._fila(conexion, factura_id, bloquear=True))
    if factura["clase"] != "factura" or factura["estado"] != "cargada":
        raise fp.DocumentoEnConflicto(
            "La nota de crédito solo puede vincularse a una factura de proveedor ya cargada.", factura_id
        )
    if nc["emisor_rut"] and factura["emisor_rut"] and nc["emisor_rut"] != factura["emisor_rut"]:
        raise fp.DocumentoEnConflicto(
            "La nota de crédito y la factura pertenecen a proveedores (RUT) distintos.", nc_documento_id
        )

    rebaja_cxp = monto_rebaja_clp if monto_rebaja_clp is not None else int(nc["monto_total_clp"] or 0)
    if rebaja_cxp < 0:
        raise fp.DocumentoInvalido("El monto de rebaja en cuenta por pagar no puede ser negativo.")

    motivo_txt = (motivo or "").strip()[:200] or f"NC folio {nc['folio'] or nc_documento_id} sobre factura {factura['folio'] or factura_id}"
    rebajas_stock: list[dict] = []

    with conexion.transaction():
        # 1. Rebaja de stock en 0055 (core_stock_bodega + productos.stock + movimientos_stock tipo='reverso')
        for linea in lineas_stock or []:
            producto_id = linea.get("producto_id")
            if not producto_id:
                continue
            factor = max(1, int(linea.get("unidades_por_paquete") or 1))
            unidades = int(round(float(linea.get("cantidad") or 0) * factor))
            if unidades <= 0:
                continue
            producto = productos_db.obtener(conexion, producto_id, bloqueo=True)
            if not producto["controla_stock"]:
                continue
            if producto["stock"] < unidades:
                raise fp.DocumentoEnConflicto(
                    f"Stock insuficiente para rebajar {unidades} u. de «{producto['nombre']}» (hay {producto['stock']}).",
                    nc_documento_id,
                )
            bodega = linea.get("bodega_codigo") or stock_core.bodega_por_categoria(producto["categoria"])
            try:
                productos_db.registrar_stock_bodega(
                    conexion, producto_id, bodega, -unidades,
                    exigir_disponible_en_bodega=bool(linea.get("bodega_codigo")),
                )
            except productos_db.ProductoInvalido as error:
                raise fp.DocumentoEnConflicto(str(error), nc_documento_id) from error
            conexion.execute(
                "UPDATE productos SET stock = stock - %s, actualizado_en = now() WHERE id = %s",
                (unidades, producto_id),
            )
            productos_db._movimiento(
                conexion,
                producto_id,
                -unidades,
                f"NC {nc['folio'] or nc_documento_id}: {motivo_txt}"[:200],
                actor,
                bodega_codigo=bodega,
                tipo="reverso",
            )
            rebajas_stock.append({
                "producto_id": producto_id,
                "nombre": producto["nombre"],
                "bodega_codigo": bodega,
                "unidades_rebajadas": unidades,
                "stock_resultante": producto["stock"] - unidades,
            })

        # 2. Rebaja append-only e idempotente en Cuenta por Pagar (PUR-004)
        cxp = asegurar_cxp_para_factura(conexion, factura_id, actor)
        cxp_id = cxp["cxp_id"]
        clave_nc = f"nc:{nc_documento_id}"
        if conexion.execute("SELECT 1 FROM cxp_movimientos WHERE clave_idempotencia = %s", (clave_nc,)).fetchone():
            raise fp.DocumentoEnConflicto("Esta nota de crédito ya fue aplicada en cuenta por pagar.", nc_documento_id)
        if rebaja_cxp > cxp["saldo_pendiente_clp"]:
            raise fp.DocumentoEnConflicto(
                f"La rebaja ({rebaja_cxp} CLP) supera el saldo pendiente de la factura ({cxp['saldo_pendiente_clp']} CLP).",
                nc_documento_id,
            )
        if rebaja_cxp > 0:
            conexion.execute(
                "INSERT INTO cxp_movimientos "
                "(id, cxp_id, tipo, monto_clp, documento_id, comprobante, motivo, clave_idempotencia, actor) "
                "VALUES (%s, %s, 'nota_credito', %s, %s, %s, %s, %s, %s)",
                (_id("CXM"), cxp_id, -rebaja_cxp, nc_documento_id, nc["folio"], motivo_txt, clave_nc, actor),
            )
        _recalcular_estado_cxp(conexion, cxp_id)

        # 3. Vincular y marcar NC como aplicada
        conexion.execute(
            "UPDATE documentos_proveedor "
            "SET estado = 'aplicada', factura_referencia_id = %s, aplicada_en = now(), aplicada_por = %s, actualizado_en = now() "
            "WHERE id = %s",
            (factura_id, actor, nc_documento_id),
        )

    return {
        "documento_id": nc_documento_id,
        "estado": "aplicada",
        "factura_referencia_id": factura_id,
        "monto_rebajado_cxp_clp": rebaja_cxp,
        "unidades_rebajadas_stock": sum(r["unidades_rebajadas"] for r in rebajas_stock),
        "rebajas_stock": rebajas_stock,
        "cuenta_por_pagar": obtener_cxp(conexion, cxp_id),
    }


def registrar_pago_cxp(
    conexion: psycopg.Connection,
    cxp_id: str,
    monto_clp: int,
    medio: str,
    comprobante: str | None,
    motivo: str | None,
    clave_idempotencia: str,
    actor: str,
) -> dict:
    """Registra un abono o pago total a proveedor en `cxp_movimientos` (append-only e idempotente)."""
    if monto_clp <= 0:
        raise fp.DocumentoInvalido("El monto del pago al proveedor debe ser mayor que 0.")
    fila = conexion.execute(
        "SELECT id, estado FROM cuentas_por_pagar WHERE id = %s FOR UPDATE",
        (cxp_id,),
    ).fetchone()
    if not fila:
        raise fp.DocumentoNoEncontrado("No existe esa cuenta por pagar.")
    if fila[1] in ("pagada", "anulada"):
        raise fp.DocumentoEnConflicto(f"La cuenta por pagar ya está {fila[1]}.")

    tot = _saldo_y_totales_cxp(conexion, cxp_id)
    if monto_clp > tot["saldo_pendiente_clp"]:
        raise fp.DocumentoEnConflicto(
            f"El pago ({monto_clp} CLP) supera el saldo pendiente ({tot['saldo_pendiente_clp']} CLP)."
        )
    clave_mov = f"pago_cxp:{cxp_id}:{clave_idempotencia}"
    with conexion.transaction():
        conexion.execute(
            "INSERT INTO cxp_movimientos "
            "(id, cxp_id, tipo, monto_clp, medio, comprobante, motivo, clave_idempotencia, actor) "
            "VALUES (%s, %s, 'pago_proveedor', %s, %s, %s, %s, %s, %s)",
            (_id("CXM"), cxp_id, -monto_clp, medio, (comprobante or "")[:60] or None,
             (motivo or "")[:200] or "Pago a proveedor", clave_mov, actor),
        )
        _recalcular_estado_cxp(conexion, cxp_id)
    return obtener_cxp(conexion, cxp_id)
