"""Búsqueda única de estadías y reservas para Llegada, Salida y Caja
(2026-11-19, pedido del propietario: «buscar por habitación, nombre del
huésped o documento, no solo por código»).

Reglas:
- Alcance por pantalla: `salida` (estadías en curso), `llegada` (reservas
  confirmadas) y `pago` (confirmadas y en curso). Cada alcance tiene sus
  roles; el resto → 403.
- Texto mínimo de 2 caracteres (o un número de habitación) y tope de
  resultados: no sirve para listar la base completa.
- Sin texto, cada pantalla recibe su lista del día: Salidas de hoy (y
  atrasadas), Llegadas de hoy, o estadías en curso con saldo pendiente.
- El documento del huésped: recepción y administración lo buscan por
  prefijo (4+ caracteres) y lo ven; caja solo encuentra con el documento
  completo y nunca lo recibe en la respuesta (no se puede enumerar).
- Solo reservas de la empresa de la sesión.
"""
from __future__ import annotations

import re
from datetime import date

import psycopg

from . import roles

ALCANCES = {
    "salida": ("en_estadia",),
    "llegada": ("confirmada",),
    "pago": ("confirmada", "en_estadia"),
}
ROLES_POR_ALCANCE = {
    "salida": roles.con_admin_hotel("recepcion"),
    "llegada": roles.con_admin_hotel("recepcion"),
    "pago": roles.con_admin_hotel("recepcion", "caja"),
}
MIN_TEXTO = 2
MAX_TEXTO = 80
MAX_RESULTADOS = 12
_TILDES = ("áéíóúüñàèìòù", "aeiouunaeiou")
_NOMBRE_SQL = "translate(lower(r.huesped_nombre), %s, %s)"
_DOC_SQL = "regexp_replace(upper(coalesce(r.huesped_documento, '')), '[^0-9A-Z]', '', 'g')"


class BusquedaInvalida(Exception):
    """422: texto demasiado corto o alcance desconocido."""


def _sin_tildes(texto: str) -> str:
    return texto.lower().translate(str.maketrans(*_TILDES))


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _condicion_termino(termino: str, ver_documento: bool) -> tuple[str, list]:
    t = _sin_tildes(termino)
    e = _escapar_like(t)
    partes = [f"{_NOMBRE_SQL} LIKE %s"]
    valores: list = [*_TILDES, f"%{e}%"]
    # Habitación: «104» encuentra 104 y HAB-104; «hab-104» exacto.
    partes.append("(lower(r.habitacion_id) = %s OR substring(lower(r.habitacion_id) from '([0-9]+[a-z]?)$') = %s)")
    valores += [t, t]
    doc = re.sub(r"[^0-9A-Za-z]", "", termino).upper()
    if ver_documento and len(doc) >= 4:
        partes.append(f"{_DOC_SQL} LIKE %s")
        valores.append(f"{doc}%")
    elif len(doc) >= 7:
        partes.append(f"{_DOC_SQL} = %s")
        valores.append(doc)
    if len(t) >= 4:
        partes.append("lower(r.id) LIKE %s")
        valores.append(f"%{e}%")
    return "(" + " OR ".join(partes) + ")", valores


def buscar(conexion: psycopg.Connection, empresa_id: str, texto: str | None, alcance: str,
           ver_documento: bool, hoy: date | None = None) -> dict:
    if alcance not in ALCANCES:
        raise BusquedaInvalida("alcance desconocido")
    hoy = hoy or date.today()
    q = " ".join((texto or "").split())[:MAX_TEXTO]
    if q and len(q) < MIN_TEXTO and not q.isdigit():
        raise BusquedaInvalida("Escribe al menos 2 letras del nombre, el número de habitación o el documento.")
    condiciones = ["r.empresa_id = %s", "r.estado = ANY(%s)"]
    valores: list = [empresa_id, list(ALCANCES[alcance])]
    if q:
        for termino in q.split()[:4]:
            sql, vals = _condicion_termino(termino, ver_documento)
            condiciones.append(sql)
            valores += vals
    externa = ""
    if not q:
        if alcance == "salida":
            condiciones.append("r.fin <= %s")
            valores.append(hoy)
        elif alcance == "llegada":
            condiciones.append("r.inicio <= %s")
            valores.append(hoy)
        else:
            externa = "WHERE s.estado = 'en_estadia' AND s.neto - s.pagado > 0"
    orden = {
        "salida": "(s.fin <= %s) DESC, s.fin, s.habitacion_id",
        "llegada": "(s.inicio <= %s) DESC, s.inicio, s.habitacion_id",
        "pago": "(s.estado = 'en_estadia') DESC, (s.neto - s.pagado > 0) DESC, s.fin, s.habitacion_id, s.id",
    }[alcance]
    valores_orden = [hoy] if alcance in ("salida", "llegada") else []
    consulta = (
        "SELECT * FROM (SELECT r.id, r.habitacion_id, h.tipo, r.inicio, r.fin, r.huesped_nombre, r.huesped_documento, "
        "r.estado, r.personas, "
        "COALESCE((SELECT SUM(CASE WHEN c.tipo = 'reverso' THEN -c.monto_clp ELSE c.monto_clp END) "
        "FROM cargos c WHERE c.reserva_id = r.id), 0) AS neto, "
        "COALESCE((SELECT SUM(CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END) FROM pagos p "
        "WHERE p.reserva_id = r.id AND p.estado = 'confirmado'), 0) AS pagado "
        "FROM reservas r JOIN habitaciones h ON h.id = r.habitacion_id WHERE "
        + " AND ".join(condiciones)
        + f") s {externa} ORDER BY {orden} LIMIT %s"
    )
    filas = conexion.execute(consulta, [*valores, *valores_orden, MAX_RESULTADOS + 1]).fetchall()
    resultados = []
    for f in filas[:MAX_RESULTADOS]:
        item = {
            "reserva_id": f[0],
            "habitacion_id": f[1],
            "tipo_habitacion": f[2],
            "inicio": f[3].isoformat(),
            "fin": f[4].isoformat(),
            "noches": (f[4] - f[3]).days,
            "huesped_nombre": f[5],
            "estado": f[7],
            "personas": f[8],
            "cuenta": {"cargos_netos_clp": f[9], "pagado_clp": f[10], "saldo_clp": f[9] - f[10]},
            "llega_hoy": f[3] == hoy,
            "sale_hoy": f[4] == hoy,
            "salida_atrasada": f[7] == "en_estadia" and f[4] < hoy,
        }
        if ver_documento:
            item["huesped_documento"] = f[6]
        resultados.append(item)
    return {
        "alcance": alcance,
        "texto": q,
        "lista_del_dia": not q,
        "resultados": resultados,
        "hay_mas": len(filas) > MAX_RESULTADOS,
    }
