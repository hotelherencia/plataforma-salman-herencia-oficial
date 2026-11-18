"""Canal público (spec-api-v1 «Canal público», V1-ISSUE-22/24).

La landing consulta disponibilidad y deja solicitudes sin sesión. La regla de
cupo y tarifa es la misma de la oferta interna (`reservas.oferta`); este
módulo solo la expone y persiste la solicitud con idempotencia propia. La
conversión la hace recepción por `reservas.crear_reserva` — la misma
operación y la misma carrera por la última unidad, nunca una vía paralela.
"""
import hashlib
import json
import os
import threading
import time
import uuid
from datetime import date, datetime

import psycopg

from . import avisos
from . import roles
from . import entrada_publica
from . import precios
from . import reservas as reservas_db
from . import seguridad

MAX_PERSONAS = 30
MAX_NOCHES = 30
TOPE_CUERPO_BYTES = 8192
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


class ClaveEnConflicto(Exception):
    """409: misma clave de idempotencia con otro cuerpo."""


class SolicitudAjenaOInexistente(Exception):
    """403 sin revelar cuál es el caso (igual que las reservas internas)."""


class TransicionInvalida(Exception):
    """409: la solicitud no admite la operación en su estado actual."""


class FrenoDeSolicitudes:
    """Freno de abuso en memoria por proceso: max_por_minuto por clave y
    cinco veces eso para todo el proceso, en una ventana de 60 s.

    Una llamada puede nombrar varias claves (IP, correo, teléfono). Si
    cualquiera ya llenó su ventana, no se anota ninguna. El tope global
    sigue al valor actual de max_por_minuto, así una prueba que lo sube
    también abre el techo del proceso.

    CE-HH-2026-001 C-02: cada `ambito` (ruta) tiene su propio techo global y
    sus propias claves, así inundar /publico/disponibilidad no agota el cupo
    de leads, solicitudes ni del webhook firmado de WhatsApp."""

    def __init__(self, max_por_minuto: int = 6) -> None:
        self.max_por_minuto = max_por_minuto
        self._intentos: dict[str, list[float]] = {}
        self._global: dict[str, list[float]] = {}
        self._cerrojo = threading.Lock()

    def _recientes(self, marcas: list[float], ahora: float) -> list[float]:
        return [t for t in marcas if ahora - t < 60]

    def permite(self, *claves: str, ambito: str = "global") -> bool:
        if not claves:
            return False
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
    """Corta un POST /publico/* que supere 8 KB, haya o no Content-Length."""

    def __init__(self, app, tope: int = TOPE_CUERPO_BYTES) -> None:
        self.app = app
        self.tope = tope

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return
        if not str(scope.get("path", "")).startswith("/publico/"):
            await self.app(scope, receive, send)
            return
        cabeceras = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        declarado = cabeceras.get("content-length")
        if declarado:
            try:
                if int(declarado) > self.tope:
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
            if recibido > self.tope:
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
    if fin <= inicio:
        raise SolicitudInvalida("fin debe ser mayor que inicio")
    if inicio < date.today():
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
    return reservas_db.oferta(conexion, inicio, fin, personas, ahora, empresa_id=empresa_id, extras=extras)


def _hash_cuerpo(cuerpo: dict) -> str:
    canonico = json.dumps(cuerpo, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def tipo_de_unidad(conexion: psycopg.Connection, habitacion_id: str) -> str | None:
    fila = conexion.execute("SELECT tipo FROM habitaciones WHERE id = %s", (habitacion_id,)).fetchone()
    return fila[0] if fila else None


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
    _validar_rango(inicio, fin, personas)
    nombre = entrada_publica.limpiar_texto(huesped_nombre)
    contacto = entrada_publica.limpiar_texto(huesped_contacto)
    tipo = entrada_publica.limpiar_texto(tipo)
    if not nombre:
        raise SolicitudInvalida("huesped_nombre es obligatorio")
    if not contacto:
        raise SolicitudInvalida("huesped_contacto es obligatorio")
    if not tipo:
        raise SolicitudInvalida("tipo es obligatorio")

    oferta = reservas_db.oferta(conexion, inicio, fin, personas, datetime.now(), empresa_id=empresa_id)
    if not any(item["tipo"] == tipo for item in oferta["oferta"]):
        raise SinCupoOSinTarifa(_motivo_sin_cupo(conexion, tipo, inicio, fin))

    cuerpo = {
        "tipo": tipo, "inicio": inicio.isoformat(), "fin": fin.isoformat(),
        "personas": personas, "huesped_nombre": nombre, "huesped_contacto": contacto,
    }
    cuerpo_hash = _hash_cuerpo(cuerpo)
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

    solicitud_id = f"SOL-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO solicitudes (id, empresa_id, tipo, habitacion_id, inicio, fin, personas, "
        "huesped_nombre, huesped_contacto, estado, origen, idempotency_key, cuerpo_hash) "
        "VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s, 'recibida', %s, %s, %s)",
        (solicitud_id, empresa_id, tipo, inicio, fin, personas,
         nombre, contacto, origen, clave, cuerpo_hash),
    )
    seguridad.auditar(conexion, f"publico:{solicitud_id}", "solicitud_recibida",
                      solicitud_id, "recibida")
    # #353: aviso al administrador en la misma transacción (bandeja de salida).
    avisos.registrar_evento(conexion, "solicitud_recibida", solicitud_id, {
        "tipo": tipo, "inicio": inicio.isoformat(), "fin": fin.isoformat(), "personas": personas, "origen": origen})
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
        "estado, origen, reserva_id, creado_en FROM solicitudes WHERE id = %s",
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


def _solicitud_de_la_empresa(conexion: psycopg.Connection, solicitud_id: str, empresa_id: str):
    fila = conexion.execute(
        "SELECT id, estado, habitacion_id, inicio, fin, huesped_nombre, personas, tipo "
        "FROM solicitudes WHERE id = %s AND empresa_id = %s",
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
    solicitud = _solicitud_de_la_empresa(conexion, solicitud_id, empresa_id)
    if solicitud[1] != "recibida":
        raise TransicionInvalida(f"la solicitud está {solicitud[1]}")
    preferida, inicio, fin, nombre, personas, tipo = solicitud[2], solicitud[3], solicitud[4], solicitud[5], solicitud[6], solicitud[7]
    oferta = reservas_db.oferta(conexion, inicio, fin, personas, datetime.now(), empresa_id=empresa_id)
    candidatas = [i["habitacion_id"] for i in sorted(
        (i for i in oferta["oferta"] if i["tipo"] == tipo),
        key=lambda i: (i["habitacion_id"] != preferida, i["total_clp"], i["habitacion_id"]),
    )]
    reserva = None
    ultimo_error: Exception | None = None
    for habitacion_id in candidatas:
        try:
            reserva = reservas_db.crear_reserva(
                conexion, empresa_id, habitacion_id, inicio, fin, nombre, None, personas=personas,
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
    solicitud = _solicitud_de_la_empresa(conexion, solicitud_id, empresa_id)
    if solicitud[1] != "recibida":
        raise TransicionInvalida(f"la solicitud está {solicitud[1]}")
    conexion.execute(
        "UPDATE solicitudes SET estado = 'rechazada', rechazo_motivo = %s WHERE id = %s",
        ((motivo or "").strip() or "sin motivo", solicitud_id),
    )
    seguridad.auditar(conexion, actor, "solicitud_rechazo", solicitud_id, "rechazada")
    return _fila_publica(conexion, solicitud_id)
