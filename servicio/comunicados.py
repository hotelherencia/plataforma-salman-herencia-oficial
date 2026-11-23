"""Comunicados internos con confirmación de lectura (#418, Corte 2).

Un comunicado va a todo el personal o a ciertos roles. Cada usuario confirma su
lectura una sola vez (solo se agrega). La administración ve quién leyó y quién falta.
"""
from __future__ import annotations

import uuid

from .operacion import NoEncontrado


def _id() -> str:
    return f"COM-{uuid.uuid4().hex[:12]}"


def crear(conexion, actor: str, datos: dict) -> dict:
    comunicado_id = _id()
    conexion.execute(
        "INSERT INTO comunicados (id, titulo, cuerpo, roles, creado_por) VALUES (%s, %s, %s, %s, %s)",
        (comunicado_id, datos["titulo"].strip(), datos["cuerpo"].strip(), sorted(set(datos.get("roles") or [])), actor),
    )
    return {"comunicado_id": comunicado_id}


def _dirigido(roles: list[str], rol: str) -> bool:
    return not roles or rol in roles


def listar(conexion, usuario: str, rol: str, *, incluir_archivados: bool = False) -> dict:
    filas = conexion.execute(
        "SELECT c.id, c.titulo, c.cuerpo, c.roles, c.archivado, c.creado_por, c.creado_en, l.leido_en "
        "FROM comunicados c LEFT JOIN comunicado_lecturas l ON l.comunicado_id = c.id AND l.usuario = %s "
        "WHERE (%s OR NOT c.archivado) ORDER BY c.creado_en DESC LIMIT 100",
        (usuario, incluir_archivados),
    ).fetchall()
    comunicados = [
        {"id": f[0], "titulo": f[1], "cuerpo": f[2], "roles": f[3], "archivado": f[4], "creado_por": f[5],
         "creado_en": f[6].isoformat(), "leido": f[7] is not None,
         "leido_en": f[7].isoformat() if f[7] else None}
        for f in filas if _dirigido(f[3], rol)
    ]
    return {"comunicados": comunicados, "sin_leer": sum(1 for c in comunicados if not c["leido"] and not c["archivado"])}


def confirmar_lectura(conexion, comunicado_id: str, usuario: str, rol: str) -> dict:
    fila = conexion.execute("SELECT roles FROM comunicados WHERE id = %s", (comunicado_id,)).fetchone()
    if fila is None or not _dirigido(fila[0], rol):
        raise NoEncontrado("el comunicado no existe")
    conexion.execute(
        "INSERT INTO comunicado_lecturas (comunicado_id, usuario) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (comunicado_id, usuario),
    )
    return {"comunicado_id": comunicado_id, "leido": True}


def archivar(conexion, comunicado_id: str) -> dict:
    r = conexion.execute("UPDATE comunicados SET archivado = true WHERE id = %s RETURNING id", (comunicado_id,)).fetchone()
    if r is None:
        raise NoEncontrado("el comunicado no existe")
    return {"comunicado_id": comunicado_id, "archivado": True}


def lecturas(conexion, empresa_id: str, comunicado_id: str) -> dict:
    fila = conexion.execute("SELECT titulo, roles FROM comunicados WHERE id = %s", (comunicado_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("el comunicado no existe")
    destinatarios = conexion.execute(
        "SELECT nombre, rol FROM usuarios WHERE empresa_id = %s AND (cardinality(%s::text[]) = 0 OR rol = ANY(%s::text[])) "
        "ORDER BY nombre",
        (empresa_id, fila[1], fila[1]),
    ).fetchall()
    leidas = {u: t for u, t in conexion.execute(
        "SELECT usuario, leido_en FROM comunicado_lecturas WHERE comunicado_id = %s", (comunicado_id,)).fetchall()}
    leyeron = [{"usuario": n, "rol": r, "leido_en": leidas[n].isoformat()} for n, r in destinatarios if n in leidas]
    faltan = [{"usuario": n, "rol": r} for n, r in destinatarios if n not in leidas]
    return {"comunicado_id": comunicado_id, "titulo": fila[0], "leyeron": leyeron, "faltan": faltan}
