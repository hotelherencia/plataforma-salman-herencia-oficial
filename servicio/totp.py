"""TOTP (RFC 6238) con biblioteca estándar: compatible con Google Authenticator.

No hay servicio externo ni clave de API: el secreto base32 lo genera este
módulo y la app del teléfono solo lo guarda. Ventana de tolerancia: el paso
actual y el anterior (desfase de reloj), nunca el siguiente.
"""
import base64
import hashlib
import hmac
import os
import struct
import time
from urllib.parse import quote

PASO_SEGUNDOS = 30
DIGITOS = 6


def generar_secreto(entropia: int = 20) -> str:
    """Secreto base32 sin padding, listo para otpauth:// y para la app."""
    return base64.b32encode(os.urandom(entropia)).decode("ascii").rstrip("=")


def _a_bytes(secreto: str) -> bytes:
    return base64.b32decode(secreto.upper() + "=" * (-len(secreto) % 8))


def codigo(secreto: str, en_segundos: int | None = None, digitos: int = DIGITOS) -> str:
    t = int(time.time()) if en_segundos is None else en_segundos
    contador = struct.pack(">Q", t // PASO_SEGUNDOS)
    resumen = hmac.new(_a_bytes(secreto), contador, hashlib.sha1).digest()
    desplazamiento = resumen[-1] & 0x0F
    valor = struct.unpack(">I", resumen[desplazamiento : desplazamiento + 4])[0] & 0x7FFFFFFF
    return str(valor % 10**digitos).zfill(digitos)


def verificar(secreto: str, codigo_usuario: str, pasos_atras: int = 1) -> bool:
    codigo_usuario = codigo_usuario.strip().replace(" ", "")
    ahora = int(time.time())
    for atras in range(pasos_atras + 1):
        if hmac.compare_digest(codigo(secreto, ahora - atras * PASO_SEGUNDOS), codigo_usuario):
            return True
    return False


def uri_de_alta(secreto: str, usuario: str, emisor: str = "Plataforma Herencia") -> str:
    """URI otpauth que Google Authenticator escanea (o se teclea a mano)."""
    return (
        f"otpauth://totp/{quote(emisor)}:{quote(usuario)}"
        f"?secret={secreto}&issuer={quote(emisor)}"
    )
