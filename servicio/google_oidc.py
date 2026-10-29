"""Adaptador opcional de login con Google (OAuth 2.0 / OIDC).

Puerto de identidad externo (spec-api-v1): sin GOOGLE_CLIENT_ID y
GOOGLE_CLIENT_SECRET en el entorno, los endpoints responden 503 «no
configurado» y este flujo no existe. Sin aprovisionamiento: solo entra un
email ya presente en `usuarios.email`.

Sin dependencias nuevas: el ID token se verifica con la stdlib (RS256 contra
el JWKS de Google, caché por `kid`), porque la imagen del servicio no lleva
pyjwt ni cryptography. Red HTTP también stdlib (urllib); en las pruebas el
intercambio de `code` y el JWKS se sustituyen por mocks.
"""
import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
import urllib.parse
import urllib.request

URL_AUTORIZACION = "https://accounts.google.com/o/oauth2/v2/auth"
URL_TOKEN = "https://oauth2.googleapis.com/token"
URL_JWKS = "https://www.googleapis.com/oauth2/v3/certs"
REDIRECT_URI = "http://localhost:8080/auth/google/callback"
ALCANCE = "openid email profile"
EMISORES = ("accounts.google.com", "https://accounts.google.com")
VIDA_ESTADO_SEG = 600  # state de un solo uso: 10 minutos
VIDA_JWKS_SEG = 3600   # caché de claves públicas por kid
_TIMEOUT_SEG = 10

# DigestInfo del SHA-256 en EMSA-PKCS1-v1_5 (RFC 8017).
_PREFIJO_SHA256 = bytes.fromhex("3031300d060960864801650304020105000420")


class ErrorGoogleOidc(Exception):
    """Fallo de intercambio, de JWKS o de verificación del ID token."""


class EstadosOAuth:
    """States de un solo uso, en memoria del proceso, con expiración."""

    def __init__(self, vida_segundos: int = VIDA_ESTADO_SEG) -> None:
        self._vida = vida_segundos
        self._estados: dict[str, float] = {}
        self._cerrojo = threading.Lock()

    def nuevo(self, ahora: float | None = None) -> str:
        ahora = time.time() if ahora is None else ahora
        estado = secrets.token_urlsafe(32)
        with self._cerrojo:
            caducados = [s for s, expira in self._estados.items() if expira <= ahora]
            for s in caducados:
                del self._estados[s]
            self._estados[estado] = ahora + self._vida
        return estado

    def tomar(self, estado: str, ahora: float | None = None) -> bool:
        """True una sola vez si existe y no expiró; el estado se consume siempre."""
        ahora = time.time() if ahora is None else ahora
        with self._cerrojo:
            expira = self._estados.pop(estado, None)
            return expira is not None and ahora <= expira


def configurado(config) -> bool:
    """True solo con ambas credenciales de Google en la configuración."""
    return bool(config and config.google_client_id and config.google_client_secret)


def url_de_consentimiento(client_id: str, estado: str) -> str:
    consulta = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": ALCANCE,
        "state": estado,
    })
    return f"{URL_AUTORIZACION}?{consulta}"


def intercambiar_codigo(code: str, client_id: str, client_secret: str) -> dict:
    """POST application/x-www-form-urlencoded al endpoint token de Google."""
    cuerpo = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode("utf-8")
    try:
        with urllib.request.urlopen(
            urllib.request.Request(URL_TOKEN, data=cuerpo, method="POST"),
            timeout=_TIMEOUT_SEG,
        ) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        raise ErrorGoogleOidc("no se pudo intercambiar el código") from error


_jwks_cache: dict[str, tuple[float, dict]] = {}
_jwks_cerrojo = threading.Lock()


def _cargar_jwks() -> dict:
    try:
        with urllib.request.urlopen(URL_JWKS, timeout=_TIMEOUT_SEG) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        raise ErrorGoogleOidc("no se pudieron obtener las claves de Google") from error


def obtener_jwks(kid: str, ahora: float | None = None) -> dict:
    """JWK de la clave `kid`; refresca la caché si el kid no está vigente."""
    ahora = time.time() if ahora is None else ahora
    with _jwks_cerrojo:
        entrada = _jwks_cache.get(kid)
        if entrada is not None and entrada[0] > ahora:
            return entrada[1]
    datos = _cargar_jwks()
    claves = datos.get("keys")
    if not isinstance(claves, list):
        raise ErrorGoogleOidc("JWKS sin claves")
    with _jwks_cerrojo:
        for clave in claves:
            if isinstance(clave, dict) and clave.get("kid"):
                _jwks_cache[clave["kid"]] = (ahora + VIDA_JWKS_SEG, clave)
    entrada = _jwks_cache.get(kid)
    if entrada is None or entrada[0] <= ahora:
        raise ErrorGoogleOidc("no hay clave para el kid del token")
    return entrada[1]


def _b64u_a_bytes(valor: str) -> bytes:
    return base64.urlsafe_b64decode(valor + "=" * (-len(valor) % 4))


def _b64u_a_entero(valor: str) -> int:
    return int.from_bytes(_b64u_a_bytes(valor), "big")


def _em_pkcs1(mensaje: bytes, k: int) -> bytes:
    digesto = hashlib.sha256(mensaje).digest()
    relleno = k - len(_PREFIJO_SHA256) - len(digesto) - 3
    if relleno < 8:
        raise ErrorGoogleOidc("clave demasiado corta para RS256")
    return b"\x00\x01" + b"\xff" * relleno + b"\x00" + _PREFIJO_SHA256 + digesto


def _verificar_rs256(mensaje: bytes, firma: bytes, jwk: dict) -> None:
    try:
        n = _b64u_a_entero(jwk["n"])
        e = _b64u_a_entero(jwk["e"])
    except (KeyError, ValueError) as error:
        raise ErrorGoogleOidc("JWK incompleto") from error
    k = (n.bit_length() + 7) // 8
    if len(firma) != k:
        raise ErrorGoogleOidc("firma de longitud inválida")
    recuperado = pow(int.from_bytes(firma, "big"), e, n).to_bytes(k, "big")
    esperado = _em_pkcs1(mensaje, k)
    if not hmac.compare_digest(recuperado, esperado):
        raise ErrorGoogleOidc("firma RS256 inválida")


def verificar_id_token(id_token: str, client_id: str, ahora: float | None = None) -> dict:
    """Verifica firma RS256 (JWKS por kid) y reclamos; devuelve los claims.

    Reclamos exigidos (spec-api-v1): iss de Google, aud == client_id,
    exp vigente, email presente y verificado. Lanza ErrorGoogleOidc.
    """
    ahora = int(time.time()) if ahora is None else int(ahora)
    partes = id_token.split(".")
    if len(partes) != 3:
        raise ErrorGoogleOidc("ID token mal formado")
    try:
        cabecera = json.loads(_b64u_a_bytes(partes[0]))
        claims = json.loads(_b64u_a_bytes(partes[1]))
    except ValueError as error:
        raise ErrorGoogleOidc("ID token mal formado") from error
    if cabecera.get("alg") != "RS256":
        raise ErrorGoogleOidc("algoritmo no soportado")
    kid = cabecera.get("kid")
    if not kid:
        raise ErrorGoogleOidc("ID token sin kid")
    _verificar_rs256(f"{partes[0]}.{partes[1]}".encode("ascii"), _b64u_a_bytes(partes[2]), obtener_jwks(kid))
    if claims.get("iss") not in EMISORES:
        raise ErrorGoogleOidc("emisor inválido")
    if claims.get("aud") != client_id:
        raise ErrorGoogleOidc("audiencia inválida")
    try:
        exp = int(claims["exp"])
    except (KeyError, TypeError, ValueError) as error:
        raise ErrorGoogleOidc("exp inválido") from error
    if exp <= ahora:
        raise ErrorGoogleOidc("ID token expirado")
    if not claims.get("email_verified"):
        raise ErrorGoogleOidc("email no verificado")
    if not claims.get("email"):
        raise ErrorGoogleOidc("sin email en el ID token")
    return claims
