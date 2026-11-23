"""Reservas de grupo: titular con varias habitaciones (PR B / RES-007).

Agrupa dos o más reservas individuales bajo una cabecera `reservas_grupo`
conservando intacta la invariante `1 reserva = 1 habitación` en
`ServicioHotelInventario`, `cargos`, `pagos` e `imputaciones_pago`.

Reglas clave:
- Creación atómica: si alguna habitación no tiene cupo, tarifa o capacidad,
  el savepoint revierte toda la operación (sin grupo ni habitaciones huérfanas).
- `titular_aloja`: indica si el titular duerme en esa habitación. Si es `false`
  (p. ej. habitación contigua para niños o acompañantes), el titular sigue como
  responsable en `reservas`, pero NO se inserta automáticamente en
  `reserva_huespedes`, exigiendo registrar a los ocupantes reales antes de la
  Llegada.
- Llegada en lote (`entrada_grupo`): atómica; exige huéspedes completos en
  cada habitación del lote. Si falla cualquiera, revierte todo el lote.
- Auditoría sin PII (sin nombres ni documentos).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

import psycopg

from . import clientes, cobro, hotel_sql, huespedes as huespedes_db, reservas as reservas_db, roles, seguridad

ROLES_GRUPOS = roles.con_admin_hotel("recepcion")


class GrupoConflicto(Exception):
    """409: conflicto operativo en grupo de reservas."""


class GrupoInvalido(ValueError):
    """422: datos inválidos para crear o modificar un grupo."""


def _grupo_de_la_empresa(conexion: psycopg.Connection, grupo_id: str, empresa_id: str, bloqueo: bool = False) -> tuple:
    sql = (
        "SELECT id, empresa_id, huesped_titular_id, titular_nombre, titular_documento_tipo, "
        "titular_documento, canal, notas, creado_por, creado_en "
        "FROM reservas_grupo WHERE id = %s"
    )
    if bloqueo:
        sql += " FOR UPDATE"
    fila = conexion.execute(sql, (grupo_id,)).fetchone()
    if fila is None or fila[1] != empresa_id:
        raise seguridad.ErrorPermiso("acceso denegado")
    return fila


def _asegurar_huesped_titular(
    conexion: psycopg.Connection,
    empresa_id: str,
    nombre: str,
    documento: str | None,
    documento_tipo: str | None,
) -> str:
    if documento and documento_tipo:
        existente = conexion.execute(
            "SELECT id FROM huespedes WHERE empresa_id = %s AND documento_tipo = %s AND documento = %s",
            (empresa_id, documento_tipo, documento),
        ).fetchone()
        if existente:
            return existente[0]
    huesped_id = f"HSP-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO huespedes (id, empresa_id, nombre, documento_tipo, documento) "
        "VALUES (%s, %s, %s, %s, %s)",
        (huesped_id, empresa_id, nombre, documento_tipo, documento),
    )
    return huesped_id


def _extras_habitacion(hab: dict) -> dict | None:
    extras = {}
    if hab.get("hora_llegada"):
        extras["hora_llegada"] = hab["hora_llegada"]
    if hab.get("hora_salida"):
        extras["hora_salida"] = hab["hora_salida"]
    if hab.get("cama_adicional"):
        extras["cama_adicional"] = True
    if hab.get("ninos") and hab["ninos"] > 0:
        extras["ninos"] = hab["ninos"]
    if hab.get("mascotas"):
        extras["mascotas"] = True
    return extras or None


def _crear_reserva_de_grupo(
    conexion: psycopg.Connection,
    empresa_id: str,
    grupo_id: str,
    titular_nombre: str,
    titular_documento: str | None,
    titular_documento_tipo: str | None,
    canal: str,
    hab: dict,
    actor: str,
) -> dict:
    inicio: date = hab["inicio"]
    fin: date = hab["fin"]
    if fin <= inicio:
        raise GrupoInvalido("la fecha de Salida debe ser posterior a la Llegada")
    adultos = int(hab.get("adultos", 1))
    ninos = int(hab.get("ninos", 0))
    if adultos < 1 or ninos < 0:
        raise GrupoInvalido("indica al menos 1 adulto y niños >= 0 por habitación")
    personas = adultos + ninos
    titular_aloja = bool(hab.get("titular_aloja", True))
    creada = reservas_db.crear_reserva(
        conexion,
        empresa_id=empresa_id,
        habitacion_id=hab["habitacion_id"],
        inicio=inicio,
        fin=fin,
        huesped_nombre=titular_nombre,
        huesped_documento=titular_documento,
        huesped_documento_tipo=titular_documento_tipo,
        personas=personas,
        canal=canal,
        extras=_extras_habitacion(hab),
        grupo_id=grupo_id,
        titular_aloja=titular_aloja,
        adultos=adultos,
        ninos_ocupacion=ninos,
    )
    reserva_id = creada["reserva_id"]
    for huesped_extra in hab.get("huespedes") or []:
        datos_h = dict(huesped_extra)
        if not titular_aloja and not datos_h.get("rol"):
            datos_h["rol"] = "acompanante"
        huespedes_db.agregar_huesped(conexion, empresa_id, reserva_id, datos_h, actor)
    return creada


def crear_grupo(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    titular_nombre: str,
    titular_documento: str | None,
    titular_documento_tipo: str | None,
    habitaciones: list[dict],
    canal: str = "recepcion",
    notas: str | None = None,
    actor: str = "sistema",
) -> dict:
    """Crea una cabecera de grupo y todas sus habitaciones en una sola transacción atómica.

    Si falla cualquier habitación (sin cupo, sin tarifa, excede capacidad, solape),
    el savepoint revierte la cabecera y todas las habitaciones previas.
    """
    if not habitaciones:
        raise GrupoInvalido("indica al menos una habitación para crear el grupo")
    nombre = " ".join((titular_nombre or "").split())[:200]
    if not nombre:
        raise GrupoInvalido("el nombre del titular es obligatorio")
    canal_norm = canal if canal in reservas_db.CANALES_RESERVA else "recepcion"
    notas_limpias = " ".join(notas.split())[:500] if notas and notas.strip() else None

    if titular_documento and titular_documento_tipo == "rut":
        clientes.exigir_nombre_coherente(conexion, clientes.rut_clave(titular_documento), nombre)

    grupo_id = f"GRP-{uuid.uuid4().hex[:12]}"
    try:
        with conexion.transaction():
            titular_huesped_id = _asegurar_huesped_titular(
                conexion, empresa_id, nombre, titular_documento, titular_documento_tipo,
            )
            conexion.execute(
                "INSERT INTO reservas_grupo "
                "(id, empresa_id, huesped_titular_id, titular_nombre, titular_documento_tipo, "
                "titular_documento, canal, notas, creado_por) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    grupo_id, empresa_id, titular_huesped_id, nombre,
                    titular_documento_tipo, titular_documento, canal_norm, notas_limpias, actor,
                ),
            )
            for hab in habitaciones:
                _crear_reserva_de_grupo(
                    conexion, empresa_id, grupo_id, nombre,
                    titular_documento, titular_documento_tipo, canal_norm, hab, actor,
                )
            seguridad.auditar(conexion, actor, "grupo_alta", grupo_id, f"habitaciones={len(habitaciones)}")
    except (
        reservas_db.SinCupo,
        reservas_db.SinTarifaVigente,
        reservas_db.HabitacionNoVendible,
        clientes.ClienteConflicto,
        huespedes_db.HuespedConflicto,
        huespedes_db.OcupacionInvalida,
    ) as error:
        raise GrupoConflicto(str(error)) from error
    except huespedes_db.HuespedInvalido as error:
        raise GrupoInvalido(str(error)) from error

    return obtener_grupo(conexion, hotel, empresa_id, grupo_id, ver_documento=True)


def agregar_reserva_a_grupo(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    grupo_id: str,
    datos: dict,
    actor: str = "sistema",
) -> dict:
    """Agrega una nueva habitación o vincula una reserva existente al grupo (atómico)."""
    fila_g = _grupo_de_la_empresa(conexion, grupo_id, empresa_id, bloqueo=True)
    titular_nombre, doc_tipo, doc, canal = fila_g[3], fila_g[4], fila_g[5], fila_g[6]

    try:
        with conexion.transaction():
            reserva_existente_id = datos.get("reserva_id")
            if reserva_existente_id:
                fila_r = cobro._reserva_de_la_empresa(conexion, reserva_existente_id, empresa_id, bloqueo=True)
                if fila_r[2] not in cobro.ESTADOS_CON_CUENTA_ABIERTA:
                    raise GrupoConflicto(f"la reserva {reserva_existente_id} está {fila_r[2]} y no puede asociarse")
                grupo_actual = conexion.execute(
                    "SELECT grupo_id FROM reservas WHERE id = %s", (reserva_existente_id,),
                ).fetchone()[0]
                if grupo_actual and grupo_actual != grupo_id:
                    raise GrupoConflicto(f"la reserva {reserva_existente_id} ya pertenece al grupo {grupo_actual}")
                titular_aloja = datos.get("titular_aloja")
                if titular_aloja is None:
                    conexion.execute(
                        "UPDATE reservas SET grupo_id = %s WHERE id = %s",
                        (grupo_id, reserva_existente_id),
                    )
                else:
                    conexion.execute(
                        "UPDATE reservas SET grupo_id = %s, titular_aloja = %s WHERE id = %s",
                        (grupo_id, bool(titular_aloja), reserva_existente_id),
                    )
                reserva_id = reserva_existente_id
            else:
                creada = _crear_reserva_de_grupo(
                    conexion, empresa_id, grupo_id, titular_nombre, doc, doc_tipo, canal, datos, actor,
                )
                reserva_id = creada["reserva_id"]
            seguridad.auditar(conexion, actor, "grupo_agregar_reserva", grupo_id, f"reserva={reserva_id}")
    except (
        reservas_db.SinCupo,
        reservas_db.SinTarifaVigente,
        reservas_db.HabitacionNoVendible,
        clientes.ClienteConflicto,
        huespedes_db.HuespedConflicto,
        huespedes_db.OcupacionInvalida,
    ) as error:
        raise GrupoConflicto(str(error)) from error
    except huespedes_db.HuespedInvalido as error:
        raise GrupoInvalido(str(error)) from error

    grupo = obtener_grupo(conexion, hotel, empresa_id, grupo_id, ver_documento=True)
    return {"reserva_id": reserva_id, "grupo": grupo}


def obtener_grupo(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    grupo_id: str,
    ver_documento: bool,
) -> dict:
    """Devuelve la cabecera del grupo, sus habitaciones y totales consolidados sin duplicación."""
    g = _grupo_de_la_empresa(conexion, grupo_id, empresa_id)
    filas = conexion.execute(
        "SELECT r.id, r.habitacion_id, h.tipo, h.capacidad, r.inicio, r.fin, r.estado, "
        "r.tarifa_noche_aceptada_clp, r.total_aceptado_clp, r.personas, r.adultos, r.ninos, "
        "r.titular_aloja, "
        "(SELECT COUNT(*) FROM reserva_huespedes rh WHERE rh.reserva_id = r.id) "
        "FROM reservas r JOIN habitaciones h ON h.id = r.habitacion_id "
        "WHERE r.empresa_id = %s AND r.grupo_id = %s "
        "ORDER BY r.inicio, r.habitacion_id, r.id",
        (empresa_id, grupo_id),
    ).fetchall()

    reservas_lista = []
    total_aceptado = 0
    total_cargos = 0
    total_pagado = 0
    estados: dict[str, int] = {}

    for f in filas:
        rid = f[0]
        neto, pagado = hotel_sql.cuenta(conexion, hotel, empresa_id, rid)
        saldo = neto - pagado
        adultos = f[10] if f[10] is not None else (f[9] or 1)
        ninos = f[11] if f[11] is not None else 0
        esperado = adultos + ninos
        registrados = int(f[13] or 0)
        faltantes = max(0, esperado - registrados)
        estado = f[6]
        estados[estado] = estados.get(estado, 0) + 1
        if estado != "cancelada":
            total_aceptado += int(f[8] or 0)
        total_cargos += neto
        total_pagado += pagado
        reservas_lista.append({
            "reserva_id": rid,
            "habitacion_id": f[1],
            "tipo_habitacion": f[2],
            "capacidad_habitacion": f[3],
            "inicio": f[4].isoformat(),
            "fin": f[5].isoformat(),
            "noches": (f[5] - f[4]).days,
            "estado": estado,
            "tarifa_noche_aceptada_clp": f[7],
            "total_aceptado_clp": f[8],
            "personas": f[9] or esperado,
            "adultos": adultos,
            "ninos": ninos,
            "titular_aloja": bool(f[12]),
            "huespedes": {
                "total_esperado": esperado,
                "registrados": registrados,
                "faltantes": faltantes,
                "completo": faltantes == 0,
            },
            "cuenta": {
                "cargos_netos_clp": neto,
                "pagado_clp": pagado,
                "saldo_clp": saldo,
            },
        })

    resultado = {
        "grupo_id": g[0],
        "titular_nombre": g[3],
        "titular_documento_tipo": g[4],
        "canal": g[6],
        "notas": g[7],
        "creado_por": g[8],
        "creado_en": g[9].isoformat(),
        "reservas": reservas_lista,
        "resumen": {
            "total_habitaciones": len(reservas_lista),
            "total_aceptado_clp": total_aceptado,
            "cargos_netos_clp": total_cargos,
            "pagado_clp": total_pagado,
            "saldo_clp": total_cargos - total_pagado,
            "estados": estados,
            "huespedes_completos": all(r["huespedes"]["completo"] for r in reservas_lista if r["estado"] == "confirmada"),
        },
    }
    if ver_documento:
        resultado["titular_documento"] = g[5]
    return resultado


def entrada_grupo(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    grupo_id: str,
    ahora: datetime,
    actor: str = "sistema",
    documento: str | None = None,
    documento_tipo: str | None = None,
    reserva_ids: list[str] | None = None,
) -> dict:
    """Ejecuta la Llegada en lote de las habitaciones confirmadas del grupo (atómica).

    Valida huéspedes completos de cada habitación antes de confirmar; si cualquier
    habitación falla (faltan huéspedes, sucia, mantenimiento, hora de llegada o
    documento), el savepoint revierte todo el lote.
    """
    _grupo_de_la_empresa(conexion, grupo_id, empresa_id, bloqueo=True)
    filas = conexion.execute(
        "SELECT id, habitacion_id, estado FROM reservas "
        "WHERE empresa_id = %s AND grupo_id = %s ORDER BY habitacion_id, id FOR UPDATE",
        (empresa_id, grupo_id),
    ).fetchall()
    por_id = {f[0]: f for f in filas}

    if reserva_ids:
        objetivos = []
        for rid in reserva_ids:
            if rid not in por_id:
                raise GrupoConflicto(f"la reserva {rid} no pertenece al grupo {grupo_id}")
            objetivos.append(por_id[rid])
    else:
        objetivos = [f for f in filas if f[2] == "confirmada"]

    if not objetivos:
        raise GrupoConflicto("no hay reservas confirmadas pendientes de Llegada en este grupo")

    procesadas = []
    try:
        with conexion.transaction():
            # Pre-validación de huéspedes completos en todas las habitaciones del lote
            # para devolver un diagnóstico claro antes de mutar cualquier estado.
            incompletas = []
            for rid, hab_id, estado in objetivos:
                if estado != "confirmada":
                    raise GrupoConflicto(f"{hab_id} ({rid}): la reserva está {estado}, no confirmada")
                try:
                    huespedes_db.verificar_huespedes_para_entrada(conexion, rid)
                except cobro.TransicionInvalida as err:
                    incompletas.append(f"{hab_id} ({rid}): {err}")
            if incompletas:
                raise GrupoConflicto("Llegada del grupo bloqueada — " + " | ".join(incompletas))

            if documento and documento.strip():
                conexion.execute(
                    "UPDATE reservas_grupo SET titular_documento = COALESCE(titular_documento, %s), "
                    "titular_documento_tipo = COALESCE(titular_documento_tipo, %s) WHERE id = %s",
                    (documento.strip(), documento_tipo, grupo_id),
                )

            for rid, hab_id, _estado in objetivos:
                try:
                    res = hotel_sql.entrada(
                        conexion, hotel, empresa_id, rid,
                        documento=documento, ahora=ahora,
                        documento_tipo=documento_tipo, actor=actor,
                    )
                except (cobro.HabitacionNoLista, cobro.TransicionInvalida, cobro.ReasignacionInvalida) as err:
                    raise GrupoConflicto(f"{hab_id} ({rid}): {err}") from err
                procesadas.append(res)

            seguridad.auditar(conexion, actor, "grupo_entrada", grupo_id, f"en_estadia:{len(procesadas)}")
    except GrupoConflicto:
        raise

    return {
        "grupo_id": grupo_id,
        "procesadas": procesadas,
        "total_procesadas": len(procesadas),
    }
