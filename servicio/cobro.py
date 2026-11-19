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

from nucleo.servicio import AccesoDenegado as AccesoNucleo

from . import hotel_sql
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
    hotel,
    empresa_id: str,
    reserva_id: str,
    monto_clp: int,
    clave: str,
    confirmar_exceso: bool = False,
    datos: dict | None = None,
    actor: str | None = None,
) -> dict:
    """Pago manual. #365: compara con el saldo de la cuenta bajo el cerrojo de
    la reserva; un monto menor queda como pago parcial (con saldo pendiente) y
    uno mayor exige `confirmar_exceso`. #364: la respuesta trae el huésped."""
    from . import clientes, contabilidad, imputacion

    reserva = _reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
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
        neto, pagado = hotel_sql.cuenta(conexion, hotel, empresa_id, reserva_id)
        return {"pago_id": existente[0], "reserva_id": reserva_id, "monto_clp": existente[1],
                "clave": clave, "modo": "manual", "estado": "confirmado", "reintento": True,
                "huesped_nombre": huesped, "habitacion_id": habitacion, "saldo_despues_clp": neto - pagado}
    # Saldo contable: incluye las noches aún no asentadas, así un abono antes de la Llegada no es «exceso».
    saldo_antes = imputacion.saldo_reserva(conexion, reserva_id)["pendiente_clp"]
    # Fase 1 contable: medio, documento y voucher se validan antes de tocar
    # el núcleo o la base (un 4xx no deja nada a medias).
    columnas = contabilidad.validar_datos_pago(conexion, empresa_id, datos)
    preparado = contabilidad.preparar_pago(conexion, empresa_id, reserva[2], columnas)
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
    pago_id = hotel_sql.registrar_pago(conexion, hotel, empresa_id, reserva_id, monto_clp, clave, efecto_id)
    # Fase 1 contable: la fila `pagos` la proyecta el dominio; aquí se le añaden medio, fecha
    # contable, turno, documento y voucher (una sola vez, en esta misma transacción).
    contabilidad.completar_pago(conexion, pago_id, columnas, preparado, actor)
    contabilidad.asentar_movimiento_pago(conexion, empresa_id, pago_id, preparado, columnas["medio"], monto_clp,
                                         actor or "sistema")
    # Contabilidad 2.1: cliente de la factura (RUT solo con números) e imputación a noche, habitación y cliente.
    receptor = columnas["receptor"]
    cliente_id = None
    if receptor:
        cliente_id = clientes.asegurar(
            conexion, receptor["rut"], receptor["razon_social"], actor or "sistema", giro=receptor["giro"],
            direccion=receptor["direccion"], comuna=receptor["comuna"], correo=receptor["correo"])
    imputacion.imputar_pago(conexion, reserva_id, pago_id, monto_clp, cliente_id, actor or "sistema")
    saldo_despues = saldo_antes - monto_clp
    tipo = "total" if saldo_despues == 0 else ("parcial" if saldo_despues > 0 else "exceso")
    # Aviso «pago registrado» en la misma transacción (sin datos del huésped).
    from . import avisos

    avisos.registrar_evento(conexion, "pago_registrado", pago_id, {
        "reserva_id": reserva_id, "habitacion_id": habitacion, "monto_clp": monto_clp,
        "tipo_pago": tipo, "saldo_despues_clp": saldo_despues}, empresa_id)
    return {"pago_id": pago_id, "reserva_id": reserva_id, "monto_clp": monto_clp,
            "clave": clave, "modo": "manual", "estado": "confirmado", "efecto_nucleo_id": efecto_id,
            "huesped_nombre": huesped, "habitacion_id": habitacion,
            "saldo_antes_clp": saldo_antes, "saldo_despues_clp": saldo_despues, "tipo": tipo,
            "medio": columnas["medio"], "documento_tipo": columnas["documento_tipo"],
            "fecha_contable": preparado["fecha_contable"].isoformat(), "turno_id": preparado["turno_id"],
            "es_anticipo": preparado["es_anticipo"]}


def caja_del_dia(conexion: psycopg.Connection, empresa_id: str, fecha: date) -> dict:
    """Pagos del día contable en hora de Chile (antes filtraba por la fecha
    UTC: un pago de noche aparecía al día siguiente). Los reversos restan."""
    filas = conexion.execute(
        "SELECT p.id, p.reserva_id, r.habitacion_id, p.monto_clp, p.modo, p.estado, r.huesped_nombre, p.creado_en, "
        "p.medio, p.tipo, p.documento_tipo, p.referencia_pago_id, p.es_anticipo, p.turno_id "
        "FROM pagos p JOIN reservas r ON r.id = p.reserva_id "
        "WHERE r.empresa_id = %s AND p.fecha_contable = %s AND p.estado = 'confirmado' "
        "ORDER BY p.creado_en",
        (empresa_id, fecha),
    ).fetchall()
    pagos = [
        {"pago_id": f[0], "reserva_id": f[1], "habitacion_id": f[2],
         "monto_clp": -f[3] if f[9] == "reverso" else f[3], "modo": f[4], "estado": f[5],
         "huesped_nombre": f[6], "registrado_en": f[7].isoformat(), "medio": f[8], "tipo": f[9],
         "documento_tipo": f[10], "referencia_pago_id": f[11], "es_anticipo": f[12], "turno_id": f[13]}
        for f in filas
    ]
    por_medio: dict[str, int] = {}
    for p in pagos:
        por_medio[p["medio"]] = por_medio.get(p["medio"], 0) + p["monto_clp"]
    return {"fecha": fecha.isoformat(), "pagos": pagos, "total_clp": sum(p["monto_clp"] for p in pagos),
            "por_medio": por_medio}


class ReasignacionInvalida(Exception):
    """409 (#360/#361): la unidad destino no sirve para esta reserva."""


ROLES_REASIGNACION = roles.con_admin_hotel("recepcion")


def detalle_reserva(conexion: psycopg.Connection, hotel, empresa_id: str, reserva_id: str, ver_documento: bool) -> dict:
    """Detalle de una reserva con su cuenta (spec-hotel-operacion-v1 §3.2).
    Ajena o inexistente → 403 sin revelar cuál."""
    _reserva_de_la_empresa(conexion, reserva_id, empresa_id)
    r = conexion.execute(
        "SELECT r.id, r.habitacion_id, h.tipo, r.inicio, r.fin, r.huesped_nombre, r.huesped_documento, r.estado, "
        "r.tarifa_noche_aceptada_clp, r.creado_en, r.personas, r.total_aceptado_clp FROM reservas r JOIN habitaciones h ON h.id = r.habitacion_id "
        "WHERE r.id = %s",
        (reserva_id,),
    ).fetchone()
    neto, pagado = hotel_sql.cuenta(conexion, hotel, empresa_id, reserva_id)
    reversados_pago = {
        f[0] for f in conexion.execute(
            "SELECT referencia_pago_id FROM pagos WHERE reserva_id = %s AND tipo = 'reverso'", (reserva_id,)
        ).fetchall()
    }
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
             "registrado_en": c[5].isoformat(), "reversado": c[6], "producto_id": c[7], "cantidad": c[8],
             "precio_unitario_clp": c[9]}
            for c in conexion.execute(
                "SELECT id, tipo, concepto, monto_clp, referencia, creado_en, "
                "EXISTS(SELECT 1 FROM cargos x WHERE x.reserva_id = cargos.reserva_id AND x.tipo = 'reverso' "
                "AND x.referencia = cargos.id), producto_id, cantidad, precio_unitario_clp FROM cargos "
                "WHERE reserva_id = %s ORDER BY creado_en, id",
                (reserva_id,),
            ).fetchall()
        ],
        "pagos": [
            {"pago_id": g[0], "monto_clp": g[1], "modo": g[2], "estado": g[3], "registrado_en": g[4].isoformat(),
             "tipo": g[5], "medio": g[6], "documento_tipo": g[7], "referencia_pago_id": g[8],
             "fecha_contable": g[9].isoformat(), "es_anticipo": g[10],
             "reversado": g[0] in reversados_pago}
            for g in conexion.execute(
                "SELECT id, monto_clp, modo, estado, creado_en, tipo, medio, documento_tipo, referencia_pago_id, "
                "fecha_contable, es_anticipo FROM pagos WHERE reserva_id = %s ORDER BY creado_en, id",
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


# --- Operación de la habitación y de la cuenta (spec-api-v1, 2026-10-30) ---

ROLES_LIMPIEZA = roles.con_admin_hotel("recepcion", roles.ASEO)
ROLES_VISTA_ASEO = roles.con_admin_hotel("recepcion", roles.ASEO)
ROLES_VERIFICACION_ASEO = roles.con_admin_hotel()
ROLES_OBSERVACION = roles.con_admin_hotel("recepcion")
ROLES_MANTENIMIENTO = roles.con_admin_hotel()
ROLES_CANCELACION = roles.con_admin_hotel("recepcion")
ROLES_CARGO = ROLES_PAGO_MANUAL
ROLES_CONCEPTO_LIBRE = roles.con_admin_hotel()
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


