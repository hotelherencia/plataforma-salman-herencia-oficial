"""Biblioteca documental por rol y buzón de sugerencias (#418, Corte 2)."""
from __future__ import annotations

import uuid

from .operacion import NoEncontrado, OperacionInvalida

CATEGORIAS = ("manual", "instructivo", "politica", "otro")


def _id(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:12]}"


def publicar(conexion, actor: str, datos: dict) -> dict:
    contenido = (datos.get("contenido") or "").strip()
    enlace = (datos.get("enlace") or "").strip() or None
    if not contenido and not enlace:
        raise OperacionInvalida("escribe el contenido o indica un enlace https")
    documento_id = _id("DOC")
    conexion.execute(
        "INSERT INTO biblioteca_documentos (id, titulo, categoria, contenido, enlace, roles, creado_por) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (documento_id, datos["titulo"].strip(), datos["categoria"], contenido, enlace,
         sorted(set(datos.get("roles") or [])), actor),
    )
    return {"documento_id": documento_id}


def listar(conexion, rol: str, *, categoria: str | None = None, incluir_archivados: bool = False) -> dict:
    filas = conexion.execute(
        "SELECT id, titulo, categoria, contenido, enlace, roles, archivado, creado_por, creado_en "
        "FROM biblioteca_documentos WHERE (%s OR NOT archivado) AND (%s::text IS NULL OR categoria = %s) "
        "ORDER BY categoria, titulo LIMIT 200",
        (incluir_archivados, categoria, categoria),
    ).fetchall()
    return {"documentos": [
        {"id": f[0], "titulo": f[1], "categoria": f[2], "contenido": f[3], "enlace": f[4], "roles": f[5],
         "archivado": f[6], "creado_por": f[7], "creado_en": f[8].isoformat()}
        for f in filas if not f[5] or rol in f[5]]}


def archivar(conexion, documento_id: str) -> dict:
    if conexion.execute("UPDATE biblioteca_documentos SET archivado = true WHERE id = %s RETURNING id", (documento_id,)).fetchone() is None:
        raise NoEncontrado("el documento no existe")
    return {"documento_id": documento_id, "archivado": True}


def sugerir(conexion, actor: str, texto: str) -> dict:
    sugerencia_id = _id("SUG")
    conexion.execute("INSERT INTO sugerencias (id, texto, autor) VALUES (%s, %s, %s)", (sugerencia_id, texto.strip(), actor))
    return {"sugerencia_id": sugerencia_id, "estado": "nueva"}


def listar_sugerencias(conexion, estado: str | None) -> dict:
    filas = conexion.execute(
        "SELECT id, texto, autor, estado, respuesta, creada_en, atendida_por FROM sugerencias "
        "WHERE (%s::text IS NULL OR estado = %s) ORDER BY creada_en DESC LIMIT 100", (estado, estado)).fetchall()
    return {"sugerencias": [
        {"id": f[0], "texto": f[1], "autor": f[2], "estado": f[3], "respuesta": f[4],
         "creada_en": f[5].isoformat(), "atendida_por": f[6]} for f in filas]}


def atender_sugerencia(conexion, sugerencia_id: str, actor: str, respuesta: str | None) -> dict:
    fila = conexion.execute("SELECT estado FROM sugerencias WHERE id = %s FOR UPDATE", (sugerencia_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("la sugerencia no existe")
    if fila[0] == "atendida":
        raise OperacionInvalida("la sugerencia ya fue atendida")
    conexion.execute(
        "UPDATE sugerencias SET estado = 'atendida', respuesta = %s, atendida_por = %s, atendida_en = now() WHERE id = %s",
        ((respuesta or "").strip() or None, actor, sugerencia_id))
    return {"sugerencia_id": sugerencia_id, "estado": "atendida"}
