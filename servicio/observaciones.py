"""Observaciones del dueño para la administración (control de dirección).

El dueño no cambia datos: deja una observación ligada a una pantalla o dato, la administración la
responde y el dueño la cierra. Cada paso se audita; el aviso a la administración no lleva el texto.
"""
from __future__ import annotations

import uuid

from . import avisos, seguridad
from .operacion import NoEncontrado, OperacionInvalida


def crear(conexion, empresa_id: str, actor: str, texto: str, referencia: str | None) -> dict:
    observacion_id = f"OBS-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO observaciones_direccion (id, empresa_id, autor, texto, referencia) VALUES (%s,%s,%s,%s,%s)",
        (observacion_id, empresa_id, actor, texto.strip(), (referencia or "").strip() or None),
    )
    avisos.registrar_evento(conexion, "observacion_dueno", observacion_id, {"referencia": referencia or ""}, empresa_id)
    seguridad.auditar(conexion, actor, "observacion_dueno", observacion_id, "abierta")
    return {"observacion_id": observacion_id, "estado": "abierta"}


def _vista(f) -> dict:
    return {
        "id": f[0], "autor": f[1], "texto": f[2], "referencia": f[3], "estado": f[4], "respuesta": f[5],
        "respondida_por": f[6], "respondida_en": f[7].isoformat() if f[7] else None,
        "creado_en": f[8].isoformat(),
    }


def listar(conexion, empresa_id: str, estado: str | None = None) -> dict:
    filas = conexion.execute(
        "SELECT id, autor, texto, referencia, estado, respuesta, respondida_por, respondida_en, creado_en "
        "FROM observaciones_direccion WHERE empresa_id = %s AND (%s::text IS NULL OR estado = %s) "
        "ORDER BY creado_en DESC LIMIT 100", (empresa_id, estado, estado),
    ).fetchall()
    items = [_vista(f) for f in filas]
    return {"observaciones": items, "abiertas": sum(1 for o in items if o["estado"] == "abierta")}


def _bloquear(conexion, empresa_id: str, observacion_id: str):
    fila = conexion.execute(
        "SELECT estado FROM observaciones_direccion WHERE id = %s AND empresa_id = %s FOR UPDATE",
        (observacion_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise NoEncontrado("la observación no existe")
    return fila[0]


def responder(conexion, empresa_id: str, actor: str, observacion_id: str, respuesta: str) -> dict:
    estado = _bloquear(conexion, empresa_id, observacion_id)
    if estado == "cerrada":
        raise OperacionInvalida("la observación ya está cerrada")
    conexion.execute(
        "UPDATE observaciones_direccion SET estado = 'respondida', respuesta = %s, respondida_por = %s, "
        "respondida_en = now() WHERE id = %s", (respuesta.strip(), actor, observacion_id),
    )
    seguridad.auditar(conexion, actor, "observacion_respuesta", observacion_id, "respondida")
    return {"observacion_id": observacion_id, "estado": "respondida"}


def cerrar(conexion, empresa_id: str, actor: str, observacion_id: str) -> dict:
    estado = _bloquear(conexion, empresa_id, observacion_id)
    if estado == "cerrada":
        return {"observacion_id": observacion_id, "estado": "cerrada"}
    conexion.execute(
        "UPDATE observaciones_direccion SET estado = 'cerrada', cerrada_en = now() WHERE id = %s", (observacion_id,),
    )
    seguridad.auditar(conexion, actor, "observacion_cierre", observacion_id, "cerrada")
    return {"observacion_id": observacion_id, "estado": "cerrada"}
