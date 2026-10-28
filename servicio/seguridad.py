"""Seguridad del servicio: claves argon2id, sesiones server-side y regla de empresa.

- La clave nunca se guarda ni viaja en claro: solo hash argon2id.
- El administrador inicial nace de variables de entorno al arrancar
  (spec-api-v1); ningún SQL del repositorio lleva credenciales.
- La regla 403 se resuelve antes que cualquier existencia: una sesión de otra
  empresa recibe el mismo rechazo con o sin recurso.
"""
import uuid
from dataclasses import dataclass

import psycopg
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_HASHER = PasswordHasher(type=Type.ID)


class ErrorPermiso(Exception):
    """403: la sesión no pertenece a la empresa del recurso."""


@dataclass(frozen=True)
class SesionActiva:
    sid: str
    usuario_id: str
    empresa_id: str
    rol: str
    nombre: str


def hashear_clave(clave: str) -> str:
    return _HASHER.hash(clave)


def verificar_clave(hash_guardado: str, clave: str) -> bool:
    try:
        return _HASHER.verify(hash_guardado, clave)
    except (VerifyMismatchError, InvalidHashError):
        return False


def crear_usuario(conexion: psycopg.Connection, empresa_id: str, nombre: str, rol: str, clave: str) -> str:
    usuario_id = f"USR-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO usuarios (id, empresa_id, nombre, rol, clave_hash) VALUES (%s, %s, %s, %s, %s)",
        (usuario_id, empresa_id, nombre, rol, hashear_clave(clave)),
    )
    return usuario_id


def asegurar_admin_inicial(
    conexion: psycopg.Connection,
    empresa_id: str,
    admin_usuario: str | None,
    admin_clave: str | None,
) -> None:
    """Si no hay usuarios, crea el administrador desde variables de entorno."""
    (n_usuarios,) = conexion.execute("SELECT count(*) FROM usuarios").fetchone()
    if n_usuarios > 0:
        return
    if not admin_usuario or not admin_clave:
        raise RuntimeError(
            "la tabla usuarios está vacía y faltan ADMIN_USUARIO/ADMIN_CLAVE en el entorno"
        )
    crear_usuario(conexion, empresa_id=empresa_id, nombre=admin_usuario, rol="administrador", clave=admin_clave)


def autenticar(conexion: psycopg.Connection, nombre: str, clave: str) -> tuple[str, str, str] | None:
    fila = conexion.execute(
        "SELECT id, empresa_id, rol, clave_hash FROM usuarios WHERE nombre = %s", (nombre,)
    ).fetchone()
    if fila is None or not verificar_clave(fila[3], clave):
        return None
    return fila[0], fila[1], fila[2]


def crear_sesion(conexion: psycopg.Connection, usuario_id: str, empresa_id: str) -> str:
    sid = uuid.uuid4().hex
    conexion.execute(
        "INSERT INTO sesiones (id, usuario_id, empresa_id) VALUES (%s, %s, %s)",
        (sid, usuario_id, empresa_id),
    )
    return sid


def obtener_sesion_activa(conexion: psycopg.Connection, sid: str) -> SesionActiva | None:
    fila = conexion.execute(
        "SELECT s.id, s.usuario_id, s.empresa_id, u.rol, u.nombre "
        "FROM sesiones s JOIN usuarios u ON u.id = s.usuario_id "
        "WHERE s.id = %s AND s.revocada_en IS NULL",
        (sid,),
    ).fetchone()
    if fila is None:
        return None
    return SesionActiva(sid=fila[0], usuario_id=fila[1], empresa_id=fila[2], rol=fila[3], nombre=fila[4])


def revocar_sesion(conexion: psycopg.Connection, sid: str) -> None:
    conexion.execute(
        "UPDATE sesiones SET revocada_en = now() WHERE id = %s AND revocada_en IS NULL", (sid,)
    )


def exigir_misma_empresa(sesion: SesionActiva, empresa_recurso: str) -> None:
    """403 antes que cualquier otra cosa: no consulta la existencia del recurso."""
    if sesion.empresa_id != empresa_recurso:
        raise ErrorPermiso("empresa ajena al recurso")
