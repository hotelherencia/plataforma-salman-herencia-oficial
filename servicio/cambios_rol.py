"""Validación de cambios de rol: quien los pide no los aprueba.

Toda asignación de un rol privilegiado en un alta, y todo cambio de rol de una cuenta existente, queda
pendiente hasta que lo valida la administración del hotel (`admin_hotel` o `administrador`) y que no sea
quien lo pidió ni el afectado. Mientras está pendiente la cuenta nueva está inactiva y la existente
conserva su rol. Único caso sin segunda persona: aún no existe ningún aprobador activo (primer arranque);
queda marcado `sin_aprobador`, auditado y alertado.
"""
from __future__ import annotations

import logging
import uuid

import psycopg

from . import observabilidad, roles, seguridad


class CambioNoEncontrado(Exception):
    pass


class CambioNoPermitido(Exception):
    """403: quien resuelve no puede (rol, o es quien lo pidió o el afectado)."""


class CambioYaResuelto(Exception):
    pass


def _vista(f) -> dict:
    return {"id": f[0], "usuario_id": f[1], "usuario": f[2], "rol_anterior": f[3], "rol_nuevo": f[4], "motivo": f[5],
            "solicitado_por": f[6], "solicitado_en": f[7].isoformat(), "estado": f[8], "resuelto_por": f[9],
            "resuelto_en": f[10].isoformat() if f[10] else None, "comentario": f[11], "sin_aprobador": f[12]}


_SELECT = ("SELECT c.id, c.usuario_id, u.nombre, c.rol_anterior, c.rol_nuevo, c.motivo, c.solicitado_por, c.solicitado_en, "
           "c.estado, c.resuelto_por, c.resuelto_en, c.comentario, c.sin_aprobador "
           "FROM cambios_rol c JOIN usuarios u ON u.id = c.usuario_id ")


def hay_aprobador(conexion: psycopg.Connection, empresa_id: str, excluir: list[str]) -> bool:
    return conexion.execute(
        "SELECT 1 FROM usuarios WHERE empresa_id = %s AND activo AND rol = ANY(%s) AND NOT (id = ANY(%s)) LIMIT 1",
        (empresa_id, sorted(roles.ROLES_APROBADORES), excluir),
    ).fetchone() is not None


def _aplicar(conexion: psycopg.Connection, usuario_id: str, rol_nuevo: str) -> None:
    conexion.execute("UPDATE usuarios SET rol = %s, activo = true WHERE id = %s", (rol_nuevo, usuario_id))
    seguridad.revocar_sesiones_de_usuario(conexion, usuario_id)  # ninguna sesión conserva el rol anterior


def solicitar(conexion: psycopg.Connection, empresa_id: str, usuario_id: str, rol_anterior: str | None,
              rol_nuevo: str, motivo: str | None, solicitante_id: str, solicitante: str) -> dict:
    cambio_id = f"CRL-{uuid.uuid4().hex[:12]}"
    directo = not hay_aprobador(conexion, empresa_id, [solicitante_id, usuario_id])
    conexion.execute(
        "INSERT INTO cambios_rol (id, empresa_id, usuario_id, rol_anterior, rol_nuevo, motivo, solicitado_por, "
        "estado, sin_aprobador, resuelto_por, resuelto_en) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CASE WHEN %s THEN now() END)",
        (cambio_id, empresa_id, usuario_id, rol_anterior, rol_nuevo, motivo, solicitante,
         "aprobado" if directo else "pendiente", directo, solicitante if directo else None, directo),
    )
    if directo:
        _aplicar(conexion, usuario_id, rol_nuevo)
        observabilidad.evento_seguridad("cambio_rol_sin_aprobador", nivel=logging.WARNING, actor=solicitante[:64],
                                        rol_nuevo=rol_nuevo)
        seguridad.auditar(conexion, solicitante, "cambio-rol", usuario_id,
                          f"{rol_anterior or 'alta'} -> {rol_nuevo} aplicado SIN aprobador (aún no existe)")
    else:
        seguridad.auditar(conexion, solicitante, "cambio-rol", usuario_id,
                          f"{rol_anterior or 'alta'} -> {rol_nuevo} solicitado; pendiente de validación")
    return {"cambio_id": cambio_id, "estado": "aprobado" if directo else "pendiente", "sin_aprobador": directo}


def listar(conexion: psycopg.Connection, empresa_id: str, estado: str | None = None) -> list[dict]:
    filas = conexion.execute(
        _SELECT + "WHERE c.empresa_id = %s AND (%s::text IS NULL OR c.estado = %s) ORDER BY c.solicitado_en DESC LIMIT 200",
        (empresa_id, estado, estado),
    ).fetchall()
    return [_vista(f) for f in filas]


def resolver(conexion: psycopg.Connection, empresa_id: str, cambio_id: str, aprobar: bool,
             sesion: seguridad.SesionActiva, comentario: str | None) -> dict:
    fila = conexion.execute(_SELECT + "WHERE c.id = %s AND c.empresa_id = %s FOR UPDATE OF c", (cambio_id, empresa_id)).fetchone()
    if fila is None:
        raise CambioNoEncontrado(cambio_id)
    c = _vista(fila)
    if sesion.rol not in roles.ROLES_APROBADORES:
        raise CambioNoPermitido("solo la administración del hotel valida cambios de rol")
    if c["solicitado_por"] == sesion.nombre or c["usuario_id"] == sesion.usuario_id:
        seguridad.auditar(conexion, sesion.nombre, "cambio-rol", c["usuario_id"], "auto-aprobación denegada")
        conexion.commit()
        raise CambioNoPermitido("no puedes validar un cambio que pediste tú ni uno que te afecta")
    if c["estado"] != "pendiente":
        raise CambioYaResuelto(c["estado"])
    conexion.execute(
        "UPDATE cambios_rol SET estado = %s, resuelto_por = %s, resuelto_en = now(), comentario = %s WHERE id = %s",
        ("aprobado" if aprobar else "rechazado", sesion.nombre, (comentario or None), cambio_id),
    )
    if aprobar:
        _aplicar(conexion, c["usuario_id"], c["rol_nuevo"])
    seguridad.auditar(conexion, sesion.nombre, "cambio-rol", c["usuario_id"],
                      f"{'aprobado' if aprobar else 'rechazado'}: {c['rol_anterior'] or 'alta'} -> {c['rol_nuevo']}")
    observabilidad.evento_seguridad("cambio_rol_resuelto", nivel=logging.WARNING, actor=sesion.nombre[:64],
                                    aprobado=aprobar, rol_nuevo=c["rol_nuevo"])
    return _vista(conexion.execute(_SELECT + "WHERE c.id = %s", (cambio_id,)).fetchone())


