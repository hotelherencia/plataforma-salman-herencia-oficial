"""Caja y contabilidad del hotel, fase 1 (2026-11-19, pedido del propietario).

- **Turnos de caja**: apertura con fondo inicial (y recepción del efectivo que
  entregó el turno anterior), cobros por medio, retiros de efectivo para
  depósito en el banco con número de comprobante, arqueo por denominación y
  cierre con cuadratura: la diferencia (sobrante o faltante) exige
  justificación.
- **Movimientos inmutables**: la base rechaza editar o borrar pagos y
  movimientos (disparadores de la migración 0050); se corrige con un reverso
  que solo registra la administración, con motivo y auditoría.
- **Fecha contable** en hora de Chile. Un día cerrado (cierre diario) no
  recibe movimientos: lo nuevo cae en el siguiente día abierto.
- **Cierre diario** (auditoría nocturna): conciliación de habitaciones
  ocupadas contra lo cobrado y los anticipos, cobros por medio, depósitos,
  turnos y documentos; queda congelada en el cierre.

Fuera de esta fase (ver contable/diseno.md): política de crédito por cliente
y garantías con tarjeta, imputación por noche, cierre mensual con Excel,
conciliación bancaria y tributaria.
"""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

import psycopg
from psycopg.types.json import Json

from . import ajustes, iva, roles

ZONA = ZoneInfo("America/Santiago")
CAJA = "principal"
MEDIOS = ajustes.MEDIOS_CAJA
DOCUMENTOS = ajustes.DOCUMENTOS_CAJA
NOMBRE_MEDIO = {"efectivo": "Efectivo", "debito": "Tarjeta de débito", "credito": "Tarjeta de crédito",
                "transferencia": "Transferencia", "no_informado": "Sin medio informado"}

# Quién opera la caja: caja y recepción (en un hotel chico la recepción cobra)
# más la administración del hotel. El cierre del día: caja o administración.
# Reversos y reapertura de un día cerrado: solo administración.
ROLES_TURNO = roles.con_admin_hotel("caja", "recepcion")
ROLES_CIERRE_DIARIO = roles.con_admin_hotel("caja")
ROLES_REVERSO = roles.con_admin_hotel()
ROLES_REAPERTURA = roles.con_admin_hotel()

MIN_JUSTIFICACION = 10


class OperacionCajaInvalida(Exception):
    """409: la operación no corresponde al estado de la caja o del día."""


class DatosCajaInvalidos(Exception):
    """422: datos de la operación inválidos (mensaje en castellano)."""


class TurnoAjenoOInexistente(Exception):
    """404: el turno no existe en esta empresa."""


# --- Fechas -------------------------------------------------------------------

def ahora_chile() -> datetime:
    return datetime.now(ZONA)


def hoy_chile() -> date:
    return ahora_chile().date()


def dia_cerrado(conexion: psycopg.Connection, empresa_id: str, fecha: date) -> bool:
    return conexion.execute(
        "SELECT 1 FROM cierres_diarios WHERE empresa_id = %s AND fecha = %s AND estado = 'cerrado'",
        (empresa_id, fecha),
    ).fetchone() is not None


def fecha_contable_actual(conexion: psycopg.Connection, empresa_id: str, hoy: date | None = None) -> date:
    """Hoy en Chile o, si hoy ya tiene cierre diario, el siguiente día abierto."""
    fecha = hoy or hoy_chile()
    while dia_cerrado(conexion, empresa_id, fecha):
        fecha += timedelta(days=1)
    return fecha


def parametros(conexion: psycopg.Connection, empresa_id: str) -> dict:
    return ajustes.leer(conexion, empresa_id, "caja")


# --- Validaciones puras ---------------------------------------------------------

_PAN = re.compile(r"\d[\d\s-]{11,}\d")


def _sin_numero_de_tarjeta(*valores) -> None:
    """PCI: jamás guardar el número completo de una tarjeta (ni el CVV). Un
    texto con 12 o más dígitos seguidos (con espacios o guiones) se rechaza."""
    for valor in valores:
        for trozo in _PAN.findall(str(valor or "")):
            if len(re.sub(r"\D", "", trozo)) >= 12:
                raise DatosCajaInvalidos(
                    "no registres el número completo de la tarjeta: solo los últimos 4 dígitos "
                    "y el código de autorización")


def _texto(valor, campo: str, maximo: int, requerido: bool = False) -> str | None:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if requerido:
            raise DatosCajaInvalidos(f"falta {campo}")
        return None
    if not isinstance(valor, str) or len(valor.strip()) > maximo:
        raise DatosCajaInvalidos(f"{campo}: texto de hasta {maximo} caracteres")
    return valor.strip()


def total_arqueo(arqueo: dict, denominaciones: list[int]) -> int:
    """Suma del conteo por denominación; rechaza valores que no están en uso."""
    if not isinstance(arqueo, dict):
        raise DatosCajaInvalidos("el arqueo es el conteo de billetes y monedas por denominación")
    total = 0
    for clave, cantidad in arqueo.items():
        try:
            valor = int(clave)
        except (TypeError, ValueError):
            raise DatosCajaInvalidos(f"denominación inválida: {clave}") from None
        if valor not in denominaciones:
            raise DatosCajaInvalidos(f"la denominación ${valor:,} no está en uso en el hotel".replace(",", "."))
        if isinstance(cantidad, bool) or not isinstance(cantidad, int) or not 0 <= cantidad <= 100000:
            raise DatosCajaInvalidos(f"cantidad inválida para ${valor:,}".replace(",", "."))
        total += valor * cantidad
    return total


def validar_datos_pago(conexion: psycopg.Connection, empresa_id: str, datos: dict | None) -> dict:
    """Medio, documento tributario y voucher de un pago manual. Devuelve las
    columnas a guardar. Sin `medio` (clientes anteriores a la fase 1) queda
    «no_informado» y no toca la caja de efectivo."""
    datos = dict(datos or {})
    param = parametros(conexion, empresa_id)
    medio = datos.get("medio") or "no_informado"
    if medio != "no_informado":
        if medio not in MEDIOS:
            raise DatosCajaInvalidos("medio de pago: efectivo, débito, crédito o transferencia")
        if not param["medios"][medio]["activo"]:
            raise DatosCajaInvalidos(f"{NOMBRE_MEDIO[medio]} no está habilitado en el hotel")
    documento = datos.get("documento_tipo")
    if documento is None:
        documento = param["documento_por_defecto"] if medio != "no_informado" else "pendiente"
    if documento not in DOCUMENTOS and documento != "pendiente":
        raise DatosCajaInvalidos("documento: boleta, factura o sin documento")
    if documento == "pendiente" and param["exigir_documento"] and medio != "no_informado":
        raise DatosCajaInvalidos("indica si el cliente requiere boleta o factura")
    receptor = None
    if documento == "factura":
        from . import documento as documento_mod

        r = datos.get("receptor") or {}
        if not isinstance(r, dict):
            raise DatosCajaInvalidos("faltan los datos de la factura")
        try:
            rut = documento_mod.normalizar_rut(r.get("rut") or "")
        except documento_mod.DocumentoInvalido as error:
            raise DatosCajaInvalidos(f"factura: {error}") from None
        receptor = {
            "rut": rut,
            "razon_social": _texto(r.get("razon_social"), "la razón social", 120, True),
            "giro": _texto(r.get("giro"), "el giro", 120, True),
            "direccion": _texto(r.get("direccion"), "la dirección", 160, True),
            "comuna": _texto(r.get("comuna"), "la comuna", 60, True),
            "correo": _texto(r.get("correo"), "el correo", 120),
        }
    marca = _texto(datos.get("tarjeta_marca"), "la marca de la tarjeta", 30)
    ultimos4 = _texto(datos.get("tarjeta_ultimos4"), "los últimos 4 dígitos", 4)
    autorizacion = _texto(datos.get("codigo_autorizacion"), "el código de autorización", 20)
    comprobante = _texto(datos.get("comprobante"), "el comprobante", 60)
    folio = _texto(datos.get("documento_folio"), "el folio", 20)
    _sin_numero_de_tarjeta(marca, ultimos4, autorizacion, comprobante, folio)
    if ultimos4 is not None and not re.fullmatch(r"\d{4}", ultimos4):
        raise DatosCajaInvalidos("últimos 4 dígitos de la tarjeta: exactamente 4 números")
    if medio in ("debito", "credito"):
        if not autorizacion:
            raise DatosCajaInvalidos("anota el código de autorización del voucher de la tarjeta")
    else:
        marca = ultimos4 = autorizacion = None
    return {"medio": medio, "documento_tipo": documento, "documento_folio": folio,
            "receptor": receptor, "tarjeta_marca": marca, "tarjeta_ultimos4": ultimos4,
            "codigo_autorizacion": autorizacion, "comprobante": comprobante}


# --- Turnos ----------------------------------------------------------------------

_COLUMNAS_TURNO = (
    "id, usuario_id, usuario_nombre, estado, fecha_contable, abierto_en, fondo_inicial_clp, "
    "recibido_de_turno_id, diferencia_recepcion_clp, nota_apertura, cerrado_en, cerrado_por, "
    "efectivo_esperado_clp, efectivo_contado_clp, diferencia_clp, justificacion, arqueo, cuadratura, "
    "entrega_siguiente_clp"
)


def _turno_dict(f) -> dict:
    return {
        "turno_id": f[0], "usuario_id": f[1], "usuario_nombre": f[2], "estado": f[3],
        "fecha_contable": f[4].isoformat(), "abierto_en": f[5].isoformat(), "fondo_inicial_clp": f[6],
        "recibido_de_turno_id": f[7], "diferencia_recepcion_clp": f[8], "nota_apertura": f[9],
        "cerrado_en": f[10].isoformat() if f[10] else None, "cerrado_por": f[11],
        "efectivo_esperado_clp": f[12], "efectivo_contado_clp": f[13], "diferencia_clp": f[14],
        "justificacion": f[15], "arqueo": f[16], "cuadratura": f[17], "entrega_siguiente_clp": f[18],
    }


def turno_abierto(conexion: psycopg.Connection, empresa_id: str, bloqueo: bool = False) -> dict | None:
    fila = conexion.execute(
        f"SELECT {_COLUMNAS_TURNO} FROM caja_turnos WHERE empresa_id = %s AND caja = %s AND estado = 'abierto'"
        + (" FOR UPDATE" if bloqueo else ""),
        (empresa_id, CAJA),
    ).fetchone()
    return _turno_dict(fila) if fila else None


def _turno(conexion: psycopg.Connection, empresa_id: str, turno_id: str, bloqueo: bool = False) -> dict:
    fila = conexion.execute(
        f"SELECT {_COLUMNAS_TURNO} FROM caja_turnos WHERE empresa_id = %s AND id = %s"
        + (" FOR UPDATE" if bloqueo else ""),
        (empresa_id, turno_id),
    ).fetchone()
    if fila is None:
        raise TurnoAjenoOInexistente("turno inexistente")
    return _turno_dict(fila)


def entrega_pendiente(conexion: psycopg.Connection, empresa_id: str) -> dict | None:
    """Último turno cerrado cuyo efectivo aún no recibe otro turno."""
    fila = conexion.execute(
        "SELECT t.id, t.usuario_nombre, t.entrega_siguiente_clp, t.cerrado_en FROM caja_turnos t "
        "WHERE t.empresa_id = %s AND t.caja = %s AND t.estado = 'cerrado' AND t.entrega_siguiente_clp IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM caja_turnos s WHERE s.recibido_de_turno_id = t.id) "
        "ORDER BY t.cerrado_en DESC LIMIT 1",
        (empresa_id, CAJA),
    ).fetchone()
    if fila is None:
        return None
    return {"turno_id": fila[0], "usuario_nombre": fila[1], "monto_clp": fila[2], "cerrado_en": fila[3].isoformat()}


def totales_turno(conexion: psycopg.Connection, turno: dict) -> dict:
    filas = conexion.execute(
        "SELECT medio, tipo, COALESCE(SUM(monto_clp), 0), count(*) FROM caja_movimientos WHERE turno_id = %s "
        "GROUP BY medio, tipo",
        (turno["turno_id"],),
    ).fetchall()
    por_medio = {m: 0 for m in (*MEDIOS, "no_informado")}
    retiros = 0
    cobros = 0
    for medio, tipo, suma, cuenta in filas:
        if tipo == "retiro_deposito":
            retiros += -suma
        else:
            por_medio[medio] += suma
            if tipo == "cobro":
                cobros += cuenta
    esperado = turno["fondo_inicial_clp"] + por_medio["efectivo"] - retiros
    return {"por_medio": por_medio, "retiros_deposito_clp": retiros, "cobros": cobros,
            "total_cobrado_clp": sum(por_medio.values()), "efectivo_esperado_clp": esperado}


def abrir_turno(conexion: psycopg.Connection, empresa_id: str, usuario_id: str, actor: str,
                fondo_inicial_clp: int, nota: str | None = None, hoy: date | None = None) -> dict:
    if isinstance(fondo_inicial_clp, bool) or not isinstance(fondo_inicial_clp, int) or fondo_inicial_clp < 0:
        raise DatosCajaInvalidos("el fondo inicial es un monto en pesos, cero o más")
    conexion.execute("SELECT pg_advisory_xact_lock(hashtext('caja_turno'), hashtext(%s))", (empresa_id,))
    if turno_abierto(conexion, empresa_id) is not None:
        raise OperacionCajaInvalida("ya hay un turno de caja abierto: ciérralo antes de abrir otro")
    nota = _texto(nota, "la nota", 500)
    pendiente = entrega_pendiente(conexion, empresa_id)
    diferencia = None
    if pendiente is not None:
        diferencia = fondo_inicial_clp - pendiente["monto_clp"]
        if diferencia != 0 and (not nota or len(nota) < MIN_JUSTIFICACION):
            raise DatosCajaInvalidos(
                f"el turno anterior entregó {_clp(pendiente['monto_clp'])} y recibes {_clp(fondo_inicial_clp)}: "
                "explica la diferencia en la nota (mínimo 10 caracteres)")
    turno_id = f"TUR-{uuid.uuid4().hex[:12]}"
    fecha = fecha_contable_actual(conexion, empresa_id, hoy)
    conexion.execute(
        "INSERT INTO caja_turnos (id, empresa_id, caja, usuario_id, usuario_nombre, fecha_contable, fondo_inicial_clp, "
        "recibido_de_turno_id, diferencia_recepcion_clp, nota_apertura) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (turno_id, empresa_id, CAJA, usuario_id, actor, fecha, fondo_inicial_clp,
         pendiente["turno_id"] if pendiente else None, diferencia, nota),
    )
    return _turno(conexion, empresa_id, turno_id)


def registrar_retiro(conexion: psycopg.Connection, empresa_id: str, turno_id: str, actor: str, monto_clp: int,
                     comprobante: str, banco: str | None = None, nota: str | None = None,
                     hoy: date | None = None) -> dict:
    """Retiro de efectivo para depósito en el banco (sale de la caja, queda en
    tránsito hasta que la cartola lo muestre: conciliación en fase 2)."""
    turno = _turno(conexion, empresa_id, turno_id, bloqueo=True)
    if turno["estado"] != "abierto":
        raise OperacionCajaInvalida("el turno está cerrado")
    if isinstance(monto_clp, bool) or not isinstance(monto_clp, int) or monto_clp <= 0:
        raise DatosCajaInvalidos("el monto del retiro debe ser mayor que $0")
    comprobante = _texto(comprobante, "el número de comprobante del depósito", 60, True)
    banco = _texto(banco, "el banco", 120)
    nota = _texto(nota, "la nota", 500)
    _sin_numero_de_tarjeta(comprobante, banco, nota)
    disponible = totales_turno(conexion, turno)["efectivo_esperado_clp"]
    if monto_clp > disponible:
        raise OperacionCajaInvalida(f"el retiro supera el efectivo que debería haber en caja ({_clp(disponible)})")
    movimiento_id = f"MOV-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO caja_movimientos (id, empresa_id, turno_id, fecha_contable, tipo, medio, monto_clp, comprobante, "
        "banco, nota, actor) VALUES (%s, %s, %s, %s, 'retiro_deposito', 'efectivo', %s, %s, %s, %s, %s)",
        (movimiento_id, empresa_id, turno_id, fecha_contable_actual(conexion, empresa_id, hoy), -monto_clp,
         comprobante, banco or parametros(conexion, empresa_id)["banco_deposito"] or None, nota, actor),
    )
    return {"movimiento_id": movimiento_id, "turno_id": turno_id, "monto_clp": monto_clp,
            "comprobante": comprobante, "efectivo_en_caja_clp": disponible - monto_clp}


def cerrar_turno(conexion: psycopg.Connection, empresa_id: str, turno_id: str, usuario_id: str, rol: str,
                 actor: str, arqueo: dict, declarado: dict | None = None, justificacion: str | None = None,
                 deposito: dict | None = None) -> dict:
    """Cierre con arqueo (conteo por denominación) y cuadratura por medio.
    `declarado`: totales del cierre de lote del POS (débito, crédito) y de
    transferencias verificadas; una diferencia exige justificación.
    `deposito`: efectivo que sale al cierre para el banco (con comprobante);
    lo que queda pasa al turno siguiente."""
    turno = _turno(conexion, empresa_id, turno_id, bloqueo=True)
    if turno["estado"] != "abierto":
        raise OperacionCajaInvalida("el turno ya está cerrado")
    if turno["usuario_id"] != usuario_id and not roles.es_admin_hotel(rol):
        raise OperacionCajaInvalida("solo quien abrió el turno o la administración puede cerrarlo")
    param = parametros(conexion, empresa_id)
    contado = total_arqueo(arqueo, param["denominaciones"])
    totales = totales_turno(conexion, turno)
    esperado = totales["efectivo_esperado_clp"]
    justificacion = _texto(justificacion, "la justificación", 1000)
    declarado = declarado or {}
    if not isinstance(declarado, dict) or set(declarado) - {"debito", "credito", "transferencia"}:
        raise DatosCajaInvalidos("cuadratura: solo débito, crédito y transferencia")
    cuadratura = {"efectivo": {"sistema_clp": esperado, "declarado_clp": contado, "diferencia_clp": contado - esperado}}
    for medio in ("debito", "credito", "transferencia"):
        sistema = totales["por_medio"][medio]
        valor = declarado.get(medio)
        if valor is None:
            valor = sistema
        if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
            raise DatosCajaInvalidos(f"cuadratura de {NOMBRE_MEDIO[medio].lower()}: monto en pesos")
        cuadratura[medio] = {"sistema_clp": sistema, "declarado_clp": valor, "diferencia_clp": valor - sistema}
    hay_diferencia = any(c["diferencia_clp"] != 0 for c in cuadratura.values())
    if hay_diferencia and (not justificacion or len(justificacion) < MIN_JUSTIFICACION):
        raise DatosCajaInvalidos("hay diferencias en la cuadratura: justifícalas (mínimo 10 caracteres)")
    revision = any(abs(c["diferencia_clp"]) > param["tolerancia_diferencia_clp"] for c in cuadratura.values())
    a_depositar = 0
    if deposito:
        if not isinstance(deposito, dict):
            raise DatosCajaInvalidos("depósito al cierre: monto y comprobante")
        a_depositar = deposito.get("monto_clp") or 0
        if isinstance(a_depositar, bool) or not isinstance(a_depositar, int) or a_depositar < 0 or a_depositar > contado:
            raise DatosCajaInvalidos("el depósito al cierre no puede superar el efectivo contado")
        if a_depositar:
            comprobante = _texto(deposito.get("comprobante"), "el número de comprobante del depósito", 60, True)
            banco = _texto(deposito.get("banco"), "el banco", 120)
            _sin_numero_de_tarjeta(comprobante, banco)
            conexion.execute(
                "INSERT INTO caja_movimientos (id, empresa_id, turno_id, fecha_contable, tipo, medio, monto_clp, "
                "comprobante, banco, nota, actor) VALUES (%s, %s, %s, %s, 'retiro_deposito', 'efectivo', %s, %s, %s, "
                "'Depósito al cierre del turno', %s)",
                (f"MOV-{uuid.uuid4().hex[:12]}", empresa_id, turno_id, fecha_contable_actual(conexion, empresa_id),
                 -a_depositar, comprobante, banco or param["banco_deposito"] or None, actor),
            )
    cuadratura["requiere_revision"] = revision
    cuadratura["deposito_al_cierre_clp"] = a_depositar
    cuadratura["totales"] = totales
    conexion.execute(
        "UPDATE caja_turnos SET estado = 'cerrado', cerrado_en = now(), cerrado_por = %s, efectivo_esperado_clp = %s, "
        "efectivo_contado_clp = %s, diferencia_clp = %s, justificacion = %s, arqueo = %s, cuadratura = %s, "
        "entrega_siguiente_clp = %s WHERE id = %s",
        (actor, esperado, contado, contado - esperado, justificacion,
         Json({str(k): v for k, v in arqueo.items()}), Json(cuadratura), contado - a_depositar, turno_id),
    )
    return detalle_turno(conexion, empresa_id, turno_id)


def movimientos(conexion: psycopg.Connection, empresa_id: str, desde: date | None = None, hasta: date | None = None,
                turno_id: str | None = None, medio: str | None = None) -> list[dict]:
    filtros, parametros_sql = ["m.empresa_id = %s"], [empresa_id]
    if turno_id:
        filtros.append("m.turno_id = %s")
        parametros_sql.append(turno_id)
    if desde:
        filtros.append("m.fecha_contable >= %s")
        parametros_sql.append(desde)
    if hasta:
        filtros.append("m.fecha_contable <= %s")
        parametros_sql.append(hasta)
    if medio:
        filtros.append("m.medio = %s")
        parametros_sql.append(medio)
    filas = conexion.execute(
        "SELECT m.id, m.turno_id, m.fecha_contable, m.tipo, m.medio, m.monto_clp, m.pago_id, m.comprobante, m.banco, "
        "m.nota, m.actor, m.creado_en, p.reserva_id, r.habitacion_id, r.huesped_nombre, p.documento_tipo, "
        "p.documento_folio, p.es_anticipo, p.tarjeta_marca, p.tarjeta_ultimos4, p.codigo_autorizacion "
        "FROM caja_movimientos m LEFT JOIN pagos p ON p.id = m.pago_id LEFT JOIN reservas r ON r.id = p.reserva_id "
        f"WHERE {' AND '.join(filtros)} ORDER BY m.creado_en, m.id LIMIT 2000",
        parametros_sql,
    ).fetchall()
    return [
        {"movimiento_id": f[0], "turno_id": f[1], "fecha_contable": f[2].isoformat(), "tipo": f[3], "medio": f[4],
         "monto_clp": f[5], "pago_id": f[6], "comprobante": f[7], "banco": f[8], "nota": f[9], "actor": f[10],
         "registrado_en": f[11].isoformat(), "reserva_id": f[12], "habitacion_id": f[13], "huesped_nombre": f[14],
         "documento_tipo": f[15], "documento_folio": f[16], "es_anticipo": f[17], "tarjeta_marca": f[18],
         "tarjeta_ultimos4": f[19], "codigo_autorizacion": f[20]}
        for f in filas
    ]


def detalle_turno(conexion: psycopg.Connection, empresa_id: str, turno_id: str) -> dict:
    turno = _turno(conexion, empresa_id, turno_id)
    return {**turno, "totales": totales_turno(conexion, turno),
            "movimientos": movimientos(conexion, empresa_id, turno_id=turno_id)}


def listar_turnos(conexion: psycopg.Connection, empresa_id: str, desde: date, hasta: date) -> list[dict]:
    filas = conexion.execute(
        f"SELECT {_COLUMNAS_TURNO} FROM caja_turnos WHERE empresa_id = %s AND fecha_contable BETWEEN %s AND %s "
        "ORDER BY abierto_en DESC LIMIT 500",
        (empresa_id, desde, hasta),
    ).fetchall()
    salida = []
    for f in filas:
        turno = _turno_dict(f)
        turno["totales"] = totales_turno(conexion, turno)
        salida.append(turno)
    return salida


def estado_caja(conexion: psycopg.Connection, empresa_id: str) -> dict:
    """Lo que ve la pestaña Turno: turno abierto con totales en vivo, efectivo
    por recibir del turno anterior y parámetros de la caja."""
    turno = turno_abierto(conexion, empresa_id)
    param = parametros(conexion, empresa_id)
    return {
        "turno": ({**turno, "totales": totales_turno(conexion, turno)} if turno else None),
        "entrega_pendiente": entrega_pendiente(conexion, empresa_id),
        "fecha_contable": fecha_contable_actual(conexion, empresa_id).isoformat(),
        "parametros": {
            "denominaciones": param["denominaciones"], "fondo_fijo_clp": param["fondo_fijo_clp"],
            "medios": [m for m in MEDIOS if param["medios"][m]["activo"]],
            "exigir_turno_efectivo": param["exigir_turno_efectivo"],
            "exigir_documento": param["exigir_documento"],
            "documento_por_defecto": param["documento_por_defecto"],
            "banco_deposito": param["banco_deposito"],
            "tolerancia_diferencia_clp": param["tolerancia_diferencia_clp"],
        },
    }


# --- Pagos: asiento en la caja y reverso ---------------------------------------

def preparar_pago(conexion: psycopg.Connection, empresa_id: str, estado_reserva: str, datos: dict) -> dict:
    """Antes de insertar el pago: turno al que se asienta, fecha contable y si
    es anticipo (cobrado antes de la Llegada). El efectivo exige turno
    abierto si así lo fija la administración."""
    turno = turno_abierto(conexion, empresa_id, bloqueo=True)
    if datos["medio"] == "efectivo" and turno is None and parametros(conexion, empresa_id)["exigir_turno_efectivo"]:
        raise OperacionCajaInvalida("abre un turno de caja (Caja y pagos → Turno) antes de recibir efectivo")
    return {"turno_id": turno["turno_id"] if turno else None,
            "fecha_contable": fecha_contable_actual(conexion, empresa_id),
            "es_anticipo": estado_reserva == "confirmada"}


def asentar_movimiento_pago(conexion: psycopg.Connection, empresa_id: str, pago_id: str, preparado: dict,
                            medio: str, monto_clp: int, actor: str, tipo: str = "cobro") -> None:
    # Débito, crédito o transferencia sin turno abierto: igual quedan en el
    # diario del día (sin turno). Un pago sin medio informado y sin turno no
    # mueve la caja (clientes anteriores a la fase 1).
    if medio == "no_informado" and preparado["turno_id"] is None:
        return
    conexion.execute(
        "INSERT INTO caja_movimientos (id, empresa_id, turno_id, fecha_contable, tipo, medio, monto_clp, pago_id, actor) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (f"MOV-{uuid.uuid4().hex[:12]}", empresa_id, preparado["turno_id"], preparado["fecha_contable"], tipo, medio,
         monto_clp, pago_id, actor),
    )


def completar_pago(conexion: psycopg.Connection, pago_id: str, columnas: dict, preparado: dict,
                   actor: str | None) -> None:
    """Datos contables de un pago recién proyectado por el dominio (misma transacción;
    el disparador `pagos_inmutables` lo permite una sola vez)."""
    conexion.execute(
        "UPDATE pagos SET medio = %s, fecha_contable = %s, turno_id = %s, es_anticipo = %s, documento_tipo = %s, "
        "documento_folio = %s, receptor = %s, tarjeta_marca = %s, tarjeta_ultimos4 = %s, codigo_autorizacion = %s, "
        "comprobante = %s, actor = %s WHERE id = %s",
        (columnas["medio"], preparado["fecha_contable"], preparado["turno_id"], preparado["es_anticipo"],
         columnas["documento_tipo"], columnas["documento_folio"],
         Json(columnas["receptor"]) if columnas["receptor"] else None,
         columnas["tarjeta_marca"], columnas["tarjeta_ultimos4"], columnas["codigo_autorizacion"],
         columnas["comprobante"], actor or "sistema", pago_id),
    )


def reversar_pago(conexion: psycopg.Connection, hotel, empresa_id: str, reserva_id: str, pago_id: str, motivo: str,
                  actor: str) -> dict:
    """Anulación de un pago: nunca se edita ni se borra; se registra un pago
    de tipo «reverso» por el mismo monto y medio, con fecha contable del día
    abierto (un día cerrado no se toca) y su movimiento de caja negativo."""
    motivo = _texto(motivo, "el motivo", 300, True)
    if len(motivo) < MIN_JUSTIFICACION:
        raise DatosCajaInvalidos("explica el motivo del reverso (mínimo 10 caracteres)")
    fila = conexion.execute(
        "SELECT p.id, p.monto_clp, p.medio, p.tipo, p.estado, r.estado, p.es_anticipo FROM pagos p JOIN reservas r ON r.id = p.reserva_id "
        "WHERE p.id = %s AND p.reserva_id = %s AND r.empresa_id = %s FOR UPDATE OF p",
        (pago_id, reserva_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise TurnoAjenoOInexistente("pago inexistente")
    if fila[3] != "pago" or fila[4] != "confirmado":
        raise OperacionCajaInvalida("solo se reversa un pago confirmado")
    if conexion.execute("SELECT 1 FROM pagos WHERE referencia_pago_id = %s AND tipo = 'reverso'", (pago_id,)).fetchone():
        raise OperacionCajaInvalida("ese pago ya fue reversado")
    preparado = preparar_pago(conexion, empresa_id, fila[5], {"medio": fila[2]})
    reverso_id = f"PAG-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO pagos (id, reserva_id, monto_clp, clave, modo, estado, tipo, referencia_pago_id, medio, "
        "fecha_contable, turno_id, documento_tipo, actor, motivo, es_anticipo) "
        "VALUES (%s, %s, %s, %s, 'manual', 'confirmado', 'reverso', %s, %s, %s, %s, 'sin_documento', %s, %s, %s)",
        (reverso_id, reserva_id, fila[1], f"reverso:{pago_id}", pago_id, fila[2], preparado["fecha_contable"],
         preparado["turno_id"], actor, motivo, fila[6]),
    )
    asentar_movimiento_pago(conexion, empresa_id, reverso_id, preparado, fila[2], -fila[1], actor, "reverso_cobro")
    from . import hotel_sql

    # El dominio deja de ver el pago anulado (hotel_sql.recargar) y el saldo vuelve a subir.
    neto, pagado = hotel_sql.cuenta(conexion, hotel, empresa_id, reserva_id)
    return {"pago_id": reverso_id, "referencia_pago_id": pago_id, "reserva_id": reserva_id, "monto_clp": fila[1],
            "medio": fila[2], "fecha_contable": preparado["fecha_contable"].isoformat(), "saldo_clp": neto - pagado}


# --- Conciliación diaria y cierre del día -----------------------------------------

def _clp(monto: int) -> str:
    return "$" + f"{monto:,}".replace(",", ".")


def _neto(bruto: int, tasa: Decimal) -> int:
    return int((Decimal(bruto) / (1 + tasa / 100)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def conciliacion_diaria(conexion: psycopg.Connection, empresa_id: str, fecha: date,
                        solo_inventario_real: bool = False) -> dict:
    """Habitaciones ocupadas la noche `fecha` contra lo cobrado y los
    anticipos de cada estadía; cobros, depósitos, turnos y documentos del día."""
    from . import panel

    habitaciones = [h for h in panel._habitaciones(conexion, None, solo_inventario_real=solo_inventario_real)]
    ids = [h["habitacion_id"] for h in habitaciones]
    reservas = conexion.execute(
        "SELECT r.id, r.habitacion_id, r.huesped_nombre, r.estado, r.inicio, r.fin, "
        "COALESCE((SELECT n.precio_clp FROM reserva_noches n WHERE n.reserva_id = r.id AND n.noche = %s), "
        "r.tarifa_noche_aceptada_clp), "
        "COALESCE((SELECT SUM(CASE WHEN c.tipo = 'reverso' THEN -c.monto_clp ELSE c.monto_clp END) FROM cargos c "
        "WHERE c.reserva_id = r.id), 0), "
        "COALESCE((SELECT SUM(CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END) FROM pagos p "
        "WHERE p.reserva_id = r.id AND p.estado = 'confirmado'), 0), "
        "COALESCE((SELECT SUM(CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END) FROM pagos p "
        "WHERE p.reserva_id = r.id AND p.estado = 'confirmado' AND p.es_anticipo), 0) "
        "FROM reservas r WHERE r.empresa_id = %s AND r.estado IN ('confirmada', 'en_estadia', 'finalizada') "
        "AND r.inicio <= %s AND r.fin > %s AND r.habitacion_id = ANY(%s) ORDER BY r.habitacion_id",
        (fecha, empresa_id, fecha, fecha, ids),
    ).fetchall()
    por_habitacion = {f[1]: f for f in reservas}
    tasa = iva.tasa(conexion)
    filas, ocupadas, ingreso, disponibles = [], 0, 0, 0
    alertas: list[str] = []
    for h in habitaciones:
        if h["en_servicio"]:
            disponibles += 1
        r = por_habitacion.get(h["habitacion_id"])
        if r is None:
            filas.append({"habitacion_id": h["habitacion_id"], "tipo": h["tipo"],
                          "estado": "fuera_de_servicio" if not h["en_servicio"] else "libre"})
            continue
        cargos, pagado, anticipos = r[7], r[8], r[9]
        saldo = cargos - pagado
        if r[3] == "confirmada":
            estado = "sin_llegada"
            alertas.append(f"{h['habitacion_id']}: reserva sin Llegada registrada (posible no-show)")
        else:
            ocupadas += 1
            ingreso += r[6] or 0
            estado = "pagada" if saldo <= 0 else ("abonada" if pagado > 0 else "pendiente")
            if estado == "pendiente":
                alertas.append(f"{h['habitacion_id']}: ocupada sin pagos ni abonos")
        filas.append({
            "habitacion_id": h["habitacion_id"], "tipo": h["tipo"], "estado": estado, "reserva_id": r[0],
            "huesped_nombre": r[2], "estado_reserva": r[3], "inicio": r[4].isoformat(), "fin": r[5].isoformat(),
            "tarifa_noche_clp": r[6], "cargos_clp": cargos, "pagado_clp": pagado, "anticipos_clp": anticipos,
            "saldo_clp": saldo,
        })
    cobros = conexion.execute(
        "SELECT medio, tipo, COALESCE(SUM(monto_clp), 0), count(*) FROM caja_movimientos "
        "WHERE empresa_id = %s AND fecha_contable = %s GROUP BY medio, tipo",
        (empresa_id, fecha),
    ).fetchall()
    por_medio = {m: 0 for m in (*MEDIOS, "no_informado")}
    depositos = 0
    for medio, tipo, suma, _ in cobros:
        if tipo == "retiro_deposito":
            depositos += -suma
        else:
            por_medio[medio] += suma
    # Pagos sin movimiento de caja (sin medio informado y sin turno): igual cuentan.
    (sin_caja,) = conexion.execute(
        "SELECT COALESCE(SUM(CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END), 0) FROM pagos p "
        "JOIN reservas r ON r.id = p.reserva_id WHERE r.empresa_id = %s AND p.fecha_contable = %s "
        "AND p.estado = 'confirmado' AND NOT EXISTS (SELECT 1 FROM caja_movimientos m WHERE m.pago_id = p.id)",
        (empresa_id, fecha),
    ).fetchone()
    por_medio["no_informado"] += sin_caja
    documentos = {d: {"cantidad": 0, "monto_clp": 0} for d in (*DOCUMENTOS, "pendiente")}
    for doc, cantidad, suma in conexion.execute(
        "SELECT p.documento_tipo, count(*), COALESCE(SUM(p.monto_clp), 0) FROM pagos p JOIN reservas r ON r.id = p.reserva_id "
        "WHERE r.empresa_id = %s AND p.fecha_contable = %s AND p.estado = 'confirmado' AND p.tipo = 'pago' "
        "GROUP BY p.documento_tipo",
        (empresa_id, fecha),
    ).fetchall():
        documentos[doc] = {"cantidad": cantidad, "monto_clp": suma}
    if documentos["pendiente"]["cantidad"]:
        alertas.append(f"{documentos['pendiente']['cantidad']} pago(s) sin boleta ni factura indicada")
    (anticipos_dia,) = conexion.execute(
        "SELECT COALESCE(SUM(CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END), 0) FROM pagos p "
        "JOIN reservas r ON r.id = p.reserva_id WHERE r.empresa_id = %s AND p.fecha_contable = %s "
        "AND p.estado = 'confirmado' AND p.es_anticipo",
        (empresa_id, fecha),
    ).fetchone()
    # Anticipos de clientes (pasivo): lo cobrado de reservas que aún no llegan.
    (anticipos_vigentes,) = conexion.execute(
        "SELECT COALESCE(SUM(CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END), 0) FROM pagos p "
        "JOIN reservas r ON r.id = p.reserva_id WHERE r.empresa_id = %s AND r.estado = 'confirmada' "
        "AND p.estado = 'confirmado' AND p.fecha_contable <= %s",
        (empresa_id, fecha),
    ).fetchone()
    turnos = listar_turnos(conexion, empresa_id, fecha, fecha)
    for t in turnos:
        if t["estado"] == "abierto":
            alertas.append(f"turno de {t['usuario_nombre']} sigue abierto")
        elif t["diferencia_clp"]:
            alertas.append(f"turno de {t['usuario_nombre']} cerró con diferencia de {_clp(t['diferencia_clp'])}")
    cierre = conexion.execute(
        "SELECT estado, cerrado_por, cerrado_en, nota, reabierto_por, motivo_reapertura FROM cierres_diarios "
        "WHERE empresa_id = %s AND fecha = %s",
        (empresa_id, fecha),
    ).fetchone()
    total_cobrado = sum(por_medio.values())
    return {
        "fecha": fecha.isoformat(),
        "habitaciones": filas,
        "resumen": {
            "habitaciones_disponibles": disponibles, "habitaciones_ocupadas": ocupadas,
            "ocupacion_pct": round(100 * ocupadas / disponibles, 1) if disponibles else 0.0,
            "ingreso_alojamiento_clp": ingreso, "ingreso_alojamiento_neto_clp": _neto(ingreso, tasa),
            "adr_clp": round(ingreso / ocupadas) if ocupadas else 0,
            "revpar_clp": round(ingreso / disponibles) if disponibles else 0,
            "iva_pct": float(tasa),
        },
        "cobros": {"por_medio": por_medio, "total_clp": total_cobrado, "depositos_clp": depositos,
                   "anticipos_recibidos_clp": anticipos_dia, "anticipos_vigentes_clp": anticipos_vigentes},
        "documentos": documentos,
        "turnos": [{k: t[k] for k in ("turno_id", "usuario_nombre", "estado", "fondo_inicial_clp",
                                      "efectivo_esperado_clp", "efectivo_contado_clp", "diferencia_clp",
                                      "justificacion", "totales")} for t in turnos],
        "alertas": alertas,
        "cierre": ({"estado": cierre[0], "cerrado_por": cierre[1], "cerrado_en": cierre[2].isoformat(),
                    "nota": cierre[3], "reabierto_por": cierre[4], "motivo_reapertura": cierre[5]} if cierre else None),
    }


def cerrar_dia(conexion: psycopg.Connection, empresa_id: str, fecha: date, usuario_id: str, actor: str,
               nota: str | None = None, confirmar_alertas: bool = False, solo_inventario_real: bool = False,
               hoy: date | None = None) -> dict:
    """Cierre diario (auditoría nocturna). Exige que no queden turnos abiertos
    de ese día ni anteriores; si hay alertas (no-show, ocupadas sin pago,
    diferencias), exige confirmarlas. Congela la conciliación."""
    hoy = hoy or hoy_chile()
    if fecha > hoy:
        raise OperacionCajaInvalida("no se puede cerrar un día que aún no llega")
    conexion.execute("SELECT pg_advisory_xact_lock(hashtext('cierre_diario'), hashtext(%s))", (empresa_id,))
    if dia_cerrado(conexion, empresa_id, fecha):
        raise OperacionCajaInvalida("ese día ya está cerrado")
    abierto = conexion.execute(
        "SELECT usuario_nombre FROM caja_turnos WHERE empresa_id = %s AND estado = 'abierto' AND fecha_contable <= %s",
        (empresa_id, fecha),
    ).fetchone()
    if abierto:
        raise OperacionCajaInvalida(f"cierra primero el turno de caja de {abierto[0]}")
    nota = _texto(nota, "la nota", 1000)
    resumen = conciliacion_diaria(conexion, empresa_id, fecha, solo_inventario_real)
    if resumen["alertas"] and not confirmar_alertas:
        raise OperacionCajaInvalida("revisa las alertas del día y confirma el cierre")
    resumen.pop("cierre", None)
    conexion.execute(
        "INSERT INTO cierres_diarios (empresa_id, fecha, estado, usuario_id, cerrado_por, nota, resumen) "
        "VALUES (%s, %s, 'cerrado', %s, %s, %s, %s) ON CONFLICT (empresa_id, fecha) DO UPDATE SET estado = 'cerrado', "
        "usuario_id = EXCLUDED.usuario_id, cerrado_por = EXCLUDED.cerrado_por, cerrado_en = now(), "
        "nota = EXCLUDED.nota, resumen = EXCLUDED.resumen",
        (empresa_id, fecha, usuario_id, actor, nota, Json(resumen)),
    )
    return {"fecha": fecha.isoformat(), "estado": "cerrado", "cerrado_por": actor,
            "siguiente_fecha_contable": fecha_contable_actual(conexion, empresa_id, hoy).isoformat(),
            "resumen": resumen}


def reabrir_dia(conexion: psycopg.Connection, empresa_id: str, fecha: date, actor: str, motivo: str) -> dict:
    motivo = _texto(motivo, "el motivo", 500, True)
    if len(motivo) < MIN_JUSTIFICACION:
        raise DatosCajaInvalidos("explica el motivo de la reapertura (mínimo 10 caracteres)")
    if not dia_cerrado(conexion, empresa_id, fecha):
        raise OperacionCajaInvalida("ese día no está cerrado")
    conexion.execute(
        "UPDATE cierres_diarios SET estado = 'reabierto', reabierto_por = %s, reabierto_en = now(), "
        "motivo_reapertura = %s WHERE empresa_id = %s AND fecha = %s",
        (actor, motivo, empresa_id, fecha),
    )
    return {"fecha": fecha.isoformat(), "estado": "reabierto", "reabierto_por": actor}


def listar_cierres(conexion: psycopg.Connection, empresa_id: str, desde: date, hasta: date) -> list[dict]:
    filas = conexion.execute(
        "SELECT fecha, estado, cerrado_por, cerrado_en, nota, reabierto_por, motivo_reapertura, "
        "resumen->'resumen', resumen->'cobros', jsonb_array_length(COALESCE(resumen->'alertas', '[]'::jsonb)) "
        "FROM cierres_diarios WHERE empresa_id = %s AND fecha BETWEEN %s AND %s ORDER BY fecha DESC",
        (empresa_id, desde, hasta),
    ).fetchall()
    return [{"fecha": f[0].isoformat(), "estado": f[1], "cerrado_por": f[2], "cerrado_en": f[3].isoformat(),
             "nota": f[4], "reabierto_por": f[5], "motivo_reapertura": f[6], "resumen": f[7], "cobros": f[8],
             "alertas": f[9]} for f in filas]


def cierre_guardado(conexion: psycopg.Connection, empresa_id: str, fecha: date) -> dict | None:
    fila = conexion.execute(
        "SELECT resumen, estado, cerrado_por, cerrado_en FROM cierres_diarios WHERE empresa_id = %s AND fecha = %s",
        (empresa_id, fecha),
    ).fetchone()
    if fila is None:
        return None
    return {**fila[0], "cierre": {"estado": fila[1], "cerrado_por": fila[2], "cerrado_en": fila[3].isoformat()}}
