"""Idempotencia por clave (spec-api-v1): misma clave y mismo cuerpo repiten
la respuesta original; misma clave con otro cuerpo responde 409.
"""
import hashlib
import json


class ConflictoIdempotencia(Exception):
    """409: la clave ya existe con otro cuerpo."""


# CE-HH-2026-001 C-01: campos secretos que nunca entran al digest guardado en
# `claves_idempotencia`. Un SHA-256 sin sal de un JSON que contiene la clave
# permitía atacar la contraseña offline con acceso de lectura a la tabla.
CAMPOS_SECRETOS = frozenset({"clave", "clave_actual", "clave_nueva", "password", "totp", "codigo_totp"})


def _sin_secretos(valor):
    if isinstance(valor, dict):
        return {k: _sin_secretos(v) for k, v in valor.items() if k not in CAMPOS_SECRETOS}
    if isinstance(valor, list):
        return [_sin_secretos(v) for v in valor]
    return valor


def hash_cuerpo(cuerpo: dict) -> str:
    """Digest del cuerpo sin campos secretos (C-01).

    Consecuencia aceptada: misma clave de idempotencia con otra contraseña y
    el resto igual se trata como reintento (no 409).
    """
    limpio = _sin_secretos(cuerpo)
    return hashlib.sha256(json.dumps(limpio, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def respuesta_previa(conexion, empresa_id: str, clave: str, cuerpo: dict) -> tuple[int, dict] | None:
    """Devuelve la respuesta ya guardada para esta clave y este cuerpo.

    None si la clave es nueva. Misma clave con otro cuerpo: ConflictoIdempotencia.
    El cerrojo es el de `ejecutar`, así que la lectura y la escritura siguientes
    quedan en la misma transacción.
    """
    digest = hash_cuerpo(cuerpo)
    conexion.execute(
        "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
        (empresa_id, clave),
    )
    fila = conexion.execute(
        "SELECT hash_cuerpo, codigo_respuesta, cuerpo_respuesta "
        "FROM claves_idempotencia WHERE empresa_id = %s AND clave = %s",
        (empresa_id, clave),
    ).fetchone()
    if fila is None:
        return None
    if fila[0] != digest:
        raise ConflictoIdempotencia("la clave ya fue usada con otro cuerpo")
    return fila[1], fila[2]


def ejecutar(conexion, empresa_id: str, clave: str, cuerpo: dict, operacion) -> tuple[int, dict]:
    """Ejecuta `operacion()` una sola vez por clave y devuelve (código, cuerpo).

    `operacion` debe devolver (codigo_respuesta, cuerpo_dict). La respuesta se
    guarda en `claves_idempotencia` y se repite intacta en reintentos. El
    cerrojo transaccional por `(empresa_id, clave)` serializa reintentos
    concurrentes en vuelo para que no ejecuten `operacion()` dos veces ni
    fallen con UniqueViolation al insertar la clave.
    """
    digest = hash_cuerpo(cuerpo)
    conexion.execute(
        "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
        (empresa_id, clave),
    )
    fila = conexion.execute(
        "SELECT hash_cuerpo, codigo_respuesta, cuerpo_respuesta "
        "FROM claves_idempotencia WHERE empresa_id = %s AND clave = %s",
        (empresa_id, clave),
    ).fetchone()
    if fila is not None:
        if fila[0] != digest:
            raise ConflictoIdempotencia("la clave ya fue usada con otro cuerpo")
        return fila[1], fila[2]
    codigo, respuesta = operacion()
    conexion.execute(
        "INSERT INTO claves_idempotencia (empresa_id, clave, hash_cuerpo, codigo_respuesta, cuerpo_respuesta) "
        "VALUES (%s, %s, %s, %s, %s)",
        (empresa_id, clave, digest, codigo, json.dumps(respuesta, ensure_ascii=False)),
    )
    return codigo, respuesta
