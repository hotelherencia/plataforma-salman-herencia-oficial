"""Acceso a datos del hotel: habitaciones, precios (servicio/precios.py), oferta y reservas.

La base de datos es la fuente de verdad de las reservas: la confirmación es
transaccional y el constraint de exclusión `reservas_sin_solape` rechaza el
solape en (habitación, rango). La tarifa aceptada queda congelada en la
reserva: cambiar tarifas no altera precios ya aceptados (spec-api-v1).
"""
import uuid
from datetime import date, datetime, timedelta

import psycopg
from psycopg.errors import ExclusionViolation

from . import iva, politicas, precios

VIGENCIA_OFERTA = timedelta(minutes=15)
ESTABLECIMIENTO_SINTETICO = "EST-SINT-001"
ESTADOS_VALIDOS = ("confirmada", "en_estadia", "finalizada", "cancelada")
ESTADOS_QUE_OCUPAN_CUPO = ("confirmada", "en_estadia")
# HECHO DOCUMENTADO (dominio, ESTADOS_VENDIBLES): bloqueada y fuera de servicio
# no entran al cupo para ninguna fecha; el mantenimiento tampoco.
ESTADOS_NO_VENDIBLES = ("bloqueada", "fuera_de_servicio")
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


def en_inventario(conexion: psycopg.Connection, habitacion_id: str) -> bool:
    fila = conexion.execute("SELECT en_inventario FROM habitaciones WHERE id = %s", (habitacion_id,)).fetchone()
    return bool(fila and fila[0])


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


def _libre(conexion: psycopg.Connection, habitacion_id: str, inicio: date, fin: date) -> bool:
    fila = conexion.execute(
        "SELECT count(*) FROM reservas WHERE habitacion_id = %s AND estado IN ('confirmada', 'en_estadia') "
        "AND daterange(inicio, fin, '[)') && daterange(%s, %s, '[)')",
        (habitacion_id, inicio, fin),
    ).fetchone()
    return fila[0] == 0


def oferta(conexion: psycopg.Connection, inicio: date, fin: date, personas: int, ahora: datetime, empresa_id: str | None = None, extras: dict | None = None) -> dict:
    # HECHO DOCUMENTADO (dominio, ESTADOS_VENDIBLES): ocupada y sucia se venden
    # en otras fechas; mantenimiento, bloqueada y fuera_de_servicio quedan fuera.
    unidades = conexion.execute(
        "SELECT id, tipo, capacidad FROM habitaciones WHERE capacidad >= %s "
        "AND mantenimiento = false AND estado_operativo <> ALL(%s) "
        "ORDER BY id",
        (personas, list(ESTADOS_NO_VENDIBLES)),
    ).fetchall()
    ids = [u[0] for u in unidades]
    ocupadas = {
        f[0]
        for f in conexion.execute(
            "SELECT DISTINCT habitacion_id FROM reservas WHERE habitacion_id = ANY(%s) "
            "AND estado IN ('confirmada', 'en_estadia') "
            "AND daterange(inicio, fin, '[)') && daterange(%s, %s, '[)')",
            (ids, inicio, fin),
        ).fetchall()
    } if ids else set()
    tabla = precios.cargar(conexion, inicio, fin, ids) if ids else None
    items = []
    for habitacion_id, tipo, capacidad in unidades:
        if habitacion_id in ocupadas:
            continue
        cotizacion = precios.cotizar_en(tabla, habitacion_id, inicio, fin)
        if cotizacion.sin_tarifa is not None:
            continue
        items.append(
            {
                "habitacion_id": habitacion_id,
                "tipo": tipo,
                "capacidad": capacidad,
                "tarifa_noche_clp": cotizacion.tarifa_primera,
                "total_clp": cotizacion.total,
                "vigente_hasta": (ahora + VIGENCIA_OFERTA).isoformat(),
            }
        )
    # UX: con 4+ personas la oferta queda vacía; el front explica el tope por
    # habitación con este dato (no lo inventa).
    tope = conexion.execute(
        "SELECT max(capacidad) FROM habitaciones WHERE mantenimiento = false "
        "AND estado_operativo <> ALL(%s)",
        (list(ESTADOS_NO_VENDIBLES),),
    ).fetchone()[0]
    cuerpo_politica = politicas.de(conexion, empresa_id)["cuerpo"] if empresa_id else politicas.inicial()
    tasa = iva.tasa(conexion)
    noches = (fin - inicio).days
    items = [politicas.enriquecer_item(item, cuerpo_politica, extras, tasa, noches) for item in items]
    return {
        "oferta": items,
        "emitida_en": ahora.isoformat(),
        "vigencia_minutos": VIGENCIA_OFERTA.total_seconds() // 60,
        "capacidad_maxima_habitacion": tope,
        "texto_cancelacion": politicas.texto_cancelacion(cuerpo_politica),
        "cancelacion_confirmacion": (cuerpo_politica.get("cancelacion") or {}).get("confirmacion"),
    }


_COLUMNAS_HABITACION = (
    "h.id, h.tipo, h.capacidad, h.estado_operativo, h.estado_preparacion, h.mantenimiento, "
    # Columna 6: precio por defecto de la unidad (propio, si no base del tipo).
    "COALESCE(h.precio_propio_clp, "
    "(SELECT th.precio_base_clp FROM tipos_habitacion th WHERE th.id = h.tipo), 0), "
    "(SELECT COUNT(*) FROM tareas_operativas ta WHERE ta.habitacion_id = h.id AND ta.estado = 'pendiente'), "
    "EXISTS(SELECT 1 FROM tareas_operativas ta WHERE ta.habitacion_id = h.id "
    "AND ta.estado = 'pendiente' AND ta.tipo = 'limpieza'), "
    # Columna 9: el precio vigente hoy lo completa el resolvedor único
    # (precios.py) en `_completar_precio_hoy`; aquí queda el hueco posicional.
    "NULL::integer, "
    "h.motivo_fuera_de_servicio, h.fuera_de_servicio_desde, h.creado_en, "
    "h.en_inventario, h.precio_propio_clp, "
    "(SELECT th.nombre FROM tipos_habitacion th WHERE th.id = h.tipo), "
    "(SELECT th.precio_base_clp FROM tipos_habitacion th WHERE th.id = h.tipo)"
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
        "en_inventario": f[13],
        "precio_propio_clp": f[14],
        "tipo_nombre": f[15],
        "precio_base_tipo_clp": f[16],
    }


def _completar_precio_hoy(conexion: psycopg.Connection, habitaciones: list[dict], hoy: date) -> list[dict]:
    """Precio vigente hoy y su origen, con el mismo resolvedor de la oferta."""
    if not habitaciones:
        return habitaciones
    tabla = precios.cargar(conexion, hoy, hoy + timedelta(days=1), [h["habitacion_id"] for h in habitaciones])
    for h in habitaciones:
        precio = tabla.precio(h["habitacion_id"], hoy)
        h["tarifa_vigente_hoy_clp"] = precio.precio_clp if precio else None
        h["origen_precio_hoy"] = precio.origen if precio else None
        # Referencia (`tarifa_noche_clp`): el precio de hoy; si hoy no se vende,
        # el precio por defecto de la unidad (propio o base del tipo).
        if precio:
            h["tarifa_noche_clp"] = precio.precio_clp
    return habitaciones


def listar_habitaciones(conexion: psycopg.Connection, hoy: date | None = None) -> list[dict]:
    """Inventario operativo de las unidades (GET /hotel/habitaciones,
    spec-api-v1 «Operación de la habitación»): estado operativo, preparación,
    mantenimiento y tareas pendientes, con la última tarifa configurada como
    referencia (`tarifa_noche_clp`) y la vigente hoy. Solo lectura."""
    hoy = hoy or date.today()
    filas = conexion.execute(
        f"SELECT {_COLUMNAS_HABITACION} FROM habitaciones h ORDER BY h.id"
    ).fetchall()
    return _completar_precio_hoy(conexion, [_habitacion_a_dict(f) for f in filas], hoy)


def excepciones_de_habitacion(
    conexion: psycopg.Connection, habitacion_id: str, hoy: date, aplicada_hoy: str | None = None
) -> list[dict]:
    """Excepciones por fecha activas que alcanzan a la habitación (las suyas y
    las de su tipo) y que aún no terminan. `aplicada_hoy` marca la que fija
    el precio de hoy (la ganadora según precios.py)."""
    return [
        {
            "excepcion_id": e[0],
            "alcance": "habitacion" if e[1] else "tipo",
            "fecha_desde": e[2].isoformat(),
            "fecha_hasta": e[3].isoformat(),
            "precio_clp": e[4],
            "motivo": e[5],
            "aplicada_hoy": e[0] == aplicada_hoy,
        }
        for e in conexion.execute(
            "SELECT e.id, e.habitacion_id, e.fecha_desde, e.fecha_hasta, e.precio_clp, e.motivo "
            "FROM excepciones_precio e JOIN habitaciones h ON h.id = %s "
            "WHERE e.activa AND e.fecha_hasta > %s AND (e.habitacion_id = h.id OR e.tipo_id = h.tipo) "
            "ORDER BY (e.habitacion_id IS NULL), e.fecha_desde, e.creado_en, e.id",
            (habitacion_id, hoy),
        ).fetchall()
    ]


def ficha_habitacion(
    conexion: psycopg.Connection,
    habitacion_id: str,
    empresa_id: str,
    ver_documento: bool,
    ver_auditoria: bool,
    hoy: date | None = None,
) -> dict:
    """Ficha de la habitación (spec-hotel-operacion-v1 §2.6): datos, precio de
    hoy y su origen, excepciones por fecha que la alcanzan, tarifas heredadas
    archivadas por la migración 0022 (solo lectura), reservas en cualquier estado, tareas y —solo
    para administrador— la auditoría cuyo recurso es la habitación."""
    hoy = hoy or date.today()
    fila = conexion.execute(
        f"SELECT {_COLUMNAS_HABITACION} FROM habitaciones h WHERE h.id = %s", (habitacion_id,)
    ).fetchone()
    if fila is None:
        raise HabitacionInexistente("acceso denegado")
    ficha = _completar_precio_hoy(conexion, [_habitacion_a_dict(fila)], hoy)[0]
    origen = ficha.get("origen_precio_hoy") or ""
    ficha["excepciones"] = excepciones_de_habitacion(
        conexion, habitacion_id, hoy, origen.split(":", 1)[1] if origen.startswith("excepcion_") else None
    )
    ficha["tarifas_archivadas"] = [
        {
            "tarifa_id": t[0],
            "fecha_desde": t[1].isoformat(),
            "fecha_hasta": t[2].isoformat(),
            "tarifa_noche_clp": t[3],
            "registrada_en": t[4].isoformat(),
            "archivada_en": t[5].isoformat() if t[5] else None,
        }
        for t in conexion.execute(
            "SELECT t.id, t.fecha_desde, t.fecha_hasta, t.tarifa_noche_clp, t.creado_en, t.archivada_en "
            "FROM tarifas t WHERE t.habitacion_id = %s "
            "ORDER BY t.fecha_desde DESC, t.creado_en DESC, t.id DESC",
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
    extras: dict | None = None,
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
    cotizacion = precios.cotizar(conexion, habitacion_id, inicio, fin)
    if cotizacion.sin_tarifa is not None:
        raise SinTarifaVigente(f"sin tarifa vigente para {habitacion_id} la noche {cotizacion.sin_tarifa}")
    cuerpo_politica = politicas.de(conexion, empresa_id)["cuerpo"]
    item = politicas.enriquecer_item(
        {"habitacion_id": habitacion_id, "tarifa_noche_clp": cotizacion.tarifa_primera, "total_clp": cotizacion.total},
        cuerpo_politica, extras, iva.tasa(conexion), (fin - inicio).days,
    )
    if not item.get("reservable", True):
        raise SinTarifaVigente(
            f"la estadía no cumple el mínimo de {item['minimo_noches']} noches de la política del hotel"
        )
    tarifa, total = cotizacion.tarifa_primera, item["total_clp"]
    snapshot = politicas.snapshot_para_reserva(cuerpo_politica, item)
    reserva_id = f"RSV-{uuid.uuid4().hex[:12]}"
    try:
        with conexion.transaction():  # savepoint: la violación no aborta la transacción externa
            conexion.execute(
                "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, "
                "tarifa_noche_aceptada_clp, personas, total_aceptado_clp, politica_snapshot, recargos) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (reserva_id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, tarifa,
                 personas, total, psycopg.types.json.Json(snapshot),
                 psycopg.types.json.Json(item.get("recargos") or [])),
            )
            # Entrega 1A: precio congelado noche a noche, con su origen.
            with conexion.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO reserva_noches (reserva_id, noche, precio_clp, origen) VALUES (%s, %s, %s, %s)",
                    [(reserva_id, noche, p.precio_clp, p.origen) for noche, p in cotizacion.noches],
                )
            conexion.execute(
                "INSERT INTO cargos (id, reserva_id, concepto, monto_clp) VALUES (%s, %s, %s, %s)",
                (f"CRG-{uuid.uuid4().hex[:12]}", reserva_id, f"Alojamiento {(fin - inicio).days} noches",
                 item["subtotal_noches_clp"]),
            )
            for recargo in item.get("recargos") or []:
                conexion.execute(
                    "INSERT INTO cargos (id, reserva_id, concepto, monto_clp) VALUES (%s, %s, %s, %s)",
                    (f"CRG-{uuid.uuid4().hex[:12]}", reserva_id, recargo["detalle"], recargo["monto_clp"]),
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
        "subtotal_noches_clp": item["subtotal_noches_clp"],
        "recargos": item.get("recargos") or [],
        "desglose": item.get("desglose"),
        "politica_cancelacion": snapshot["texto_cancelacion"],
        "personas": personas,
    }


def noches_de_reserva(conexion: psycopg.Connection, reserva_id: str) -> list[dict]:
    """Precio congelado por noche (vacío para reservas anteriores a la 1A)."""
    return [
        {"noche": f[0].isoformat(), "precio_clp": f[1], "origen": f[2]}
        for f in conexion.execute(
            "SELECT noche, precio_clp, origen FROM reserva_noches WHERE reserva_id = %s ORDER BY noche",
            (reserva_id,),
        ).fetchall()
    ]
