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
    """States de un solo uso, en memoria del proceso, con expiración.

    SEC-A05 (#330): cada state queda vinculado a un identificador de
    transacción (`tx`) que el flujo HTTP guarda en una cookie HttpOnly de
    vida corta: el callback solo acepta el state si la cookie coincide con
    la que originó el login. Sin esto, un state interceptado era válido en
    cualquier navegador (login CSRF, auditoría 2026-11-03).

    Límite conocido (V1, un proceso): el diccionario vive en memoria del
    proceso; con réplicas habría que persistir las transacciones o fijar
    afinidad — pendiente para el escalado multi-instancia.
    """

    def __init__(self, vida_segundos: int = VIDA_ESTADO_SEG) -> None:
        self._vida = vida_segundos
        self._estados: dict[str, tuple[float, str | None]] = {}
        self._cerrojo = threading.Lock()

    def nuevo(self, tx: str | None = None, ahora: float | None = None) -> str:
        ahora = time.time() if ahora is None else ahora
        estado = secrets.token_urlsafe(32)
        with self._cerrojo:
            caducados = [s for s, (expira, _) in self._estados.items() if expira <= ahora]
            for s in caducados:
                del self._estados[s]
            self._estados[estado] = (ahora + self._vida, tx)
        return estado

    def tomar(self, estado: str, tx: str | None = None, ahora: float | None = None) -> bool:
        """True una sola vez si existe, no expiró y la transacción coincide.

        El estado se consume siempre (intento válido o no) para no dejar
        material reutilizable."""
        ahora = time.time() if ahora is None else ahora
        with self._cerrojo:
            guardado = self._estados.pop(estado, None)
            if guardado is None:
                return False
            expira, tx_guardado = guardado
            return ahora <= expira and tx_guardado == tx


# CE-HH-2026-001 C-03: valores `amr` (RFC 8176) que acreditan un segundo factor.
AMR_CON_MFA = frozenset({"mfa", "otp", "hwk", "swk", "sms", "fpt", "face", "pop"})
VIDA_PENDIENTE_MFA_SEG = 300
MAX_INTENTOS_MFA = 5


def acredita_mfa(claims: dict) -> bool:
    amr = claims.get("amr") or []
    if isinstance(amr, str):
        amr = [amr]
    return any(valor in AMR_CON_MFA for valor in amr)


class PendientesMfa:
    """Login Google de administrador a la espera del código TOTP local.

    La clave es el valor de una cookie HttpOnly de vida corta (no viaja en
    la URL). Un solo uso al completar; se descarta tras MAX_INTENTOS_MFA
    códigos inválidos o al expirar. Mismo límite multi-instancia que
    EstadosOAuth (memoria del proceso)."""

    def __init__(self, vida_segundos: int = VIDA_PENDIENTE_MFA_SEG, max_intentos: int = MAX_INTENTOS_MFA) -> None:
        self._vida = vida_segundos
        self._max = max_intentos
        self._pendientes: dict[str, dict] = {}
        self._cerrojo = threading.Lock()

    def nuevo(self, usuario_id: str, empresa_id: str, nombre: str, ahora: float | None = None) -> str:
        ahora = time.time() if ahora is None else ahora
        tx = secrets.token_urlsafe(32)
        with self._cerrojo:
            for clave in [c for c, v in self._pendientes.items() if v["expira"] <= ahora]:
                del self._pendientes[clave]
            self._pendientes[tx] = {
                "usuario_id": usuario_id, "empresa_id": empresa_id, "nombre": nombre,
                "expira": ahora + self._vida, "intentos": 0,
            }
        return tx

    def ver(self, tx: str | None, ahora: float | None = None) -> dict | None:
        ahora = time.time() if ahora is None else ahora
        if not tx:
            return None
        with self._cerrojo:
            pendiente = self._pendientes.get(tx)
            if pendiente is None:
                return None
            if pendiente["expira"] <= ahora:
                del self._pendientes[tx]
                return None
            return dict(pendiente)

    def fallo(self, tx: str) -> None:
        with self._cerrojo:
            pendiente = self._pendientes.get(tx)
            if pendiente is None:
                return
            pendiente["intentos"] += 1
            if pendiente["intentos"] >= self._max:
                del self._pendientes[tx]

    def consumir(self, tx: str) -> None:
        with self._cerrojo:
            self._pendientes.pop(tx, None)


def configurado(config) -> bool:
    """True solo con ambas credenciales de Google en la configuración."""
    return bool(config and config.google_client_id and config.google_client_secret)


def url_de_consentimiento(client_id: str, estado: str, redirect_uri: str = REDIRECT_URI) -> str:
    consulta = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": ALCANCE,
        "state": estado,
    })
    return f"{URL_AUTORIZACION}?{consulta}"


def intercambiar_codigo(code: str, client_id: str, client_secret: str, redirect_uri: str = REDIRECT_URI) -> dict:
    """POST application/x-www-form-urlencoded al endpoint token de Google."""
    cuerpo = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
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
