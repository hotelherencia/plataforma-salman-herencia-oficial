"""Seguridad del servicio: claves argon2id, sesiones server-side y regla de empresa.

- La clave nunca se guarda ni viaja en claro: solo hash argon2id.
- El administrador inicial nace de variables de entorno al arrancar
  (spec-api-v1); ningún SQL del repositorio lleva credenciales.
- La regla 403 se resuelve antes que cualquier existencia: una sesión de otra
  empresa recibe el mismo rechazo con o sin recurso.
"""
import threading
import time
import uuid
from dataclasses import dataclass

import psycopg
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from . import totp

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


def autenticar(conexion: psycopg.Connection, nombre: str, clave: str) -> tuple[str, str, str, bool] | None:
    fila = conexion.execute(
        "SELECT id, empresa_id, rol, clave_hash, totp_activado FROM usuarios "
        "WHERE nombre = %s AND activo = true",
        (nombre,),
    ).fetchone()
    if fila is None or not verificar_clave(fila[3], clave):
        return None
    return fila[0], fila[1], fila[2], fila[4]


def buscar_usuario_por_email(conexion: psycopg.Connection, email: str) -> tuple[str, str, str, str] | None:
    """Identidad vinculada a Google: (id, empresa_id, rol, nombre) o None.

    SEC-A01 (#326): solo cuentas activas; una baja debe comportarse como un
    email sin vínculo (el callback redirige a «cuenta_sin_vinculo» y no abre
    sesión), jamás como una cuenta recuperable."""
    fila = conexion.execute(
        "SELECT id, empresa_id, rol, nombre FROM usuarios WHERE email = %s AND activo = true", (email,)
    ).fetchone()
    if fila is None:
        return None
    return fila[0], fila[1], fila[2], fila[3]


def vincular_email(conexion: psycopg.Connection, nombre: str, email: str) -> None:
    """Asigna el email al usuario (arranque, desde ADMIN_EMAIL). No pisa a otro dueño."""
    dueno = conexion.execute(
        "SELECT nombre FROM usuarios WHERE email = %s", (email,)
    ).fetchone()
    if dueno is not None and dueno[0] != nombre:
        return
    conexion.execute(
        "UPDATE usuarios SET email = %s WHERE nombre = %s AND email IS DISTINCT FROM %s",
        (email, nombre, email),
    )


def crear_sesion(conexion: psycopg.Connection, usuario_id: str, empresa_id: str, horas_vigencia: int = 12) -> str:
    sid = uuid.uuid4().hex
    conexion.execute(
        "INSERT INTO sesiones (id, usuario_id, empresa_id, expira_en) VALUES (%s, %s, %s, now() + (%s || ' hours')::interval)",
        (sid, usuario_id, empresa_id, str(horas_vigencia)),
    )
    return sid


def iniciar_alta_totp(conexion: psycopg.Connection, usuario_id: str) -> str:
    """Genera el secreto TOTP PENDIENTE: jamás toca el factor activo.

    SEC-A02 (#327): antes esta función escribía el secreto nuevo en la
    columna única y ponía totp_activado=false, dejando la cuenta sin 2FA
    hasta confirmar el reemplazo. La protección vigente se mantiene hasta
    que `activar_totp` mueve el pendiente a activo."""
    secreto = totp.generar_secreto()
    conexion.execute(
        "UPDATE usuarios SET totp_secreto_pendiente = %s WHERE id = %s",
        (secreto, usuario_id),
    )
    return secreto


def secreto_totp(conexion: psycopg.Connection, usuario_id: str) -> str | None:
    fila = conexion.execute(
        "SELECT totp_secreto FROM usuarios WHERE id = %s", (usuario_id,)
    ).fetchone()
    return fila[0] if fila else None


def secreto_totp_pendiente(conexion: psycopg.Connection, usuario_id: str) -> str | None:
    fila = conexion.execute(
        "SELECT totp_secreto_pendiente FROM usuarios WHERE id = %s", (usuario_id,)
    ).fetchone()
    return fila[0] if fila else None


def activar_totp(conexion: psycopg.Connection, usuario_id: str) -> None:
    """Mueve el secreto pendiente a activo (idempotente tras verificar el código)."""
    conexion.execute(
        "UPDATE usuarios SET totp_secreto = totp_secreto_pendiente, "
        "totp_secreto_pendiente = NULL, totp_activado = TRUE WHERE id = %s",
        (usuario_id,),
    )


def desactivar_totp(conexion: psycopg.Connection, usuario_id: str) -> None:
    conexion.execute(
        "UPDATE usuarios SET totp_activado = FALSE, totp_secreto = NULL, "
        "totp_secreto_pendiente = NULL WHERE id = %s",
        (usuario_id,),
    )


def reautenticar_clave(conexion: psycopg.Connection, usuario_id: str, clave: str) -> bool:
    """SEC-A02 (#327): verifica la clave actual para operaciones sensibles
    del segundo factor (reemplazar/desactivar)."""
    fila = conexion.execute(
        "SELECT clave_hash FROM usuarios WHERE id = %s", (usuario_id,)
    ).fetchone()
    return fila is not None and verificar_clave(fila[0], clave)


def obtener_sesion_activa(conexion: psycopg.Connection, sid: str) -> SesionActiva | None:
    """SEC-A01 (#326): el JOIN exige `u.activo` — una baja mata las sesiones
    vivas aunque la revocación por filas no haya corrido (carrera o baja por
    SQL directo)."""
    fila = conexion.execute(
        "SELECT s.id, s.usuario_id, s.empresa_id, u.rol, u.nombre "
        "FROM sesiones s JOIN usuarios u ON u.id = s.usuario_id "
        "WHERE s.id = %s AND s.revocada_en IS NULL AND u.activo = true "
        "AND (s.expira_en IS NULL OR s.expira_en > now())",
        (sid,),
    ).fetchone()
    if fila is None:
        return None
    return SesionActiva(sid=fila[0], usuario_id=fila[1], empresa_id=fila[2], rol=fila[3], nombre=fila[4])


def auditar(conexion: psycopg.Connection, actor: str, accion: str, recurso: str, resultado: str) -> None:
    conexion.execute(
        "INSERT INTO auditoria (id, actor, accion, recurso, resultado) VALUES (%s, %s, %s, %s, %s)",
        (f"AUD-{uuid.uuid4().hex[:12]}", actor, accion, recurso, resultado),
    )


class FrenoDeLogins:
    """Freno de fuerza bruta en memoria por proceso: 5 fallos en 5 minutos bloquean 5 minutos.

    Doble contador: por (ip, usuario) y por usuario solo (este último
    sobrevive a proxies de borde que rotan la IP vista por el proceso,
    test_preh7_seguridad «no depende de la ip»)."""

    def __init__(self, max_intentos: int = 5, ventana_segundos: int = 300) -> None:
        self._max = max_intentos
        self._ventana = ventana_segundos
        self._fallos: dict[tuple[str, str], list[float]] = {}
        self._fallos_usuario: dict[str, list[float]] = {}
        self._cerrojo = threading.Lock()

    def _contar(self, fallos: list[float], ahora: float) -> list[float]:
        return [t for t in fallos if ahora - t < self._ventana]

    def bloqueado(self, ip: str, usuario: str, ahora: float) -> bool:
        with self._cerrojo:
            fallos = self._contar(self._fallos.get((ip, usuario), []), ahora)
            self._fallos[(ip, usuario)] = fallos
            return len(fallos) >= self._max

    def registrar_fallo(self, ip: str, usuario: str, ahora: float) -> None:
        with self._cerrojo:
            self._fallos.setdefault((ip, usuario), []).append(ahora)

    def reiniciar(self, ip: str, usuario: str) -> None:
        with self._cerrojo:
            self._fallos.pop((ip, usuario), None)

    def bloqueado_usuario(self, usuario: str, ahora: float) -> bool:
        with self._cerrojo:
            fallos = self._contar(self._fallos_usuario.get(usuario, []), ahora)
            self._fallos_usuario[usuario] = fallos
            return len(fallos) >= self._max

    def registrar_fallo_usuario(self, usuario: str, ahora: float) -> None:
        with self._cerrojo:
            self._fallos_usuario.setdefault(usuario, []).append(ahora)

    def reiniciar_usuario(self, usuario: str) -> None:
        with self._cerrojo:
            self._fallos_usuario.pop(usuario, None)


def revocar_sesion(conexion: psycopg.Connection, sid: str) -> None:
    conexion.execute(
        "UPDATE sesiones SET revocada_en = now() WHERE id = %s AND revocada_en IS NULL", (sid,)
    )


def revocar_sesiones_de_usuario(conexion: psycopg.Connection, usuario_id: str) -> int:
    """Revoca todas las sesiones vivas del usuario; devuelve cuántas cayeron."""
    return conexion.execute(
        "UPDATE sesiones SET revocada_en = now() WHERE usuario_id = %s AND revocada_en IS NULL",
        (usuario_id,),
    ).rowcount


def listar_usuarios(conexion: psycopg.Connection, empresa_id: str) -> list[dict]:
    """Gestión de usuarios (spec-api-v1): jamás devuelve clave_hash."""
    filas = conexion.execute(
        "SELECT id, nombre, rol, activo FROM usuarios WHERE empresa_id = %s ORDER BY nombre",
        (empresa_id,),
    ).fetchall()
    return [{"id": f[0], "nombre": f[1], "rol": f[2], "activo": f[3]} for f in filas]


def buscar_usuario_en_empresa(conexion: psycopg.Connection, empresa_id: str, usuario_id: str):
    fila = conexion.execute(
        "SELECT id, nombre, rol, activo FROM usuarios WHERE id = %s AND empresa_id = %s",
        (usuario_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise ErrorPermiso("acceso denegado")  # 403 sin revelar existencia
    return fila


def cambiar_clave(conexion: psycopg.Connection, usuario_id: str, clave_nueva: str) -> None:
    conexion.execute(
        "UPDATE usuarios SET clave_hash = %s WHERE id = %s",
        (hashear_clave(clave_nueva), usuario_id),
    )


def contar_administradores_activos(conexion: psycopg.Connection, empresa_id: str) -> int:
    (n,) = conexion.execute(
        "SELECT count(*) FROM usuarios WHERE empresa_id = %s AND rol = 'administrador' AND activo = true",
        (empresa_id,),
    ).fetchone()
    return n


def dar_de_baja(conexion: psycopg.Connection, usuario_id: str) -> None:
    conexion.execute("UPDATE usuarios SET activo = false WHERE id = %s", (usuario_id,))
    revocar_sesiones_de_usuario(conexion, usuario_id)


def exigir_misma_empresa(sesion: SesionActiva, empresa_recurso: str) -> None:
    """403 antes que cualquier otra cosa: no consulta la existencia del recurso."""
    if sesion.empresa_id != empresa_recurso:
        raise ErrorPermiso("empresa ajena al recurso")
