"""Acceso a datos del hotel: habitaciones, tarifas, oferta y reservas.

La base de datos es la fuente de verdad de las reservas: la confirmación es
transaccional y el constraint de exclusión `reservas_sin_solape` rechaza el
solape en (habitación, rango). La tarifa aceptada queda congelada en la
reserva: cambiar tarifas no altera precios ya aceptados (spec-api-v1).
"""
import uuid
from datetime import date, datetime, timedelta

import psycopg
from psycopg.errors import ExclusionViolation

VIGENCIA_OFERTA = timedelta(minutes=15)
ESTABLECIMIENTO_SINTETICO = "EST-SINT-001"
# HECHO DOCUMENTADO: texto de hotel_inventario.servicio.POLITICA_CANCELACION
# (LIMITE_CANCELACION_GRATUITA 48 h, HORA_LLEGADA 15:00).
POLITICA_CANCELACION = (
    "cancelación gratuita hasta 48 horas antes de la llegada; "
    "después se carga la primera noche"
)
ESTADOS_VALIDOS = ("confirmada", "en_estadia", "finalizada", "cancelada")
ESTADOS_QUE_OCUPAN_CUPO = ("confirmada", "en_estadia")
# HECHO DOCUMENTADO (dominio, ESTADOS_VENDIBLES): bloqueada y fuera de servicio
# no entran al cupo para ninguna fecha; el mantenimiento tampoco.
ESTADOS_NO_VENDIBLES = ("bloqueada", "fuera_de_servicio")
# Regla única de vigencia de tarifas (spec-hotel-operacion-v1 §2.5): la de mayor
# fecha_desde que cubre la noche; a igualdad, la registrada más recientemente.
ORDEN_VIGENCIA_TARIFA = "ORDER BY t.fecha_desde DESC, t.creado_en DESC, t.id DESC"


class SinCupo(Exception):
    """409: la unidad ya está reservada en ese rango."""


class SinTarifaVigente(Exception):
    """409: no hay tarifa para la fecha de inicio."""


class HabitacionNoVendible(Exception):
    """409: la unidad está fuera del cupo (mantenimiento, bloqueada o fuera de servicio)."""


class HabitacionYaExiste(Exception):
    """409: alta con If-None-Match: * sobre una habitación existente."""


class HabitacionInexistente(Exception):
    """403 sin revelar existencia (mismo criterio que limpieza/mantenimiento)."""


class ReservasVigentes(Exception):
    """409: no se retira de operación una unidad con reservas confirmada/en_estadia."""

    def __init__(self, reservas: list[str]):
        super().__init__("la habitación tiene reservas vigentes")
        self.reservas = reservas


class TarifaSolapadaInutil(Exception):
    """409 (#299, DECISIÓN 2026-11-06): carga redundante de tarifa.

    Reconciliación documentada con CA-HAB-03 (spec §2.3, ratificada 2026-11-03):
    el append-only con desempate `fecha_desde DESC, creado_en DESC` ES el
    mecanismo de cambio de precio — una tarifa nueva siempre gana al menos su
    primera noche (misma fecha_desde gana por recencia), así que «prohibir
    todo solape» rompería el criterio de aceptación. Lo que sí se prohíbe es
    la carga que no aporta nada: el duplicado exacto (misma unidad y rango),
    que solo confunde el historial (la clase de error detrás de #306).
    """


def sembrar_habitaciones(conexion: psycopg.Connection) -> None:
    for n in range(1, 4):
        conexion.execute(
            "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (f"HAB-SINT-10{n}", ESTABLECIMIENTO_SINTETICO, "doble", 2),
        )


def guardar_habitacion(
    conexion: psycopg.Connection,
    habitacion_id: str,
    tipo: str,
    capacidad: int,
    solo_crear: bool = False,
    establecimiento_id: str = ESTABLECIMIENTO_SINTETICO,
) -> dict:
    """Alta o edición de tipo y capacidad (spec-hotel-operacion-v1 §2.2–2.3).

    Solo toca esas dos columnas: reservas, tarifas, estados y tareas quedan
    intactos. `solo_crear` (If-None-Match: *) rechaza una habitación existente.
    Devuelve `creada` y `cambios {campo: [antes, después]}`."""
    actual = conexion.execute(
        "SELECT tipo, capacidad FROM habitaciones WHERE id = %s FOR UPDATE", (habitacion_id,)
    ).fetchone()
    if actual is None:
        conexion.execute(
            "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES (%s, %s, %s, %s)",
            (habitacion_id, establecimiento_id, tipo, capacidad),
        )
        return {"creada": True, "cambios": {"tipo": [None, tipo], "capacidad": [None, capacidad]}}
    if solo_crear:
        raise HabitacionYaExiste(f"la habitación {habitacion_id} ya existe")
    cambios = {
        campo: [antes, despues]
        for campo, antes, despues in (("tipo", actual[0], tipo), ("capacidad", actual[1], capacidad))
        if antes != despues
    }
    if cambios:
        conexion.execute(
            "UPDATE habitaciones SET tipo = %s, capacidad = %s WHERE id = %s", (tipo, capacidad, habitacion_id)
        )
    return {"creada": False, "cambios": cambios}


def fijar_servicio(conexion: psycopg.Connection, habitacion_id: str, en_servicio: bool, motivo: str | None) -> dict:
    """Retiro de operación (baja lógica) y reincorporación (spec-hotel-operacion-v1
    §2.4). Retirar exige que ninguna reserva confirmada o en estadía use la
    unidad; nada se borra y la preparación y el mantenimiento se conservan."""
    fila = conexion.execute(
        "SELECT estado_operativo, motivo_fuera_de_servicio FROM habitaciones WHERE id = %s FOR UPDATE",
        (habitacion_id,),
    ).fetchone()
    if fila is None:
        raise HabitacionInexistente("acceso denegado")
    retirada = fila[0] == "fuera_de_servicio"
    cambio = False
    if not en_servicio and not retirada:
        vigentes = [
            f[0]
            for f in conexion.execute(
                "SELECT id FROM reservas WHERE habitacion_id = %s AND estado = ANY(%s) ORDER BY inicio, id",
                (habitacion_id, list(ESTADOS_QUE_OCUPAN_CUPO)),
            ).fetchall()
        ]
        if vigentes:
            raise ReservasVigentes(vigentes)
        conexion.execute(
            "UPDATE habitaciones SET estado_operativo = 'fuera_de_servicio', motivo_fuera_de_servicio = %s, "
            "fuera_de_servicio_desde = now() WHERE id = %s",
            (motivo, habitacion_id),
        )
        cambio = True
    elif en_servicio and retirada:
        conexion.execute(
            "UPDATE habitaciones SET estado_operativo = 'disponible', motivo_fuera_de_servicio = NULL, "
            "fuera_de_servicio_desde = NULL WHERE id = %s",
            (habitacion_id,),
        )
        cambio = True
    estado, motivo_actual = conexion.execute(
        "SELECT estado_operativo, motivo_fuera_de_servicio FROM habitaciones WHERE id = %s", (habitacion_id,)
    ).fetchone()
    return {
        "habitacion_id": habitacion_id,
        "en_servicio": estado != "fuera_de_servicio",
        "estado_operativo": estado,
        "motivo": motivo_actual,
        "cambio": cambio,
    }


def insertar_tarifa(
    conexion: psycopg.Connection, habitacion_id: str, fecha_desde: date, fecha_hasta: date, tarifa_noche_clp: int
) -> str:
    # #299 (DECISIÓN 2026-11-06): se rechaza la carga idéntica (misma unidad,
    # rango Y precio), que no aporta vigencia alguna. El solape con distinto
    # precio o rango sigue siendo el mecanismo de cambio de precio (CA-HAB-03:
    # gana la más reciente por `creado_en`).
    duplicada = conexion.execute(
        "SELECT 1 FROM tarifas WHERE habitacion_id = %s AND fecha_desde = %s AND fecha_hasta = %s "
        "AND tarifa_noche_clp = %s LIMIT 1",
        (habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp),
    ).fetchone()
    if duplicada is not None:
        raise TarifaSolapadaInutil(
            f"ya existe una tarifa idéntica para {habitacion_id} en [{fecha_desde}, {fecha_hasta}) "
            f"a ${tarifa_noche_clp}/noche; la vigente ya tiene ese precio"
        )
    tarifa_id = f"TAR-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
        "VALUES (%s, %s, %s, %s, %s)",
        (tarifa_id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp),
    )
    return tarifa_id


def tarifa_vigente(conexion: psycopg.Connection, habitacion_id: str, fecha: date) -> int | None:
    fila = conexion.execute(
        "SELECT t.tarifa_noche_clp FROM tarifas t WHERE t.habitacion_id = %s AND t.fecha_desde <= %s "
        f"AND t.fecha_hasta > %s {ORDEN_VIGENCIA_TARIFA} LIMIT 1",
        (habitacion_id, fecha, fecha),
    ).fetchone()
    return fila[0] if fila else None


def precio_noches(conexion: psycopg.Connection, habitacion_id: str, inicio: date, fin: date) -> tuple[int, int]:
    """(tarifa de la primera noche, total noche a noche).

    DECISIÓN del propietario 2026-11-06 (#305, opción b, ratificada): cada
    noche se cobra con la tarifa vigente de esa noche; la oferta y la reserva
    quedan alineadas (lo ofertado es lo cargado). `tarifa_noche_aceptada_clp`
    conserva su significado de referencia: tarifa de la noche de inicio
    (base de la penalidad de cancelación, spec-hotel-operacion §3).
    Reemplaza la regla provisional D-TAR-02 (tarifa de inicio × noches).
    """
    tarifa_primera = tarifa_vigente(conexion, habitacion_id, inicio)
    total = 0
    noche = inicio
    while noche < fin:
        total += tarifa_vigente(conexion, habitacion_id, noche)
        noche += timedelta(days=1)
    return tarifa_primera, total


def tarifas_por_noche(conexion: psycopg.Connection, desde: date, hasta: date) -> dict[tuple[str, date], int]:
    """Tarifa vigente de cada (habitación, noche) en [desde, hasta), con la
    misma regla que `tarifa_vigente` (una sola consulta para la rejilla)."""
    filas = conexion.execute(
        "SELECT h.id, d::date, (SELECT t.tarifa_noche_clp FROM tarifas t WHERE t.habitacion_id = h.id "
        f"AND t.fecha_desde <= d::date AND t.fecha_hasta > d::date {ORDEN_VIGENCIA_TARIFA} LIMIT 1) "
        "FROM habitaciones h CROSS JOIN generate_series(%s::date, %s::date - 1, interval '1 day') d",
        (desde, hasta),
    ).fetchall()
    return {(f[0], f[1]): f[2] for f in filas if f[2] is not None}


def primera_noche_sin_tarifa(conexion: psycopg.Connection, habitacion_id: str, inicio: date, fin: date) -> date | None:
    """Primera noche de [inicio, fin) sin tarifa vigente, o None si todas la
    tienen (spec-hotel-operacion-v1 §2.8: la misma regla que pinta `sin_tarifa`
    en la ocupación). No fija el precio: eso sigue en `tarifa_vigente(inicio)`."""
    fila = conexion.execute(
        "SELECT d::date FROM generate_series(%s::date, %s::date - 1, interval '1 day') d "
        "WHERE NOT EXISTS (SELECT 1 FROM tarifas t WHERE t.habitacion_id = %s "
        "AND t.fecha_desde <= d::date AND t.fecha_hasta > d::date) ORDER BY d LIMIT 1",
        (inicio, fin, habitacion_id),
    ).fetchone()
    return fila[0] if fila else None


def _libre(conexion: psycopg.Connection, habitacion_id: str, inicio: date, fin: date) -> bool:
    fila = conexion.execute(
        "SELECT count(*) FROM reservas WHERE habitacion_id = %s AND estado IN ('confirmada', 'en_estadia') "
        "AND daterange(inicio, fin, '[)') && daterange(%s, %s, '[)')",
        (habitacion_id, inicio, fin),
    ).fetchone()
    return fila[0] == 0


def oferta(conexion: psycopg.Connection, inicio: date, fin: date, personas: int, ahora: datetime) -> dict:
    # HECHO DOCUMENTADO (dominio, ESTADOS_VENDIBLES): ocupada y sucia se venden
    # en otras fechas; mantenimiento, bloqueada y fuera_de_servicio quedan fuera.
    unidades = conexion.execute(
        "SELECT id, tipo, capacidad FROM habitaciones WHERE capacidad >= %s "
        "AND mantenimiento = false AND estado_operativo <> ALL(%s) "
        "ORDER BY id",
        (personas, list(ESTADOS_NO_VENDIBLES)),
    ).fetchall()
    items = []
    for habitacion_id, tipo, _capacidad in unidades:
        if primera_noche_sin_tarifa(conexion, habitacion_id, inicio, fin) is not None or not _libre(
            conexion, habitacion_id, inicio, fin
        ):
            continue
        tarifa, total = precio_noches(conexion, habitacion_id, inicio, fin)
        items.append(
            {
                "habitacion_id": habitacion_id,
                "tipo": tipo,
                "tarifa_noche_clp": tarifa,
                "total_clp": total,
                "politica_cancelacion": POLITICA_CANCELACION,
                "vigente_hasta": (ahora + VIGENCIA_OFERTA).isoformat(),
            }
        )
    return {"oferta": items, "emitida_en": ahora.isoformat(), "vigencia_minutos": VIGENCIA_OFERTA.total_seconds() // 60}


_COLUMNAS_HABITACION = (
    "h.id, h.tipo, h.capacidad, h.estado_operativo, h.estado_preparacion, h.mantenimiento, "
    "COALESCE((SELECT t.tarifa_noche_clp FROM tarifas t WHERE t.habitacion_id = h.id "
    "ORDER BY t.fecha_desde DESC, t.creado_en DESC, t.id DESC LIMIT 1), 0), "
    "(SELECT COUNT(*) FROM tareas_operativas ta WHERE ta.habitacion_id = h.id AND ta.estado = 'pendiente'), "
    "EXISTS(SELECT 1 FROM tareas_operativas ta WHERE ta.habitacion_id = h.id "
    "AND ta.estado = 'pendiente' AND ta.tipo = 'limpieza'), "
    "(SELECT t.tarifa_noche_clp FROM tarifas t WHERE t.habitacion_id = h.id "
    f"AND t.fecha_desde <= %s AND t.fecha_hasta > %s {ORDEN_VIGENCIA_TARIFA} LIMIT 1), "
    "h.motivo_fuera_de_servicio, h.fuera_de_servicio_desde, h.creado_en"
)


def _habitacion_a_dict(f) -> dict:
    return {
        "habitacion_id": f[0],
        "tipo": f[1],
        "capacidad": f[2],
        "estado_operativo": f[3],
        "estado_preparacion": f[4],
        "mantenimiento": f[5],
        "tarifa_noche_clp": f[6],
        "tareas_pendientes": f[7],
        "limpieza_pendiente": f[8],
        "tarifa_vigente_hoy_clp": f[9],
        "en_servicio": f[3] != "fuera_de_servicio",
        "motivo_fuera_de_servicio": f[10],
        "fuera_de_servicio_desde": f[11].isoformat() if f[11] else None,
        "creado_en": f[12].isoformat(),
    }


def listar_habitaciones(conexion: psycopg.Connection, hoy: date | None = None) -> list[dict]:
    """Inventario operativo de las unidades (GET /hotel/habitaciones,
    spec-api-v1 «Operación de la habitación»): estado operativo, preparación,
    mantenimiento y tareas pendientes, con la última tarifa configurada como
    referencia (`tarifa_noche_clp`) y la vigente hoy. Solo lectura."""
    hoy = hoy or date.today()
    filas = conexion.execute(
        f"SELECT {_COLUMNAS_HABITACION} FROM habitaciones h ORDER BY h.id", (hoy, hoy)
    ).fetchall()
    return [_habitacion_a_dict(f) for f in filas]


def ficha_habitacion(
    conexion: psycopg.Connection,
    habitacion_id: str,
    empresa_id: str,
    ver_documento: bool,
    ver_auditoria: bool,
    hoy: date | None = None,
) -> dict:
    """Ficha de la habitación (spec-hotel-operacion-v1 §2.6): datos, historial
    de tarifas con la vigente hoy, reservas en cualquier estado, tareas y —solo
    para administrador— la auditoría cuyo recurso es la habitación."""
    hoy = hoy or date.today()
    fila = conexion.execute(
        f"SELECT {_COLUMNAS_HABITACION} FROM habitaciones h WHERE h.id = %s", (hoy, hoy, habitacion_id)
    ).fetchone()
    if fila is None:
        raise HabitacionInexistente("acceso denegado")
    ficha = _habitacion_a_dict(fila)
    vigente_id = conexion.execute(
        "SELECT t.id FROM tarifas t WHERE t.habitacion_id = %s AND t.fecha_desde <= %s AND t.fecha_hasta > %s "
        f"{ORDEN_VIGENCIA_TARIFA} LIMIT 1",
        (habitacion_id, hoy, hoy),
    ).fetchone()
    ficha["tarifas"] = [
        {
            "tarifa_id": t[0],
            "fecha_desde": t[1].isoformat(),
            "fecha_hasta": t[2].isoformat(),
            "tarifa_noche_clp": t[3],
            "registrada_en": t[4].isoformat(),
            "vigente_hoy": vigente_id is not None and t[0] == vigente_id[0],
        }
        for t in conexion.execute(
            "SELECT t.id, t.fecha_desde, t.fecha_hasta, t.tarifa_noche_clp, t.creado_en FROM tarifas t "
            f"WHERE t.habitacion_id = %s {ORDEN_VIGENCIA_TARIFA}",
            (habitacion_id,),
        ).fetchall()
    ]
    ficha["reservas"] = list(
        reversed(buscar_reservas(conexion, empresa_id, habitacion_id=habitacion_id, ver_documento=ver_documento))
    )
    ficha["tareas"] = [
        {
            "tarea_id": t[0],
            "tipo": t[1],
            "estado": t[2],
            "creada_en": t[3].isoformat(),
            "completada_en": t[4].isoformat() if t[4] else None,
        }
        for t in conexion.execute(
            "SELECT id, tipo, estado, creado_en, completada_en FROM tareas_operativas "
            "WHERE habitacion_id = %s ORDER BY creado_en DESC, id DESC",
            (habitacion_id,),
        ).fetchall()
    ]
    if ver_auditoria:
        ficha["auditoria"] = [
            {"actor": a[0], "accion": a[1], "resultado": a[2], "registrada_en": a[3].isoformat()}
            for a in conexion.execute(
                "SELECT actor, accion, resultado, creado_en FROM auditoria WHERE recurso = %s "
                "ORDER BY creado_en DESC, id DESC",
                (habitacion_id,),
            ).fetchall()
        ]
    return ficha


def buscar_reservas(
    conexion: psycopg.Connection,
    empresa_id: str,
    fecha: date | None = None,
    estado: str | None = None,
    texto: str | None = None,
    ver_documento: bool = False,
    desde: date | None = None,
    hasta: date | None = None,
    habitacion_id: str | None = None,
) -> list[dict]:
    """Búsqueda de reservas de la empresa (spec-api-v1): filtros opcionales con
    AND, orden por inicio, id. huesped_documento solo para ROLES_DOCUMENTO.
    `desde`/`hasta` (2026-11-03): la reserva toca el periodo [desde, hasta)."""
    consulta = (
        "SELECT id, habitacion_id, inicio, fin, huesped_nombre, estado, "
        "tarifa_noche_aceptada_clp, huesped_documento FROM reservas WHERE empresa_id = %s"
    )
    parametros: list = [empresa_id]
    if fecha is not None:
        consulta += " AND inicio <= %s AND fin > %s"
        parametros += [fecha, fecha]
    if desde is not None:
        consulta += " AND fin > %s"
        parametros.append(desde)
    if hasta is not None:
        consulta += " AND inicio < %s"
        parametros.append(hasta)
    if habitacion_id is not None:
        consulta += " AND habitacion_id = %s"
        parametros.append(habitacion_id)
    if estado is not None:
        consulta += " AND estado = %s"
        parametros.append(estado)
    if texto:
        patron = f"%{texto}%"
        consulta += " AND (id ILIKE %s OR huesped_nombre ILIKE %s OR huesped_documento ILIKE %s OR habitacion_id ILIKE %s)"
        parametros += [patron, patron, patron, patron]
    consulta += " ORDER BY inicio, id"
    filas = conexion.execute(consulta, parametros).fetchall()
    items = []
    for fila in filas:
        item = {
            "reserva_id": fila[0],
            "habitacion_id": fila[1],
            "inicio": fila[2].isoformat(),
            "fin": fila[3].isoformat(),
            "huesped_nombre": fila[4],
            "estado": fila[5],
            "tarifa_noche_aceptada_clp": fila[6],
            "noches": (fila[3] - fila[2]).days,
        }
        if ver_documento:
            item["huesped_documento"] = fila[7]
        items.append(item)
    return items


def crear_reserva(
    conexion: psycopg.Connection,
    empresa_id: str,
    habitacion_id: str,
    inicio: date,
    fin: date,
    huesped_nombre: str,
    huesped_documento: str | None,
    personas: int | None = None,
) -> dict:
    # El estado se lee tras el cerrojo: un retiro concurrente y esta reserva se
    # serializan sobre la fila (spec-hotel-operacion-v1 §2.7, misma regla que la oferta).
    habitacion = conexion.execute(
        "SELECT estado_operativo, mantenimiento, capacidad FROM habitaciones WHERE id = %s FOR UPDATE", (habitacion_id,)
    ).fetchone()
    if habitacion is not None and (habitacion[1] or habitacion[0] in ESTADOS_NO_VENDIBLES):
        raise HabitacionNoVendible(f"{habitacion_id} está fuera del cupo: no admite reservas nuevas")
    # #298 (DECISIÓN 2026-11-06): las personas se validan contra la capacidad
    # al confirmar, igual que la oferta las filtra.
    if personas is not None and habitacion is not None and habitacion[2] < personas:
        raise SinCupo(f"la unidad {habitacion_id} admite hasta {habitacion[2]} personas")
    # Cada noche necesita tarifa (§2.8) y cada noche se cobra con su tarifa
    # vigente (#305, DECISIÓN 2026-11-06; reemplaza D-TAR-02).
    descubierta = primera_noche_sin_tarifa(conexion, habitacion_id, inicio, fin)
    if descubierta is not None:
        raise SinTarifaVigente(f"sin tarifa vigente para {habitacion_id} la noche {descubierta}")
    tarifa, total = precio_noches(conexion, habitacion_id, inicio, fin)
    reserva_id = f"RSV-{uuid.uuid4().hex[:12]}"
    try:
        with conexion.transaction():  # savepoint: la violación no aborta la transacción externa
            conexion.execute(
                "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, "
                "tarifa_noche_aceptada_clp, personas) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (reserva_id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, tarifa, personas),
            )
            conexion.execute(
                "INSERT INTO cargos (id, reserva_id, concepto, monto_clp) VALUES (%s, %s, %s, %s)",
                (f"CRG-{uuid.uuid4().hex[:12]}", reserva_id, f"Alojamiento {(fin - inicio).days} noches", total),
            )
    except ExclusionViolation as error:
        raise SinCupo(f"sin cupo para {habitacion_id} en [{inicio}, {fin})") from error
    return {
        "reserva_id": reserva_id,
        "habitacion_id": habitacion_id,
        "inicio": inicio.isoformat(),
        "fin": fin.isoformat(),
        "estado": "confirmada",
        "tarifa_noche_aceptada_clp": tarifa,
        "total_clp": total,
        "personas": personas,
    }
