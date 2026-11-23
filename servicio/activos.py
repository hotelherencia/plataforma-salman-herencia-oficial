"""Inventario de activos por habitación y mantenimiento preventivo periódico (#418, Corte 2)."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from .operacion import NoEncontrado, OperacionInvalida, _habitacion_existe


def _id(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:12]}"


def _activo(f) -> dict:
    return {"id": f[0], "habitacion_id": f[1], "area": f[2], "nombre": f[3], "categoria": f[4], "estado": f[5], "notas": f[6]}


_COLS = "id, habitacion_id, area, nombre, categoria, estado, notas"


def crear_activo(conexion, actor: str, datos: dict) -> dict:
    if not datos.get("habitacion_id") and not datos.get("area"):
        raise OperacionInvalida("indica la habitación o el área")
    if datos.get("habitacion_id"):
        _habitacion_existe(conexion, datos["habitacion_id"])
    activo_id = _id("ACT")
    conexion.execute(
        "INSERT INTO activos (id, habitacion_id, area, nombre, categoria, notas, creado_por) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (activo_id, datos.get("habitacion_id"), datos.get("area"), datos["nombre"].strip(), datos["categoria"],
         datos.get("notas"), actor),
    )
    return {"activo_id": activo_id}


def listar_activos(conexion, habitacion_id: str | None, estado: str | None) -> dict:
    filas = conexion.execute(
        f"SELECT {_COLS} FROM activos WHERE (%s::text IS NULL OR habitacion_id = %s) AND (%s::text IS NULL OR estado = %s) "
        "ORDER BY habitacion_id NULLS LAST, nombre LIMIT 500",
        (habitacion_id, habitacion_id, estado, estado),
    ).fetchall()
    return {"activos": [_activo(f) for f in filas]}


def actualizar_activo(conexion, activo_id: str, cambios: dict) -> dict:
    fila = conexion.execute(f"SELECT {_COLS} FROM activos WHERE id = %s FOR UPDATE", (activo_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("el activo no existe")
    estado = cambios.get("estado") or fila[5]
    notas = cambios["notas"] if cambios.get("notas") is not None else fila[6]
    conexion.execute("UPDATE activos SET estado = %s, notas = %s WHERE id = %s", (estado, notas, activo_id))
    if estado == "de_baja":
        conexion.execute("UPDATE mantenciones_plan SET activo = false WHERE activo_id = %s", (activo_id,))
    return {"activo_id": activo_id, "estado": estado}


def crear_plan(conexion, actor: str, activo_id: str, datos: dict) -> dict:
    fila = conexion.execute("SELECT estado FROM activos WHERE id = %s", (activo_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("el activo no existe")
    if fila[0] == "de_baja":
        raise OperacionInvalida("el activo está de baja")
    proxima = datos.get("proxima") or (date.today() + timedelta(days=datos["cada_dias"]))
    plan_id = _id("MPL")
    conexion.execute(
        "INSERT INTO mantenciones_plan (id, activo_id, descripcion, cada_dias, proxima, creado_por) VALUES (%s, %s, %s, %s, %s, %s)",
        (plan_id, activo_id, datos["descripcion"].strip(), datos["cada_dias"], proxima, actor),
    )
    return {"plan_id": plan_id, "proxima": proxima.isoformat()}


def listar_mantenciones(conexion, dentro_de_dias: int, hoy: date) -> dict:
    limite = hoy + timedelta(days=dentro_de_dias)
    filas = conexion.execute(
        "SELECT p.id, p.activo_id, p.descripcion, p.cada_dias, p.proxima, a.nombre, a.habitacion_id, a.area "
        "FROM mantenciones_plan p JOIN activos a ON a.id = p.activo_id "
        "WHERE p.activo AND p.proxima <= %s ORDER BY p.proxima, a.nombre LIMIT 200", (limite,)).fetchall()
    return {"mantenciones": [
        {"plan_id": f[0], "activo_id": f[1], "descripcion": f[2], "cada_dias": f[3], "proxima": f[4].isoformat(),
         "activo": f[5], "habitacion_id": f[6], "area": f[7], "vencida": f[4] < hoy}
        for f in filas]}


def registrar_realizada(conexion, plan_id: str, actor: str, fecha: date, nota: str | None, hoy: date) -> dict:
    fila = conexion.execute("SELECT cada_dias, activo FROM mantenciones_plan WHERE id = %s FOR UPDATE", (plan_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("el plan de mantención no existe")
    if not fila[1]:
        raise OperacionInvalida("el plan está inactivo")
    if fecha > hoy:
        raise OperacionInvalida("la fecha de la mantención no puede ser futura")
    if conexion.execute("SELECT 1 FROM mantenciones_realizadas WHERE plan_id = %s AND fecha = %s", (plan_id, fecha)).fetchone():
        raise OperacionInvalida("esa mantención ya está registrada en esa fecha")
    conexion.execute(
        "INSERT INTO mantenciones_realizadas (id, plan_id, fecha, realizada_por, nota) VALUES (%s, %s, %s, %s, %s)",
        (_id("MRE"), plan_id, fecha, actor, (nota or "").strip() or None))
    proxima = fecha + timedelta(days=fila[0])
    conexion.execute("UPDATE mantenciones_plan SET proxima = %s WHERE id = %s", (proxima, plan_id))
    return {"plan_id": plan_id, "proxima": proxima.isoformat()}
