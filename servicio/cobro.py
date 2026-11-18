"""Cobro por el núcleo y operación de la estadía (spec-api-v1).

- El efecto de un pago lo registra el núcleo; si el núcleo rechaza, no hay
  pago. El registro durable del efecto vive en `efectos_nucleo`.
- modo="manual": caja en efectivo o transferencia que recepción registra;
  sin consulta bancaria y sin conciliación. modo="pasarela" sin adaptador:
  503 y nada marcado como cobrado.
- Una reserva ajena o inexistente responde 403 sin revelar cuál es el caso.
"""
import uuid
from datetime import date, datetime, timedelta

import psycopg
from psycopg.errors import ExclusionViolation

from hotel_inventario.servicio import HORA_LLEGADA, LIMITE_CANCELACION_GRATUITA
from nucleo.servicio import AccesoDenegado as AccesoNucleo

from . import reservas as reservas_db
from . import roles

ROLES_PAGO_MANUAL = roles.con_admin_hotel("recepcion", "caja")
ROLES_CAJA = roles.con_admin_hotel("caja")


class RecursoAjenoOInexistente(Exception):
    """403 sin revelar si la reserva existe."""


class PagoDuplicadoConDatosDistintos(Exception):
    """409 (V1-ISSUE-32): ya existe un pago con esa (reserva, clave) pero con
    monto o modo distintos; no es un reintento, es un conflicto."""


class PagoEnExceso(Exception):
    """409 (#365): el monto supera el saldo y no se confirmó el exceso."""

    def __init__(self, saldo_clp: int, exceso_clp: int):
        super().__init__(
            f"el pago supera el saldo pendiente ({saldo_clp} CLP) en {exceso_clp} CLP; "
            "confírmalo explícitamente si corresponde"
        )
        self.saldo_clp = saldo_clp
        self.exceso_clp = exceso_clp


class CargoNoReversable(Exception):
    """409 (#359): el cargo no existe en la reserva, ya fue reversado o es un reverso."""


class PasarelaNoConfigurada(Exception):
    """503: puerto sin adaptador; nada queda marcado como cobrado."""


class PagoRechazadoPorNucleo(Exception):
    """El núcleo rechazó el efecto; no se guarda el pago."""


class HabitacionNoLista(Exception):
    """409: la habitación no está lista para el check-in."""


class TransicionInvalida(Exception):
    """409: la reserva no admite la operación en su estado actual."""


class SaldoPendiente(Exception):
    """409: la cuenta no está saldada; la salida exige saldo 0."""


def _reserva_de_la_empresa(
    conexion: psycopg.Connection, reserva_id: str, empresa_id: str, bloqueo: bool = False
):
    clausula = " FOR UPDATE" if bloqueo else ""
    fila = conexion.execute(
        f"SELECT id, habitacion_id, estado FROM reservas WHERE id = %s AND empresa_id = %s{clausula}",
        (reserva_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise RecursoAjenoOInexistente("acceso denegado")
    return fila


def registrar_pago_manual(
    conexion: psycopg.Connection,
    nucleo,
    empresa_id: str,
    reserva_id: str,
    monto_clp: int,
    clave: str,
    confirmar_exceso: bool = False,
) -> dict:
    """Pago manual. #365: compara con el saldo de la cuenta bajo el cerrojo de
    la reserva; un monto menor queda como pago parcial (con saldo pendiente) y
    uno mayor exige `confirmar_exceso`. #364: la respuesta trae el huésped."""
    _reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    huesped, habitacion = conexion.execute(
        "SELECT huesped_nombre, habitacion_id FROM reservas WHERE id = %s", (reserva_id,)
    ).fetchone()
    existente = conexion.execute(
        "SELECT id, monto_clp, modo FROM pagos WHERE reserva_id = %s AND clave = %s", (reserva_id, clave)
    ).fetchone()
    if existente is not None:
        if existente[1] != monto_clp or existente[2] != "manual":
            raise PagoDuplicadoConDatosDistintos(
                f"ya existe un pago con la clave «{clave}» por {existente[1]} CLP; "
                "usa otra clave de cobro o el mismo monto para reintentar"
            )
        neto, pagado = cuenta_de_reserva(conexion, reserva_id)
        return {"pago_id": existente[0], "reserva_id": reserva_id, "monto_clp": existente[1],
                "clave": clave, "modo": "manual", "estado": "confirmado", "reintento": True,
                "huesped_nombre": huesped, "habitacion_id": habitacion, "saldo_despues_clp": neto - pagado}
    neto, pagado = cuenta_de_reserva(conexion, reserva_id)
    saldo_antes = neto - pagado
    if monto_clp > saldo_antes and not confirmar_exceso:
        raise PagoEnExceso(saldo_antes, monto_clp - max(saldo_antes, 0))
    clave_efecto = f"{reserva_id}:{clave}"
    try:
        nucleo.aplicar_resultado_pago(empresa_id, clave_efecto, "confirmado", monto_clp)
    except AccesoNucleo as error:
        raise PagoRechazadoPorNucleo("el núcleo rechazó el cobro") from error
    efecto_id = f"EFX-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO efectos_nucleo (id, clave, estado, monto_clp) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (clave) DO NOTHING",
        (efecto_id, clave_efecto, "confirmado", monto_clp),
    )
    pago_id = f"PAG-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO pagos (id, reserva_id, monto_clp, clave, modo, estado, efecto_nucleo_id) "
        "VALUES (%s, %s, %s, %s, 'manual', 'confirmado', %s)",
        (pago_id, reserva_id, monto_clp, clave, efecto_id),
    )
    saldo_despues = saldo_antes - monto_clp
    tipo = "total" if saldo_despues == 0 else ("parcial" if saldo_despues > 0 else "exceso")
    return {"pago_id": pago_id, "reserva_id": reserva_id, "monto_clp": monto_clp,
            "clave": clave, "modo": "manual", "estado": "confirmado", "efecto_nucleo_id": efecto_id,
            "huesped_nombre": huesped, "habitacion_id": habitacion,
            "saldo_antes_clp": saldo_antes, "saldo_despues_clp": saldo_despues, "tipo": tipo}


def caja_del_dia(conexion: psycopg.Connection, empresa_id: str, fecha: date) -> dict:
    filas = conexion.execute(
        "SELECT p.id, p.reserva_id, r.habitacion_id, p.monto_clp, p.modo, p.estado, r.huesped_nombre "
        "FROM pagos p JOIN reservas r ON r.id = p.reserva_id "
        "WHERE r.empresa_id = %s AND p.creado_en::date = %s AND p.estado = 'confirmado' "
        "ORDER BY p.creado_en",
        (empresa_id, fecha),
    ).fetchall()
    pagos = [
        {"pago_id": f[0], "reserva_id": f[1], "habitacion_id": f[2], "monto_clp": f[3], "modo": f[4], "estado": f[5],
         "huesped_nombre": f[6]}
        for f in filas
    ]
    return {"fecha": fecha.isoformat(), "pagos": pagos, "total_clp": sum(p["monto_clp"] for p in pagos)}


class ReasignacionInvalida(Exception):
    """409 (#360/#361): la unidad destino no sirve para esta reserva."""


ROLES_REASIGNACION = roles.con_admin_hotel("recepcion")


def reasignar(
    conexion: psycopg.Connection, empresa_id: str, reserva_id: str, destino: str, motivo: str, actor: str
) -> dict:
    """#361: mueve la reserva (confirmada o en estadía) a otra unidad con la
    tarifa pactada. Valida que la unidad esté en venta, sin mantenimiento,
    con capacidad y libre en el rango (la exclusión de la base decide la
    carrera). En estadía la destino debe estar preparada; la origen queda
    sucia con tarea de limpieza, igual que en la salida."""
    reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    origen, estado = reserva[1], reserva[2]
    if estado not in ESTADOS_CON_CUENTA_ABIERTA:
        raise TransicionInvalida(f"la reserva está {estado}")
    if destino == origen:
        raise ReasignacionInvalida(f"la reserva ya está en {destino}")
    motivo = (motivo or "").strip()
    if len(motivo) < 3:
        raise ReasignacionInvalida("indica el motivo del cambio de habitación")
    (personas,) = conexion.execute("SELECT personas FROM reservas WHERE id = %s", (reserva_id,)).fetchone()
    # Cerrojo en orden estable para no cruzarse con otra reasignación inversa.
    for hid in sorted((origen, destino)):
        conexion.execute("SELECT 1 FROM habitaciones WHERE id = %s FOR UPDATE", (hid,))
    fila = conexion.execute(
        "SELECT estado_operativo, estado_preparacion, mantenimiento, capacidad "
        "FROM habitaciones WHERE id = %s",
        (destino,),
    ).fetchone()
    if fila is None:
        raise ReasignacionInvalida(f"la habitación {destino} no existe")
    (inicio, fin) = conexion.execute("SELECT inicio, fin FROM reservas WHERE id = %s", (reserva_id,)).fetchone()
    if fila[0] in reservas_db.ESTADOS_NO_VENDIBLES or reservas_db.mantenimiento_solapa(conexion, destino, inicio, fin):
        raise ReasignacionInvalida(f"la habitación {destino} está fuera del cupo (mantenimiento o bloqueo)")
    if personas is not None and fila[3] < personas:
        raise ReasignacionInvalida(f"la habitación {destino} admite hasta {fila[3]} personas")
    if estado == "en_estadia" and fila[1] not in ("limpia", "inspeccionada"):
        raise ReasignacionInvalida(f"la habitación {destino} no está lista (preparación: {fila[1]})")
    try:
        with conexion.transaction():
            conexion.execute("UPDATE reservas SET habitacion_id = %s WHERE id = %s", (destino, reserva_id))
    except ExclusionViolation as error:
        raise ReasignacionInvalida(f"la habitación {destino} está ocupada en parte de esas fechas") from error
    if estado == "en_estadia":
        conexion.execute("UPDATE habitaciones SET estado_operativo = 'ocupada' WHERE id = %s", (destino,))
        (otra,) = conexion.execute(
            "SELECT count(*) FROM reservas WHERE habitacion_id = %s AND estado = 'en_estadia'", (origen,)
        ).fetchone()
        if otra == 0:
            conexion.execute(
                "UPDATE habitaciones SET estado_operativo = 'disponible', estado_preparacion = 'sucia' WHERE id = %s",
                (origen,),
            )
            conexion.execute(
                "INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado) VALUES (%s, %s, 'limpieza', 'pendiente')",
                (f"TAR-{uuid.uuid4().hex[:12]}", origen),
            )
    reasignacion_id = f"REA-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO reasignaciones (id, reserva_id, desde_habitacion_id, hacia_habitacion_id, motivo, actor, estado_reserva) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (reasignacion_id, reserva_id, origen, destino, motivo, actor, estado),
    )
    return {"reasignacion_id": reasignacion_id, "reserva_id": reserva_id, "desde_habitacion_id": origen,
            "hacia_habitacion_id": destino, "estado": estado, "motivo": motivo}


def entrada(conexion: psycopg.Connection, empresa_id: str, reserva_id: str, documento: str | None = None,
            documento_tipo: str | None = None, habitacion_id: str | None = None, actor: str = "sistema") -> dict:
    """Check-in (spec-api-v1 «Operación de la habitación»): en la misma
    transacción valida mantenimiento, disponibilidad, preparación y que ninguna
    otra estadía ocupe la unidad; al pasar, la reserva queda en_estadia y la
    habitación ocupada. D-ENT-01 (DECISIÓN 2026-11-06, #296): exige el
    documento del huésped antes de `en_estadia`; si la reserva aún no lo trae
    (p. ej. conversión de solicitud pública), la entrada lo captura."""
    _reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    if _reserva[2] != "confirmada":
        raise TransicionInvalida(f"la reserva está {_reserva[2]}")
    # REQUISITO PROPUESTO 2026-11-03 (v1-issue-07, en ratificación; fuente:
    # regla de llegada del dominio check_in): la entrada exige que la reserva
    # haya comenzado. Fecha del servidor, igual que la cancelación.
    (inicio,) = conexion.execute(
        "SELECT inicio FROM reservas WHERE id = %s", (reserva_id,)
    ).fetchone()
    if inicio > date.today():
        raise TransicionInvalida(f"aún no llega su día de entrada ({inicio.isoformat()})")
    # D-ENT-01: documento exigido antes de en_estadia (después de la regla de
    # inicio para no enmascarar el 409 de «aún no llega su día»).
    (documento_guardado,) = conexion.execute(
        "SELECT huesped_documento FROM reservas WHERE id = %s", (reserva_id,)
    ).fetchone()
    if not documento_guardado:
        if not documento or not documento.strip():
            raise TransicionInvalida("registra el documento del huésped para pasar la entrada")
        conexion.execute(
            "UPDATE reservas SET huesped_documento = %s, huesped_documento_tipo = %s WHERE id = %s",
            (documento.strip(), documento_tipo, reserva_id),
        )
    # #360: la unidad se confirma al llegar; si recepción elige otra, se
    # reasigna aquí mismo y la entrada sigue sobre la nueva.
    if habitacion_id and habitacion_id != _reserva[1]:
        reasignar(conexion, empresa_id, reserva_id, habitacion_id, "asignada en la entrada", actor)
        _reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    habitacion = conexion.execute(
        "SELECT estado_operativo, estado_preparacion, mantenimiento FROM habitaciones WHERE id = %s FOR UPDATE",
        (_reserva[1],),
    ).fetchone()
    hoy = date.today()
    if reservas_db.mantenimiento_solapa(conexion, _reserva[1], hoy, hoy + timedelta(days=1)):
        raise HabitacionNoLista("la habitación tiene mantenimiento abierto")
    # Espejo del dominio (check_in): OCUPADA no bloquea — el turnover de una
    # reserva no solapada está permitido (DECISIÓN 2026-10-30). Solo bloquean
    # los estados no vendibles y la suciedad; el solape lo cubre la consulta
    # de otra estadía más abajo.
    if habitacion[0] in ("bloqueada", "fuera_de_servicio"):
        raise HabitacionNoLista("la habitación no está disponible")
    if habitacion[1] not in ("limpia", "inspeccionada"):
        raise HabitacionNoLista("la habitación no está lista para el check-in")
    (otra_estadia,) = conexion.execute(
        "SELECT count(*) FROM reservas WHERE habitacion_id = %s AND estado = 'en_estadia' AND id <> %s "
        "AND daterange(inicio, fin, '[)') && "
        "(SELECT daterange(inicio, fin, '[)') FROM reservas WHERE id = %s)",
        (_reserva[1], reserva_id, reserva_id),
    ).fetchone()
    if otra_estadia > 0:
        raise HabitacionNoLista("hay otra estadía en curso en esa habitación")
    conexion.execute("UPDATE reservas SET estado = 'en_estadia' WHERE id = %s", (reserva_id,))
    conexion.execute(
        "UPDATE habitaciones SET estado_operativo = 'ocupada' WHERE id = %s", (_reserva[1],)
    )
    return {"reserva_id": reserva_id, "habitacion_id": _reserva[1], "estado": "en_estadia"}


def cuenta_de_reserva(conexion: psycopg.Connection, reserva_id: str) -> tuple[int, int]:
    """(cargos netos, pagado): cargo menos reverso, y pagos confirmados. Única
    fórmula del saldo: la usan la salida y el detalle de la reserva."""
    (neto,) = conexion.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo = 'reverso' THEN -monto_clp ELSE monto_clp END), 0) "
        "FROM cargos WHERE reserva_id = %s",
        (reserva_id,),
    ).fetchone()
    (pagado,) = conexion.execute(
        "SELECT COALESCE(SUM(monto_clp), 0) FROM pagos WHERE reserva_id = %s AND estado = 'confirmado'", (reserva_id,)
    ).fetchone()
    return neto, pagado


def detalle_reserva(conexion: psycopg.Connection, empresa_id: str, reserva_id: str, ver_documento: bool) -> dict:
    """Detalle de una reserva con su cuenta (spec-hotel-operacion-v1 §3.2).
    Ajena o inexistente → 403 sin revelar cuál."""
    _reserva_de_la_empresa(conexion, reserva_id, empresa_id)
    r = conexion.execute(
        "SELECT r.id, r.habitacion_id, h.tipo, r.inicio, r.fin, r.huesped_nombre, r.huesped_documento, r.estado, "
        "r.tarifa_noche_aceptada_clp, r.creado_en, r.personas, r.total_aceptado_clp FROM reservas r JOIN habitaciones h ON h.id = r.habitacion_id "
        "WHERE r.id = %s",
        (reserva_id,),
    ).fetchone()
    neto, pagado = cuenta_de_reserva(conexion, reserva_id)
    detalle = {
        "reserva_id": r[0],
        "habitacion_id": r[1],
        "tipo_habitacion": r[2],
        "inicio": r[3].isoformat(),
        "fin": r[4].isoformat(),
        "noches": (r[4] - r[3]).days,
        "huesped_nombre": r[5],
        "estado": r[7],
        "tarifa_noche_aceptada_clp": r[8],
        "personas": r[10],
        "creada_en": r[9].isoformat(),
        # Entrega 1A: total y precio congelado por noche (null/vacío en
        # reservas anteriores a la migración 0021).
        "total_aceptado_clp": r[11],
        "precio_por_noche": reservas_db.noches_de_reserva(conexion, reserva_id),
        "cargos": [
            {"cargo_id": c[0], "tipo": c[1], "concepto": c[2], "monto_clp": c[3], "referencia": c[4],
             "registrado_en": c[5].isoformat(), "reversado": c[6]}
            for c in conexion.execute(
                "SELECT id, tipo, concepto, monto_clp, referencia, creado_en, "
                "EXISTS(SELECT 1 FROM cargos x WHERE x.reserva_id = cargos.reserva_id AND x.tipo = 'reverso' "
                "AND x.referencia = cargos.id) FROM cargos "
                "WHERE reserva_id = %s ORDER BY creado_en, id",
                (reserva_id,),
            ).fetchall()
        ],
        "pagos": [
            {"pago_id": g[0], "monto_clp": g[1], "modo": g[2], "estado": g[3], "registrado_en": g[4].isoformat()}
            for g in conexion.execute(
                "SELECT id, monto_clp, modo, estado, creado_en FROM pagos WHERE reserva_id = %s ORDER BY creado_en, id",
                (reserva_id,),
            ).fetchall()
        ],
        "cuenta": {"cargos_netos_clp": neto, "pagado_clp": pagado, "saldo_clp": neto - pagado},
        "liquidacion": None,
        "reasignaciones": [
            {"desde_habitacion_id": a[0], "hacia_habitacion_id": a[1], "motivo": a[2], "actor": a[3],
             "registrado_en": a[4].isoformat()}
            for a in conexion.execute(
                "SELECT desde_habitacion_id, hacia_habitacion_id, motivo, actor, creado_en FROM reasignaciones "
                "WHERE reserva_id = %s ORDER BY creado_en",
                (reserva_id,),
            ).fetchall()
        ],
    }
    if ver_documento:
        detalle["huesped_documento"] = r[6]
    liquidacion = conexion.execute(
        "SELECT id, total_clp, pagado_clp, saldo_clp, creado_en FROM liquidaciones WHERE reserva_id = %s",
        (reserva_id,),
    ).fetchone()
    if liquidacion:
        detalle["liquidacion"] = {
            "liquidacion_id": liquidacion[0], "total_clp": liquidacion[1], "pagado_clp": liquidacion[2],
            "saldo_clp": liquidacion[3], "liquidada_en": liquidacion[4].isoformat(),
        }
    return detalle


def salida(conexion: psycopg.Connection, empresa_id: str, reserva_id: str) -> dict:
    """Check-out: exige saldo neto (cargo menos reverso) en cero; finaliza la
    reserva y abre la limpieza. V1-ISSUE-15: solo deja la unidad disponible y
    sucia si no queda otra estadía en curso (el turnover no solapado de
    entrada admite dos estadías contiguas en la misma habitación)."""
    _reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    if _reserva[2] != "en_estadia":
        raise TransicionInvalida("check-out requiere una estadía en curso")
    neto, pagado = cuenta_de_reserva(conexion, reserva_id)
    saldo = neto - pagado
    if saldo != 0:
        raise SaldoPendiente(f"la cuenta tiene saldo pendiente de {saldo} CLP")
    liquidacion_id = f"LQ-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO liquidaciones (id, reserva_id, total_clp, pagado_clp, saldo_clp) "
        "VALUES (%s, %s, %s, %s, 0) ON CONFLICT (reserva_id) DO NOTHING",
        (liquidacion_id, reserva_id, neto, pagado),
    )
    conexion.execute("UPDATE reservas SET estado = 'finalizada' WHERE id = %s", (reserva_id,))
    (otra_estadia,) = conexion.execute(
        "SELECT count(*) FROM reservas WHERE habitacion_id = %s AND estado = 'en_estadia' AND id <> %s",
        (_reserva[1], reserva_id),
    ).fetchone()
    if otra_estadia > 0:
        # Otra estadía sigue en curso en la unidad: la habitación permanece
        # ocupada y limpia (la limpieza del turnover ya ocurrió antes de esa
        # entrada); la tarea se abre en la salida de la última estadía.
        conexion.execute(
            "UPDATE habitaciones SET estado_operativo = 'ocupada' WHERE id = %s", (_reserva[1],)
        )
    else:
        conexion.execute(
            "UPDATE habitaciones SET estado_operativo = 'disponible', estado_preparacion = 'sucia' WHERE id = %s",
            (_reserva[1],),
        )
        conexion.execute(
            "INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado) VALUES (%s, %s, 'limpieza', 'pendiente')",
            (f"TSK-{uuid.uuid4().hex[:12]}", _reserva[1]),
        )
    return {
        "liquidacion_id": liquidacion_id,
        "reserva_id": reserva_id,
        "total_clp": neto,
        "pagado_clp": pagado,
        "saldo_clp": 0,
        "estado": "liquidada",
    }


# --- Operación de la habitación y de la cuenta (spec-api-v1, 2026-10-30) ---

ROLES_LIMPIEZA = roles.con_admin_hotel("recepcion", roles.ASEO)
ROLES_VISTA_ASEO = roles.con_admin_hotel("recepcion", roles.ASEO)
ROLES_VERIFICACION_ASEO = roles.con_admin_hotel()
ROLES_OBSERVACION = roles.con_admin_hotel("recepcion")
ROLES_MANTENIMIENTO = roles.con_admin_hotel()
ROLES_CANCELACION = roles.con_admin_hotel("recepcion")
ROLES_CARGO = ROLES_PAGO_MANUAL
ROLES_REVERSO = roles.con_admin_hotel()
ESTADOS_CON_CUENTA_ABIERTA = ("confirmada", "en_estadia")


def _habitacion_o_403(conexion: psycopg.Connection, habitacion_id: str):
    fila = conexion.execute(
        "SELECT estado_operativo, estado_preparacion, mantenimiento FROM habitaciones WHERE id = %s",
        (habitacion_id,),
    ).fetchone()
    if fila is None:
        raise RecursoAjenoOInexistente("acceso denegado")
    return fila


def completar_limpieza(conexion: psycopg.Connection, habitacion_id: str, actor: str | None = None) -> dict:
    """Completa la limpieza pendiente y, si la unidad estaba sucia, la deja
    limpia. #362: registra quién la hizo (puede haber varias personas de aseo)."""
    _habitacion_o_403(conexion, habitacion_id)
    actualizadas = conexion.execute(
        "UPDATE tareas_operativas SET estado = 'completada', completada_en = now(), completada_por = %s "
        "WHERE habitacion_id = %s AND tipo = 'limpieza' AND estado = 'pendiente'",
        (actor, habitacion_id),
    ).rowcount
    conexion.execute(
        "UPDATE habitaciones SET estado_preparacion = 'limpia' "
        "WHERE id = %s AND estado_preparacion = 'sucia'",
        (habitacion_id,),
    )
    preparacion = conexion.execute(
        "SELECT estado_preparacion FROM habitaciones WHERE id = %s", (habitacion_id,)
    ).fetchone()[0]
    return {"habitacion_id": habitacion_id, "estado_preparacion": preparacion, "tareas_completadas": actualizadas}


class OperacionAseoInvalida(Exception):
    """409 (#363): la limpieza no está para verificar u la observación no existe."""


def vista_aseo(conexion: psycopg.Connection, hoy: date) -> dict:
    """#362: lista para el personal de aseo. Primero las habitaciones con
    limpieza pendiente; luego el estado de cada una (ocupada, llega o sale
    hoy, libre). Sin nombres ni datos del huésped ni precios."""
    filas = conexion.execute(
        "SELECT h.id, h.tipo, h.estado_operativo, h.estado_preparacion, "
        f"{reservas_db.SQL_MANTENIMIENTO_SOLAPA}, "
        "(SELECT t.id FROM tareas_operativas t WHERE t.habitacion_id = h.id AND t.tipo = 'limpieza' "
        " AND t.estado = 'pendiente' ORDER BY t.creado_en LIMIT 1), "
        "EXISTS(SELECT 1 FROM reservas r WHERE r.habitacion_id = h.id AND r.estado = 'en_estadia'), "
        "EXISTS(SELECT 1 FROM reservas r WHERE r.habitacion_id = h.id AND r.estado = 'confirmada' AND r.inicio = %s), "
        "EXISTS(SELECT 1 FROM reservas r WHERE r.habitacion_id = h.id AND r.estado = 'en_estadia' AND r.fin = %s) "
        "FROM habitaciones h ORDER BY h.id",
        (hoy, hoy + timedelta(days=1), hoy, hoy),
    ).fetchall()
    observaciones: dict[str, list] = {}
    for o in conexion.execute(
        "SELECT id, habitacion_id, texto, autor, creado_en FROM observaciones_habitacion "
        "WHERE atendida_en IS NULL ORDER BY creado_en"
    ).fetchall():
        observaciones.setdefault(o[1], []).append(
            {"observacion_id": o[0], "texto": o[2], "autor": o[3], "registrada_en": o[4].isoformat()})
    ultimas: dict[str, dict] = {}
    for t in conexion.execute(
        "SELECT DISTINCT ON (habitacion_id) habitacion_id, id, completada_en, completada_por, verificacion, "
        "verificada_por, observacion FROM tareas_operativas WHERE tipo = 'limpieza' AND estado = 'completada' "
        "ORDER BY habitacion_id, completada_en DESC"
    ).fetchall():
        ultimas[t[0]] = {"tarea_id": t[1], "completada_en": t[2].isoformat() if t[2] else None,
                         "completada_por": t[3], "verificacion": t[4], "verificada_por": t[5], "observacion": t[6]}
    habitaciones = []
    for f in filas:
        if f[6]:
            situacion = "sale_hoy" if f[8] else "ocupada"
        elif f[7]:
            situacion = "llega_hoy"
        else:
            situacion = "libre"
        habitaciones.append({
            "habitacion_id": f[0], "tipo": f[1], "estado_operativo": f[2], "estado_preparacion": f[3],
            "mantenimiento_hoy": bool(f[4]), "tarea_limpieza_id": f[5], "limpieza_pendiente": f[5] is not None,
            "situacion": situacion, "observaciones": observaciones.get(f[0], []),
            "ultima_limpieza": ultimas.get(f[0]),
        })
    habitaciones.sort(key=lambda h: (not h["limpieza_pendiente"], h["situacion"] != "llega_hoy", h["habitacion_id"]))
    por_verificar = [h["habitacion_id"] for h in habitaciones
                     if h["ultima_limpieza"] and h["ultima_limpieza"]["verificacion"] is None]
    return {"fecha": hoy.isoformat(), "habitaciones": habitaciones, "por_verificar": por_verificar,
            "pendientes": sum(1 for h in habitaciones if h["limpieza_pendiente"])}


def verificar_limpieza(conexion: psycopg.Connection, tarea_id: str, aprobada: bool,
                       observacion: str | None, actor: str) -> dict:
    """#363: la administración verifica la limpieza. Rechazada → la unidad
    vuelve a sucia con una tarea nueva y la observación queda para aseo."""
    tarea = conexion.execute(
        "SELECT habitacion_id, estado, verificacion FROM tareas_operativas "
        "WHERE id = %s AND tipo = 'limpieza' FOR UPDATE",
        (tarea_id,),
    ).fetchone()
    if tarea is None or tarea[1] != "completada":
        raise OperacionAseoInvalida("esa limpieza no existe o aún no se completa")
    if tarea[2] is not None:
        raise OperacionAseoInvalida(f"esa limpieza ya fue {tarea[2]}")
    texto = (observacion or "").strip() or None
    if not aprobada and not texto:
        raise OperacionAseoInvalida("al rechazar, deja una observación para aseo")
    habitacion_id = tarea[0]
    conexion.execute(
        "UPDATE tareas_operativas SET verificacion = %s, verificada_por = %s, verificada_en = now(), observacion = %s "
        "WHERE id = %s",
        ("verificada" if aprobada else "rechazada", actor, texto, tarea_id),
    )
    if aprobada:
        conexion.execute(
            "UPDATE habitaciones SET estado_preparacion = 'inspeccionada' WHERE id = %s AND estado_preparacion = 'limpia'",
            (habitacion_id,),
        )
    else:
        conexion.execute("UPDATE habitaciones SET estado_preparacion = 'sucia' WHERE id = %s", (habitacion_id,))
        conexion.execute(
            "INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado) VALUES (%s, %s, 'limpieza', 'pendiente')",
            (f"TSK-{uuid.uuid4().hex[:12]}", habitacion_id),
        )
        agregar_observacion(conexion, habitacion_id, f"Limpieza rechazada: {texto}", actor)
    (preparacion,) = conexion.execute(
        "SELECT estado_preparacion FROM habitaciones WHERE id = %s", (habitacion_id,)
    ).fetchone()
    return {"tarea_id": tarea_id, "habitacion_id": habitacion_id,
            "verificacion": "verificada" if aprobada else "rechazada", "estado_preparacion": preparacion}


def agregar_observacion(conexion: psycopg.Connection, habitacion_id: str, texto: str, autor: str) -> dict:
    """#363: nota de la administración para aseo en una habitación."""
    _habitacion_o_403(conexion, habitacion_id)
    texto = (texto or "").strip()
    if not texto:
        raise OperacionAseoInvalida("la observación no puede ir vacía")
    observacion_id = f"OBS-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO observaciones_habitacion (id, habitacion_id, texto, autor) VALUES (%s, %s, %s, %s)",
        (observacion_id, habitacion_id, texto[:500], autor),
    )
    return {"observacion_id": observacion_id, "habitacion_id": habitacion_id, "texto": texto[:500], "autor": autor}


def atender_observacion(conexion: psycopg.Connection, habitacion_id: str, observacion_id: str, actor: str) -> dict:
    fila = conexion.execute(
        "UPDATE observaciones_habitacion SET atendida_en = now(), atendida_por = %s "
        "WHERE id = %s AND habitacion_id = %s AND atendida_en IS NULL RETURNING id",
        (actor, observacion_id, habitacion_id),
    ).fetchone()
    if fila is None:
        raise OperacionAseoInvalida("esa observación no existe o ya fue atendida")
    return {"observacion_id": observacion_id, "habitacion_id": habitacion_id, "atendida_por": actor}


def fijar_mantenimiento(conexion: psycopg.Connection, habitacion_id: str, abierto: bool,
                        desde: date | None = None, hasta: date | None = None) -> dict:
    """#349: el mantenimiento puede llevar rango de fechas; solo saca la unidad
    del cupo en ese rango (sin fechas, solo el día en curso)."""
    _habitacion_o_403(conexion, habitacion_id)
    (actual,) = conexion.execute(
        "SELECT mantenimiento FROM habitaciones WHERE id = %s", (habitacion_id,)
    ).fetchone()
    if abierto:
        # Sin fecha, el mantenimiento empieza hoy (y sin término bloquea hasta hoy).
        desde = desde or date.today()
        conexion.execute(
            "UPDATE habitaciones SET mantenimiento_desde = %s, mantenimiento_hasta = %s WHERE id = %s",
            (desde, hasta, habitacion_id),
        )
    if abierto and not actual:
        conexion.execute("UPDATE habitaciones SET mantenimiento = true WHERE id = %s", (habitacion_id,))
        conexion.execute(
            "INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado) VALUES (%s, %s, 'mantenimiento', 'pendiente')",
            (f"TSK-{uuid.uuid4().hex[:12]}", habitacion_id),
        )
    elif not abierto and actual:
        conexion.execute(
            "UPDATE habitaciones SET mantenimiento = false, mantenimiento_desde = NULL, mantenimiento_hasta = NULL "
            "WHERE id = %s",
            (habitacion_id,),
        )
        conexion.execute(
            "UPDATE tareas_operativas SET estado = 'completada', completada_en = now() "
            "WHERE habitacion_id = %s AND tipo = 'mantenimiento' AND estado = 'pendiente'",
            (habitacion_id,),
        )
    return {"habitacion_id": habitacion_id, "mantenimiento": abierto,
            "desde": desde.isoformat() if abierto and desde else None,
            "hasta": hasta.isoformat() if abierto and hasta else None}


def asentar_cargo(conexion: psycopg.Connection, empresa_id: str, reserva_id: str, concepto: str, monto_clp: int) -> dict:
    """Cargo de texto libre (minibar, consumo, extra): solo con la cuenta abierta."""
    _reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    if _reserva[2] not in ESTADOS_CON_CUENTA_ABIERTA:
        raise TransicionInvalida(f"la reserva está {_reserva[2]}")
    cargo_id = f"CRG-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO cargos (id, reserva_id, concepto, monto_clp, tipo) VALUES (%s, %s, %s, %s, 'cargo')",
        (cargo_id, reserva_id, concepto, monto_clp),
    )
    return {"cargo_id": cargo_id, "reserva_id": reserva_id, "concepto": concepto, "monto_clp": monto_clp, "tipo": "cargo"}


def reversar_cargo(
    conexion: psycopg.Connection, empresa_id: str, reserva_id: str, cargo_id: str, motivo: str
) -> dict:
    """#359: anular un cargo es asentar su reverso (movimiento contrario), nunca
    borrarlo. Un cargo se reversa una sola vez y solo con la cuenta abierta."""
    reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    if reserva[2] not in ESTADOS_CON_CUENTA_ABIERTA:
        raise TransicionInvalida(f"la reserva está {reserva[2]}")
    motivo = (motivo or "").strip()
    if not motivo:
        raise CargoNoReversable("indica el motivo del reverso")
    cargo = conexion.execute(
        "SELECT concepto, monto_clp, tipo FROM cargos WHERE id = %s AND reserva_id = %s", (cargo_id, reserva_id)
    ).fetchone()
    if cargo is None or cargo[2] != "cargo":
        raise CargoNoReversable("ese cargo no existe en la reserva o ya es un reverso")
    if conexion.execute(
        "SELECT 1 FROM cargos WHERE reserva_id = %s AND tipo = 'reverso' AND referencia = %s", (reserva_id, cargo_id)
    ).fetchone():
        raise CargoNoReversable("ese cargo ya fue reversado")
    reverso_id = f"CRG-{uuid.uuid4().hex[:12]}"
    concepto = f"Reverso de {cargo[0]}: {motivo}"[:200]
    conexion.execute(
        "INSERT INTO cargos (id, reserva_id, concepto, monto_clp, tipo, referencia) VALUES (%s, %s, %s, %s, 'reverso', %s)",
        (reverso_id, reserva_id, concepto, cargo[1], cargo_id),
    )
    neto, pagado = cuenta_de_reserva(conexion, reserva_id)
    return {"cargo_id": reverso_id, "reserva_id": reserva_id, "tipo": "reverso", "referencia": cargo_id,
            "concepto": concepto, "monto_clp": cargo[1], "saldo_clp": neto - pagado}


def cancelar(conexion: psycopg.Connection, empresa_id: str, reserva_id: str, ahora: datetime) -> dict:
    """Cancelación (spec-api-v1): reversos por los cargos sin reversar y, fuera
    del límite de 48 h, cargo de la primera noche. Los cargos no se tocan:
    nada de UPDATE ni DELETE sobre ellos. El cerrojo `FOR UPDATE` sobre la fila
    de `reservas` serializa solicitudes concurrentes con distinta clave para
    que solo una transición proceda y jamás se dupliquen reversos ni penalidad."""
    _reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    if _reserva[2] != "confirmada":
        raise TransicionInvalida(f"la reserva está {_reserva[2]}")
    fila = conexion.execute(
        "SELECT inicio, tarifa_noche_aceptada_clp FROM reservas WHERE id = %s", (reserva_id,)
    ).fetchone()
    inicio, tarifa_noche = fila[0], fila[1]
    cargos = conexion.execute(
        "SELECT id, concepto, monto_clp FROM cargos WHERE reserva_id = %s AND tipo = 'cargo'", (reserva_id,)
    ).fetchall()
    reversados = {
        f[0]
        for f in conexion.execute(
            "SELECT referencia FROM cargos WHERE reserva_id = %s AND tipo = 'reverso' AND referencia IS NOT NULL",
            (reserva_id,),
        ).fetchall()
    }
    reversos = []
    for cargo_id, concepto, monto in cargos:
        if cargo_id in reversados:
            continue
        reverso_id = f"CRG-{uuid.uuid4().hex[:12]}"
        conexion.execute(
            "INSERT INTO cargos (id, reserva_id, concepto, monto_clp, tipo, referencia) VALUES (%s, %s, %s, %s, 'reverso', %s)",
            (reverso_id, reserva_id, f"Reverso de {concepto}", monto, cargo_id),
        )
        reversos.append({"cargo_id": reverso_id, "referencia": cargo_id, "monto_clp": monto})
    penalidad = None
    # HECHO DOCUMENTADO (dominio cancelar/LIMITE/HORA_LLEGADA): llegada a las
    # 15:00 del inicio; con menos de 48 h se carga la primera noche.
    llegada = datetime.combine(inicio, HORA_LLEGADA)
    if llegada - ahora < LIMITE_CANCELACION_GRATUITA:
        cargo_id = f"CRG-{uuid.uuid4().hex[:12]}"
        conexion.execute(
            "INSERT INTO cargos (id, reserva_id, concepto, monto_clp, tipo) VALUES (%s, %s, %s, %s, 'cargo')",
            (cargo_id, reserva_id, "Cancelación fuera de plazo: primera noche", tarifa_noche),
        )
        penalidad = {"cargo_id": cargo_id, "monto_clp": tarifa_noche}
    conexion.execute("UPDATE reservas SET estado = 'cancelada' WHERE id = %s", (reserva_id,))
    return {
        "reserva_id": reserva_id,
        "estado": "cancelada",
        "reversos": reversos,
        "penalidad_clp": penalidad["monto_clp"] if penalidad else 0,
        "reembolso": "no configurado",
    }
