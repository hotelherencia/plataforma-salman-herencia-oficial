"""Servidores de correo configurables desde la plataforma (#355, 2026-11-18).

Decisión del propietario: «habilitar todo lo necesario para configurar
cualquier servidor de correo, todos los tipos posibles y parametrizados,
desde Configuración». Un buzón tiene un propósito y un proveedor:

Propósitos
- `lectura_enviados`: la plataforma revisa la carpeta de enviados y, si el
  hotel ya le escribió al correo de un lead `nuevo` después de su creación,
  lo pasa a `contactado` con la nota «auto: correo enviado desde <buzón> el
  <fecha>» (#355). Solo metadatos: destinatarios y fecha, nunca el asunto ni
  el cuerpo.
- `envio_avisos`: desde dónde salen los avisos de solicitudes (#353). Si hay
  uno activo, reemplaza al SMTP de variables de entorno.
- `recepcion_dte` (2026-11-19): casilla de intercambio del SII. Se leen los
  adjuntos XML (EnvioDTE) de los correos que llegan y cada factura queda
  pendiente de revisión en Productos (ver `facturas_proveedor`). Solo se
  descargan adjuntos .xml de hasta 2 MB; lo demás se ignora. Gmail necesita
  el alcance `gmail.readonly` y Microsoft 365 `Mail.Read`.

Proveedores (cubren Gmail, Google Workspace, Microsoft 365/Outlook, Yahoo,
Zoho, iCloud, hosting cPanel/Plesk y cualquier servidor estándar)
- `imap` / `smtp`: servidor propio o de cualquier proveedor. Seguridad
  SSL/TLS, STARTTLS o ninguna; autenticación por clave (o clave de
  aplicación) u OAuth2 (XOAUTH2 con refresh token).
- `gmail_api`: API de Gmail con cuenta de servicio (delegación de dominio en
  Workspace) u OAuth2 con refresh token. Lectura con alcance
  `gmail.metadata`; envío con `gmail.send`.
- `microsoft_graph`: Microsoft 365 con una aplicación de Entra ID
  (client credentials). Lectura con `Mail.ReadBasic.All`; envío con
  `Mail.Send`.

Los secretos (claves, client secrets, refresh tokens, JSON de la cuenta de
servicio) se guardan cifrados con Fernet usando `CORREO_CLAVE_CIFRADO`
(variable de Railway). Nunca vuelven en la API: solo qué campos están
guardados.
"""
from __future__ import annotations

import base64
import email.utils
import imaplib
import json
import logging
import os
import re
import smtplib
import ssl
import threading
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.parser import BytesHeaderParser
from typing import Callable

import psycopg

from . import ajustes, leads, seguridad

_log = logging.getLogger("servicio.correo")

PROPOSITOS = ("lectura_enviados", "envio_avisos", "recepcion_dte")
PROVEEDORES = {
    "lectura_enviados": ("imap", "gmail_api", "microsoft_graph"),
    "recepcion_dte": ("imap", "gmail_api", "microsoft_graph"),
    "envio_avisos": ("smtp", "gmail_api", "microsoft_graph"),
}
SEGURIDADES = ("ssl", "starttls", "ninguna")
AUTENTICACIONES = {
    "imap": ("clave", "oauth2"),
    "smtp": ("clave", "oauth2", "ninguna"),
    "gmail_api": ("cuenta_servicio", "oauth2"),
    "microsoft_graph": ("aplicacion",),
}
# Parámetros (no secretos) y secretos aceptados por proveedor.
PARAMETROS = {
    "imap": ("host", "puerto", "seguridad", "usuario", "autenticacion", "carpeta_enviados", "carpeta_entrada",
             "token_url", "client_id"),
    "smtp": ("host", "puerto", "seguridad", "usuario", "autenticacion", "remitente", "destino", "token_url", "client_id"),
    "gmail_api": ("usuario", "autenticacion", "client_id", "remitente", "destino"),
    "microsoft_graph": ("tenant_id", "client_id", "usuario", "remitente", "destino"),
}
SECRETOS = {
    "imap": ("clave", "client_secret", "refresh_token"),
    "smtp": ("clave", "client_secret", "refresh_token"),
    "gmail_api": ("cuenta_servicio_json", "client_secret", "refresh_token"),
    "microsoft_graph": ("client_secret",),
}
# Carpetas de enviados habituales si el servidor no anuncia \Sent (RFC 6154).
CARPETAS_ENVIADOS = (
    "Sent", "Sent Items", "Sent Messages", "Enviados", "Elementos enviados", "Mensajes enviados",
    "INBOX.Sent", "INBOX.Enviados", "[Gmail]/Sent Mail", "[Gmail]/Enviados", "[Google Mail]/Sent Mail",
)
TOKEN_URL_GOOGLE = "https://oauth2.googleapis.com/token"
MAX_MENSAJES_POR_REVISION = 2000
AUTOR_AUTO = "auto:correo"
_RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

HttpFn = Callable[[str, str, dict, bytes | None], dict]


class CorreoInvalido(Exception):
    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


class CifradoNoConfigurado(Exception):
    pass


# --- cifrado de secretos ---------------------------------------------------

def _fernet():
    clave = os.environ.get("CORREO_CLAVE_CIFRADO", "").strip()
    if not clave:
        raise CifradoNoConfigurado(
            "falta CORREO_CLAVE_CIFRADO en las variables del servicio: sin ella no se guardan claves de correo")
    from cryptography.fernet import Fernet  # import diferido: solo quien guarda secretos lo necesita

    try:
        return Fernet(clave.encode())
    except ValueError as error:
        raise CifradoNoConfigurado("CORREO_CLAVE_CIFRADO no es una clave Fernet válida") from error


def cifrado_disponible() -> bool:
    try:
        _fernet()
        return True
    except CifradoNoConfigurado:
        return False


def cifrar(secretos: dict) -> str | None:
    return _fernet().encrypt(json.dumps(secretos).encode()).decode() if secretos else None


def descifrar(token: str | None) -> dict:
    return json.loads(_fernet().decrypt(token.encode())) if token else {}


# --- validación ------------------------------------------------------------

def _texto(valor, campo, maximo=320, requerido=False):
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if requerido:
            raise CorreoInvalido(f"falta {campo}")
        return None
    if not isinstance(valor, str) or len(valor) > maximo:
        raise CorreoInvalido(f"{campo} debe ser texto de hasta {maximo} caracteres")
    return valor.strip()


def _correo(valor, campo, requerido=False):
    texto = _texto(valor, campo, requerido=requerido)
    if texto and not _RE_CORREO.match(texto):
        raise CorreoInvalido(f"{campo} no es un correo válido")
    return texto.lower() if texto else None


def validar(proposito: str, proveedor: str, parametros: dict, secretos: dict, secretos_previos: dict) -> tuple[dict, dict]:
    """Devuelve (parámetros limpios, secretos resultantes). Un secreto omitido
    o vacío conserva el guardado; `null` explícito lo borra."""
    if proposito not in PROPOSITOS:
        raise CorreoInvalido(f"propósito desconocido: {proposito}")
    if proveedor not in PROVEEDORES[proposito]:
        raise CorreoInvalido(f"el proveedor {proveedor} no sirve para {proposito}")
    if not isinstance(parametros, dict) or set(parametros) - set(PARAMETROS[proveedor]):
        raise CorreoInvalido(f"parámetros permitidos para {proveedor}: {', '.join(PARAMETROS[proveedor])}")
    if not isinstance(secretos, dict) or set(secretos) - set(SECRETOS[proveedor]):
        raise CorreoInvalido(f"secretos permitidos para {proveedor}: {', '.join(SECRETOS[proveedor])}")
    p = dict(parametros)
    limpio: dict = {}
    auth = p.get("autenticacion") or AUTENTICACIONES[proveedor][0]
    if auth not in AUTENTICACIONES[proveedor]:
        raise CorreoInvalido(f"autenticación permitida para {proveedor}: {', '.join(AUTENTICACIONES[proveedor])}")
    if proveedor != "microsoft_graph":
        limpio["autenticacion"] = auth
    if proveedor in ("imap", "smtp"):
        limpio["host"] = _texto(p.get("host"), "host", 255, requerido=True)
        seguridad_ = p.get("seguridad") or ("ssl" if proveedor == "imap" else "starttls")
        if seguridad_ not in SEGURIDADES:
            raise CorreoInvalido("seguridad debe ser ssl, starttls o ninguna")
        limpio["seguridad"] = seguridad_
        defecto = {"imap": {"ssl": 993, "starttls": 143, "ninguna": 143},
                   "smtp": {"ssl": 465, "starttls": 587, "ninguna": 25}}[proveedor][seguridad_]
        puerto = p.get("puerto") or defecto
        if isinstance(puerto, str) and puerto.isdigit():
            puerto = int(puerto)
        if isinstance(puerto, bool) or not isinstance(puerto, int) or not 1 <= puerto <= 65535:
            raise CorreoInvalido("puerto debe estar entre 1 y 65535")
        limpio["puerto"] = puerto
        limpio["usuario"] = _texto(p.get("usuario"), "usuario", requerido=auth != "ninguna")
        if proveedor == "imap" and proposito == "recepcion_dte":
            limpio["carpeta_entrada"] = _texto(p.get("carpeta_entrada"), "carpeta_entrada", 200) or "INBOX"
        elif proveedor == "imap":
            limpio["carpeta_enviados"] = _texto(p.get("carpeta_enviados"), "carpeta_enviados", 200)
    if proveedor == "gmail_api":
        limpio["usuario"] = _correo(p.get("usuario"), "usuario (correo del buzón)", requerido=True)
    if proveedor == "microsoft_graph":
        limpio["tenant_id"] = _texto(p.get("tenant_id"), "tenant_id", 100, requerido=True)
        limpio["client_id"] = _texto(p.get("client_id"), "client_id", 200, requerido=True)
        limpio["usuario"] = _correo(p.get("usuario"), "usuario (correo del buzón)", requerido=True)
    if auth == "oauth2":
        limpio["client_id"] = _texto(p.get("client_id"), "client_id", 300, requerido=True)
        if proveedor in ("imap", "smtp"):
            url = _texto(p.get("token_url"), "token_url", 500) or TOKEN_URL_GOOGLE
            if not url.startswith("https://"):
                raise CorreoInvalido("token_url debe ser https")
            limpio["token_url"] = url
    if proposito == "envio_avisos":
        limpio["remitente"] = _correo(p.get("remitente") or limpio.get("usuario"), "remitente", requerido=True)
        limpio["destino"] = _correo(p.get("destino"), "destino (quién recibe los avisos)", requerido=True)

    resultado = dict(secretos_previos)
    for nombre, valor in secretos.items():
        if valor is None:
            resultado.pop(nombre, None)
        elif isinstance(valor, str) and valor.strip():
            if len(valor) > 20000:
                raise CorreoInvalido(f"{nombre} es demasiado largo")
            resultado[nombre] = valor.strip() if nombre != "clave" else valor
    resultado = {k: v for k, v in resultado.items() if k in SECRETOS[proveedor]}
    requeridos = {
        "clave": ("clave",), "oauth2": ("client_secret", "refresh_token"),
        "cuenta_servicio": ("cuenta_servicio_json",), "aplicacion": ("client_secret",), "ninguna": (),
    }[auth]
    faltan = [s for s in requeridos if s not in resultado]
    if faltan:
        raise CorreoInvalido(f"faltan secretos: {', '.join(faltan)}")
    if auth == "cuenta_servicio":
        try:
            cuenta = json.loads(resultado["cuenta_servicio_json"])
            assert cuenta["client_email"] and cuenta["private_key"]
        except Exception as error:  # noqa: BLE001
            raise CorreoInvalido("cuenta_servicio_json debe ser el JSON de la cuenta de servicio de Google") from error
    return limpio, resultado


# --- persistencia ----------------------------------------------------------

_COLUMNAS = ("id, etiqueta, proposito, proveedor, parametros, secretos_cifrados, activo, revisado_hasta, "
             "ultima_revision_en, ultimo_resultado, ultimo_error, actualizado_por, actualizado_en")


def _vista(fila) -> dict:
    guardados = []
    if fila[5]:
        try:
            guardados = sorted(descifrar(fila[5]))
        except Exception:  # noqa: BLE001 (clave rotada o ausente)
            guardados = ["(no se pueden leer: revisa CORREO_CLAVE_CIFRADO)"]
    return {
        "buzon_id": fila[0], "etiqueta": fila[1], "proposito": fila[2], "proveedor": fila[3],
        "parametros": fila[4], "secretos_guardados": guardados, "activo": fila[6],
        "revisado_hasta": fila[7].isoformat() if fila[7] else None,
        "ultima_revision_en": fila[8].isoformat() if fila[8] else None,
        "ultimo_resultado": fila[9], "ultimo_error": fila[10],
        "actualizado_por": fila[11], "actualizado_en": fila[12].isoformat() if fila[12] else None,
    }


def listar(conexion: psycopg.Connection, empresa_id: str) -> list[dict]:
    filas = conexion.execute(
        f"SELECT {_COLUMNAS} FROM buzones_correo WHERE empresa_id = %s ORDER BY proposito, etiqueta", (empresa_id,)
    ).fetchall()
    return [_vista(f) for f in filas]


def _fila(conexion, empresa_id, buzon_id, bloquear=False):
    fila = conexion.execute(
        f"SELECT {_COLUMNAS} FROM buzones_correo WHERE id = %s AND empresa_id = %s" + (" FOR UPDATE" if bloquear else ""),
        (buzon_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise CorreoInvalido("buzón inexistente")
    return fila


def guardar(conexion: psycopg.Connection, empresa_id: str, buzon_id: str | None, cuerpo: dict, actor: str) -> dict:
    etiqueta = _texto(cuerpo.get("etiqueta"), "etiqueta", 60, requerido=True)
    activo = cuerpo.get("activo", True)
    if not isinstance(activo, bool):
        raise CorreoInvalido("activo debe ser verdadero o falso")
    previos: dict = {}
    if buzon_id:
        fila = _fila(conexion, empresa_id, buzon_id, bloquear=True)
        proposito = fila[2]
        previos = descifrar(fila[5]) if fila[5] else {}
        if cuerpo.get("proveedor", fila[3]) != fila[3]:
            previos = {}
    else:
        proposito = cuerpo.get("proposito")
    proveedor = cuerpo.get("proveedor")
    parametros, secretos = validar(proposito, proveedor, cuerpo.get("parametros") or {},
                                   cuerpo.get("secretos") or {}, previos)
    token = cifrar(secretos) if secretos else None
    if buzon_id:
        conexion.execute(
            "UPDATE buzones_correo SET etiqueta = %s, proveedor = %s, parametros = %s, secretos_cifrados = %s, "
            "activo = %s, actualizado_por = %s, actualizado_en = now(), ultimo_error = NULL WHERE id = %s",
            (etiqueta, proveedor, json.dumps(parametros), token, activo, actor, buzon_id),
        )
    else:
        buzon_id = f"BZN-{uuid.uuid4().hex[:12]}"
        conexion.execute(
            "INSERT INTO buzones_correo (id, empresa_id, etiqueta, proposito, proveedor, parametros, "
            "secretos_cifrados, activo, actualizado_por) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (buzon_id, empresa_id, etiqueta, proposito, proveedor, json.dumps(parametros), token, activo, actor),
        )
    if activo and proposito == "envio_avisos":
        # un solo buzón de envío activo por empresa
        conexion.execute(
            "UPDATE buzones_correo SET activo = false WHERE empresa_id = %s AND proposito = 'envio_avisos' AND id <> %s",
            (empresa_id, buzon_id),
        )
    seguridad.auditar(conexion, actor, "buzon_correo", buzon_id, f"guardado:{proposito}:{proveedor}")
    return _vista(_fila(conexion, empresa_id, buzon_id))


def eliminar(conexion: psycopg.Connection, empresa_id: str, buzon_id: str, actor: str) -> None:
    _fila(conexion, empresa_id, buzon_id)
    conexion.execute("DELETE FROM buzones_correo WHERE id = %s", (buzon_id,))
    seguridad.auditar(conexion, actor, "buzon_correo", buzon_id, "eliminado")


# --- HTTP y OAuth2 ---------------------------------------------------------

def _http(metodo: str, url: str, cabeceras: dict, cuerpo: bytes | None) -> dict:
    peticion = urllib.request.Request(url, data=cuerpo, headers=cabeceras, method=metodo)
    with urllib.request.urlopen(peticion, timeout=20) as respuesta:  # noqa: S310 (URLs de proveedores)
        datos = respuesta.read()
    return json.loads(datos) if datos else {}


def _formulario(datos: dict) -> bytes:
    return urllib.parse.urlencode(datos).encode()


def _token_refresh(http: HttpFn, token_url: str, client_id: str, client_secret: str, refresh_token: str) -> str:
    r = http("POST", token_url, {"Content-Type": "application/x-www-form-urlencoded"}, _formulario({
        "grant_type": "refresh_token", "client_id": client_id, "client_secret": client_secret,
        "refresh_token": refresh_token,
    }))
    return r["access_token"]


def _b64url(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _token_cuenta_servicio(http: HttpFn, cuenta_json: str, usuario: str, alcance: str) -> str:
    """JWT RS256 firmado con la clave de la cuenta de servicio (delegación de
    dominio: `sub` = buzón a leer)."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    cuenta = json.loads(cuenta_json)
    ahora = int(time.time())
    url = cuenta.get("token_uri") or TOKEN_URL_GOOGLE
    cabecera = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    carga = _b64url(json.dumps({"iss": cuenta["client_email"], "sub": usuario, "scope": alcance,
                                "aud": url, "iat": ahora, "exp": ahora + 3600}).encode())
    clave = serialization.load_pem_private_key(cuenta["private_key"].encode(), password=None)
    firma = clave.sign(f"{cabecera}.{carga}".encode(), padding.PKCS1v15(), hashes.SHA256())
    r = http("POST", url, {"Content-Type": "application/x-www-form-urlencoded"}, _formulario({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": f"{cabecera}.{carga}.{_b64url(firma)}",
    }))
    return r["access_token"]


def _token_graph(http: HttpFn, tenant_id: str, client_id: str, client_secret: str) -> str:
    r = http("POST", f"https://login.microsoftonline.com/{urllib.parse.quote(tenant_id)}/oauth2/v2.0/token",
             {"Content-Type": "application/x-www-form-urlencoded"}, _formulario({
                 "grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret,
                 "scope": "https://graph.microsoft.com/.default"}))
    return r["access_token"]


def _xoauth2(usuario: str, token: str) -> bytes:
    return f"user={usuario}\x01auth=Bearer {token}\x01\x01".encode()


# --- proveedores -----------------------------------------------------------

@dataclass
class Enviado:
    fecha: datetime
    destinatarios: list[str]


def _direcciones(*valores: str | None) -> list[str]:
    return sorted({d.lower() for _, d in email.utils.getaddresses([v for v in valores if v]) if "@" in d})


MAX_MENSAJES_DTE = 100          # por revisión
MAX_MENSAJE_DTE = 15 * 1024 * 1024
MAX_ADJUNTO_DTE = 2 * 1024 * 1024


@dataclass
class AdjuntoXml:
    mensaje_id: str
    fecha: datetime
    remitente: str | None
    nombre: str
    contenido: bytes


def _es_xml(nombre: str, tipo: str | None) -> bool:
    return (nombre or "").lower().endswith(".xml") or (tipo or "").lower() in ("text/xml", "application/xml")


def _remitente(valor: str | None) -> str | None:
    direcciones = _direcciones(valor)
    return direcciones[0][:200] if direcciones else None


def adjuntos_xml_de_mensaje(crudo: bytes, mensaje_id: str, desde: datetime | None = None) -> list[AdjuntoXml]:
    """Correo completo (RFC 822) → sus adjuntos XML de tamaño razonable."""
    import email
    from email import policy

    mensaje = email.message_from_bytes(crudo, policy=policy.default)
    try:
        fecha = email.utils.parsedate_to_datetime(mensaje.get("Date"))
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        fecha = datetime.now(timezone.utc)
    if desde and fecha < desde:
        return []
    salida = []
    for parte in mensaje.walk():
        if parte.is_multipart():
            continue
        nombre = parte.get_filename() or ""
        if not _es_xml(nombre, parte.get_content_type()) or not (nombre or parte.get_content_disposition() == "attachment"):
            continue
        contenido = parte.get_payload(decode=True) or b""
        if 0 < len(contenido) <= MAX_ADJUNTO_DTE:
            salida.append(AdjuntoXml(mensaje_id, fecha, _remitente(mensaje.get("From")), nombre[:120], contenido))
    return salida


@dataclass
class Buzon:
    """Un buzón ya descifrado, listo para leer enviados o enviar."""
    buzon_id: str
    etiqueta: str
    proposito: str
    proveedor: str
    parametros: dict
    secretos: dict
    http: HttpFn = field(default=_http)
    imap_fabrica: Callable | None = None
    smtp_fabrica: Callable | None = None

    # -- tokens
    def _token_google(self, alcance: str) -> str:
        if self.parametros.get("autenticacion") == "cuenta_servicio":
            return _token_cuenta_servicio(self.http, self.secretos["cuenta_servicio_json"], self.parametros["usuario"], alcance)
        return _token_refresh(self.http, TOKEN_URL_GOOGLE, self.parametros["client_id"],
                              self.secretos["client_secret"], self.secretos["refresh_token"])

    def _token_oauth_servidor(self) -> str:
        return _token_refresh(self.http, self.parametros["token_url"], self.parametros["client_id"],
                              self.secretos["client_secret"], self.secretos["refresh_token"])

    def _token_graph(self) -> str:
        return _token_graph(self.http, self.parametros["tenant_id"], self.parametros["client_id"],
                            self.secretos["client_secret"])

    # -- lectura de enviados (solo metadatos)
    def enviados_desde(self, desde: datetime) -> list[Enviado]:
        return {"imap": self._enviados_imap, "gmail_api": self._enviados_gmail,
                "microsoft_graph": self._enviados_graph}[self.proveedor](desde)

    def _imap(self):
        p = self.parametros
        if self.imap_fabrica:
            return self.imap_fabrica(p)
        if p["seguridad"] == "ssl":
            conexion = imaplib.IMAP4_SSL(p["host"], p["puerto"], ssl_context=ssl.create_default_context(), timeout=20)
        else:
            conexion = imaplib.IMAP4(p["host"], p["puerto"], timeout=20)
            if p["seguridad"] == "starttls":
                conexion.starttls(ssl.create_default_context())
        return conexion

    def _carpeta_enviados(self, imap) -> str:
        if self.parametros.get("carpeta_enviados"):
            return self.parametros["carpeta_enviados"]
        estado, lineas = imap.list()
        nombres = []
        for linea in lineas or []:
            texto = linea.decode(errors="replace") if isinstance(linea, bytes) else str(linea)
            m = re.match(r'^\((?P<attr>[^)]*)\) (?:"[^"]*"|NIL) (?P<nombre>.+)$', texto)
            if not m:
                continue
            nombre = m.group("nombre").strip().strip('"')
            if "\\sent" in m.group("attr").lower():
                return nombre
            nombres.append(nombre)
        for candidato in CARPETAS_ENVIADOS:
            if candidato in nombres:
                return candidato
        raise CorreoInvalido("no encontré la carpeta de enviados; indícala en «carpeta de enviados»")

    def _enviados_imap(self, desde: datetime) -> list[Enviado]:
        imap = self._imap()
        try:
            p = self.parametros
            if p["autenticacion"] == "oauth2":
                token = self._token_oauth_servidor()
                imap.authenticate("XOAUTH2", lambda _: _xoauth2(p["usuario"], token))
            else:
                imap.login(p["usuario"], self.secretos["clave"])
            carpeta = self._carpeta_enviados(imap)
            estado, _ = imap.select(f'"{carpeta}"', readonly=True)
            if estado != "OK":
                raise CorreoInvalido(f"no pude abrir la carpeta «{carpeta}»")
            # SINCE es por día: se filtra la hora exacta con el Date de cada mensaje.
            estado, datos = imap.uid("SEARCH", None, "SINCE", desde.strftime("%d-%b-%Y"))
            uids = (datos[0] or b"").split()[-MAX_MENSAJES_POR_REVISION:]
            resultado: list[Enviado] = []
            parser = BytesHeaderParser()
            for i in range(0, len(uids), 200):
                lote = b",".join(uids[i:i + 200]).decode()
                estado, partes = imap.uid("FETCH", lote, "(BODY.PEEK[HEADER.FIELDS (DATE TO CC BCC)])")
                for parte in partes or []:
                    if not isinstance(parte, tuple):
                        continue
                    cabeceras = parser.parsebytes(parte[1])
                    try:
                        fecha = email.utils.parsedate_to_datetime(cabeceras.get("Date"))
                    except (TypeError, ValueError):
                        continue
                    if fecha.tzinfo is None:
                        fecha = fecha.replace(tzinfo=timezone.utc)
                    if fecha >= desde:
                        resultado.append(Enviado(fecha, _direcciones(cabeceras.get("To"), cabeceras.get("Cc"), cabeceras.get("Bcc"))))
            return resultado
        finally:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001
                pass

    def _enviados_gmail(self, desde: datetime) -> list[Enviado]:
        token = self._token_google("https://www.googleapis.com/auth/gmail.metadata")
        cab = {"Authorization": f"Bearer {token}"}
        base = f"https://gmail.googleapis.com/gmail/v1/users/{urllib.parse.quote(self.parametros['usuario'])}/messages"
        ids: list[str] = []
        pagina = None
        while len(ids) < MAX_MENSAJES_POR_REVISION:
            q = {"labelIds": "SENT", "q": f"after:{int(desde.timestamp())}", "maxResults": 500}
            if pagina:
                q["pageToken"] = pagina
            r = self.http("GET", f"{base}?{urllib.parse.urlencode(q)}", cab, None)
            ids += [m["id"] for m in r.get("messages", [])]
            pagina = r.get("nextPageToken")
            if not pagina:
                break
        resultado = []
        for mid in ids[:MAX_MENSAJES_POR_REVISION]:
            consulta = urllib.parse.urlencode([("format", "metadata")] + [("metadataHeaders", h) for h in ("To", "Cc", "Bcc")])
            m = self.http("GET", f"{base}/{mid}?{consulta}", cab, None)
            cabeceras = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
            fecha = datetime.fromtimestamp(int(m["internalDate"]) / 1000, tz=timezone.utc)
            resultado.append(Enviado(fecha, _direcciones(cabeceras.get("to"), cabeceras.get("cc"), cabeceras.get("bcc"))))
        return resultado

    def _enviados_graph(self, desde: datetime) -> list[Enviado]:
        token = self._token_graph()
        cab = {"Authorization": f"Bearer {token}"}
        filtro = f"sentDateTime ge {desde.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
        url = (f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(self.parametros['usuario'])}"
               f"/mailFolders/sentitems/messages?" + urllib.parse.urlencode({
                   "$select": "sentDateTime,toRecipients,ccRecipients,bccRecipients",
                   "$filter": filtro, "$top": "200"}))
        resultado = []
        while url and len(resultado) < MAX_MENSAJES_POR_REVISION:
            r = self.http("GET", url, cab, None)
            for m in r.get("value", []):
                destinos = [d["emailAddress"]["address"].lower()
                            for clave in ("toRecipients", "ccRecipients", "bccRecipients")
                            for d in (m.get(clave) or []) if d.get("emailAddress", {}).get("address")]
                fecha = datetime.fromisoformat(m["sentDateTime"].replace("Z", "+00:00"))
                resultado.append(Enviado(fecha, sorted(set(destinos))))
            url = r.get("@odata.nextLink")
        return resultado

    # -- recepción de DTE (adjuntos XML de los correos que llegan)
    def adjuntos_xml_desde(self, desde: datetime) -> list["AdjuntoXml"]:
        return {"imap": self._adjuntos_imap, "gmail_api": self._adjuntos_gmail,
                "microsoft_graph": self._adjuntos_graph}[self.proveedor](desde)

    def _adjuntos_imap(self, desde: datetime) -> list["AdjuntoXml"]:
        imap = self._imap()
        try:
            p = self.parametros
            if p["autenticacion"] == "oauth2":
                token = self._token_oauth_servidor()
                imap.authenticate("XOAUTH2", lambda _: _xoauth2(p["usuario"], token))
            else:
                imap.login(p["usuario"], self.secretos["clave"])
            carpeta = p.get("carpeta_entrada") or "INBOX"
            estado, _ = imap.select(f'"{carpeta}"', readonly=True)
            if estado != "OK":
                raise CorreoInvalido(f"no pude abrir la carpeta «{carpeta}»")
            estado, datos = imap.uid("SEARCH", None, "SINCE", desde.strftime("%d-%b-%Y"))
            uids = (datos[0] or b"").split()[-MAX_MENSAJES_DTE:]
            resultado: list[AdjuntoXml] = []
            for uid in uids:
                # Primero el tamaño: un correo enorme no se descarga.
                estado, tam = imap.uid("FETCH", uid.decode(), "(RFC822.SIZE)")
                m = re.search(rb"RFC822\.SIZE (\d+)", b" ".join(t if isinstance(t, bytes) else b" ".join(t) for t in (tam or []) if t))
                if not m or int(m.group(1)) > MAX_MENSAJE_DTE:
                    continue
                estado, partes = imap.uid("FETCH", uid.decode(), "(BODY.PEEK[])")
                crudo = next((pt[1] for pt in partes or [] if isinstance(pt, tuple)), None)
                if crudo:
                    resultado += adjuntos_xml_de_mensaje(crudo, f"imap:{uid.decode()}", desde)
            return resultado
        finally:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001
                pass

    def _adjuntos_gmail(self, desde: datetime) -> list["AdjuntoXml"]:
        token = self._token_google("https://www.googleapis.com/auth/gmail.readonly")
        cab = {"Authorization": f"Bearer {token}"}
        base = f"https://gmail.googleapis.com/gmail/v1/users/{urllib.parse.quote(self.parametros['usuario'])}/messages"
        q = {"q": f"has:attachment filename:xml after:{int(desde.timestamp())} -in:sent", "maxResults": MAX_MENSAJES_DTE}
        ids = [m["id"] for m in self.http("GET", f"{base}?{urllib.parse.urlencode(q)}", cab, None).get("messages", [])]
        resultado: list[AdjuntoXml] = []
        for mid in ids[:MAX_MENSAJES_DTE]:
            m = self.http("GET", f"{base}/{mid}?format=full", cab, None)
            cabeceras = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
            fecha = datetime.fromtimestamp(int(m.get("internalDate", 0)) / 1000, tz=timezone.utc)
            pendientes = [m.get("payload", {})]
            while pendientes:
                parte = pendientes.pop()
                pendientes += parte.get("parts", []) or []
                nombre = parte.get("filename") or ""
                cuerpo = parte.get("body", {}) or {}
                if not _es_xml(nombre, parte.get("mimeType")) or int(cuerpo.get("size") or 0) > MAX_ADJUNTO_DTE:
                    continue
                datos = cuerpo.get("data")
                if not datos and cuerpo.get("attachmentId"):
                    datos = self.http("GET", f"{base}/{mid}/attachments/{cuerpo['attachmentId']}", cab, None).get("data")
                if not datos:
                    continue
                contenido = base64.urlsafe_b64decode(datos + "=" * (-len(datos) % 4))
                if len(contenido) <= MAX_ADJUNTO_DTE:
                    resultado.append(AdjuntoXml(f"gmail:{mid}", fecha, _remitente(cabeceras.get("from")), nombre[:120], contenido))
        return resultado

    def _adjuntos_graph(self, desde: datetime) -> list["AdjuntoXml"]:
        token = self._token_graph()
        cab = {"Authorization": f"Bearer {token}"}
        usuario = urllib.parse.quote(self.parametros["usuario"])
        filtro = f"receivedDateTime ge {desde.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} and hasAttachments eq true"
        url = (f"https://graph.microsoft.com/v1.0/users/{usuario}/mailFolders/inbox/messages?"
               + urllib.parse.urlencode({"$select": "id,receivedDateTime,from", "$filter": filtro, "$top": str(MAX_MENSAJES_DTE)}))
        resultado: list[AdjuntoXml] = []
        for m in self.http("GET", url, cab, None).get("value", [])[:MAX_MENSAJES_DTE]:
            fecha = datetime.fromisoformat(m["receivedDateTime"].replace("Z", "+00:00"))
            remitente = ((m.get("from") or {}).get("emailAddress") or {}).get("address")
            adjuntos = self.http("GET", f"https://graph.microsoft.com/v1.0/users/{usuario}/messages/{m['id']}/attachments?"
                                 + urllib.parse.urlencode({"$select": "id,name,contentType,size"}), cab, None)
            for a in adjuntos.get("value", []):
                if not _es_xml(a.get("name") or "", a.get("contentType")) or int(a.get("size") or 0) > MAX_ADJUNTO_DTE:
                    continue
                completo = self.http("GET", f"https://graph.microsoft.com/v1.0/users/{usuario}/messages/{m['id']}/attachments/{a['id']}", cab, None)
                if completo.get("contentBytes"):
                    contenido = base64.b64decode(completo["contentBytes"])
                    if len(contenido) <= MAX_ADJUNTO_DTE:
                        resultado.append(AdjuntoXml(f"graph:{m['id']}", fecha, (remitente or "")[:200] or None,
                                                    (a.get("name") or "")[:120], contenido))
        return resultado

    # -- envío
    def enviar(self, asunto: str, cuerpo: str, destinos: list[str] | None = None, html: str | None = None) -> None:
        """Texto plano y, si viene, versión HTML. Sin `destinos` va al destino
        guardado en el buzón (los avisos traen los de Configuración → Avisos)."""
        p = self.parametros
        para = list(destinos or []) or [p["destino"]]
        mensaje = EmailMessage()
        mensaje["Subject"] = asunto
        mensaje["From"] = p["remitente"]
        mensaje["To"] = ", ".join(para)
        mensaje.set_content(cuerpo)
        if html:
            mensaje.add_alternative(html, subtype="html")
        if self.proveedor == "smtp":
            self._enviar_smtp(mensaje)
        elif self.proveedor == "gmail_api":
            token = self._token_google("https://www.googleapis.com/auth/gmail.send")
            self.http("POST", f"https://gmail.googleapis.com/gmail/v1/users/{urllib.parse.quote(p['usuario'])}/messages/send",
                      {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                      json.dumps({"raw": _b64url(mensaje.as_bytes())}).encode())
        else:
            token = self._token_graph()
            cuerpo_graph = {"contentType": "HTML", "content": html} if html else {"contentType": "Text", "content": cuerpo}
            self.http("POST", f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(p['usuario'])}/sendMail",
                      {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                      json.dumps({"message": {"subject": asunto, "body": cuerpo_graph,
                                              "toRecipients": [{"emailAddress": {"address": d}} for d in para]},
                                  "saveToSentItems": False}).encode())

    def _enviar_smtp(self, mensaje: EmailMessage) -> None:
        p = self.parametros
        if self.smtp_fabrica:
            smtp = self.smtp_fabrica(p)
        elif p["seguridad"] == "ssl":
            smtp = smtplib.SMTP_SSL(p["host"], p["puerto"], context=ssl.create_default_context(), timeout=20)
        else:
            smtp = smtplib.SMTP(p["host"], p["puerto"], timeout=20)
            if p["seguridad"] == "starttls":
                smtp.starttls(context=ssl.create_default_context())
        try:
            if p["autenticacion"] == "clave":
                smtp.login(p["usuario"], self.secretos["clave"])
            elif p["autenticacion"] == "oauth2":
                token = self._token_oauth_servidor()
                smtp.ehlo()
                smtp.docmd("AUTH", "XOAUTH2 " + base64.b64encode(_xoauth2(p["usuario"], token)).decode())
            smtp.send_message(mensaje)
        finally:
            try:
                smtp.quit()
            except Exception:  # noqa: BLE001
                pass

    # -- prueba de conexión
    def probar(self) -> dict:
        if self.proposito == "recepcion_dte":
            adjuntos = self.adjuntos_xml_desde(datetime.now(timezone.utc) - timedelta(days=7))
            return {"ok": True, "detalle": f"conexión correcta: {len(adjuntos)} XML recibido(s) en los últimos 7 días"}
        if self.proposito == "lectura_enviados":
            enviados = self.enviados_desde(datetime.now(timezone.utc) - timedelta(days=7))
            return {"ok": True, "detalle": f"conexión correcta: {len(enviados)} correo(s) enviado(s) en los últimos 7 días"}
        self.enviar("[Hotel Herencia] Prueba de conexión del buzón de avisos",
                    "Correo de prueba de la plataforma: el buzón de envío de avisos funciona.\n"
                    "Qué avisos llegan y a quién se define en Configuración → Avisos.")
        return {"ok": True, "detalle": f"correo de prueba enviado a {self.parametros['destino']}"}


Fabrica = Callable[[dict], Buzon]


def buzon_desde_fila(fila, http: HttpFn | None = None) -> Buzon:
    return Buzon(buzon_id=fila[0], etiqueta=fila[1], proposito=fila[2], proveedor=fila[3],
                 parametros=fila[4], secretos=descifrar(fila[5]), http=http or _http)


def cargar(conexion: psycopg.Connection, empresa_id: str, buzon_id: str) -> Buzon:
    return buzon_desde_fila(_fila(conexion, empresa_id, buzon_id))


def buzon_envio_activo(conexion: psycopg.Connection, empresa_id: str | None = None) -> Buzon | None:
    if empresa_id:
        fila = conexion.execute(
            f"SELECT {_COLUMNAS} FROM buzones_correo WHERE empresa_id = %s AND proposito = 'envio_avisos' AND activo "
            "ORDER BY actualizado_en DESC LIMIT 1",
            (empresa_id,),
        ).fetchone()
    else:
        fila = conexion.execute(
            f"SELECT {_COLUMNAS} FROM buzones_correo WHERE proposito = 'envio_avisos' AND activo "
            "ORDER BY actualizado_en DESC LIMIT 1"
        ).fetchone()
    if fila is None:
        return None
    try:
        return buzon_desde_fila(fila)
    except Exception as error:  # noqa: BLE001
        _log.warning("buzon_envio_ilegible id=%s error=%s", fila[0], type(error).__name__)
        return None


# --- revisión de enviados → lead contactado (#355) -------------------------

LLAVE_BLOQUEO = 355_000_355


def _fecha_texto(fecha: datetime) -> str:
    return fecha.astimezone(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M")


def marcar_contactados(conexion: psycopg.Connection, empresa_id: str, etiqueta: str,
                       enviados: list[Enviado], registrar_buzon: bool = True) -> int:
    """Por cada correo enviado, los leads `nuevo` de ese destinatario creados
    antes del envío pasan a `contactado` (transición normal de leads)."""
    por_destino: dict[str, datetime] = {}
    for e in enviados:
        for d in e.destinatarios:
            por_destino[d] = min(por_destino.get(d, e.fecha), e.fecha)  # el primer envío
    marcados = 0
    for destino, fecha in sorted(por_destino.items()):
        filas = conexion.execute(
            "SELECT l.id FROM leads l LEFT JOIN contactos c ON c.id = l.contacto_id "
            "WHERE l.empresa_id = %s AND l.estado = 'nuevo' AND l.creado_en < %s "
            "AND lower(coalesce(l.correo, c.correo)) = %s FOR UPDATE OF l",
            (empresa_id, fecha, destino),
        ).fetchall()
        for (lead_id,) in filas:
            nota = (f"auto: correo enviado desde {etiqueta} el {_fecha_texto(fecha)}" if registrar_buzon
                    else f"auto: correo enviado el {_fecha_texto(fecha)}")
            leads.gestionar(conexion, empresa_id, lead_id, "contactado", nota, AUTOR_AUTO)
            marcados += 1
    return marcados


def revisar(conexion: psycopg.Connection, empresa_id: str, fabrica: Callable | None = None) -> dict:
    """Revisa todos los buzones de lectura activos de la empresa. Un fallo en
    un buzón queda en su `ultimo_error` y no detiene a los demás."""
    config = ajustes.leer(conexion, empresa_id, "revision_correo")
    filas = conexion.execute(
        f"SELECT {_COLUMNAS} FROM buzones_correo WHERE empresa_id = %s AND proposito = 'lectura_enviados' AND activo "
        "ORDER BY etiqueta FOR UPDATE SKIP LOCKED", (empresa_id,)
    ).fetchall()
    total = {"buzones": 0, "mensajes": 0, "leads_contactados": 0, "errores": 0}
    ahora = datetime.now(timezone.utc)
    piso = ahora - timedelta(days=leads.ventana_nuevo_dias())
    for fila in filas:
        total["buzones"] += 1
        desde = max(fila[7] - timedelta(minutes=10), piso) if fila[7] else piso
        try:
            buzon = (fabrica or buzon_desde_fila)(fila)
            enviados = buzon.enviados_desde(desde)
            marcados = marcar_contactados(conexion, empresa_id, fila[1], enviados, config["registrar_buzon"])
            total["mensajes"] += len(enviados)
            total["leads_contactados"] += marcados
            conexion.execute(
                "UPDATE buzones_correo SET revisado_hasta = %s, ultima_revision_en = now(), ultimo_error = NULL, "
                "ultimo_resultado = %s WHERE id = %s",
                (ahora, f"{len(enviados)} enviado(s) revisado(s), {marcados} lead(s) marcado(s)", fila[0]),
            )
        except Exception as error:  # noqa: BLE001 (red, credenciales, proveedor)
            total["errores"] += 1
            detalle = error.detalle if isinstance(error, CorreoInvalido) else f"{type(error).__name__}: {error}"
            conexion.execute(
                "UPDATE buzones_correo SET ultima_revision_en = now(), ultimo_error = %s WHERE id = %s",
                (detalle[:300], fila[0]),
            )
            _log.warning("revision_correo_fallida buzon=%s error=%s", fila[0], detalle[:200])
    return total


def revisar_recepcion_dte(conexion: psycopg.Connection, empresa_id: str, fabrica: Callable | None = None) -> dict:
    """Lee los XML que llegaron a los buzones `recepcion_dte` y deja cada
    factura pendiente de revisión (idempotente por emisor + tipo + folio).
    Un adjunto que no es DTE (acuse, respuesta, otro XML) se ignora."""
    from . import facturas_proveedor
    from .importacion_productos import FacturaInvalida

    filas = conexion.execute(
        f"SELECT {_COLUMNAS} FROM buzones_correo WHERE empresa_id = %s AND proposito = 'recepcion_dte' AND activo "
        "ORDER BY etiqueta", (empresa_id,),
    ).fetchall()
    total = {"buzones": 0, "adjuntos": 0, "documentos": 0, "repetidos": 0, "ignorados": 0, "errores": 0}
    ahora = datetime.now(timezone.utc)
    piso = ahora - timedelta(days=30)
    for fila in filas:
        total["buzones"] += 1
        desde = max(fila[7] - timedelta(minutes=10), piso) if fila[7] else piso
        try:
            buzon = (fabrica or buzon_desde_fila)(fila)
            adjuntos = buzon.adjuntos_xml_desde(desde)
            nuevos = repetidos = ignorados = 0
            for adjunto in adjuntos:
                try:
                    with conexion.transaction():
                        r = facturas_proveedor.crear_desde_xml(
                            conexion, adjunto.contenido, "correo", f"correo:{fila[1]}"[:80], buzon_id=fila[0],
                            mensaje_id=adjunto.mensaje_id, remitente=adjunto.remitente)
                except (FacturaInvalida, psycopg.errors.UniqueViolation):
                    ignorados += 1
                    continue
                nuevos += len(r["creados"])
                repetidos += len(r["repetidos"])
                ignorados += len(r["ignorados"])
            total["adjuntos"] += len(adjuntos)
            total["documentos"] += nuevos
            total["repetidos"] += repetidos
            total["ignorados"] += ignorados
            conexion.execute(
                "UPDATE buzones_correo SET revisado_hasta = %s, ultima_revision_en = now(), ultimo_error = NULL, "
                "ultimo_resultado = %s WHERE id = %s",
                (ahora, f"{len(adjuntos)} XML revisado(s), {nuevos} documento(s) nuevo(s) por revisar", fila[0]),
            )
        except Exception as error:  # noqa: BLE001 (red, credenciales, proveedor)
            total["errores"] += 1
            detalle = error.detalle if isinstance(error, CorreoInvalido) else f"{type(error).__name__}: {error}"
            conexion.execute("UPDATE buzones_correo SET ultima_revision_en = now(), ultimo_error = %s WHERE id = %s",
                             (detalle[:300], fila[0]))
            _log.warning("recepcion_dte_fallida buzon=%s error=%s", fila[0], detalle[:200])
    return total


class Revisor:
    """Hilo que revisa los enviados cada `intervalo_minutos` (ajuste
    `revision_correo`, inicial 15). Con varios procesos, un bloqueo
    consultivo de PostgreSQL evita revisiones simultáneas."""

    def __init__(self, database_url: str | None, fabrica: Callable | None = None):
        self.database_url = database_url
        self.fabrica = fabrica
        self._parar = threading.Event()
        self._ultima: dict[str, float] = {}

    def una_pasada(self, forzar: bool = False) -> dict:
        resultado: dict = {}
        if not self.database_url:
            return resultado
        with psycopg.connect(self.database_url) as conexion:
            if not conexion.execute("SELECT pg_try_advisory_xact_lock(%s)", (LLAVE_BLOQUEO,)).fetchone()[0]:
                return resultado
            empresas = [f[0] for f in conexion.execute(
                "SELECT DISTINCT empresa_id FROM buzones_correo "
                "WHERE proposito IN ('lectura_enviados', 'recepcion_dte') AND activo").fetchall()]
            for empresa_id in empresas:
                config = ajustes.leer(conexion, empresa_id, "revision_correo")
                vence = self._ultima.get(empresa_id, 0) + config["intervalo_minutos"] * 60
                if not forzar and (not config["activo"] or time.monotonic() < vence):
                    continue
                self._ultima[empresa_id] = time.monotonic()
                resultado[empresa_id] = revisar(conexion, empresa_id, self.fabrica)
                resultado[empresa_id]["dte"] = revisar_recepcion_dte(conexion, empresa_id, self.fabrica)
            conexion.commit()
        return resultado

    def iniciar(self) -> None:
        if not self.database_url:
            return

        def bucle():
            while not self._parar.wait(60):
                try:
                    self.una_pasada()
                except Exception as error:  # noqa: BLE001
                    _log.warning("revisor_correo_error %s", type(error).__name__)

        threading.Thread(target=bucle, name="revisor-correo", daemon=True).start()

    def detener(self) -> None:
        self._parar.set()
