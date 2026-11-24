"""Gestión de huéspedes y ocupación real de reservas (PR A, 2026-11-20).

Cada reserva tiene ocupación (`adultos`, `ninos`) y una lista de huéspedes
vinculados en `reserva_huespedes` (un `'titular'` y cero o más `'acompanante'`).
Los datos personales viven en `huespedes`; la auditoría nunca registra PII
(sin nombres ni documentos).
"""
from __future__ import annotations

import uuid
from datetime import date

import psycopg
from psycopg.errors import UniqueViolation

from . import clientes, cobro, documento as documento_mod, hotel_sql, politicas, seguridad


class HuespedInvalido(ValueError):
    """422: datos de huésped inválidos."""


class HuespedConflicto(Exception):
    """409: conflicto de huésped o cupo de ocupación."""


class OcupacionInvalida(Exception):
    """409: ocupación fuera de la capacidad de la habitación o estado inválido."""


def _limpiar_texto(valor: str | None, max_len: int) -> str | None:
    if valor is None:
        return None
    limpio = " ".join(valor.split())
    if not limpio:
        return None
    return limpio[:max_len]


def _normalizar_documento(documento: str | None, documento_tipo: str | None) -> tuple[str | None, str | None]:
    doc = (documento or "").strip() or None
    if doc is None:
        return None, documento_tipo
    if documento_tipo is None:
        raise HuespedInvalido("indica si el documento es rut o pasaporte")
    try:
        return documento_mod.normalizar(documento_tipo, doc), documento_tipo
    except documento_mod.DocumentoInvalido as error:
        raise HuespedInvalido(str(error)) from error


def _fila_huesped(f: tuple, ver_documento: bool) -> dict:
    item = {
        "huesped_id": f[0],
        "nombre": f[1],
        "documento_tipo": f[2],
        "nacionalidad": f[4],
        "fecha_nacimiento": f[5].isoformat() if f[5] else None,
        "telefono": f[6],
        "correo": f[7],
        "notas": f[8],
    }
    if ver_documento:
        item["documento"] = f[3]
    return item


def buscar(
    conexion: psycopg.Connection,
    empresa_id: str,
    documento: str,
    documento_tipo: str | None = None,
) -> list[dict]:
    """Busca huéspedes de la empresa por documento (RUT o pasaporte)."""
    doc_limpio = (documento or "").strip()
    if not doc_limpio:
        raise HuespedInvalido("indica el documento a buscar")
    if documento_tipo is not None:
        doc_norm, tipo_norm = _normalizar_documento(doc_limpio, documento_tipo)
        filas = conexion.execute(
            "SELECT id, nombre, documento_tipo, documento, nacionalidad, fecha_nacimiento, telefono, correo, notas "
            "FROM huespedes WHERE empresa_id = %s AND documento_tipo = %s AND documento = %s "
            "ORDER BY actualizado_en DESC, id",
            (empresa_id, tipo_norm, doc_norm),
        ).fetchall()
    else:
        candidatos = [doc_limpio, doc_limpio.upper()]
        try:
            candidatos.append(documento_mod.normalizar_rut(doc_limpio))
        except documento_mod.DocumentoInvalido:
            pass
        filas = conexion.execute(
            "SELECT id, nombre, documento_tipo, documento, nacionalidad, fecha_nacimiento, telefono, correo, notas "
            "FROM huespedes WHERE empresa_id = %s AND documento IS NOT NULL "
            "AND (documento = ANY(%s) OR documento ILIKE %s) "
            "ORDER BY actualizado_en DESC, id LIMIT 20",
            (empresa_id, candidatos, f"%{doc_limpio}%"),
        ).fetchall()
    return [_fila_huesped(f, ver_documento=True) for f in filas]


def asegurar_titular_reserva(
    conexion: psycopg.Connection,
    empresa_id: str,
    reserva_id: str,
    nombre: str,
    documento: str | None,
    documento_tipo: str | None,
) -> str:
    """Crea o reutiliza el huésped titular y lo vincula a la reserva."""
    huesped_id = None
    if documento and documento_tipo:
        existente = conexion.execute(
            "SELECT id FROM huespedes WHERE empresa_id = %s AND documento_tipo = %s AND documento = %s",
            (empresa_id, documento_tipo, documento),
        ).fetchone()
        if existente:
            huesped_id = existente[0]
    if huesped_id is None:
        huesped_id = f"HSP-{uuid.uuid4().hex[:12]}"
        conexion.execute(
            "INSERT INTO huespedes (id, empresa_id, nombre, documento_tipo, documento) "
            "VALUES (%s, %s, %s, %s, %s)",
            (huesped_id, empresa_id, nombre, documento_tipo, documento),
        )
    conexion.execute(
        "INSERT INTO reserva_huespedes (id, reserva_id, huesped_id, rol, es_nino) "
        "VALUES (%s, %s, %s, 'titular', false) "
        "ON CONFLICT (reserva_id, huesped_id) DO NOTHING",
        (f"RHP-{uuid.uuid4().hex[:12]}", reserva_id, huesped_id),
    )
    return huesped_id


def sincronizar_documento_titular(
    conexion: psycopg.Connection,
    empresa_id: str,
    reserva_id: str,
    documento: str,
    documento_tipo: str | None,
) -> None:
    """Actualiza el documento del titular en `huespedes` cuando la entrada lo captura."""
    fila = conexion.execute(
        "SELECT huesped_id FROM reserva_huespedes WHERE reserva_id = %s AND rol = 'titular'",
        (reserva_id,),
    ).fetchone()
    if not fila:
        return
    try:
        with conexion.transaction():
            conexion.execute(
                "UPDATE huespedes SET documento = %s, documento_tipo = %s, actualizado_en = now() "
                "WHERE id = %s AND empresa_id = %s",
                (documento, documento_tipo, fila[0], empresa_id),
            )
    except UniqueViolation:
        # Si ya existía otro registro maestro con ese documento, re-vincula la reserva a ese huésped.
        otro = conexion.execute(
            "SELECT id FROM huespedes WHERE empresa_id = %s AND documento_tipo = %s AND documento = %s",
            (empresa_id, documento_tipo, documento),
        ).fetchone()
        if otro and otro[0] != fila[0]:
            conexion.execute(
                "UPDATE reserva_huespedes SET huesped_id = %s WHERE reserva_id = %s AND rol = 'titular'",
                (otro[0], reserva_id),
            )


def obtener_huespedes_reserva(
    conexion: psycopg.Connection,
    empresa_id: str,
    reserva_id: str,
    ver_documento: bool,
) -> dict:
    cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id)
    r = conexion.execute(
        "SELECT r.adultos, r.ninos, r.personas, h.capacidad, r.estado, r.habitacion_id, r.grupo_id, "
        "r.titular_aloja, r.es_huesped_provisorio "
        "FROM reservas r JOIN habitaciones h ON h.id = r.habitacion_id WHERE r.id = %s",
        (reserva_id,),
    ).fetchone()
    adultos = r[0] if r[0] is not None else (r[2] or 1)
    ninos = r[1] if r[1] is not None else 0
    total_esperado = adultos + ninos
    filas = conexion.execute(
        "SELECT hu.id, hu.nombre, hu.documento_tipo, hu.documento, hu.nacionalidad, "
        "hu.fecha_nacimiento, hu.telefono, hu.correo, hu.notas, rh.rol, rh.es_nino "
        "FROM reserva_huespedes rh JOIN huespedes hu ON hu.id = rh.huesped_id "
        "WHERE rh.reserva_id = %s ORDER BY (rh.rol = 'titular') DESC, rh.creado_en ASC, rh.id ASC",
        (reserva_id,),
    ).fetchall()
    lista = []
    for f in filas:
        item = _fila_huesped(f[:9], ver_documento=ver_documento)
        item["rol"] = f[9]
        item["es_nino"] = bool(f[10])
        lista.append(item)
    registrados = len(lista)
    faltantes = max(0, total_esperado - registrados)
    return {
        "reserva_id": reserva_id,
        "estado": r[4],
        "habitacion_id": r[5],
        "grupo_id": r[6],
        "titular_aloja": bool(r[7]) if r[7] is not None else True,
        "es_huesped_provisorio": bool(r[8]) if r[8] is not None else False,
        "capacidad_habitacion": r[3],
        "adultos": adultos,
        "ninos": ninos,
        "total_esperado": total_esperado,
        "registrados": registrados,
        "faltantes": faltantes,
        "completo": faltantes == 0 and not bool(r[8]),
        "huespedes": lista,
    }


def _reversar_ajustes_ocupacion_previos(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    reserva_id: str,
    motivo: str,
    prefijo: str = "Ajuste ocupación",
) -> int:
    """Revierte cargos activos previos de ajuste (append-only) y retorna su suma."""
    activos = [
        c for c in hotel.cuenta(empresa_id, reserva_id)
        if c.tipo.value == "cargo"
        and c.concepto.startswith(prefijo)
        and not any(r.tipo.value == "reverso" and r.referencia == c.id for r in hotel.cuenta(empresa_id, reserva_id))
    ]
    suma = 0
    for c in activos:
        hotel.reversar_cargo(empresa_id, c.id, motivo=motivo)
        suma += c.monto_clp
    return suma


def actualizar_ocupacion(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    reserva_id: str,
    adultos: int,
    ninos: int,
    actor: str,
) -> dict:
    cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    r = conexion.execute(
        "SELECT r.habitacion_id, r.estado, r.inicio, r.fin, r.adultos, r.ninos, r.personas, "
        "r.tarifa_noche_aceptada_clp, h.capacidad, r.upgrade_desde_tipo, r.tarifa_lista_clp, "
        "r.upgrade_ajustado_clp "
        "FROM reservas r JOIN habitaciones h ON h.id = r.habitacion_id WHERE r.id = %s",
        (reserva_id,),
    ).fetchone()
    (habitacion_id, estado, inicio, fin, a_prev, n_prev, p_prev, tarifa_noche, capacidad,
     upgrade_tipo, tarifa_lista, upgrade_ajustado) = r
    if estado not in cobro.ESTADOS_CON_CUENTA_ABIERTA:
        raise cobro.TransicionInvalida(f"la reserva está {estado}")
    total_nuevo = adultos + ninos
    if adultos < 1 or ninos < 0 or total_nuevo > capacidad:
        raise OcupacionInvalida(f"la habitación {habitacion_id} admite entre 1 y {capacidad} personas")

    adultos_prev = a_prev if a_prev is not None else (p_prev or 1)
    ninos_prev = n_prev if n_prev is not None else 0
    noches = max(1, (fin - inicio).days)

    conexion.execute(
        "UPDATE reservas SET adultos = %s, ninos = %s, personas = %s WHERE id = %s",
        (adultos, ninos, total_nuevo, reserva_id),
    )

    cuerpo_pol = politicas.de(conexion, empresa_id)["cuerpo"]
    calc = politicas.calcular_recargo_ocupacion(
        cuerpo_pol, tarifa_noche, noches, adultos, ninos, adultos_prev, ninos_prev,
    )
    delta_clp = calc["delta_clp"]
    if delta_clp != 0:
        hotel_sql.recargar(conexion, hotel, empresa_id)
        etiqueta = f"Ajuste ocupación ({adultos} ad., {ninos} ni.)"
        if delta_clp > 0:
            hotel.asentar_cargo(empresa_id, reserva_id, etiqueta, delta_clp)
        else:
            prev_cargado = _reversar_ajustes_ocupacion_previos(
                conexion, hotel, empresa_id, reserva_id, motivo=etiqueta,
            )
            neto_restante = prev_cargado + delta_clp
            if neto_restante > 0:
                hotel.asentar_cargo(empresa_id, reserva_id, etiqueta, neto_restante)
        hotel_sql.persistir(conexion, hotel, empresa_id)

    if upgrade_tipo and tarifa_lista is not None:
        # SPEC-UPG-01: con 2 o más personas deja de valer la tarifa Single; se cobra la de la habitación.
        deseado = max(0, tarifa_lista - tarifa_noche) * noches if total_nuevo >= 2 else 0
        diferencia = deseado - (upgrade_ajustado or 0)
        if diferencia != 0:
            hotel_sql.recargar(conexion, hotel, empresa_id)
            etiqueta_up = f"Ajuste upgrade a tarifa de la habitación ({total_nuevo} personas)"
            if diferencia > 0:
                hotel.asentar_cargo(empresa_id, reserva_id, etiqueta_up, diferencia)
            else:
                previo = _reversar_ajustes_ocupacion_previos(
                    conexion, hotel, empresa_id, reserva_id, motivo=etiqueta_up, prefijo="Ajuste upgrade",
                )
                if previo + diferencia > 0:
                    hotel.asentar_cargo(empresa_id, reserva_id, etiqueta_up, previo + diferencia)
            hotel_sql.persistir(conexion, hotel, empresa_id)
            conexion.execute(
                "UPDATE reservas SET upgrade_ajustado_clp = %s WHERE id = %s", (deseado, reserva_id),
            )
    seguridad.auditar(
        conexion, actor, "reserva_ocupacion", reserva_id,
        f"adultos={adultos},ninos={ninos},delta_clp={delta_clp}",
    )
    return {
        "reserva_id": reserva_id,
        "adultos": adultos,
        "ninos": ninos,
        "total_esperado": total_nuevo,
        "capacidad_habitacion": capacidad,
        "delta_clp": delta_clp,
        "avisos": calc["avisos"],
    }


def agregar_huesped(
    conexion: psycopg.Connection,
    empresa_id: str,
    reserva_id: str,
    datos: dict,
    actor: str,
) -> dict:
    cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    r = conexion.execute(
        "SELECT estado, adultos, ninos, personas, es_huesped_provisorio FROM reservas WHERE id = %s",
        (reserva_id,),
    ).fetchone()
    estado, a, n, p, era_provisorio = r
    if estado not in cobro.ESTADOS_CON_CUENTA_ABIERTA:
        raise cobro.TransicionInvalida(f"la reserva está {estado}")
    total_esperado = (a if a is not None else (p or 1)) + (n if n is not None else 0)
    registrados = conexion.execute(
        "SELECT COUNT(*) FROM reserva_huespedes WHERE reserva_id = %s", (reserva_id,),
    ).fetchone()[0]
    if registrados >= total_esperado:
        raise HuespedConflicto(
            "ya están registrados todos los huéspedes de la ocupación; actualiza la ocupación si vienen más personas"
        )

    rol = datos.get("rol") or "acompanante"
    es_nino = bool(datos.get("es_nino", False))
    tiene_titular = conexion.execute(
        "SELECT 1 FROM reserva_huespedes WHERE reserva_id = %s AND rol = 'titular'", (reserva_id,),
    ).fetchone()
    if era_provisorio and not tiene_titular and not es_nino:
        # Al reemplazar una reserva provisoria, el primer huésped adulto real pasa a ser titular.
        rol = "titular"
    if rol == "titular" and tiene_titular:
        raise HuespedConflicto("la reserva ya tiene un huésped titular")

    huesped_id = datos.get("huesped_id")
    if huesped_id:
        existe = conexion.execute(
            "SELECT id FROM huespedes WHERE id = %s AND empresa_id = %s", (huesped_id, empresa_id),
        ).fetchone()
        if not existe:
            raise cobro.RecursoAjenoOInexistente("huésped no encontrado")
    else:
        nombre = _limpiar_texto(datos.get("nombre"), 200)
        if not nombre:
            raise HuespedInvalido("nombre es obligatorio (máx. 200)")
        doc, doc_tipo = _normalizar_documento(datos.get("documento"), datos.get("documento_tipo"))
        if doc and doc_tipo:
            existente = conexion.execute(
                "SELECT id FROM huespedes WHERE empresa_id = %s AND documento_tipo = %s AND documento = %s",
                (empresa_id, doc_tipo, doc),
            ).fetchone()
            if existente:
                huesped_id = existente[0]
        if huesped_id is None:
            huesped_id = f"HSP-{uuid.uuid4().hex[:12]}"
            conexion.execute(
                "INSERT INTO huespedes "
                "(id, empresa_id, nombre, documento_tipo, documento, nacionalidad, fecha_nacimiento, telefono, correo, notas) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    huesped_id,
                    empresa_id,
                    nombre,
                    doc_tipo,
                    doc,
                    _limpiar_texto(datos.get("nacionalidad"), 80),
                    datos.get("fecha_nacimiento"),
                    _limpiar_texto(datos.get("telefono"), 40),
                    _limpiar_texto(datos.get("correo"), 120),
                    _limpiar_texto(datos.get("notas"), 400),
                ),
            )

    try:
        with conexion.transaction():
            conexion.execute(
                "INSERT INTO reserva_huespedes (id, reserva_id, huesped_id, rol, es_nino) "
                "VALUES (%s, %s, %s, %s, %s)",
                (f"RHP-{uuid.uuid4().hex[:12]}", reserva_id, huesped_id, rol, es_nino),
            )
    except UniqueViolation as error:
        raise HuespedConflicto("ese huésped ya está registrado en esta reserva") from error

    if era_provisorio and rol == "titular":
        h_real = conexion.execute(
            "SELECT nombre, documento, documento_tipo FROM huespedes WHERE id = %s",
            (huesped_id,),
        ).fetchone()
        if h_real and h_real[0] and h_real[1]:
            conexion.execute(
                "UPDATE reservas SET huesped_nombre = %s, huesped_documento = %s, "
                "huesped_documento_tipo = %s, es_huesped_provisorio = FALSE WHERE id = %s",
                (h_real[0], h_real[1], h_real[2], reserva_id),
            )

    seguridad.auditar(conexion, actor, "reserva_huesped_alta", reserva_id, f"rol={rol},es_nino={es_nino}")
    return obtener_huespedes_reserva(conexion, empresa_id, reserva_id, ver_documento=True)


def editar_huesped_en_reserva(
    conexion: psycopg.Connection,
    empresa_id: str,
    reserva_id: str,
    huesped_id: str,
    datos: dict,
    actor: str,
) -> dict:
    cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    vinculo = conexion.execute(
        "SELECT rh.rol, rh.es_nino, hu.nombre, hu.documento_tipo, hu.documento, "
        "hu.nacionalidad, hu.fecha_nacimiento, hu.telefono, hu.correo, hu.notas "
        "FROM reserva_huespedes rh JOIN huespedes hu ON hu.id = rh.huesped_id "
        "WHERE rh.reserva_id = %s AND rh.huesped_id = %s AND hu.empresa_id = %s",
        (reserva_id, huesped_id, empresa_id),
    ).fetchone()
    if not vinculo:
        raise cobro.RecursoAjenoOInexistente("huésped no vinculado a esta reserva")

    rol_actual = vinculo[0]
    nombre_nuevo = _limpiar_texto(datos.get("nombre"), 200) if "nombre" in datos and datos["nombre"] is not None else vinculo[2]
    if not nombre_nuevo:
        raise HuespedInvalido("nombre es obligatorio")

    if "documento" in datos or "documento_tipo" in datos:
        doc_raw = datos.get("documento")
        tipo_raw = datos.get("documento_tipo") if datos.get("documento_tipo") is not None else vinculo[3]
        if doc_raw is not None and str(doc_raw).strip():
            doc_nuevo, tipo_nuevo = _normalizar_documento(doc_raw, tipo_raw)
        elif doc_raw is None and "documento" not in datos:
            doc_nuevo, tipo_nuevo = vinculo[4], vinculo[3]
        else:
            doc_nuevo, tipo_nuevo = vinculo[4], vinculo[3]
    else:
        doc_nuevo, tipo_nuevo = vinculo[4], vinculo[3]

    nacionalidad = _limpiar_texto(datos.get("nacionalidad"), 80) if "nacionalidad" in datos else vinculo[5]
    fecha_nac = datos.get("fecha_nacimiento") if "fecha_nacimiento" in datos else vinculo[6]
    telefono = _limpiar_texto(datos.get("telefono"), 40) if "telefono" in datos else vinculo[7]
    correo = _limpiar_texto(datos.get("correo"), 120) if "correo" in datos else vinculo[8]
    notas = _limpiar_texto(datos.get("notas"), 400) if "notas" in datos else vinculo[9]
    es_nino = bool(datos["es_nino"]) if "es_nino" in datos and datos["es_nino"] is not None else bool(vinculo[1])

    cambiados = []
    if nombre_nuevo != vinculo[2]:
        cambiados.append("nombre")
    if (doc_nuevo, tipo_nuevo) != (vinculo[4], vinculo[3]):
        cambiados.append("documento")
    if (nacionalidad, fecha_nac, telefono, correo, notas) != (vinculo[5], vinculo[6], vinculo[7], vinculo[8], vinculo[9]):
        cambiados.append("contacto")
    if es_nino != bool(vinculo[1]):
        cambiados.append("es_nino")

    try:
        with conexion.transaction():
            conexion.execute(
                "UPDATE huespedes SET nombre = %s, documento_tipo = %s, documento = %s, "
                "nacionalidad = %s, fecha_nacimiento = %s, telefono = %s, correo = %s, notas = %s, "
                "actualizado_en = now() WHERE id = %s",
                (nombre_nuevo, tipo_nuevo, doc_nuevo, nacionalidad, fecha_nac, telefono, correo, notas, huesped_id),
            )
    except UniqueViolation as error:
        raise HuespedConflicto("ya existe otro huésped registrado con ese documento") from error

    conexion.execute(
        "UPDATE reserva_huespedes SET es_nino = %s WHERE reserva_id = %s AND huesped_id = %s",
        (es_nino, reserva_id, huesped_id),
    )

    if rol_actual == "titular":
        conexion.execute(
            "UPDATE reservas SET huesped_nombre = %s, huesped_documento = %s, huesped_documento_tipo = %s, "
            "es_huesped_provisorio = CASE WHEN %s THEN FALSE ELSE es_huesped_provisorio END "
            "WHERE id = %s",
            (nombre_nuevo, doc_nuevo, tipo_nuevo, bool(doc_nuevo), reserva_id),
        )

    if cambiados:
        seguridad.auditar(conexion, actor, "reserva_huesped_edicion", reserva_id, f"campos={','.join(cambiados)}")
    return obtener_huespedes_reserva(conexion, empresa_id, reserva_id, ver_documento=True)


def quitar_huesped_de_reserva(
    conexion: psycopg.Connection,
    empresa_id: str,
    reserva_id: str,
    huesped_id: str,
    actor: str,
) -> dict:
    estado = cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)[2]
    if estado not in cobro.ESTADOS_CON_CUENTA_ABIERTA:
        raise cobro.TransicionInvalida(f"la reserva está {estado}")
    fila = conexion.execute(
        "SELECT rol FROM reserva_huespedes WHERE reserva_id = %s AND huesped_id = %s",
        (reserva_id, huesped_id),
    ).fetchone()
    if not fila:
        raise cobro.RecursoAjenoOInexistente("huésped no vinculado a esta reserva")
    if fila[0] == "titular":
        raise HuespedConflicto("no se puede quitar al huésped titular de la reserva")
    conexion.execute(
        "DELETE FROM reserva_huespedes WHERE reserva_id = %s AND huesped_id = %s",
        (reserva_id, huesped_id),
    )
    seguridad.auditar(conexion, actor, "reserva_huesped_baja", reserva_id, "acompanante")
    return obtener_huespedes_reserva(conexion, empresa_id, reserva_id, ver_documento=True)


def verificar_huespedes_para_entrada(conexion: psycopg.Connection, reserva_id: str) -> None:
    """Exige que estén registrados todos los huéspedes según `adultos + ninos` antes de la Llegada.
    Mantiene compatibilidad con reservas antiguas/1 titular auto-asegurando el titular si falta la
    fila en `reserva_huespedes` (#413). Si `titular_aloja` es `false` (habitación de grupo donde
    el titular no duerme), nunca auto-inserta al titular: exige registrar a los ocupantes reales."""
    r = conexion.execute(
        "SELECT empresa_id, adultos, ninos, personas, huesped_nombre, huesped_documento, "
        "huesped_documento_tipo, titular_aloja, es_huesped_provisorio FROM reservas WHERE id = %s",
        (reserva_id,),
    ).fetchone()
    if not r:
        return
    empresa_id, adultos, ninos, personas, nombre, documento, documento_tipo, aloja, provisorio = r
    if provisorio:
        raise cobro.TransicionInvalida(
            "Esta reserva está a nombre provisorio de una empresa o institución. "
            "Registra los nombres y documentos reales de los huéspedes antes de la Llegada."
        )
    titular_aloja = True if aloja is None else bool(aloja)
    esperado = (adultos if adultos is not None else (personas or 1)) + (ninos if ninos is not None else 0)
    registrados = conexion.execute(
        "SELECT COUNT(*) FROM reserva_huespedes WHERE reserva_id = %s", (reserva_id,),
    ).fetchone()[0]
    if registrados == 0 and titular_aloja and nombre:
        asegurar_titular_reserva(conexion, empresa_id, reserva_id, nombre, documento, documento_tipo)
        registrados = conexion.execute(
            "SELECT COUNT(*) FROM reserva_huespedes WHERE reserva_id = %s", (reserva_id,),
        ).fetchone()[0]
    if registrados < esperado:
        faltan = esperado - registrados
        raise cobro.TransicionInvalida(
            f"Faltan {faltan} huésped(es) por registrar para completar la ocupación "
            f"({registrados} de {esperado} registrados). Regístralos en Huéspedes antes de la Llegada."
        )
