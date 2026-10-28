"""Cobro por el núcleo y operación de la estadía (spec-api-v1).

- El efecto de un pago lo registra el núcleo; si el núcleo rechaza, no hay
  pago. El registro durable del efecto vive en `efectos_nucleo`.
- modo="manual": caja en efectivo o transferencia que recepción registra;
  sin consulta bancaria y sin conciliación. modo="pasarela" sin adaptador:
  503 y nada marcado como cobrado.
- Una reserva ajena o inexistente responde 403 sin revelar cuál es el caso.
"""
import uuid
from datetime import date

import psycopg

from nucleo.servicio import AccesoDenegado as AccesoNucleo

ROLES_PAGO_MANUAL = frozenset({"recepcion", "caja", "administrador"})
ROLES_CAJA = frozenset({"caja", "administrador"})


class RecursoAjenoOInexistente(Exception):
    """403 sin revelar si la reserva existe."""


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
        "SELECT id, monto_clp FROM pagos WHERE reserva_id = %s AND clave = %s", (reserva_id, clave)
    ).fetchone()
    if existente is not None:
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
    _reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id)
    if _reserva[2] != "confirmada":
        raise TransicionInvalida(f"la reserva está {_reserva[2]}")
    habitacion = conexion.execute(
        "SELECT estado_operativo, estado_preparacion FROM habitaciones WHERE id = %s", (_reserva[1],)
    ).fetchone()
    if habitacion[0] != "disponible" or habitacion[1] not in ("limpia", "inspeccionada"):
        raise HabitacionNoLista("la habitación no está lista para el check-in")
    conexion.execute("UPDATE reservas SET estado = 'en_estadia' WHERE id = %s", (reserva_id,))
    return {"reserva_id": reserva_id, "habitacion_id": _reserva[1], "estado": "en_estadia"}


def salida(conexion: psycopg.Connection, empresa_id: str, reserva_id: str) -> dict:
    _reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id)
    if _reserva[2] != "en_estadia":
        raise TransicionInvalida("check-out requiere una estadía en curso")
    (total,) = conexion.execute(
        "SELECT COALESCE(SUM(monto_clp), 0) FROM cargos WHERE reserva_id = %s", (reserva_id,)
    ).fetchone()
    (pagado,) = conexion.execute(
        "SELECT COALESCE(SUM(monto_clp), 0) FROM pagos WHERE reserva_id = %s AND estado = 'confirmado'", (reserva_id,)
    ).fetchone()
    saldo = total - pagado
    if saldo != 0:
        raise SaldoPendiente(f"la cuenta tiene saldo pendiente de {saldo} CLP")
    liquidacion_id = f"LQ-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO liquidaciones (id, reserva_id, total_clp, pagado_clp, saldo_clp) "
        "VALUES (%s, %s, %s, %s, 0) ON CONFLICT (reserva_id) DO NOTHING",
        (liquidacion_id, reserva_id, total, pagado),
    )
    conexion.execute("UPDATE reservas SET estado = 'finalizada' WHERE id = %s", (reserva_id,))
    return {
        "liquidacion_id": liquidacion_id,
        "reserva_id": reserva_id,
        "total_clp": total,
        "pagado_clp": pagado,
        "saldo_clp": 0,
        "estado": "liquidada",
    }
