"""Oráculo congelado de la regla de precios ANTERIOR a la entrega 1A.

Copia literal de las funciones de `servicio/reservas.py` en `27f9ccf`
(tarifa_vigente, precio_noches, tarifas_por_noche, primera_noche_sin_tarifa,
_libre y oferta). Solo lo usa la prueba de regresión de precios para
comparar, sobre el mismo inventario, lo que cotizaba la plataforma antes de
la migración 0021 con lo que cotiza el resolvedor único después. No se
importa desde el servicio y no debe editarse.
"""
from datetime import date, datetime, timedelta

import psycopg

VIGENCIA_OFERTA = timedelta(minutes=15)
POLITICA_CANCELACION = (
    "cancelación gratuita hasta 48 horas antes de la llegada; "
    "después se carga la primera noche"
)
ESTADOS_NO_VENDIBLES = ("bloqueada", "fuera_de_servicio")
ORDEN_VIGENCIA_TARIFA = "ORDER BY t.fecha_desde DESC, t.creado_en DESC, t.id DESC"


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
    for habitacion_id, tipo, capacidad in unidades:
        if primera_noche_sin_tarifa(conexion, habitacion_id, inicio, fin) is not None or not _libre(
            conexion, habitacion_id, inicio, fin
        ):
            continue
        tarifa, total = precio_noches(conexion, habitacion_id, inicio, fin)
        items.append(
            {
                "habitacion_id": habitacion_id,
                "tipo": tipo,
                "capacidad": capacidad,
                "tarifa_noche_clp": tarifa,
                "total_clp": total,
                "politica_cancelacion": POLITICA_CANCELACION,
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
    return {
        "oferta": items,
        "emitida_en": ahora.isoformat(),
        "vigencia_minutos": VIGENCIA_OFERTA.total_seconds() // 60,
        "capacidad_maxima_habitacion": tope,
    }


# --- Siembra de tarifas fijas referenciales tal como en 27f9ccf -------------
# (inventario_documental.aplicar_tarifas_fijas_referenciales + reservas.
# insertar_tarifa). Agregada en la entrega 1A.2, cuando la siembra del
# servicio pasó a precio base del tipo: la prueba de regresión necesita
# reproducir los datos de producción anteriores a 0022.
VIGENCIA_FIJA_DESDE = date(2020, 1, 1)
VIGENCIA_FIJA_HASTA = date(2099, 12, 31)


def aplicar_tarifas_fijas_referenciales(conexion: psycopg.Connection, lote: dict) -> int:
    import uuid

    from servicio.inventario_documental import es_id_inventario_real, precio_fijo_referencial

    insertadas = 0
    for hab in lote.get("habitaciones") or []:
        habitacion_id = hab["habitacion_id"]
        if not es_id_inventario_real(habitacion_id):
            continue
        tarifa_doc = hab.get("tarifa_propuesta_por_tipo") or {}
        if not tarifa_doc.get("publicar_tarifa_activa"):
            continue
        precio = precio_fijo_referencial(hab.get("tipo_salman", ""))
        if precio is None:
            precio = int(tarifa_doc.get("monto_clp") or 0) or None
        if precio is None or precio <= 0:
            continue
        if conexion.execute("SELECT 1 FROM habitaciones WHERE id = %s", (habitacion_id,)).fetchone() is None:
            continue
        if conexion.execute(
            "SELECT 1 FROM tarifas WHERE habitacion_id = %s AND fecha_desde = %s AND fecha_hasta = %s "
            "AND tarifa_noche_clp = %s LIMIT 1",
            (habitacion_id, VIGENCIA_FIJA_DESDE, VIGENCIA_FIJA_HASTA, precio),
        ).fetchone() is not None:
            continue
        conexion.execute(
            "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
            "VALUES (%s, %s, %s, %s, %s)",
            (f"TAR-{uuid.uuid4().hex[:12]}", habitacion_id, VIGENCIA_FIJA_DESDE, VIGENCIA_FIJA_HASTA, precio),
        )
        insertadas += 1
    return insertadas
