"""Adaptador hotel ↔ SQL (ADP-2): PostgreSQL es almacén y proyección, no decide.

`recargar` lee las filas y llena el dominio; `persistir` escribe el estado que
dejó el dominio. Solo traduce nombres (una tabla por concepto, abajo); si el
check-in procede, si hay cupo o cuánto se penaliza lo decide
`ServicioHotelInventario`, nunca este módulo. Sin DELETE; los cargos son
append-only. Se ejecuta dentro de la transacción de la ruta (no hace commit).
"""
import sys
import threading
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

# El dominio vive fuera del paquete `servicio`: mismo arreglo de rutas que `aplicacion.py`, para que
# este módulo sea importable aunque otro (canal público, agente) se cargue primero.
_RAIZ = Path(__file__).resolve().parents[1]
for _ruta in (_RAIZ / "core" / "incremento1", _RAIZ / "verticales" / "hotel" / "incremento1"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

import psycopg
from psycopg.errors import ExclusionViolation

from . import imputacion

from hotel_inventario.servicio import (
    CargoNoReversible,
    CheckInIncompleto,
    CheckInNoPermitido,
    CheckOutNoPermitido,
    ESTADO_NO_VENDIBLE,
    ReasignacionNoPermitida,
    ReservaNoCancelable,
    SIN_CUPO,
    VIGENCIA_OFERTA,
)
from hotel_inventario.dominio import (
    Cargo,
    EstadoReserva,
    EstadoTarea,
    EstadoUnidad,
    Huesped,
    Liquidacion,
    Pago,
    Reserva,
    TareaOperativa,
    TipoCargo,
    Unidad,
)

# Proyección de nombres de reserva (dominio → fila) y su inversa.
_RESERVA_A_FILA = {
    EstadoReserva.CONFIRMADA: "confirmada",
    EstadoReserva.HOSPEDADA: "en_estadia",
    EstadoReserva.SALIDA: "finalizada",
    EstadoReserva.CANCELADA: "cancelada",
}
_RESERVA_DE_FILA = {fila: estado for estado, fila in _RESERVA_A_FILA.items()}

# Unidad: estados que viven en `estado_operativo` y estados que viven en `estado_preparacion`.
_OPERATIVO_DE_FILA = {
    "ocupada": EstadoUnidad.OCUPADA,
    "bloqueada": EstadoUnidad.BLOQUEADA,
    "fuera_de_servicio": EstadoUnidad.FUERA_DE_SERVICIO,
}
_PREPARACION_DE_FILA = {
    "limpia": EstadoUnidad.LIMPIA,
    "sucia": EstadoUnidad.SUCIA,
    "inspeccionada": EstadoUnidad.INSPECCIONADA,
}
_OPERATIVO_A_FILA = {estado: fila for fila, estado in _OPERATIVO_DE_FILA.items()}

# El dominio es un singleton en memoria: cada operación hotelera recarga, decide
# y persiste dentro de esta sección crítica, que la ruta mantiene hasta el commit.
EXCLUSIVO = threading.RLock()

# Candado de PostgreSQL por transacción: serializa las operaciones del hotel entre procesos (varias instancias),
# porque el dominio numera sus ids sobre lo que lee y dos procesos podrían numerar igual. Se libera solo al
# confirmar o deshacer la transacción; `EXCLUSIVO` cubre los hilos de un mismo proceso.
CLAVE_BLOQUEO = 77075051


def bloquear(conexion: psycopg.Connection) -> None:
    conexion.execute("SELECT pg_advisory_xact_lock(%s)", (CLAVE_BLOQUEO,))


# Hotel del proceso para los llamadores que no tienen la petición a mano (canal público, agente,
# evaluación): `crear_app` y la evaluación lo registran al construir la aplicación.
_REGISTRADO = None


def ahora():
    """Reloj del servidor en hora de Chile (America/Santiago, naive para el dominio) para
    las reglas que dependen de la hora (llegada 15:00, 48 h). Un solo punto para pruebas."""
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("America/Santiago")).replace(tzinfo=None)


def registrar(hotel) -> None:
    global _REGISTRADO
    _REGISTRADO = hotel


def asegurar_registrado(fabrica) -> None:
    """Registra `fabrica()` solo si el proceso aún no tiene hotel (p. ej. la evaluación sin app HTTP)."""
    if _REGISTRADO is None:
        registrar(fabrica())


def hotel_registrado():
    if _REGISTRADO is None:
        raise RuntimeError("no hay un hotel del dominio registrado: construir la aplicación primero")
    return _REGISTRADO


def _existe(conexion: psycopg.Connection, tabla: str, columna: str | None = None) -> bool:
    """¿Existe la tabla (o la columna) en el esquema migrado?"""
    if columna is None:
        return conexion.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{tabla}",)).fetchone()[0]
    return conexion.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' "
        "AND table_name = %s AND column_name = %s)",
        (tabla, columna),
    ).fetchone()[0]


def _estado_unidad(operativo: str, preparacion: str) -> EstadoUnidad:
    if operativo in _OPERATIVO_DE_FILA:
        return _OPERATIVO_DE_FILA[operativo]
    return _PREPARACION_DE_FILA.get(preparacion, EstadoUnidad.LIMPIA)


def recargar(conexion: psycopg.Connection, hotel, empresa_id: str, rango: tuple[date, date] | None = None,
             mantenimiento_en: tuple[date, date] | None = None) -> None:
    """Llena el dominio con las filas actuales (reemplaza su estado en memoria).

    `rango` [inicio, fin) es la ventana de la operación: el precio de cada noche sale del resolvedor
    único (`precios`, configuración en SQL) y el mantenimiento solo cuenta si solapa esa ventana
    (#349), o la que diga `mantenimiento_en`. Sin ninguna, el mantenimiento es el estado abierto/cerrado
    de la unidad."""
    from . import reservas as reservas_db  # evita el ciclo de importación
    from . import precios

    ventana = mantenimiento_en or rango
    if ventana is None:
        mantenimiento_sql, parametros = "h.mantenimiento", ()
    else:
        mantenimiento_sql = reservas_db.SQL_MANTENIMIENTO_SOLAPA.replace("mantenimiento", "h.mantenimiento")
        parametros = ventana
    unidades = tuple(
        Unidad(
            id=h_id,
            establecimiento_id=est,
            capacidad=capacidad,
            tarifa_noche_clp=precio or 0,
            estado=_estado_unidad(operativo, preparacion),
            mantenimiento=bool(mantenimiento),
        )
        for h_id, est, capacidad, operativo, preparacion, mantenimiento, precio in conexion.execute(
            "SELECT h.id, h.establecimiento_id, h.capacidad, h.estado_operativo, h.estado_preparacion, "
            f"{mantenimiento_sql}, COALESCE(h.precio_propio_clp, tp.precio_base_clp) "
            "FROM habitaciones h LEFT JOIN tipos_habitacion tp ON tp.id = h.tipo ORDER BY h.id",
            parametros,
        ).fetchall()
    )
    filas_reserva = conexion.execute(
        "SELECT id, habitacion_id, inicio, fin, huesped_nombre, huesped_documento, "
        "tarifa_noche_aceptada_clp, estado FROM reservas WHERE empresa_id = %s ORDER BY creado_en, id",
        (empresa_id,),
    ).fetchall()
    reservas = tuple(
        Reserva(rid, empresa_id, hab, inicio, fin, Huesped(nombre, documento, sintetico=False),
                _RESERVA_DE_FILA[estado])
        for rid, hab, inicio, fin, nombre, documento, _tarifa, estado in filas_reserva
    )
    tarifas_aceptadas = {fila[0]: fila[6] for fila in filas_reserva}
    cargos = tuple(
        Cargo(cid, rid, TipoCargo(tipo), concepto, monto, referencia)
        for cid, rid, tipo, concepto, monto, referencia in conexion.execute(
            "SELECT c.id, c.reserva_id, c.tipo, c.concepto, c.monto_clp, c.referencia "
            "FROM cargos c JOIN reservas r ON r.id = c.reserva_id WHERE r.empresa_id = %s "
            "ORDER BY c.creado_en, c.id",
            (empresa_id,),
        ).fetchall()
    )
    pagos = tuple(
        Pago(pid, rid, monto, clave)
        for pid, rid, monto, clave in conexion.execute(
            "SELECT p.id, p.reserva_id, "
            "CASE WHEN p.tipo = 'reverso' THEN -p.monto_clp ELSE p.monto_clp END, "
            "p.clave FROM pagos p "
            "JOIN reservas r ON r.id = p.reserva_id "
            # Fase 1 contable: un pago anulado (fila «reverso» que lo referencia) no existe para el dominio;
            # una devolución formal de saldo a favor (reverso sin referencia_pago_id) resta del pagado.
            "WHERE r.empresa_id = %s AND p.estado = 'confirmado' AND ("
            "  (p.tipo = 'pago' AND NOT EXISTS (SELECT 1 FROM pagos v WHERE v.referencia_pago_id = p.id AND v.tipo = 'reverso')) "
            "  OR (p.tipo = 'reverso' AND p.referencia_pago_id IS NULL)"
            ") ORDER BY p.creado_en, p.id",
            (empresa_id,),
        ).fetchall()
    )
    tareas = tuple(
        TareaOperativa(tid, empresa_id, hab, tipo, EstadoTarea(estado))
        for tid, hab, tipo, estado in conexion.execute(
            "SELECT id, habitacion_id, tipo, estado FROM tareas_operativas ORDER BY creado_en, id"
        ).fetchall()
    )
    # El dominio guarda una tarifa por día (fecha inclusive): una por noche con precio resuelto.
    tarifas_por_rango = ()
    if rango is not None and rango[1] > rango[0]:
        tarifas_por_rango = tuple(
            (hab, noche, noche, precio.precio_clp, "temporada")
            for (hab, noche), precio in precios.precios_del_rango(conexion, rango[0], rango[1]).items()
        )
    liquidaciones = tuple(
        Liquidacion(rid, total, pagado, saldo)
        for rid, total, pagado, saldo in conexion.execute(
            "SELECT l.reserva_id, l.total_clp, l.pagado_clp, l.saldo_clp FROM liquidaciones l "
            "JOIN reservas r ON r.id = l.reserva_id WHERE r.empresa_id = %s",
            (empresa_id,),
        ).fetchall()
    )
    hotel.recargar(
        unidades=unidades,
        reservas=reservas,
        cargos=cargos,
        pagos=pagos,
        tareas=tareas,
        tarifas_aceptadas=tarifas_aceptadas,
        tarifas_por_rango=tarifas_por_rango,
        liquidaciones=liquidaciones,
    )


def persistir(conexion: psycopg.Connection, hotel, empresa_id: str) -> None:
    """Escribe el estado del dominio. Upserts por id; cargos y pagos solo se insertan."""
    for u in hotel._unidades.values():
        # La unidad ya existe (el inventario lo crea la API y `recargar` la leyó): solo se proyectan
        # sus estados. El mantenimiento y el tipo no se tocan aquí (el primero depende del rango).
        if u.estado in _OPERATIVO_A_FILA:
            conexion.execute(
                "UPDATE habitaciones SET estado_operativo = %s WHERE id = %s", (_OPERATIVO_A_FILA[u.estado], u.id)
            )
        else:
            conexion.execute(
                "UPDATE habitaciones SET estado_operativo = 'disponible', estado_preparacion = %s WHERE id = %s",
                (u.estado.value, u.id),
            )
    for r in hotel._reservas.values():
        fila = _RESERVA_A_FILA.get(r.estado)
        if fila is None or r.empresa_id != empresa_id:
            continue  # pendiente/rechazada no tienen fila: no se proyectan
        conexion.execute(
            "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, "
            "huesped_documento, tarifa_noche_aceptada_clp, estado) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (id) DO UPDATE SET habitacion_id = EXCLUDED.habitacion_id, inicio = EXCLUDED.inicio, "
            "fin = EXCLUDED.fin, huesped_nombre = EXCLUDED.huesped_nombre, "
            "huesped_documento = COALESCE(EXCLUDED.huesped_documento, reservas.huesped_documento), "
            "tarifa_noche_aceptada_clp = EXCLUDED.tarifa_noche_aceptada_clp, estado = EXCLUDED.estado",
            (r.id, empresa_id, r.unidad_id, r.inicio, r.fin, r.huesped.nombre, r.huesped.documento,
             hotel._tarifa_de_reserva(r.id), fila),
        )
    for t in hotel._tareas.values():
        conexion.execute(
            "INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado, completada_en) "
            "VALUES (%s,%s,%s,%s, CASE WHEN %s = 'completada' THEN now() END) "
            "ON CONFLICT (id) DO UPDATE SET estado = EXCLUDED.estado, "
            "completada_en = COALESCE(tareas_operativas.completada_en, EXCLUDED.completada_en)",
            (t.id, t.unidad_id, t.tipo, t.estado.value, t.estado.value),
        )
    for c in hotel._cargos:
        conexion.execute(
            "INSERT INTO cargos (id, reserva_id, concepto, monto_clp, tipo, referencia) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
            (c.id, c.reserva_id, c.concepto, c.monto_clp, c.tipo.value, c.referencia),
        )
    for p in hotel._pagos:
        if p.monto_clp <= 0:
            continue  # devolución formal ya persistida en SQL con tipo='reverso' y monto_clp > 0
        conexion.execute(
            "INSERT INTO pagos (id, reserva_id, monto_clp, clave, modo) VALUES (%s,%s,%s,%s,'manual') "
            "ON CONFLICT (reserva_id, clave) DO NOTHING",
            (p.id, p.reserva_id, p.monto_clp, p.clave or p.id),
        )
    for liquidacion in hotel._liquidaciones.values():
        conexion.execute(
            "INSERT INTO liquidaciones (id, reserva_id, total_clp, pagado_clp, saldo_clp) VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (reserva_id) DO NOTHING",
            (f"LQ-{uuid.uuid4().hex[:12]}", liquidacion.reserva_id, liquidacion.total_cargos_clp,
             liquidacion.total_pagos_clp, liquidacion.saldo_clp),
        )


def candidatas(conexion: psycopg.Connection, hotel, empresa_id: str, inicio, fin, personas: int, ahora) -> list[dict]:
    """Unidades vendibles según `consultar_oferta` del dominio (ADP-4 AC-1): cupo, capacidad y estado
    los decide el dominio; el mantenimiento llega ya recortado al rango. Añade `tipo` y el total noche a
    noche (#305) con el precio que resuelve `precios` (configuración); una unidad con alguna noche sin
    precio no se ofrece (AC-4)."""
    from . import precios

    with EXCLUSIVO:  # lectura atómica del singleton: recargar y consultar sin que otro lo cambie
        recargar(conexion, hotel, empresa_id, (inicio, fin))
        ofertas = hotel.consultar_oferta(empresa_id, inicio, fin, personas, ahora)
        if not ofertas:
            return []
        ids = [o.unidad_id for o in ofertas]
        tipos = dict(conexion.execute("SELECT id, tipo FROM habitaciones WHERE id = ANY(%s)", (ids,)).fetchall())
        tabla = precios.cargar(conexion, inicio, fin, ids)
        items = []
        for o in ofertas:
            cotizacion = precios.cotizar_en(tabla, o.unidad_id, inicio, fin)
            if cotizacion.sin_tarifa is not None:
                continue
            items.append(
                {
                    "habitacion_id": o.unidad_id,
                    "tipo": tipos.get(o.unidad_id),
                    "capacidad": hotel._unidades[o.unidad_id].capacidad,
                    "tarifa_noche_clp": o.tarifa_noche_clp,
                    "total_clp": cotizacion.total,
                    "vigente_hasta": o.vigente_hasta.isoformat(),
                }
            )
        return items


def reservar(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    habitacion_id: str,
    inicio,
    fin,
    huesped_nombre: str,
    huesped_documento: str | None,
    personas: int | None = None,
    columnas: dict | None = None,
    noches=(),
    recargos=(),
) -> dict:
    """Confirma por `hotel.reservar` (ADP-4 AC-2). `confirmada=False` se traduce a la excepción de
    siempre con el motivo del dominio. No asienta el alojamiento: nace en la entrada (AC-3). Los
    recargos de la política sí se asientan como cargos de la cuenta, por `hotel.asentar_cargo`.
    `columnas` son datos que el dominio no modela (total aceptado, política, documento) y `noches` el
    precio congelado por noche: se guardan en la misma transacción."""
    from . import reservas as reservas_db  # evita el ciclo de importación

    # Cerrojo de fila: dos confirmaciones de la misma unidad se serializan y la
    # segunda recarga ya con la primera confirmada.
    conexion.execute("SELECT 1 FROM habitaciones WHERE id = %s FOR UPDATE", (habitacion_id,))
    recargar(conexion, hotel, empresa_id, (inicio, fin))
    unidad = hotel._unidades.get(habitacion_id)
    # Guarda de proyección sobre un dato que `reservar` no recibe: las personas del huésped.
    if personas is not None and unidad is not None and unidad.capacidad < personas:
        raise reservas_db.SinCupo(f"la unidad {habitacion_id} admite hasta {unidad.capacidad} personas")
    resultado = hotel.reservar(
        empresa_id, habitacion_id, inicio, fin, Huesped(huesped_nombre, huesped_documento, sintetico=False)
    )
    if not resultado.confirmada:
        if resultado.motivo == SIN_CUPO:
            raise reservas_db.SinCupo(f"sin cupo para {habitacion_id} en [{inicio}, {fin})")
        if resultado.motivo == ESTADO_NO_VENDIBLE:
            raise reservas_db.HabitacionNoVendible(f"{habitacion_id} está fuera del cupo: no admite reservas nuevas")
        raise reservas_db.SinTarifaVigente(f"{resultado.motivo}: {habitacion_id}")
    reserva = resultado.reserva
    for numero, recargo in enumerate(recargos, start=1):
        hotel.asentar_cargo(empresa_id, reserva.id, recargo["detalle"], recargo["monto_clp"], clave=f"recargo:{numero}")
    tarifa = hotel.tarifa_vigente(empresa_id, habitacion_id, inicio)
    try:
        with conexion.transaction():  # savepoint: la violación no aborta la transacción externa
            persistir(conexion, hotel, empresa_id)
            fijas = {"personas": personas, **(columnas or {})}
            conexion.execute(
                "UPDATE reservas SET " + ", ".join(f"{c} = %s" for c in fijas) + " WHERE id = %s",
                (*fijas.values(), reserva.id),
            )
            with conexion.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO reserva_noches (reserva_id, noche, precio_clp, origen) VALUES (%s, %s, %s, %s)",
                    [(reserva.id, noche, precio.precio_clp, precio.origen) for noche, precio in noches],
                )
    except ExclusionViolation as error:
        raise reservas_db.SinCupo(f"sin cupo para {habitacion_id} en [{inicio}, {fin})") from error
    return {"reserva_id": reserva.id, "tarifa_noche_aceptada_clp": tarifa}


def reasignar(conexion: psycopg.Connection, hotel, empresa_id: str, reserva_id: str, destino: str, motivo: str,
              actor: str) -> dict:
    """#361: mueve la reserva (confirmada o en estadía) a otra unidad con la tarifa pactada, por
    `hotel.reasignar`. El dominio decide si la unidad sirve (vendible, sin mantenimiento en el rango,
    libre, lista si hay estadía en curso); aquí solo se valida el texto del motivo y la capacidad contra
    las personas de la reserva (dato que el dominio no modela) y se proyecta el cambio y su historial."""
    from . import cobro  # evita el ciclo de importación

    reserva = cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)  # 403 y cerrojo de fila
    origen, estado = reserva[1], reserva[2]
    if estado not in cobro.ESTADOS_CON_CUENTA_ABIERTA:
        raise cobro.TransicionInvalida(f"la reserva está {estado}")
    motivo = (motivo or "").strip()
    if len(motivo) < 3:
        raise cobro.ReasignacionInvalida("indica el motivo del cambio de habitación")
    (personas, inicio, fin) = conexion.execute(
        "SELECT personas, inicio, fin FROM reservas WHERE id = %s", (reserva_id,)
    ).fetchone()
    # Cerrojo en orden estable para no cruzarse con otra reasignación inversa.
    for hid in sorted((origen, destino)):
        conexion.execute("SELECT 1 FROM habitaciones WHERE id = %s FOR UPDATE", (hid,))
    recargar(conexion, hotel, empresa_id, mantenimiento_en=(inicio, fin))
    unidad = hotel._unidades.get(destino)
    if unidad is not None and personas is not None and unidad.capacidad < personas:
        raise cobro.ReasignacionInvalida(f"la habitación {destino} admite hasta {unidad.capacidad} personas")
    try:
        hotel.reasignar(empresa_id, reserva_id, destino)
        with conexion.transaction():  # savepoint: la exclusión de la base decide la carrera
            persistir(conexion, hotel, empresa_id)
    except ReasignacionNoPermitida as error:
        raise cobro.ReasignacionInvalida(str(error)) from error
    except ExclusionViolation as error:
        raise cobro.ReasignacionInvalida(f"la habitación {destino} está ocupada en parte de esas fechas") from error
    reasignacion_id = f"REA-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO reasignaciones (id, reserva_id, desde_habitacion_id, hacia_habitacion_id, motivo, actor, estado_reserva) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (reasignacion_id, reserva_id, origen, destino, motivo, actor, estado),
    )
    return {"reasignacion_id": reasignacion_id, "reserva_id": reserva_id, "desde_habitacion_id": origen,
            "hacia_habitacion_id": destino, "estado": estado, "motivo": motivo}


def entrada(
    conexion: psycopg.Connection, hotel, empresa_id: str, reserva_id: str, documento: str | None, ahora,
    documento_tipo: str | None = None, habitacion_id: str | None = None, personas: int | None = None, actor: str = "sistema",
) -> dict:
    """Check-in por `hotel.check_in` (ADP-5): documento, llegada ≥ 15:00, mantenimiento y unidad lista
    los decide el dominio; los rechazos salen como `TransicionInvalida` (409). Asienta la primera noche
    (la asienta el dominio) y las restantes con el precio de cada noche (#305), para que la salida
    liquide la estadía completa. #360: si recepción elige otra unidad, se reasigna antes de entrar."""
    from . import cobro, huespedes as huespedes_db  # evita el ciclo de importación

    fila = cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)  # 403 y cerrojo de fila
    try:
        with conexion.transaction():  # savepoint: un 409 no deja reasignación ni documento parcial comprometidos
            if fila[2] == "confirmada" and habitacion_id and habitacion_id != fila[1]:
                reasignar(conexion, hotel, empresa_id, reserva_id, habitacion_id, "asignada en la entrada", actor)
            (guardado, inicio, fin, personas_actual, hab_actual) = conexion.execute(
                "SELECT huesped_documento, inicio, fin, personas, habitacion_id FROM reservas WHERE id = %s", (reserva_id,)
            ).fetchone()
            if personas is not None:
                cap_row = conexion.execute("SELECT capacidad FROM habitaciones WHERE id = %s", (hab_actual,)).fetchone()
                if cap_row is not None and cap_row[0] < personas:
                    raise cobro.TransicionInvalida(f"la habitación {hab_actual} admite hasta {cap_row[0]} personas")
                conexion.execute(
                    "UPDATE reservas SET personas = %s WHERE id = %s",
                    (personas, reserva_id),
                )
            if not guardado and documento and documento.strip():
                # D-ENT-01: la entrada captura el documento que la reserva aún no traía
                conexion.execute(
                    "UPDATE reservas SET huesped_documento = %s, huesped_documento_tipo = %s WHERE id = %s",
                    (documento.strip(), documento_tipo, reserva_id),
                )
                huespedes_db.sincronizar_documento_titular(
                    conexion, empresa_id, reserva_id, documento.strip(), documento_tipo,
                )
            huespedes_db.verificar_huespedes_para_entrada(conexion, reserva_id)
            hoy = ahora.date()
            recargar(conexion, hotel, empresa_id, (inicio, fin), mantenimiento_en=(hoy, hoy + timedelta(days=1)))
            noches_congeladas = dict(
                conexion.execute(
                    "SELECT noche, precio_clp FROM reserva_noches WHERE reserva_id = %s", (reserva_id,)
                ).fetchall()
            )
            reserva = hotel.check_in(empresa_id, reserva_id, ahora)
            noche = reserva.inicio + timedelta(days=1)
            while noche < reserva.fin:
                # Congelamiento de tarifa (#305): respeta el precio pactado en reserva_noches
                # incluso si cambió la tarifa vigente o se reasignó la habitación antes de entrar.
                precio_noche = noches_congeladas.get(noche)
                if precio_noche is None:
                    precio_noche = hotel.tarifa_vigente(empresa_id, reserva.unidad_id, noche)
                hotel.asentar_cargo(
                    empresa_id, reserva_id, "Noche", precio_noche,
                    clave=f"noche:{noche.isoformat()}",
                )
                noche += timedelta(days=1)
            persistir(conexion, hotel, empresa_id)
            imputacion.aplicar_anticipos(conexion, reserva_id, actor)  # los abonos previos se aplican noche a noche
    except CheckInIncompleto as error:
        raise cobro.TransicionInvalida("registra el documento del huésped para pasar la entrada") from error
    except CheckInNoPermitido as error:
        raise cobro.TransicionInvalida(str(error)) from error
    return {"reserva_id": reserva_id, "habitacion_id": reserva.unidad_id, "estado": "en_estadia", "personas": personas if personas is not None else personas_actual}


def cancelar(conexion: psycopg.Connection, hotel, empresa_id: str, reserva_id: str, ahora) -> dict:
    """Cancelación por `hotel.cancelar` (ADP-7): la política de 48 h / primera noche es del dominio.
    Un cargo asentado antes de llegar (recargos, consumo) lo revierte `reversar_cargo` del dominio,
    para que una reserva cancelada no conserve cargos huérfanos. La penalidad no se revierte."""
    from . import cobro  # evita el ciclo de importación

    estado = cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)[2]  # 403 y cerrojo
    recargar(conexion, hotel, empresa_id)
    previos = [c.id for c in hotel.cuenta(empresa_id, reserva_id)]
    try:
        resultado = hotel.cancelar(empresa_id, reserva_id, ahora)
    except ReservaNoCancelable as error:
        raise cobro.TransicionInvalida(f"la reserva está {estado}") from error
    reversos = []
    for cargo_id in previos:
        try:
            reverso = hotel.reversar_cargo(empresa_id, cargo_id)
        except CargoNoReversible:
            continue  # un reverso o un cargo ya reversado: lo dice el dominio
        reversos.append({"cargo_id": reverso.id, "referencia": cargo_id, "monto_clp": reverso.monto_clp})
    persistir(conexion, hotel, empresa_id)
    from . import productos as productos_db

    # Devuelve el stock de cualquier cargo de producto reversado al cancelar la reserva.
    for item in reversos:
        fila_prod = conexion.execute(
            "SELECT producto_id, cantidad FROM cargos WHERE id = %s", (item["referencia"],)
        ).fetchone()
        if fila_prod and fila_prod[0]:
            productos_db.devolver_por_reverso(
                conexion, fila_prod[0], fila_prod[1] or 1, "cancelacion", item["cargo_id"]
            )
    return {
        "reserva_id": reserva_id,
        "estado": "cancelada",
        "reversos": reversos,
        "penalidad_clp": resultado.cargo.monto_clp if resultado.cargo else 0,
        "reembolso": "no configurado",
    }


def cuenta(conexion: psycopg.Connection, hotel, empresa_id: str, reserva_id: str) -> tuple[int, int]:
    """(cargos netos, pagado) tal como los dice el dominio: la única fórmula de la cuenta."""
    recargar(conexion, hotel, empresa_id)
    neto = sum(
        c.monto_clp if c.tipo is TipoCargo.CARGO else -c.monto_clp for c in hotel.cuenta(empresa_id, reserva_id)
    )
    return neto, sum(p.monto_clp for p in hotel.pagos(empresa_id, reserva_id))


def registrar_pago(conexion: psycopg.Connection, hotel, empresa_id: str, reserva_id: str, monto_clp: int,
                   clave: str, efecto_nucleo_id: str) -> str:
    """Pago manual por `hotel.registrar_pago` (ADP-6 AC-1; el dominio deduplica por reserva y clave).
    La fila `pagos` es su proyección y conserva el efecto del núcleo. Devuelve el id de la fila."""
    recargar(conexion, hotel, empresa_id)
    hotel.registrar_pago(empresa_id, reserva_id, monto_clp, clave, estado="confirmado")
    persistir(conexion, hotel, empresa_id)
    conexion.execute(
        "UPDATE pagos SET efecto_nucleo_id = %s WHERE reserva_id = %s AND clave = %s",
        (efecto_nucleo_id, reserva_id, clave),
    )
    return conexion.execute(
        "SELECT id FROM pagos WHERE reserva_id = %s AND clave = %s", (reserva_id, clave)
    ).fetchone()[0]


def salida(conexion: psycopg.Connection, hotel, empresa_id: str, reserva_id: str, ahora) -> dict:
    """Check-out por `hotel.check_out` (ADP-6 AC-2/3): el saldo lo dice `hotel.saldo_clp`; distinto
    de cero es 409. La liquidación persistida es la del dominio."""
    from . import cobro  # evita el ciclo de importación

    estado = cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)[2]  # 403 y cerrojo
    if estado != "en_estadia":
        raise cobro.TransicionInvalida("check-out requiere una estadía en curso")
    recargar(conexion, hotel, empresa_id)
    saldo = hotel.saldo_clp(empresa_id, reserva_id)
    if saldo != 0:
        raise cobro.SaldoPendiente(f"la cuenta tiene saldo pendiente de {saldo} CLP")
    try:
        hotel.check_out(empresa_id, reserva_id, ahora)
    except CheckOutNoPermitido as error:
        raise cobro.TransicionInvalida("check-out requiere una estadía en curso") from error
    liquidacion = hotel.liquidacion(empresa_id, reserva_id)
    persistir(conexion, hotel, empresa_id)
    (liquidacion_id,) = conexion.execute(
        "SELECT id FROM liquidaciones WHERE reserva_id = %s", (reserva_id,)
    ).fetchone()
    return {
        "liquidacion_id": liquidacion_id,
        "reserva_id": reserva_id,
        "total_clp": liquidacion.total_cargos_clp,
        "pagado_clp": liquidacion.total_pagos_clp,
        "saldo_clp": liquidacion.saldo_clp,
        "estado": "liquidada",
    }


def asentar_cargo(conexion: psycopg.Connection, hotel, empresa_id: str, reserva_id: str, concepto: str | None,
                  monto_clp: int | None, producto_id: str | None = None, cantidad: int = 1,
                  actor: str = "sistema") -> dict:
    """Cargo por `hotel.asentar_cargo` (ADP-8 AC-1): solo con la cuenta abierta. #357: con `producto_id`
    el concepto y el precio salen del catálogo (copiados al cargo) y, si el producto controla stock,
    se descuenta en la misma transacción; el catálogo y el stock son SQL, la cuenta es del dominio."""
    from . import cobro  # evita el ciclo de importación
    from . import productos as productos_db

    estado = cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)[2]  # 403 y cerrojo
    recargar(conexion, hotel, empresa_id)
    precio_unitario = None
    if producto_id:
        producto = productos_db.obtener(conexion, producto_id)
        precio_unitario = producto["precio_clp"]
        monto_clp = precio_unitario * cantidad
        concepto = producto["nombre"] if cantidad == 1 else f"{producto['nombre']} × {cantidad}"
    else:
        cantidad = None
    try:
        cargo = hotel.asentar_cargo(empresa_id, reserva_id, concepto, monto_clp)
    except ReservaNoCancelable as error:
        raise cobro.TransicionInvalida(f"la reserva está {estado}") from error
    if producto_id:
        productos_db.descontar_para_cargo(conexion, producto_id, cantidad, actor, cargo.id)
    persistir(conexion, hotel, empresa_id)
    conexion.execute(
        "UPDATE cargos SET producto_id = %s, cantidad = %s, precio_unitario_clp = %s WHERE id = %s",
        (producto_id, cantidad, precio_unitario, cargo.id),
    )
    return {"cargo_id": cargo.id, "reserva_id": reserva_id, "concepto": concepto, "monto_clp": monto_clp,
            "tipo": "cargo", "producto_id": producto_id, "cantidad": cantidad,
            "precio_unitario_clp": precio_unitario}


def reversar_cargo(conexion: psycopg.Connection, hotel, empresa_id: str, reserva_id: str, cargo_id: str,
                   motivo: str, actor: str = "sistema") -> dict:
    """Reverso por `hotel.reversar_cargo` (#359): anular un cargo es asentar su reverso, nunca borrarlo.
    Una sola vez por cargo y solo con la cuenta abierta; el dominio dice si es reversible."""
    from . import cobro  # evita el ciclo de importación
    from . import productos as productos_db

    estado = cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)[2]  # 403 y cerrojo
    if estado not in cobro.ESTADOS_CON_CUENTA_ABIERTA:
        raise cobro.TransicionInvalida(f"la reserva está {estado}")
    motivo = (motivo or "").strip()
    if not motivo:
        raise cobro.CargoNoReversable("indica el motivo del reverso")
    recargar(conexion, hotel, empresa_id)
    original = next((c for c in hotel.cuenta(empresa_id, reserva_id) if c.id == cargo_id), None)
    if original is None:
        raise cobro.CargoNoReversable("ese cargo no existe en la reserva o ya es un reverso")
    try:
        reverso = hotel.reversar_cargo(empresa_id, cargo_id, motivo=motivo)
    except CargoNoReversible as error:
        raise cobro.CargoNoReversable(
            "ese cargo ya fue reversado" if "ya reversado" in str(error)
            else "ese cargo no existe en la reserva o ya es un reverso"
        ) from error
    persistir(conexion, hotel, empresa_id)
    producto_id, cantidad = conexion.execute(
        "SELECT producto_id, cantidad FROM cargos WHERE id = %s", (cargo_id,)
    ).fetchone()
    if producto_id:
        # #357: el reverso de un producto con stock lo devuelve.
        productos_db.devolver_por_reverso(conexion, producto_id, cantidad or 1, actor, reverso.id)
    neto = sum(
        c.monto_clp if c.tipo is TipoCargo.CARGO else -c.monto_clp for c in hotel.cuenta(empresa_id, reserva_id)
    )
    pagado = sum(p.monto_clp for p in hotel.pagos(empresa_id, reserva_id))
    return {"cargo_id": reverso.id, "reserva_id": reserva_id, "tipo": "reverso", "referencia": cargo_id,
            "concepto": reverso.concepto, "monto_clp": reverso.monto_clp, "saldo_clp": neto - pagado}


def completar_limpieza(conexion: psycopg.Connection, hotel, empresa_id: str, habitacion_id: str,
                       actor: str | None = None) -> dict:
    """Limpieza por `hotel.completar_tarea` (ADP-8 AC-2): sin tarea pendiente, 409. #362: la
    proyección guarda quién la hizo."""
    from . import cobro  # evita el ciclo de importación

    recargar(conexion, hotel, empresa_id)
    if habitacion_id not in hotel._unidades:
        raise cobro.RecursoAjenoOInexistente("acceso denegado")
    pendientes = [
        t for t in hotel.tareas(empresa_id)
        if t.unidad_id == habitacion_id and t.tipo == "limpieza" and t.estado is EstadoTarea.PENDIENTE
    ]
    if not pendientes:
        raise cobro.TransicionInvalida("no hay una limpieza pendiente en la habitación")
    for tarea in pendientes:
        hotel.completar_tarea(empresa_id, tarea.id)
    persistir(conexion, hotel, empresa_id)
    conexion.execute(
        "UPDATE tareas_operativas SET completada_por = %s WHERE id = ANY(%s)",
        (actor, [t.id for t in pendientes]),
    )
    (preparacion,) = conexion.execute(
        "SELECT estado_preparacion FROM habitaciones WHERE id = %s", (habitacion_id,)
    ).fetchone()
    return {"habitacion_id": habitacion_id, "estado_preparacion": preparacion, "tareas_completadas": len(pendientes)}


def fijar_mantenimiento(conexion: psycopg.Connection, hotel, empresa_id: str, habitacion_id: str,
                        abierto: bool, desde: date | None = None, hasta: date | None = None) -> dict:
    """Mantenimiento por `hotel.abrir_mantenimiento` / `cerrar_mantenimiento` (ADP-8 AC-3). Repetir el
    mismo estado no hace nada (el dominio abriría una tarea más). #349: el rango de fechas es dato de
    la proyección; solo saca la unidad del cupo en ese rango (sin fecha, el día en curso)."""
    from . import cobro  # evita el ciclo de importación

    recargar(conexion, hotel, empresa_id)
    unidad = hotel._unidades.get(habitacion_id)
    if unidad is None:
        raise cobro.RecursoAjenoOInexistente("acceso denegado")
    if abierto:
        desde = desde or date.today()
        conexion.execute(
            "UPDATE habitaciones SET mantenimiento_desde = %s, mantenimiento_hasta = %s WHERE id = %s",
            (desde, hasta, habitacion_id),
        )
    if abierto and not unidad.mantenimiento:
        hotel.abrir_mantenimiento(empresa_id, habitacion_id)
        conexion.execute("UPDATE habitaciones SET mantenimiento = true WHERE id = %s", (habitacion_id,))
    elif not abierto and unidad.mantenimiento:
        hotel.cerrar_mantenimiento(empresa_id, habitacion_id)
        conexion.execute(
            "UPDATE habitaciones SET mantenimiento = false, mantenimiento_desde = NULL, "
            "mantenimiento_hasta = NULL WHERE id = %s",
            (habitacion_id,),
        )
    persistir(conexion, hotel, empresa_id)
    return {"habitacion_id": habitacion_id, "mantenimiento": abierto,
            "desde": desde.isoformat() if abierto and desde else None,
            "hasta": hasta.isoformat() if abierto and hasta else None}
