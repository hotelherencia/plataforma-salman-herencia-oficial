"""Cobro por el núcleo y operación de la estadía (spec-api-v1).

- El efecto de un pago lo registra el núcleo; si el núcleo rechaza, no hay
  pago. El registro durable del efecto vive en `efectos_nucleo`.
- modo="manual": caja en efectivo o transferencia que recepción registra;
  sin consulta bancaria y sin conciliación. modo="pasarela" sin adaptador:
  503 y nada marcado como cobrado.
- Una reserva ajena o inexistente responde 403 sin revelar cuál es el caso.
"""
import uuid
from datetime import date, datetime

import psycopg

from hotel_inventario.servicio import HORA_LLEGADA, LIMITE_CANCELACION_GRATUITA
from nucleo.servicio import AccesoDenegado as AccesoNucleo

ROLES_PAGO_MANUAL = frozenset({"recepcion", "caja", "administrador"})
ROLES_CAJA = frozenset({"caja", "administrador"})


class RecursoAjenoOInexistente(Exception):
    """403 sin revelar si la reserva existe."""


class PagoDuplicadoConDatosDistintos(Exception):
    """409 (V1-ISSUE-32): ya existe un pago con esa (reserva, clave) pero con
    monto o modo distintos; no es un reintento, es un conflicto."""


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


def _reserva_de_la_empresa(conexion: psycopg.Connection, reserva_id: str, empresa_id: str):
    fila = conexion.execute(
        "SELECT id, habitacion_id, estado FROM reservas WHERE id = %s AND empresa_id = %s",
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
) -> dict:
    _reserva_de_la_empresa(conexion, reserva_id, empresa_id)
    existente = conexion.execute(
        "SELECT id, monto_clp, modo FROM pagos WHERE reserva_id = %s AND clave = %s", (reserva_id, clave)
    ).fetchone()
    if existente is not None:
        if existente[1] != monto_clp or existente[2] != "manual":
            raise PagoDuplicadoConDatosDistintos(
                f"ya existe un pago con la clave «{clave}» por {existente[1]} CLP; "
                "usa otra clave de cobro o el mismo monto para reintentar"
            )
        return {"pago_id": existente[0], "reserva_id": reserva_id, "monto_clp": existente[1],
                "clave": clave, "modo": "manual", "estado": "confirmado", "reintento": True}
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
    return {"pago_id": pago_id, "reserva_id": reserva_id, "monto_clp": monto_clp,
            "clave": clave, "modo": "manual", "estado": "confirmado", "efecto_nucleo_id": efecto_id}


def caja_del_dia(conexion: psycopg.Connection, empresa_id: str, fecha: date) -> dict:
    filas = conexion.execute(
        "SELECT p.id, p.reserva_id, r.habitacion_id, p.monto_clp, p.modo, p.estado "
        "FROM pagos p JOIN reservas r ON r.id = p.reserva_id "
        "WHERE r.empresa_id = %s AND p.creado_en::date = %s AND p.estado = 'confirmado' "
        "ORDER BY p.creado_en",
        (empresa_id, fecha),
    ).fetchall()
    pagos = [
        {"pago_id": f[0], "reserva_id": f[1], "habitacion_id": f[2], "monto_clp": f[3], "modo": f[4], "estado": f[5]}
        for f in filas
    ]
    return {"fecha": fecha.isoformat(), "pagos": pagos, "total_clp": sum(p["monto_clp"] for p in pagos)}


def entrada(conexion: psycopg.Connection, empresa_id: str, reserva_id: str) -> dict:
    """Check-in (spec-api-v1 «Operación de la habitación»): en la misma
    transacción valida mantenimiento, disponibilidad, preparación y que ninguna
    otra estadía ocupe la unidad; al pasar, la reserva queda en_estadia y la
    habitación ocupada."""
    _reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id)
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
    habitacion = conexion.execute(
        "SELECT estado_operativo, estado_preparacion, mantenimiento FROM habitaciones WHERE id = %s",
        (_reserva[1],),
    ).fetchone()
    if habitacion[2]:
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
        "r.tarifa_noche_aceptada_clp, r.creado_en FROM reservas r JOIN habitaciones h ON h.id = r.habitacion_id "
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
        "creada_en": r[9].isoformat(),
        "cargos": [
            {"cargo_id": c[0], "tipo": c[1], "concepto": c[2], "monto_clp": c[3], "referencia": c[4],
             "registrado_en": c[5].isoformat()}
            for c in conexion.execute(
                "SELECT id, tipo, concepto, monto_clp, referencia, creado_en FROM cargos "
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
    _reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id)
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

ROLES_LIMPIEZA = frozenset({"recepcion", "administrador"})
ROLES_MANTENIMIENTO = frozenset({"administrador"})
ROLES_CANCELACION = frozenset({"recepcion", "administrador"})
ROLES_CARGO = ROLES_PAGO_MANUAL
ESTADOS_CON_CUENTA_ABIERTA = ("confirmada", "en_estadia")


def _habitacion_o_403(conexion: psycopg.Connection, habitacion_id: str):
    fila = conexion.execute(
        "SELECT estado_operativo, estado_preparacion, mantenimiento FROM habitaciones WHERE id = %s",
        (habitacion_id,),
    ).fetchone()
    if fila is None:
        raise RecursoAjenoOInexistente("acceso denegado")
    return fila


def completar_limpieza(conexion: psycopg.Connection, habitacion_id: str) -> dict:
    """Completa la limpieza pendiente y, si la unidad estaba sucia, la deja limpia."""
    _habitacion_o_403(conexion, habitacion_id)
    actualizadas = conexion.execute(
        "UPDATE tareas_operativas SET estado = 'completada', completada_en = now() "
        "WHERE habitacion_id = %s AND tipo = 'limpieza' AND estado = 'pendiente'",
        (habitacion_id,),
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


def fijar_mantenimiento(conexion: psycopg.Connection, habitacion_id: str, abierto: bool) -> dict:
    _habitacion_o_403(conexion, habitacion_id)
    (actual,) = conexion.execute(
        "SELECT mantenimiento FROM habitaciones WHERE id = %s", (habitacion_id,)
    ).fetchone()
    if abierto and not actual:
        conexion.execute("UPDATE habitaciones SET mantenimiento = true WHERE id = %s", (habitacion_id,))
        conexion.execute(
            "INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado) VALUES (%s, %s, 'mantenimiento', 'pendiente')",
            (f"TSK-{uuid.uuid4().hex[:12]}", habitacion_id),
        )
    elif not abierto and actual:
        conexion.execute("UPDATE habitaciones SET mantenimiento = false WHERE id = %s", (habitacion_id,))
        conexion.execute(
            "UPDATE tareas_operativas SET estado = 'completada', completada_en = now() "
            "WHERE habitacion_id = %s AND tipo = 'mantenimiento' AND estado = 'pendiente'",
            (habitacion_id,),
        )
    return {"habitacion_id": habitacion_id, "mantenimiento": abierto}


def asentar_cargo(conexion: psycopg.Connection, empresa_id: str, reserva_id: str, concepto: str, monto_clp: int) -> dict:
    """Cargo de texto libre (minibar, consumo, extra): solo con la cuenta abierta."""
    _reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id)
    if _reserva[2] not in ESTADOS_CON_CUENTA_ABIERTA:
        raise TransicionInvalida(f"la reserva está {_reserva[2]}")
    cargo_id = f"CRG-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO cargos (id, reserva_id, concepto, monto_clp, tipo) VALUES (%s, %s, %s, %s, 'cargo')",
        (cargo_id, reserva_id, concepto, monto_clp),
    )
    return {"cargo_id": cargo_id, "reserva_id": reserva_id, "concepto": concepto, "monto_clp": monto_clp, "tipo": "cargo"}


def cancelar(conexion: psycopg.Connection, empresa_id: str, reserva_id: str, ahora: datetime) -> dict:
    """Cancelación (spec-api-v1): reversos por los cargos sin reversar y, fuera
    del límite de 48 h, cargo de la primera noche. Los cargos no se tocan:
    nada de UPDATE ni DELETE sobre ellos."""
    _reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id)
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
