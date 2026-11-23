"""Canal público (spec-api-v1 «Canal público», V1-ISSUE-22/24).

La landing consulta disponibilidad y deja solicitudes sin sesión. La regla de
cupo y tarifa es la misma de la oferta interna (`reservas.oferta`); este
módulo solo la expone y persiste la solicitud con idempotencia propia. La
conversión la hace recepción por `reservas.crear_reserva` — la misma
operación y la misma carrera por la última unidad, nunca una vía paralela.
"""
import hashlib
import re
import json
import os
import threading
import time
import uuid
from datetime import date, datetime

import psycopg

from . import ajustes
from . import avisos
from . import roles
from . import entrada_publica
from . import precios
from . import reservas as reservas_db
from . import seguridad

MAX_PERSONAS = 30
MAX_NOCHES = 30
MAX_CONTACTO = 220
TOPE_CUERPO_BYTES = 8192
# SA-BODY-01 (auditoría 2026-11-17): el resto de las rutas también tiene tope.
# Antes solo /publico/* lo tenía y un POST sin sesión (webhook, /sesion) se
# leía entero en memoria antes de validar firma o credenciales.
TOPE_CUERPO_WEBHOOK_BYTES = 1024 * 1024
TOPE_CUERPO_GENERAL_BYTES = 256 * 1024
# Facturas de proveedores (2026-11-19): la foto o el PDF (máx. 10 MB) y el XML
# del SII (máx. 1,5 MB) necesitan más que el tope general, solo en esas rutas.
TOPE_CUERPO_ARCHIVO_BYTES = 10 * 1024 * 1024 + 4096
TOPE_CUERPO_XML_BYTES = 2 * 1024 * 1024
RUTAS_XML = ("/hotel/productos/documentos/xml", "/hotel/productos/importacion")
_METODOS_CON_CUERPO = frozenset({"POST", "PUT", "PATCH", "DELETE"})
ROLES_GESTION = roles.con_admin_hotel("recepcion")


class SolicitudInvalida(Exception):
    """422: validación de fechas, personas o datos del huésped."""

    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


class SinCupoOSinTarifa(Exception):
    """409: la unidad no está en la oferta del rango; nada se persiste."""

    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


class TopePorCliente(SinCupoOSinTarifa):
    """409 (#348): el cliente ya alcanzó el tope de solicitudes del período."""


def contacto_normalizado(contacto: str) -> str:
    """Correo en minúsculas o teléfono como +dígitos (misma regla que la migración 0030).
    Si el contacto trae el formato estructurado `correo · Tel: ... · Doc: ...`, toma la base."""
    texto = (contacto or "").strip()
    base = texto.split("·")[0].strip() if "·" in texto else texto
    if "@" in base:
        return base.lower()
    if "@" in texto:
        return texto.lower()
    digitos = "".join(c for c in base if c.isdigit())
    if len(digitos) == 9 and digitos.startswith("9"):
        return "+56" + digitos
    return "+" + digitos if digitos else base.lower()


def telefono_e164(texto: str | None) -> str | None:
    """+569XXXXXXXX para móviles chilenos de 9 dígitos; +dígitos (8 a 15) para el resto; None si no sirve."""
    digitos = "".join(c for c in (texto or "") if c.isdigit())
    if len(digitos) == 9 and digitos.startswith("9"):
        return "+56" + digitos
    if len(digitos) == 11 and digitos.startswith("569"):
        return "+" + digitos
    return "+" + digitos if 8 <= len(digitos) <= 15 else None


def extraer_contacto(contacto: str) -> dict:
    """Separa `correo · Tel: … · Doc: …` (o un correo o teléfono solos) en datos propios y normalizados."""
    texto = (contacto or "").strip()
    correo = re.search(r"[^\s·]+@[^\s·]+", texto)
    tel = re.search(r"Tel:\s*([^·]+)", texto, re.IGNORECASE)
    doc = re.search(r"Doc:\s*([^·]+)", texto, re.IGNORECASE)
    telefono = telefono_e164(tel.group(1)) if tel else (None if correo else telefono_e164(texto.split("·")[0]))
    return {
        "huesped_correo": correo.group(0).lower() if correo else None,
        "huesped_telefono": telefono,
        "huesped_documento": doc.group(1).strip() if doc else None,
    }


def _exigir_tope(conexion: psycopg.Connection, empresa_id: str, contacto: str) -> None:
    tope = ajustes.leer(conexion, empresa_id, "tope_solicitudes_cliente")
    if not tope["activo"]:
        return
    (n,) = conexion.execute(
        "SELECT count(*) FROM solicitudes WHERE empresa_id = %s AND contacto_normalizado = %s "
        "AND estado IN ('recibida', 'convertida') AND creado_en > now() - make_interval(days => %s)",
        (empresa_id, contacto, tope["dias"]),
    ).fetchone()
    if n >= tope["max_solicitudes"]:
        raise TopePorCliente(
            f"ya registramos {n} solicitudes con este contacto en los últimos {tope['dias']} días; "
            "recepción te responderá a la brevedad. Si necesitas otra, escríbenos por WhatsApp."
        )


class ClaveEnConflicto(Exception):
    """409: misma clave de idempotencia con otro cuerpo."""


class SolicitudAjenaOInexistente(Exception):
    """403 sin revelar cuál es el caso (igual que las reservas internas)."""


class TransicionInvalida(Exception):
    """409: la solicitud no admite la operación en su estado actual."""


class FrenoDeSolicitudes:
    """Freno de abuso persistente en PostgreSQL (OBS-01 / #414) con respaldo en memoria
    para pruebas unitarias sin base de datos: max_por_minuto por clave y cinco veces eso
    para todo el ámbito, en una ventana deslizante de 60 s.

    Una llamada puede nombrar varias claves (IP, correo, teléfono). Si
    cualquiera ya llenó su ventana, no se anota ninguna. El tope global
    sigue al valor actual de max_por_minuto, así una prueba que lo sube
    también abre el techo del ámbito.

    En PostgreSQL se guardan solo hashes SHA-256 de las claves (sin PII ni IP
    en texto plano) y se serializa por ámbito con `pg_advisory_xact_lock`.

    CE-HH-2026-001 C-02: cada `ambito` (ruta) tiene su propio techo global y
    sus propias claves, así inundar /publico/disponibilidad no agota el cupo
    de leads, solicitudes ni del webhook firmado de WhatsApp."""

    _CLAVE_GLOBAL = "__global__"

    def __init__(self, max_por_minuto: int = 6, database_url: str | None = None) -> None:
        self.max_por_minuto = max_por_minuto
        self._database_url = database_url
        self._intentos: dict[str, list[float]] = {}
        self._global: dict[str, list[float]] = {}
        self._cerrojo = threading.Lock()

    def _recientes(self, marcas: list[float], ahora: float) -> list[float]:
        return [t for t in marcas if ahora - t < 60]

    @staticmethod
    def _hash_clave(ambito: str, clave: str) -> str:
        return hashlib.sha256(f"{ambito}|{clave}".encode("utf-8")).hexdigest()

    def limpiar(self) -> None:
        """Limpia las ventanas (uso en pruebas de aislamiento)."""
        with self._cerrojo:
            self._intentos.clear()
            self._global.clear()
        if self._database_url:
            with psycopg.connect(self._database_url) as conn:
                conn.execute("DELETE FROM freno_solicitudes_eventos")
                conn.commit()

    def _permite_pg(self, claves: tuple[str, ...], ambito: str) -> bool:
        hashes = list(dict.fromkeys(self._hash_clave(ambito, c) for c in claves))
        with psycopg.connect(self._database_url) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"freno:{ambito}",))
            conn.execute(
                "DELETE FROM freno_solicitudes_eventos "
                "WHERE ambito = %s AND registrado_en < now() - interval '60 seconds'",
                (ambito,),
            )
            (global_n,) = conn.execute(
                "SELECT count(*) FROM freno_solicitudes_eventos "
                "WHERE ambito = %s AND clave_hash = %s AND registrado_en >= now() - interval '60 seconds'",
                (ambito, self._CLAVE_GLOBAL),
            ).fetchone()
            if global_n >= self.max_por_minuto * 5:
                conn.commit()
                return False
            for h in hashes:
                (n,) = conn.execute(
                    "SELECT count(*) FROM freno_solicitudes_eventos "
                    "WHERE ambito = %s AND clave_hash = %s AND registrado_en >= now() - interval '60 seconds'",
                    (ambito, h),
                ).fetchone()
                if n >= self.max_por_minuto:
                    conn.commit()
                    return False
            filas = [(ambito, self._CLAVE_GLOBAL)] + [(ambito, h) for h in hashes]
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO freno_solicitudes_eventos (ambito, clave_hash) VALUES (%s, %s)",
                    filas,
                )
            conn.commit()
            return True

    def permite(self, *claves: str, ambito: str = "global") -> bool:
        if not claves:
            return False
        if self._database_url:
            return self._permite_pg(claves, ambito)
        claves = tuple(f"{ambito}|{clave}" for clave in claves)
        ahora = time.monotonic()
        with self._cerrojo:
            if len(self._intentos) > 4096:
                self._intentos = {
                    clave: self._recientes(marcas, ahora)
                    for clave, marcas in self._intentos.items()
                    if self._recientes(marcas, ahora)
                }
            techo = self._recientes(self._global.get(ambito, []), ahora)
            self._global[ambito] = techo
            if len(techo) >= self.max_por_minuto * 5:
                return False
            ventanas: dict[str, list[float]] = {}
            for clave in claves:
                ventana = self._recientes(self._intentos.get(clave, []), ahora)
                if len(ventana) >= self.max_por_minuto:
                    self._intentos[clave] = ventana
                    return False
                ventanas[clave] = ventana
            techo.append(ahora)
            for clave, ventana in ventanas.items():
                ventana.append(ahora)
                self._intentos[clave] = ventana
            return True


def ip_visible(request) -> str:
    """IP del visitante. Sin proxy de confianza se usa el par de la conexión,
    y se ignora X-Forwarded-For (el cliente podría inventarlo). Con
    RAILWAY_ENVIRONMENT o CONFIAR_PROXY=1 se toma el último salto: el proxy
    lo agrega y el primero de la lista puede venir del cliente."""
    peer = request.client.host if request.client else "desconocida"
    confiar = bool(os.environ.get("RAILWAY_ENVIRONMENT")) or os.environ.get("CONFIAR_PROXY") == "1"
    if not confiar:
        return peer
    partes = [p.strip() for p in (request.headers.get("x-forwarded-for") or "").split(",") if p.strip()]
    if not partes:
        return peer
    return partes[-1][:64]


class TopeCuerpoPublico:
    """Corta un cuerpo que supere su tope, haya o no Content-Length.

    POST /publico/*: 8 KB. Webhook de mensajería: 1 MB. Cualquier otra
    mutación: 256 KB (SA-BODY-01)."""

    def __init__(
        self,
        app,
        tope: int = TOPE_CUERPO_BYTES,
        tope_webhook: int = TOPE_CUERPO_WEBHOOK_BYTES,
        tope_general: int = TOPE_CUERPO_GENERAL_BYTES,
    ) -> None:
        self.app = app
        self.tope = tope
        self.tope_webhook = tope_webhook
        self.tope_general = tope_general

    def _tope_de(self, ruta: str) -> int:
        if ruta.startswith("/publico/"):
            return self.tope
        if ruta.startswith("/mensajeria/"):
            return self.tope_webhook
        if ruta == "/hotel/productos/documentos/archivo":
            return max(self.tope_general, TOPE_CUERPO_ARCHIVO_BYTES)
        if ruta.startswith(RUTAS_XML):
            return max(self.tope_general, TOPE_CUERPO_XML_BYTES)
        return self.tope_general

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") not in _METODOS_CON_CUERPO:
            await self.app(scope, receive, send)
            return
        tope = self._tope_de(str(scope.get("path", "")))
        cabeceras = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        declarado = cabeceras.get("content-length")
        if declarado:
            try:
                if int(declarado) > tope:
                    await _responder_413(send)
                    return
            except ValueError:
                await _responder_413(send)
                return
        recibido = 0
        trozos: list[bytes] = []
        while True:
            mensaje = await receive()
            if mensaje["type"] != "http.request":
                continue
            bloque = mensaje.get("body", b"") or b""
            recibido += len(bloque)
            if recibido > tope:
                await _responder_413(send)
                return
            trozos.append(bloque)
            if not mensaje.get("more_body", False):
                break
        cuerpo = b"".join(trozos)
        ya = False

        async def repetir():
            nonlocal ya
            if ya:
                return {"type": "http.request", "body": b"", "more_body": False}
            ya = True
            return {"type": "http.request", "body": cuerpo, "more_body": False}

        await self.app(scope, repetir, send)


async def _responder_413(send) -> None:
    cuerpo = b'{"detail":"el cuerpo supera el tama\xc3\xb1o permitido"}'
    await send({
        "type": "http.response.start",
        "status": 413,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(cuerpo)).encode()),
        ],
    })
    await send({"type": "http.response.body", "body": cuerpo})


def _validar_rango(inicio: date, fin: date, personas: int) -> None:
    from . import contabilidad

    if fin <= inicio:
        raise SolicitudInvalida("fin debe ser mayor que inicio")
    if inicio < contabilidad.hoy_chile():
        raise SolicitudInvalida("inicio debe ser hoy o una fecha futura")
    if (fin - inicio).days > MAX_NOCHES:
        raise SolicitudInvalida(f"el rango supera las {MAX_NOCHES} noches")
    if personas < 1 or personas > MAX_PERSONAS:
        raise SolicitudInvalida(f"personas debe estar entre 1 y {MAX_PERSONAS}")


def disponibilidad(
    conexion: psycopg.Connection, inicio: date, fin: date, personas: int, ahora: datetime,
    empresa_id: str | None = None, extras: dict | None = None,
) -> dict:
    _validar_rango(inicio, fin, personas)
    resultado = reservas_db.oferta(conexion, inicio, fin, personas, ahora, empresa_id=empresa_id, extras=extras)
    # #346 (criterio 3): el visitante nunca recibe un número de habitación; ve
    # una línea por unidad libre con su tipo y precio, y el hotel asigna al convertir.
    resultado["oferta"] = [{k: v for k, v in item.items() if k != "habitacion_id"} for item in resultado["oferta"]]
    return resultado


def _hash_cuerpo(cuerpo: dict) -> str:
    canonico = json.dumps(cuerpo, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def tipo_de_unidad(conexion: psycopg.Connection, habitacion_id: str) -> str | None:
    fila = conexion.execute("SELECT tipo FROM habitaciones WHERE id = %s", (habitacion_id,)).fetchone()
    return fila[0] if fila else None


def clave_registrada(conexion: psycopg.Connection, empresa_id: str, clave: str) -> bool:
    """True si ya hay una solicitud con esa Idempotency-Key en la empresa:
    el envío es un reintento tras un corte de red o un despliegue."""
    return conexion.execute(
        "SELECT 1 FROM solicitudes WHERE empresa_id = %s AND idempotency_key = %s",
        (empresa_id, clave),
    ).fetchone() is not None


def crear_solicitud(
    conexion: psycopg.Connection,
    empresa_id: str,
    tipo: str,
    inicio: date,
    fin: date,
    personas: int,
    huesped_nombre: str,
    huesped_contacto: str,
    clave: str,
    origen: str = "landing",
) -> dict:
    """Persiste la solicitud por TIPO de habitación (#346): el visitante no
    elige ni recibe un número; el hotel asigna la unidad al convertir.
    Reintento (misma clave y cuerpo) devuelve la solicitud original con
    reintento=true; misma clave y otro cuerpo → ClaveEnConflicto (409). Sin
    unidad libre con tarifa del tipo → 409 y nada se persiste."""
    nombre = entrada_publica.limpiar_texto(huesped_nombre)
    contacto = entrada_publica.limpiar_texto(huesped_contacto)
    tipo = entrada_publica.limpiar_texto(tipo)
    if not nombre:
        raise SolicitudInvalida("huesped_nombre es obligatorio")
    if not contacto:
        raise SolicitudInvalida("huesped_contacto es obligatorio")
    if not tipo:
        raise SolicitudInvalida("tipo es obligatorio")

    cuerpo = {
        "tipo": tipo, "inicio": inicio.isoformat(), "fin": fin.isoformat(),
        "personas": personas, "huesped_nombre": nombre, "huesped_contacto": contacto,
    }
    cuerpo_hash = _hash_cuerpo(cuerpo)
    # Idempotencia antes de cupo/reloj: si el reintento corresponde a una solicitud ya creada,
    # devuelve la original aunque la última habitación se haya agotado o haya pasado la medianoche.
    existente = conexion.execute(
        "SELECT id, cuerpo_hash FROM solicitudes WHERE empresa_id = %s AND idempotency_key = %s",
        (empresa_id, clave),
    ).fetchone()
    if existente is not None:
        if existente[1] != cuerpo_hash:
            raise ClaveEnConflicto("esa clave ya se usó con otros datos")
        original = vista_publica(_fila_publica(conexion, existente[0]))
        original["reintento"] = True
        return original

    _validar_rango(inicio, fin, personas)
    oferta = reservas_db.oferta(conexion, inicio, fin, personas, datetime.now(), empresa_id=empresa_id)
    if not any(item["tipo"] == tipo for item in oferta["oferta"]):
        raise SinCupoOSinTarifa(_motivo_sin_cupo(conexion, tipo, inicio, fin))

    # #348: tope por cliente (después del reintento idempotente, que no cuenta).
    normalizado = contacto_normalizado(contacto)
    _exigir_tope(conexion, empresa_id, normalizado)
    datos_contacto = extraer_contacto(contacto)
    solicitud_id = f"SOL-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO solicitudes (id, empresa_id, tipo, habitacion_id, inicio, fin, personas, "
        "huesped_nombre, huesped_contacto, estado, origen, idempotency_key, cuerpo_hash, contacto_normalizado, "
        "huesped_correo, huesped_telefono, huesped_documento) "
        "VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s, 'recibida', %s, %s, %s, %s, %s, %s, %s)",
        (solicitud_id, empresa_id, tipo, inicio, fin, personas,
         nombre, contacto, origen, clave, cuerpo_hash, normalizado,
         datos_contacto["huesped_correo"], datos_contacto["huesped_telefono"],
         datos_contacto["huesped_documento"]),
    )
    seguridad.auditar(conexion, f"publico:{solicitud_id}", "solicitud_recibida",
                      solicitud_id, "recibida")
    # #353: aviso al administrador en la misma transacción (bandeja de salida).
    avisos.registrar_evento(conexion, "solicitud_recibida", solicitud_id, {
        "tipo": tipo, "inicio": inicio.isoformat(), "fin": fin.isoformat(), "personas": personas, "origen": origen},
        empresa_id)
    return vista_publica(_fila_publica(conexion, solicitud_id))


def _motivo_sin_cupo(conexion: psycopg.Connection, tipo: str, inicio: date, fin: date) -> str:
    """Mensaje legible y sin número de unidad: «sin tarifa» solo si ninguna
    unidad del tipo tiene precio para todo el rango (falta configurar el
    precio); si alguna lo tiene, lo que falta es cupo."""
    primera_sin_tarifa = None
    for (habitacion_id,) in conexion.execute(
        "SELECT id FROM habitaciones WHERE tipo = %s ORDER BY id", (tipo,)
    ).fetchall():
        descubierta = precios.cotizar(conexion, habitacion_id, inicio, fin).sin_tarifa
        if descubierta is None:
            return f"no hay cupo para el tipo {tipo} en ese rango"
        primera_sin_tarifa = primera_sin_tarifa or descubierta
    if primera_sin_tarifa is not None:
        return f"sin tarifa vigente para el tipo {tipo} la noche {primera_sin_tarifa}"
    return f"no hay cupo para el tipo {tipo} en ese rango"


def _fila_publica(conexion: psycopg.Connection, solicitud_id: str) -> dict:
    fila = conexion.execute(
        "SELECT id, tipo, habitacion_id, inicio, fin, personas, huesped_nombre, huesped_contacto, "
        "estado, origen, reserva_id, creado_en, huesped_correo, huesped_telefono, huesped_documento, "
        "contacto_verificado FROM solicitudes WHERE id = %s",
        (solicitud_id,),
    ).fetchone()
    if fila is None:
        raise SolicitudAjenaOInexistente("acceso denegado")
    return {
        "solicitud_id": fila[0],
        "tipo": fila[1],
        # Unidad asignada (interna): NULL hasta la conversión.
        "habitacion_id": fila[2],
        "inicio": fila[3].isoformat(),
        "fin": fila[4].isoformat(),
        "personas": fila[5],
        "huesped_nombre": fila[6],
        "huesped_contacto": fila[7],
        "estado": fila[8],
        "origen": fila[9],
        "reserva_id": fila[10],
        "creado_en": fila[11].isoformat(),
        "huesped_correo": fila[12],
        "huesped_telefono": fila[13],
        "huesped_documento": fila[14],
        "contacto_verificado": fila[15],
    }


def vista_publica(fila: dict) -> dict:
    """Lo que ve el visitante: nunca el número de habitación (#346)."""
    return {k: v for k, v in fila.items() if k != "habitacion_id"}


def bandeja(conexion: psycopg.Connection, empresa_id: str, estado: str | None) -> dict:
    if estado is not None and estado not in ("recibida", "convertida", "rechazada"):
        raise SolicitudInvalida("estado debe ser recibida, convertida o rechazada")
    if estado is None:
        filas = conexion.execute(
            "SELECT id FROM solicitudes WHERE empresa_id = %s ORDER BY creado_en, id",
            (empresa_id,),
        ).fetchall()
    else:
        filas = conexion.execute(
            "SELECT id FROM solicitudes WHERE empresa_id = %s AND estado = %s ORDER BY creado_en, id",
            (empresa_id, estado),
        ).fetchall()
    return {"solicitudes": [_fila_publica(conexion, fila[0]) for fila in filas]}


def _solicitud_de_la_empresa(
    conexion: psycopg.Connection, solicitud_id: str, empresa_id: str, bloqueo: bool = False
):
    clausula = " FOR UPDATE" if bloqueo else ""
    fila = conexion.execute(
        f"SELECT id, estado, habitacion_id, inicio, fin, huesped_nombre, personas, tipo, origen "
        f"FROM solicitudes WHERE id = %s AND empresa_id = %s{clausula}",
        (solicitud_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise SolicitudAjenaOInexistente("acceso denegado")
    return fila


def convertir(
    conexion: psycopg.Connection, empresa_id: str, solicitud_id: str, actor: str
) -> dict:
    """Crea la reserva por reservas.crear_reserva (misma carrera por la
    última unidad) sobre CUALQUIER unidad libre del tipo pedido (#347). Si la
    solicitud traía una unidad (filas anteriores a #346) se prueba primero.
    Sin unidad libre con tarifa → 409 y la solicitud queda recibida."""
    solicitud = _solicitud_de_la_empresa(conexion, solicitud_id, empresa_id, bloqueo=True)
    if solicitud[1] != "recibida":
        raise TransicionInvalida(f"la solicitud está {solicitud[1]}")
    preferida, inicio, fin, nombre, personas, tipo, origen = (
        solicitud[2], solicitud[3], solicitud[4], solicitud[5], solicitud[6], solicitud[7], solicitud[8],
    )
    canal_reserva = origen if origen in reservas_db.CANALES_RESERVA else "landing"
    oferta = reservas_db.oferta(conexion, inicio, fin, personas, datetime.now(), empresa_id=empresa_id)
    candidatas = [i["habitacion_id"] for i in sorted(
        (i for i in oferta["oferta"] if i["tipo"] == tipo),
        key=lambda i: (i["habitacion_id"] != preferida, i["total_clp"], i["habitacion_id"]),
    )]
    reserva = None
    ultimo_error: Exception | None = None
    contacto_sol = conexion.execute(
        "SELECT huesped_correo, huesped_telefono FROM solicitudes WHERE id = %s", (solicitud_id,),
    ).fetchone() or (None, None)
    for habitacion_id in candidatas:
        try:
            reserva = reservas_db.crear_reserva(
                conexion, empresa_id, habitacion_id, inicio, fin, nombre, None,
                personas=personas, canal=canal_reserva,
                huesped_correo=contacto_sol[0], huesped_telefono=contacto_sol[1],
            )
            break
        except (reservas_db.SinCupo, reservas_db.SinTarifaVigente, reservas_db.HabitacionNoVendible) as error:
            ultimo_error = error  # carrera: otra operación tomó esa unidad; se prueba la siguiente
    if reserva is None:
        detalle = str(ultimo_error) if ultimo_error else f"no quedan habitaciones del tipo {tipo} libres en ese rango"
        raise SinCupoOSinTarifa(detalle)
    conexion.execute(
        "UPDATE solicitudes SET estado = 'convertida', reserva_id = %s, habitacion_id = %s, "
        "convertida_en = now(), convertida_por = %s WHERE id = %s",
        (reserva["reserva_id"], reserva["habitacion_id"], actor, solicitud_id),
    )
    seguridad.auditar(conexion, actor, "solicitud_conversion", solicitud_id,
                      f"convertida:{reserva['reserva_id']}:{reserva['habitacion_id']}")
    cuerpo = _fila_publica(conexion, solicitud_id)
    cuerpo["reintento"] = False
    return cuerpo


def rechazar(
    conexion: psycopg.Connection, empresa_id: str, solicitud_id: str, motivo: str, actor: str
) -> dict:
    solicitud = _solicitud_de_la_empresa(conexion, solicitud_id, empresa_id, bloqueo=True)
    if solicitud[1] != "recibida":
        raise TransicionInvalida(f"la solicitud está {solicitud[1]}")
    conexion.execute(
        "UPDATE solicitudes SET estado = 'rechazada', rechazo_motivo = %s WHERE id = %s",
        ((motivo or "").strip() or "sin motivo", solicitud_id),
    )
    seguridad.auditar(conexion, actor, "solicitud_rechazo", solicitud_id, "rechazada")
    return _fila_publica(conexion, solicitud_id)


def editar(
    conexion: psycopg.Connection, empresa_id: str, solicitud_id: str, huesped_nombre: str,
    huesped_contacto: str, personas: int, actor: str,
) -> dict:
    """Corrige nombre, contacto y personas de la solicitud. Nombre y contacto se corrigen en cualquier
    estado; las personas solo mientras está «recibida» (después la reserva ya las tiene y se cambian
    ahí). Unidad, tipo y fechas no se editan: mueven cupo y tarifa, y se rehacen con otra solicitud."""
    nombre = entrada_publica.limpiar_texto(huesped_nombre)
    contacto = entrada_publica.limpiar_texto(huesped_contacto)
    if not nombre or len(nombre) > 120:
        raise SolicitudInvalida("huesped_nombre es obligatorio (máx. 120)")
    if not contacto or len(contacto) > MAX_CONTACTO:
        raise SolicitudInvalida(f"huesped_contacto es obligatorio (máx. {MAX_CONTACTO})")
    if not 1 <= personas <= MAX_PERSONAS:
        raise SolicitudInvalida(f"personas debe estar entre 1 y {MAX_PERSONAS}")
    actual = conexion.execute(
        "SELECT estado, huesped_nombre, huesped_contacto, personas FROM solicitudes "
        "WHERE id = %s AND empresa_id = %s FOR UPDATE",
        (solicitud_id, empresa_id),
    ).fetchone()
    if actual is None:
        raise SolicitudAjenaOInexistente("acceso denegado")
    if actual[0] != "recibida" and personas != actual[3]:
        raise TransicionInvalida(f"la solicitud está {actual[0]}: ya no se cambian las personas")
    cambiados = [c for c, a, n in zip(("huesped_nombre", "huesped_contacto", "personas"), actual[1:],
                                      (nombre, contacto, personas)) if a != n]
    if cambiados:
        conexion.execute(
            "UPDATE solicitudes SET huesped_nombre = %s, huesped_contacto = %s, personas = %s, "
            "contacto_normalizado = %s, huesped_correo = %s, huesped_telefono = %s, huesped_documento = %s, "
            "contacto_verificado = CASE WHEN huesped_contacto <> %s THEN FALSE ELSE contacto_verificado END "
            "WHERE id = %s",
            (nombre, contacto, personas, contacto_normalizado(contacto),
             *(extraer_contacto(contacto)[k] for k in ("huesped_correo", "huesped_telefono", "huesped_documento")),
             contacto, solicitud_id),
        )
        seguridad.auditar(conexion, actor, "solicitud_edicion", solicitud_id, ",".join(cambiados))
    return _fila_publica(conexion, solicitud_id)
