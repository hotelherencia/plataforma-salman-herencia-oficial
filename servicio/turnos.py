"""Turnos semanales por área y cambios de turno aprobados (#418, Corte 2).

La administración arma el rol de turnos; quien tiene un turno puede pedir que lo
cubra otra persona y la administración aprueba o rechaza. Al aprobar, el turno
pasa a la persona propuesta y la solicitud queda como historia.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from .operacion import NoEncontrado, OperacionInvalida

AREAS = ("recepcion", "aseo", "desayunos", "mantencion")
MAX_DIAS = 31


def _id(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:12]}"


def _turno(f) -> dict:
    return {"id": f[0], "fecha": f[1].isoformat(), "area": f[2], "usuario": f[3],
            "hora_inicio": f[4].strftime("%H:%M"), "hora_fin": f[5].strftime("%H:%M"), "nota": f[6]}


_COLS = "id, fecha, area, usuario, hora_inicio, hora_fin, nota"


def listar(conexion, desde: date, hasta: date, area: str | None = None, usuario: str | None = None) -> dict:
    if hasta <= desde:
        raise OperacionInvalida("hasta debe ser posterior a desde")
    if (hasta - desde).days > MAX_DIAS:
        raise OperacionInvalida(f"el rango admite como máximo {MAX_DIAS} días")
    filas = conexion.execute(
        f"SELECT {_COLS} FROM turnos WHERE fecha >= %s AND fecha < %s "
        "AND (%s::text IS NULL OR area = %s) AND (%s::text IS NULL OR usuario = %s) "
        "ORDER BY fecha, hora_inicio, area, usuario",
        (desde, hasta, area, area, usuario, usuario),
    ).fetchall()
    dias = {}
    for f in filas:
        dias.setdefault(f[1].isoformat(), []).append(_turno(f))
    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(),
            "dias": [{"fecha": (desde + timedelta(days=i)).isoformat(),
                      "turnos": dias.get((desde + timedelta(days=i)).isoformat(), [])}
                     for i in range((hasta - desde).days)]}


def _usuario_existe(conexion, empresa_id: str, nombre: str) -> None:
    if conexion.execute("SELECT 1 FROM usuarios WHERE empresa_id = %s AND nombre = %s", (empresa_id, nombre)).fetchone() is None:
        raise NoEncontrado(f"el usuario «{nombre}» no existe")


def crear(conexion, empresa_id: str, actor: str, datos: dict) -> dict:
    _usuario_existe(conexion, empresa_id, datos["usuario"])
    if datos["hora_fin"] <= datos["hora_inicio"]:
        raise OperacionInvalida("la hora de fin debe ser posterior a la de inicio")
    turno_id = _id("TUR")
    if conexion.execute(
        "SELECT 1 FROM turnos WHERE fecha = %s AND usuario = %s AND hora_inicio = %s AND hora_fin = %s",
        (datos["fecha"], datos["usuario"], datos["hora_inicio"], datos["hora_fin"]),
    ).fetchone():
        raise OperacionInvalida("esa persona ya tiene ese mismo turno ese día")
    conexion.execute(
        "INSERT INTO turnos (id, fecha, area, usuario, hora_inicio, hora_fin, nota, creado_por) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (turno_id, datos["fecha"], datos["area"], datos["usuario"], datos["hora_inicio"], datos["hora_fin"],
         datos.get("nota"), actor),
    )
    return {"turno_id": turno_id}


def solicitar_cambio(conexion, empresa_id: str, turno_id: str, solicitante: str, es_admin: bool, propuesto: str, motivo: str) -> dict:
    fila = conexion.execute("SELECT usuario, fecha FROM turnos WHERE id = %s FOR UPDATE", (turno_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("el turno no existe")
    if fila[0] != solicitante and not es_admin:
        raise OperacionInvalida("solo quien tiene el turno (o la administración) puede pedir el cambio")
    if fila[1] < date.today():
        raise OperacionInvalida("el turno ya pasó")
    if propuesto == fila[0]:
        raise OperacionInvalida("la persona propuesta ya tiene el turno")
    _usuario_existe(conexion, empresa_id, propuesto)
    if conexion.execute("SELECT 1 FROM turno_cambios WHERE turno_id = %s AND estado = 'pendiente'", (turno_id,)).fetchone():
        raise OperacionInvalida("ese turno ya tiene un cambio pendiente")
    cambio_id = _id("CTU")
    conexion.execute(
        "INSERT INTO turno_cambios (id, turno_id, solicitante, propuesto, motivo) VALUES (%s, %s, %s, %s, %s)",
        (cambio_id, turno_id, solicitante, propuesto, motivo.strip()),
    )
    return {"cambio_id": cambio_id, "estado": "pendiente"}


def listar_cambios(conexion, estado: str | None) -> dict:
    filas = conexion.execute(
        "SELECT c.id, c.turno_id, c.solicitante, c.propuesto, c.motivo, c.estado, c.creado_en, c.resuelto_por, "
        "t.fecha, t.area, t.hora_inicio, t.hora_fin "
        "FROM turno_cambios c JOIN turnos t ON t.id = c.turno_id "
        "WHERE (%s::text IS NULL OR c.estado = %s) ORDER BY c.creado_en DESC LIMIT 100",
        (estado, estado),
    ).fetchall()
    return {"cambios": [
        {"id": f[0], "turno_id": f[1], "solicitante": f[2], "propuesto": f[3], "motivo": f[4], "estado": f[5],
         "creado_en": f[6].isoformat(), "resuelto_por": f[7], "fecha": f[8].isoformat(), "area": f[9],
         "hora_inicio": f[10].strftime("%H:%M"), "hora_fin": f[11].strftime("%H:%M")}
        for f in filas]}


def resolver_cambio(conexion, cambio_id: str, aprobar: bool, actor: str) -> dict:
    fila = conexion.execute(
        "SELECT turno_id, propuesto, estado FROM turno_cambios WHERE id = %s FOR UPDATE", (cambio_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("la solicitud no existe")
    if fila[2] != "pendiente":
        raise OperacionInvalida(f"la solicitud ya fue {fila[2]}")
    if aprobar:
        if conexion.execute(
            "SELECT 1 FROM turnos t JOIN turnos o ON o.fecha = t.fecha AND o.hora_inicio = t.hora_inicio "
            "AND o.hora_fin = t.hora_fin AND o.usuario = %s WHERE t.id = %s", (fila[1], fila[0]),
        ).fetchone():
            raise OperacionInvalida("la persona propuesta ya tiene un turno igual ese día")
        conexion.execute("UPDATE turnos SET usuario = %s WHERE id = %s", (fila[1], fila[0]))
    conexion.execute(
        "UPDATE turno_cambios SET estado = %s, resuelto_por = %s, resuelto_en = now() WHERE id = %s",
        ("aprobado" if aprobar else "rechazado", actor, cambio_id),
    )
    return {"cambio_id": cambio_id, "estado": "aprobado" if aprobar else "rechazado", "turno_id": fila[0]}
