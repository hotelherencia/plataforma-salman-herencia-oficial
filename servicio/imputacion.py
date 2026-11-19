"""Imputación de pagos y abonos, saldo por reserva y movimientos de la cuenta (contabilidad fase 2.1).

El dominio del hotel decide la cuenta, los pagos y la liquidación; aquí se lleva el libro que no modela: a qué
noche, habitación y cliente va cada peso. Es solo de agregar (triggers de la migración 0051): un reverso de pago
agrega filas negativas, nunca edita ni borra.
"""
from __future__ import annotations

import re
import uuid
from datetime import date
from zoneinfo import ZoneInfo

import psycopg

from . import roles

ROLES_MOVIMIENTOS = roles.con_admin_hotel("caja")
ZONA = ZoneInfo("America/Santiago")

_RE_NOCHE = re.compile(r"noche:(\d{4}-\d{2}-\d{2})")


def _noches_asentadas(conexion: psycopg.Connection, reserva_id: str) -> list[tuple[date, int]]:
    """(noche, monto) de las noches ya asentadas en la cuenta (cargos «Noche» no reversados), en orden."""
    filas = conexion.execute(
        "SELECT c.referencia, c.monto_clp FROM cargos c WHERE c.reserva_id = %s AND c.tipo = 'cargo' "
        "AND c.concepto = 'Noche' AND NOT EXISTS (SELECT 1 FROM cargos x WHERE x.reserva_id = c.reserva_id "
        "AND x.tipo = 'reverso' AND x.referencia = c.id) ORDER BY c.creado_en, c.id", (reserva_id,),
    ).fetchall()
    noches = []
    for referencia, monto in filas:
        encontrada = _RE_NOCHE.search(referencia or "")
        if encontrada:
            noches.append((date.fromisoformat(encontrada.group(1)), monto))
    return sorted(noches)


def _imputado_por_noche(conexion: psycopg.Connection, reserva_id: str) -> dict[date, int]:
    return {
        noche: total for noche, total in conexion.execute(
            "SELECT noche, sum(monto_clp) FROM imputaciones_pago WHERE reserva_id = %s AND noche IS NOT NULL "
            "AND tipo IN ('consumo', 'aplicacion_anticipo', 'ajuste') GROUP BY noche", (reserva_id,)
        ).fetchall()
    }


def _insertar(conexion, pago_id, reserva_id, habitacion_id, noche, cliente_id, monto, tipo, actor, revierte_id=None):
    imputacion_id = f"IMP-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO imputaciones_pago (id, pago_id, reserva_id, habitacion_id, noche, cliente_id, monto_clp, tipo, "
        "revierte_id, actor) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (imputacion_id, pago_id, reserva_id, habitacion_id, noche, cliente_id, monto, tipo, revierte_id, actor),
    )
    return imputacion_id


def imputar_pago(conexion: psycopg.Connection, reserva_id: str, pago_id: str, monto_clp: int,
                 cliente_id: str | None, actor: str) -> None:
    """Reparte un pago recién registrado. Antes de la Llegada es abono (anticipo). Con la estadía en curso va a
    las noches más antiguas con saldo, luego a los consumos sueltos y el resto queda como abono."""
    estado, habitacion_id = conexion.execute(
        "SELECT estado, habitacion_id FROM reservas WHERE id = %s", (reserva_id,)).fetchone()
    restante = monto_clp
    if estado != "confirmada":
        ya = _imputado_por_noche(conexion, reserva_id)
        asentadas = _noches_asentadas(conexion, reserva_id)
        for noche, precio in asentadas:
            if restante <= 0:
                break
            parte = min(restante, max(precio - ya.get(noche, 0), 0))
            if parte > 0:
                _insertar(conexion, pago_id, reserva_id, habitacion_id, noche, cliente_id, parte, "consumo", actor)
                restante -= parte
        if restante > 0:
            (neto,) = conexion.execute(
                "SELECT COALESCE(SUM(CASE WHEN tipo = 'reverso' THEN -monto_clp ELSE monto_clp END), 0) "
                "FROM cargos WHERE reserva_id = %s", (reserva_id,)).fetchone()
            (sueltos_pagados,) = conexion.execute(
                "SELECT COALESCE(SUM(monto_clp), 0) FROM imputaciones_pago WHERE reserva_id = %s "
                "AND noche IS NULL AND tipo = 'consumo'", (reserva_id,)).fetchone()
            pendiente_sueltos = max(neto - sum(m for _, m in asentadas) - sueltos_pagados, 0)
            parte = min(restante, pendiente_sueltos)
            if parte > 0:
                _insertar(conexion, pago_id, reserva_id, habitacion_id, None, cliente_id, parte, "consumo", actor)
                restante -= parte
    if restante > 0:
        _insertar(conexion, pago_id, reserva_id, habitacion_id, None, cliente_id, restante, "anticipo", actor)


def aplicar_anticipos(conexion: psycopg.Connection, reserva_id: str, actor: str) -> None:
    """Con las noches ya asentadas (Llegada), aplica los abonos sin aplicar al consumo de cada noche, de la más
    antigua a la más nueva y de los abonos más viejos a los más nuevos."""
    habitacion_id = conexion.execute("SELECT habitacion_id FROM reservas WHERE id = %s", (reserva_id,)).fetchone()[0]
    anticipos = conexion.execute(
        "SELECT a.pago_id, a.cliente_id, COALESCE(SUM(a.monto_clp) FILTER (WHERE a.tipo = 'anticipo'), 0) "
        "- COALESCE(SUM(a.monto_clp) FILTER (WHERE a.tipo = 'aplicacion_anticipo'), 0) AS libre "
        "FROM imputaciones_pago a WHERE a.reserva_id = %s AND a.tipo IN ('anticipo', 'aplicacion_anticipo') "
        "GROUP BY a.pago_id, a.cliente_id ORDER BY min(a.creado_en), a.pago_id", (reserva_id,)).fetchall()
    bolsas = [[pago, cliente, libre] for pago, cliente, libre in anticipos if libre > 0]
    ya = _imputado_por_noche(conexion, reserva_id)
    for noche, precio in _noches_asentadas(conexion, reserva_id):
        pendiente = max(precio - ya.get(noche, 0), 0)
        for bolsa in bolsas:
            if pendiente <= 0:
                break
            parte = min(pendiente, bolsa[2])
            if parte > 0:
                _insertar(conexion, bolsa[0], reserva_id, habitacion_id, noche, bolsa[1], parte,
                          "aplicacion_anticipo", actor)
                bolsa[2] -= parte
                pendiente -= parte


def revertir_pago(conexion: psycopg.Connection, pago_id: str, actor: str) -> None:
    """Reverso de un pago: agrega, por cada fila de imputación del pago que aún no fue revertida, otra negativa
    (misma noche, mismo tipo, `revierte_id` apuntando a la original)."""
    filas = conexion.execute(
        "SELECT i.id, i.reserva_id, i.habitacion_id, i.noche, i.cliente_id, i.monto_clp, i.tipo FROM imputaciones_pago i "
        "WHERE i.pago_id = %s AND i.revierte_id IS NULL AND NOT EXISTS "
        "(SELECT 1 FROM imputaciones_pago r WHERE r.revierte_id = i.id) ORDER BY i.creado_en, i.id", (pago_id,)).fetchall()
    for original, reserva_id, habitacion_id, noche, cliente_id, monto, tipo in filas:
        _insertar(conexion, pago_id, reserva_id, habitacion_id, noche, cliente_id, -monto, tipo, actor,
                  revierte_id=original)


def saldo_reserva(conexion: psycopg.Connection, reserva_id: str) -> dict:
    """Total, abonado, pagado y pendiente de una reserva, con el detalle por noche.

    total      lo que se cobra: la cuenta (cargos menos reversos) más las noches aún no asentadas.
    abonado    dinero recibido que todavía no se aplicó a ninguna noche o consumo.
    pagado     dinero ya aplicado al consumo.
    pendiente  total menos todo lo recibido (negativo = saldo a favor del cliente).
    Un pago reversado deja de contar, igual que para el dominio."""
    (estado,) = conexion.execute("SELECT estado FROM reservas WHERE id = %s", (reserva_id,)).fetchone()
    (neto,) = conexion.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo = 'reverso' THEN -monto_clp ELSE monto_clp END), 0) "
        "FROM cargos WHERE reserva_id = %s", (reserva_id,)).fetchone()
    asentadas = dict(_noches_asentadas(conexion, reserva_id))
    precios = conexion.execute(
        "SELECT noche, precio_clp FROM reserva_noches WHERE reserva_id = %s ORDER BY noche", (reserva_id,)).fetchall()
    proyectadas = {} if estado != "confirmada" else {n: p for n, p in precios if n not in asentadas}
    total = neto + sum(proyectadas.values())
    (recibido,) = conexion.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo = 'reverso' THEN -monto_clp ELSE monto_clp END), 0) "
        "FROM pagos WHERE reserva_id = %s AND estado = 'confirmado'", (reserva_id,)).fetchone()
    (anticipos, aplicado) = conexion.execute(
        "SELECT COALESCE(SUM(monto_clp) FILTER (WHERE tipo = 'anticipo'), 0), "
        "COALESCE(SUM(monto_clp) FILTER (WHERE tipo = 'aplicacion_anticipo'), 0) "
        "FROM imputaciones_pago WHERE reserva_id = %s", (reserva_id,)).fetchone()
    abonado = anticipos - aplicado
    imputado = _imputado_por_noche(conexion, reserva_id)
    noches = []
    for noche, precio in sorted({**proyectadas, **asentadas}.items()):
        pagado_noche = min(max(imputado.get(noche, 0), 0), precio)
        noches.append({"noche": noche.isoformat(), "precio_clp": precio, "pagado_clp": pagado_noche,
                       "pendiente_clp": precio - pagado_noche, "asentada": noche in asentadas})
    return {"reserva_id": reserva_id, "estado": estado, "total_clp": total, "abonado_clp": abonado,
            "pagado_clp": recibido - abonado, "pendiente_clp": total - recibido, "recibido_clp": recibido,
            "noches": noches}


def movimientos_cuenta(conexion: psycopg.Connection, empresa_id: str, desde: date, hasta: date) -> list[dict]:
    """Cargos, reversos y pagos del rango (días en hora de Chile) con quién los hizo. La cuenta de una reserva no
    depende de que haya una caja abierta: un movimiento hecho con la caja cerrada queda aquí igual."""
    filas = conexion.execute(
        "SELECT * FROM ("
        " SELECT c.creado_en, c.tipo, c.concepto, CASE WHEN c.tipo = 'reverso' THEN -c.monto_clp ELSE c.monto_clp END,"
        "  c.reserva_id, r.habitacion_id, r.huesped_nombre, c.producto_id, c.cantidad, NULL::text AS medio,"
        "  NULL::text AS documento_tipo, NULL::text AS documento_folio,"
        "  COALESCE((SELECT a.actor FROM auditoria a WHERE (a.accion = 'cargo' AND a.recurso = c.reserva_id || ':' || c.id)"
        "   OR (a.accion = 'cargo_reverso' AND a.resultado = c.id) ORDER BY a.creado_en LIMIT 1),"
        "  (SELECT a.actor FROM auditoria a WHERE a.recurso = c.reserva_id AND a.accion IN ('entrada', 'cancelacion', 'reserva')"
        "   ORDER BY a.creado_en LIMIT 1)) AS actor"
        " FROM cargos c JOIN reservas r ON r.id = c.reserva_id WHERE r.empresa_id = %(e)s"
        " UNION ALL"
        " SELECT p.creado_en, CASE WHEN p.tipo = 'reverso' THEN 'reverso_pago' ELSE 'pago' END,"
        "  CASE WHEN p.tipo = 'reverso' THEN 'Reverso de pago' ELSE 'Pago' END,"
        "  CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END, p.reserva_id, r.habitacion_id,"
        "  r.huesped_nombre, NULL::text, NULL::int, p.medio, p.documento_tipo, p.documento_folio, COALESCE(p.actor,"
        "  (SELECT a.actor FROM auditoria a WHERE a.accion = 'pago' AND a.recurso = p.reserva_id || ':' || p.clave"
        "   ORDER BY a.creado_en LIMIT 1))"
        " FROM pagos p JOIN reservas r ON r.id = p.reserva_id WHERE r.empresa_id = %(e)s AND p.estado = 'confirmado'"
        ") m WHERE (m.creado_en AT TIME ZONE 'America/Santiago')::date BETWEEN %(d)s AND %(h)s ORDER BY m.creado_en, 2",
        {"e": empresa_id, "d": desde, "h": hasta},
    ).fetchall()
    return [
        {"fecha_hora": f[0].astimezone(ZONA).isoformat(timespec="seconds"), "tipo": f[1], "concepto": f[2],
         "monto_clp": f[3], "reserva_id": f[4], "habitacion_id": f[5], "huesped_nombre": f[6], "producto_id": f[7],
         "cantidad": f[8], "medio": f[9], "documento_tipo": f[10], "documento_folio": f[11], "actor": f[12]}
        for f in filas
    ]
