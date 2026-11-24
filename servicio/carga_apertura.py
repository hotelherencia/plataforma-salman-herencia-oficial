"""Carga inicial operativa y migración de apertura (F20 / MIG-002..006).

Soporta `--dry-run` (emite acta de validación sin escribir en la base) y `--aplicar`
(carga 100 % idempotente y auditable sin PII) desde CSV saneados:
1. Inventarios iniciales (`Lavandería`, `Insumos Aseo`, `Insumos Desayuno`, `Cocina`) en `0055`.
2. Incidencias operativas iniciales de mantenimiento en `0059` y activos con plan de mantención en `0069`.
3. Reservas futuras y anticipos heredados al corte 31-12-2026.
"""
from __future__ import annotations

import csv
import hashlib
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import psycopg

from . import contabilidad, documento as documento_mod, hotel_sql, productos as productos_db, reservas as reservas_db, seguridad

FECHA_CORTE_APERTURA = date(2026, 12, 31)
CATEGORIAS_PRODUCTO = {"minibar", "cafeteria", "servicio", "extra"}
GRAVEDADES_INCIDENCIA = {"baja", "media", "alta", "critica"}
CATEGORIAS_ACTIVO = {"mobiliario", "electrico", "climatizacion", "sanitario", "electronico", "otro"}
ESTADOS_ACTIVO = {"operativo", "en_reparacion", "de_baja"}
MEDIOS_ANTICIPO = {"efectivo", "debito", "credito", "transferencia"}
COLUMNAS_PROHIBIDAS = {"password", "clave", "clave_hash", "contrasena", "contraseña", "secret", "token", "tarjeta", "cvv"}


def _leer_csv(ruta: Path) -> tuple[list[str], list[dict[str, str]]]:
    with ruta.open("r", encoding="utf-8-sig", newline="") as fh:
        muestra = fh.read(2048)
        fh.seek(0)
        delimitador = ";" if muestra.count(";") > muestra.count(",") else ","
        lector = csv.DictReader(fh, delimiter=delimitador)
        cabeceras = [c.strip() for c in (lector.fieldnames or []) if c]
        filas = []
        for idx, row in enumerate(lector, start=2):
            limpia = {k.strip(): (v.strip() if isinstance(v, str) else "") for k, v in row.items() if k}
            if not any(limpia.values()):
                continue
            limpia["_linea"] = str(idx)
            filas.append(limpia)
    return cabeceras, filas


def _validar_sin_columnas_sensibles(cabeceras: list[str]) -> list[str]:
    errores = []
    for col in cabeceras:
        if col.lower() in COLUMNAS_PROHIBIDAS:
            errores.append(f"columna prohibida detectada en CSV (credencial/secreto): «{col}»")
    return errores


def _bool_csv(valor: str, defecto: bool = False) -> bool:
    v = (valor or "").strip().lower()
    if not v:
        return defecto
    return v in ("1", "true", "si", "sí", "yes", "s", "t")


def _int_csv(valor: str, nombre: str, minimo: int = 0) -> int:
    try:
        n = int((valor or "").strip())
    except ValueError as err:
        raise ValueError(f"{nombre} debe ser un entero") from err
    if n < minimo:
        raise ValueError(f"{nombre} debe ser >= {minimo}")
    return n


def _fecha_csv(valor: str, nombre: str) -> date:
    try:
        return date.fromisoformat((valor or "").strip())
    except ValueError as err:
        raise ValueError(f"{nombre} debe tener formato YYYY-MM-DD") from err


# --- 1. Inventarios iniciales en 0055 ------------------------------------------

def cargar_inventarios_csv(
    conexion: psycopg.Connection,
    ruta_csv: Path,
    *,
    aplicar: bool = False,
    actor: str = "migracion_apertura",
) -> dict:
    cabeceras, filas = _leer_csv(ruta_csv)
    errores: list[dict] = [{"linea": 1, "error": e} for e in _validar_sin_columnas_sensibles(cabeceras)]
    requeridas = {"codigo", "nombre", "categoria", "bodega_codigo", "stock_inicial"}
    faltantes = sorted(requeridas - set(cabeceras))
    if faltantes:
        errores.append({"linea": 1, "error": f"faltan columnas obligatorias: {', '.join(faltantes)}"})
        return {"archivo": str(ruta_csv.name), "total_filas": len(filas), "validos": 0, "aplicados": 0, "omitidos": 0, "errores": errores}

    bodegas_activas = {
        r[0] for r in conexion.execute("SELECT codigo FROM core_bodegas WHERE activa").fetchall()
    }
    validas = []
    codigos_vistos: set[str] = set()
    for f in filas:
        linea = int(f["_linea"])
        try:
            codigo = f["codigo"].strip()
            nombre = f["nombre"].strip()
            categoria = f["categoria"].strip().lower()
            bodega = f["bodega_codigo"].strip().lower()
            if not codigo or not nombre:
                raise ValueError("codigo y nombre son obligatorios")
            clave_cod = codigo.lower()
            if clave_cod in codigos_vistos:
                raise ValueError(f"codigo duplicado en el CSV: {codigo}")
            codigos_vistos.add(clave_cod)
            if categoria not in CATEGORIAS_PRODUCTO:
                raise ValueError(f"categoria inválida «{categoria}» (permitidas: {', '.join(sorted(CATEGORIAS_PRODUCTO))})")
            if bodega not in bodegas_activas:
                raise ValueError(f"bodega_codigo inexistente o inactiva: «{bodega}»")
            stock_ini = _int_csv(f["stock_inicial"], "stock_inicial", minimo=0)
            stock_min = _int_csv(f.get("stock_minimo") or "0", "stock_minimo", minimo=0)
            precio = _int_csv(f.get("precio_clp") or "1", "precio_clp", minimo=1)
            costo = _int_csv(f["costo_clp"], "costo_clp", minimo=0) if f.get("costo_clp") else None
            activo = _bool_csv(f.get("activo", ""), defecto=True)
            validas.append({
                "linea": linea, "codigo": codigo, "nombre": nombre, "categoria": categoria,
                "bodega_codigo": bodega, "stock_inicial": stock_ini, "stock_minimo": stock_min,
                "precio_clp": precio, "costo_clp": costo, "activo": activo,
            })
        except ValueError as err:
            errores.append({"linea": linea, "error": str(err)})

    aplicados = 0
    omitidos = 0
    if aplicar and not errores:
        with conexion.transaction():
            for item in validas:
                motivo_idem = f"apertura:{item['codigo']}:{item['bodega_codigo']}"
                ya_cargado = conexion.execute(
                    "SELECT 1 FROM movimientos_stock WHERE motivo = %s LIMIT 1", (motivo_idem,)
                ).fetchone()
                existente = conexion.execute(
                    "SELECT id FROM productos WHERE lower(codigo) = lower(%s) OR lower(nombre) = lower(%s) LIMIT 1",
                    (item["codigo"], item["nombre"]),
                ).fetchone()
                if ya_cargado:
                    omitidos += 1
                    continue
                if existente:
                    pid = existente[0]
                    conexion.execute(
                        "UPDATE productos SET controla_stock = true, stock_minimo = GREATEST(stock_minimo, %s), "
                        "costo_clp = COALESCE(%s, costo_clp), actualizado_en = now() WHERE id = %s",
                        (item["stock_minimo"], item["costo_clp"], pid),
                    )
                else:
                    pid = f"PRD-{hashlib.md5(item['codigo'].lower().encode()).hexdigest()[:10]}"
                    conexion.execute(
                        "INSERT INTO productos (id, nombre, categoria, precio_clp, activo, controla_stock, stock, codigo, costo_clp, stock_minimo) "
                        "VALUES (%s, %s, %s, %s, %s, true, 0, %s, %s, %s)",
                        (pid, item["nombre"], item["categoria"], item["precio_clp"], item["activo"],
                         item["codigo"], item["costo_clp"], item["stock_minimo"]),
                    )
                if item["stock_inicial"] > 0:
                    productos_db.registrar_stock_bodega(conexion, pid, item["bodega_codigo"], item["stock_inicial"])
                    conexion.execute(
                        "UPDATE productos SET stock = stock + %s, actualizado_en = now() WHERE id = %s",
                        (item["stock_inicial"], pid),
                    )
                # Registrar marca de apertura idempotente (incluso con stock 0 si se desea trazabilidad)
                productos_db._movimiento(
                    conexion, pid, item["stock_inicial"], motivo_idem, actor,
                    bodega_codigo=item["bodega_codigo"], tipo="entrada",
                )
                aplicados += 1
            seguridad.auditar(
                conexion, actor, "apertura_inventarios", ruta_csv.name,
                f"aplicados={aplicados},omitidos={omitidos}",
            )

    return {
        "archivo": str(ruta_csv.name),
        "total_filas": len(filas),
        "validos": len(validas),
        "aplicados": aplicados,
        "omitidos": omitidos,
        "errores": errores,
    }


# --- 2. Incidencias iniciales de mantenimiento en 0059 -------------------------

def cargar_incidencias_csv(
    conexion: psycopg.Connection,
    ruta_csv: Path,
    *,
    aplicar: bool = False,
    actor: str = "migracion_apertura",
) -> dict:
    cabeceras, filas = _leer_csv(ruta_csv)
    errores: list[dict] = [{"linea": 1, "error": e} for e in _validar_sin_columnas_sensibles(cabeceras)]
    requeridas = {"codigo_externo", "descripcion", "gravedad"}
    faltantes = sorted(requeridas - set(cabeceras))
    if faltantes:
        errores.append({"linea": 1, "error": f"faltan columnas obligatorias: {', '.join(faltantes)}"})
        return {"archivo": str(ruta_csv.name), "total_filas": len(filas), "validos": 0, "aplicados": 0, "omitidos": 0, "errores": errores}

    habs_validas = {r[0] for r in conexion.execute("SELECT id FROM habitaciones").fetchall()}
    validas = []
    codigos_vistos: set[str] = set()
    for f in filas:
        linea = int(f["_linea"])
        try:
            cod = f["codigo_externo"].strip()
            if not cod:
                raise ValueError("codigo_externo es obligatorio")
            if cod.lower() in codigos_vistos:
                raise ValueError(f"codigo_externo duplicado en CSV: {cod}")
            codigos_vistos.add(cod.lower())
            hab_id = f.get("habitacion_id", "").strip() or None
            area = f.get("area", "").strip() or None
            if not hab_id and not area:
                raise ValueError("indica habitacion_id o area")
            if hab_id and hab_id not in habs_validas:
                raise ValueError(f"habitacion_id inexistente: «{hab_id}»")
            desc = f["descripcion"].strip()
            if not (3 <= len(desc) <= 1000):
                raise ValueError("descripcion debe tener entre 3 y 1000 caracteres")
            gravedad = f["gravedad"].strip().lower() or "media"
            if gravedad not in GRAVEDADES_INCIDENCIA:
                raise ValueError(f"gravedad inválida «{gravedad}»")
            responsable = f.get("responsable", "").strip()[:120] or None
            plazo = _fecha_csv(f["plazo"], "plazo") if f.get("plazo") else None
            costo = _int_csv(f["costo_clp"], "costo_clp", minimo=0) if f.get("costo_clp") else None
            bloquea = _bool_csv(f.get("bloquea_disponibilidad", ""), defecto=False)
            if bloquea and not hab_id:
                raise ValueError("bloquea_disponibilidad=true exige habitacion_id")
            inc_id = f"INC-APR-{hashlib.md5(cod.lower().encode()).hexdigest()[:10]}"
            validas.append({
                "linea": linea, "id": inc_id, "codigo_externo": cod, "habitacion_id": hab_id,
                "area": area, "descripcion": desc, "gravedad": gravedad, "responsable": responsable,
                "plazo": plazo, "costo_clp": costo, "bloquea_disponibilidad": bloquea,
            })
        except ValueError as err:
            errores.append({"linea": linea, "error": str(err)})

    aplicados = 0
    omitidos = 0
    if aplicar and not errores:
        with conexion.transaction():
            for item in validas:
                existe = conexion.execute("SELECT 1 FROM incidencias WHERE id = %s", (item["id"],)).fetchone()
                if existe:
                    omitidos += 1
                    continue
                bloqueo_aplicado = False
                if item["bloquea_disponibilidad"] and item["habitacion_id"]:
                    ya_mant = conexion.execute(
                        "SELECT mantenimiento FROM habitaciones WHERE id = %s FOR UPDATE",
                        (item["habitacion_id"],),
                    ).fetchone()
                    if ya_mant and not ya_mant[0]:
                        conexion.execute(
                            "UPDATE habitaciones SET mantenimiento = true, mantenimiento_desde = %s, "
                            "mantenimiento_hasta = %s WHERE id = %s",
                            (date.today(), item["plazo"], item["habitacion_id"]),
                        )
                        bloqueo_aplicado = True
                conexion.execute(
                    "INSERT INTO incidencias (id, habitacion_id, area, descripcion, gravedad, responsable, "
                    "plazo, estado, costo_clp, bloquea_disponibilidad, bloqueo_aplicado, creada_por) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,'abierta',%s,%s,%s,%s)",
                    (item["id"], item["habitacion_id"], item["area"], item["descripcion"], item["gravedad"],
                     item["responsable"], item["plazo"], item["costo_clp"], item["bloquea_disponibilidad"],
                     bloqueo_aplicado, actor),
                )
                conexion.execute(
                    "INSERT INTO incidencia_eventos (incidencia_id, accion, detalle, actor) "
                    "VALUES (%s, 'creada', %s, %s)",
                    (item["id"], f"carga apertura {item['codigo_externo']} gravedad={item['gravedad']}", actor),
                )
                aplicados += 1
            seguridad.auditar(
                conexion, actor, "apertura_incidencias", ruta_csv.name,
                f"aplicados={aplicados},omitidos={omitidos}",
            )

    return {
        "archivo": str(ruta_csv.name),
        "total_filas": len(filas),
        "validos": len(validas),
        "aplicados": aplicados,
        "omitidos": omitidos,
        "errores": errores,
    }


# --- 2b. Activos y planes de mantención iniciales en 0069 ---------------------

def cargar_activos_csv(
    conexion: psycopg.Connection,
    ruta_csv: Path,
    *,
    aplicar: bool = False,
    actor: str = "migracion_apertura",
) -> dict:
    """Activos por habitación o área común, con su plan de mantención opcional. Idempotente:
    el id sale del `codigo_externo`, así que repetir la carga no duplica filas."""
    cabeceras, filas = _leer_csv(ruta_csv)
    errores: list[dict] = [{"linea": 1, "error": e} for e in _validar_sin_columnas_sensibles(cabeceras)]
    requeridas = {"codigo_externo", "nombre"}
    faltantes = sorted(requeridas - set(cabeceras))
    if faltantes:
        errores.append({"linea": 1, "error": f"faltan columnas obligatorias: {', '.join(faltantes)}"})
        return {"archivo": str(ruta_csv.name), "total_filas": len(filas), "validos": 0, "aplicados": 0, "omitidos": 0, "errores": errores}

    habs_validas = {r[0] for r in conexion.execute("SELECT id FROM habitaciones").fetchall()}
    validas = []
    vistos: set[str] = set()
    for f in filas:
        linea = int(f["_linea"])
        try:
            cod = f["codigo_externo"].strip()
            if not cod:
                raise ValueError("codigo_externo es obligatorio")
            if cod.lower() in vistos:
                raise ValueError(f"codigo_externo duplicado en CSV: {cod}")
            vistos.add(cod.lower())
            hab_id = f.get("habitacion_id", "").strip() or None
            area = f.get("area", "").strip() or None
            if not hab_id and not area:
                raise ValueError("indica habitacion_id o area")
            if hab_id and hab_id not in habs_validas:
                raise ValueError(f"habitacion_id inexistente: «{hab_id}»")
            if area and not (2 <= len(area) <= 60):
                raise ValueError("area debe tener entre 2 y 60 caracteres")
            nombre = f["nombre"].strip()
            if not (2 <= len(nombre) <= 80):
                raise ValueError("nombre debe tener entre 2 y 80 caracteres")
            categoria = (f.get("categoria") or "otro").strip().lower()
            if categoria not in CATEGORIAS_ACTIVO:
                raise ValueError(f"categoria inválida «{categoria}»")
            estado = (f.get("estado") or "operativo").strip().lower()
            if estado not in ESTADOS_ACTIVO:
                raise ValueError(f"estado inválido «{estado}»")
            notas = (f.get("notas") or "").strip()[:300] or None
            plan = None
            desc = (f.get("mantencion_descripcion") or "").strip()
            if desc:
                if not (3 <= len(desc) <= 200):
                    raise ValueError("mantencion_descripcion debe tener entre 3 y 200 caracteres")
                cada = _int_csv(f.get("mantencion_cada_dias") or "", "mantencion_cada_dias", minimo=1)
                if cada > 1830:
                    raise ValueError("mantencion_cada_dias debe ser <= 1830")
                plan = {"descripcion": desc, "cada_dias": cada,
                        "proxima": _fecha_csv(f.get("mantencion_proxima") or "", "mantencion_proxima")}
            digest = hashlib.md5(cod.lower().encode()).hexdigest()[:10]
            validas.append({"linea": linea, "id": f"ACT-{digest}", "plan_id": f"MNP-{digest}", "habitacion_id": hab_id,
                            "area": area, "nombre": nombre, "categoria": categoria, "estado": estado,
                            "notas": notas, "plan": plan})
        except ValueError as err:
            errores.append({"linea": linea, "error": str(err)})

    aplicados = omitidos = 0
    if aplicar and not errores:
        with conexion.transaction():
            for item in validas:
                if conexion.execute("SELECT 1 FROM activos WHERE id = %s", (item["id"],)).fetchone():
                    omitidos += 1
                    continue
                conexion.execute(
                    "INSERT INTO activos (id, habitacion_id, area, nombre, categoria, estado, notas, creado_por) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (item["id"], item["habitacion_id"], item["area"], item["nombre"], item["categoria"],
                     item["estado"], item["notas"], actor),
                )
                if item["plan"]:
                    conexion.execute(
                        "INSERT INTO mantenciones_plan (id, activo_id, descripcion, cada_dias, proxima, creado_por) "
                        "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                        (item["plan_id"], item["id"], item["plan"]["descripcion"], item["plan"]["cada_dias"],
                         item["plan"]["proxima"], actor),
                    )
                aplicados += 1
            seguridad.auditar(conexion, actor, "apertura_activos", ruta_csv.name,
                              f"aplicados={aplicados},omitidos={omitidos}")

    return {"archivo": str(ruta_csv.name), "total_filas": len(filas), "validos": len(validas),
            "aplicados": aplicados, "omitidos": omitidos, "errores": errores}


# --- 3. Reservas futuras y anticipos heredados (corte 31-12-2026) --------------

def cargar_reservas_apertura_csv(
    conexion: psycopg.Connection,
    empresa_id: str,
    ruta_csv: Path,
    *,
    aplicar: bool = False,
    actor: str = "migracion_apertura",
    fecha_corte: date = FECHA_CORTE_APERTURA,
    nucleo=None,
    hotel=None,
) -> dict:
    cabeceras, filas = _leer_csv(ruta_csv)
    errores: list[dict] = [{"linea": 1, "error": e} for e in _validar_sin_columnas_sensibles(cabeceras)]
    requeridas = {"codigo_externo", "habitacion_id", "llegada", "salida", "adultos", "titular_nombre"}
    faltantes = sorted(requeridas - set(cabeceras))
    if faltantes:
        errores.append({"linea": 1, "error": f"faltan columnas obligatorias: {', '.join(faltantes)}"})
        return {"archivo": str(ruta_csv.name), "total_filas": len(filas), "validos": 0, "aplicados": 0, "omitidos": 0, "errores": errores}

    habs = {
        r[0]: int(r[1])
        for r in conexion.execute("SELECT id, capacidad FROM habitaciones WHERE estado_operativo <> 'fuera_de_servicio'").fetchall()
    }
    validas = []
    codigos_vistos: set[str] = set()
    rangos_por_hab: dict[str, list[tuple[date, date, int]]] = {}

    for f in filas:
        linea = int(f["_linea"])
        try:
            cod = f["codigo_externo"].strip()
            if not cod:
                raise ValueError("codigo_externo es obligatorio")
            if cod.lower() in codigos_vistos:
                raise ValueError(f"codigo_externo duplicado: {cod}")
            codigos_vistos.add(cod.lower())
            hab_id = f["habitacion_id"].strip()
            if hab_id not in habs:
                raise ValueError(f"habitacion_id inexistente o fuera de servicio: «{hab_id}»")
            llegada = _fecha_csv(f["llegada"], "llegada")
            salida = _fecha_csv(f["salida"], "salida")
            if salida <= llegada:
                raise ValueError("salida debe ser posterior a llegada")
            if salida <= fecha_corte:
                raise ValueError(f"reserva ya terminada al corte {fecha_corte.isoformat()}: solo cargar estadías vigentes o futuras")
            adultos = _int_csv(f["adultos"], "adultos", minimo=1)
            ninos = _int_csv(f.get("ninos") or "0", "ninos", minimo=0)
            personas = adultos + ninos
            if personas > habs[hab_id]:
                raise ValueError(f"{hab_id} admite máximo {habs[hab_id]} personas (CSV trae {personas})")
            for ini_p, fin_p, lin_p in rangos_por_hab.get(hab_id, []):
                if llegada < fin_p and salida > ini_p:
                    raise ValueError(f"solape interno en CSV para {hab_id} con línea {lin_p}")
            rangos_por_hab.setdefault(hab_id, []).append((llegada, salida, linea))

            canal = (f.get("canal") or "directo").strip().lower()
            if canal not in reservas_db.CANALES_RESERVA:
                raise ValueError(f"canal inválido: «{canal}»")
            nombre = " ".join(f["titular_nombre"].split())[:200]
            if not nombre:
                raise ValueError("titular_nombre es obligatorio")

            doc_tipo = (f.get("documento_tipo") or "").strip().lower() or None
            doc_raw = (f.get("documento") or "").strip() or None
            doc_norm = None
            if doc_raw:
                if doc_tipo not in ("rut", "pasaporte"):
                    raise ValueError("si indicas documento, documento_tipo debe ser rut o pasaporte")
                try:
                    doc_norm = documento_mod.normalizar(doc_tipo, doc_raw)
                except documento_mod.DocumentoInvalido as derr:
                    raise ValueError(str(derr)) from derr

            anticipo = _int_csv(f.get("anticipo_clp") or "0", "anticipo_clp", minimo=0)
            anticipo_medio = (f.get("anticipo_medio") or "").strip().lower() or None
            fecha_ant = _fecha_csv(f["fecha_anticipo"], "fecha_anticipo") if f.get("fecha_anticipo") else fecha_corte
            comprobante = (f.get("comprobante") or "").strip()[:60] or None
            if anticipo > 0:
                if anticipo_medio not in MEDIOS_ANTICIPO:
                    raise ValueError(f"anticipo_clp > 0 exige anticipo_medio en {', '.join(sorted(MEDIOS_ANTICIPO))}")
                if fecha_ant > fecha_corte:
                    raise ValueError(f"fecha_anticipo ({fecha_ant.isoformat()}) no puede ser posterior al corte {fecha_corte.isoformat()}")

            validas.append({
                "linea": linea, "codigo_externo": cod, "habitacion_id": hab_id,
                "llegada": llegada, "salida": salida, "adultos": adultos, "ninos": ninos,
                "personas": personas, "canal": canal, "titular_nombre": nombre,
                "documento_tipo": doc_tipo, "documento": doc_norm,
                "anticipo_clp": anticipo, "anticipo_medio": anticipo_medio,
                "fecha_anticipo": fecha_ant, "comprobante": comprobante,
            })
        except ValueError as err:
            errores.append({"linea": linea, "error": str(err)})

    aplicados = 0
    omitidos = 0
    total_anticipos_clp = sum(v["anticipo_clp"] for v in validas)

    if aplicar and not errores:
        if hotel is None:
            hotel = hotel_sql.hotel_registrado()
        with hotel_sql.EXCLUSIVO:
            hotel_sql.bloquear(conexion)
            for item in validas:
                clave_rsv = f"apertura:rsv:{item['codigo_externo']}"
                prev = conexion.execute(
                    "SELECT cuerpo_respuesta->>'reserva_id' FROM claves_idempotencia "
                    "WHERE empresa_id = %s AND clave = %s",
                    (empresa_id, clave_rsv),
                ).fetchone()
                if prev and prev[0]:
                    omitidos += 1
                    continue
                creada = reservas_db.crear_reserva(
                    conexion,
                    empresa_id=empresa_id,
                    habitacion_id=item["habitacion_id"],
                    inicio=item["llegada"],
                    fin=item["salida"],
                    huesped_nombre=item["titular_nombre"],
                    huesped_documento=item["documento"],
                    huesped_documento_tipo=item["documento_tipo"],
                    personas=item["personas"],
                    canal=item["canal"],
                    extras={"ninos": item["ninos"]} if item["ninos"] > 0 else None,
                )
                rid = creada["reserva_id"]
                conexion.execute(
                    "UPDATE reservas SET adultos = %s, ninos = %s WHERE id = %s",
                    (item["adultos"], item["ninos"], rid),
                )
                # Registrar anticipo heredado al corte (append-only e idempotente; en la transacción principal)
                if item["anticipo_clp"] > 0:
                    from . import cobro
                    if nucleo is None:
                        from nucleo.servicio import Nucleo
                        nucleo = Nucleo()
                    cobro.registrar_pago_manual(
                        conexion, nucleo, hotel, empresa_id, rid,
                        item["anticipo_clp"],
                        clave=f"apertura:ant:{item['codigo_externo']}",
                        confirmar_exceso=True,
                        datos={
                            "medio": item["anticipo_medio"],
                            "documento_tipo": "sin_documento",
                            "comprobante": item["comprobante"] or f"APR-{item['codigo_externo']}"[:60],
                        },
                        actor=actor,
                    )
                # Guardar llave idempotente sin PII
                conexion.execute(
                    "INSERT INTO claves_idempotencia (empresa_id, clave, hash_cuerpo, codigo_respuesta, cuerpo_respuesta) "
                    "VALUES (%s, %s, %s, 201, %s)",
                    (
                        empresa_id,
                        clave_rsv,
                        hashlib.sha256(clave_rsv.encode()).hexdigest(),
                        psycopg.types.json.Json({"reserva_id": rid, "codigo_externo": item["codigo_externo"]}),
                    ),
                )
                aplicados += 1
            seguridad.auditar(
                conexion, actor, "apertura_reservas", ruta_csv.name,
                f"aplicados={aplicados},omitidos={omitidos}",
            )

    return {
        "archivo": str(ruta_csv.name),
        "fecha_corte": fecha_corte.isoformat(),
        "total_filas": len(filas),
        "validos": len(validas),
        "total_anticipos_validados_clp": total_anticipos_clp,
        "aplicados": aplicados,
        "omitidos": omitidos,
        "errores": errores,
    }


def ejecutar_apertura(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    inventarios_csv: Path | None = None,
    incidencias_csv: Path | None = None,
    reservas_csv: Path | None = None,
    activos_csv: Path | None = None,
    aplicar: bool = False,
    actor: str = "migracion_apertura",
    nucleo=None,
    hotel=None,
) -> dict:
    """Ejecuta validación (`--dry-run`) o aplicación idempotente (`--aplicar`) y emite el acta."""
    acta = {
        "generado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modo": "aplicar" if aplicar else "dry-run",
        "fecha_corte": FECHA_CORTE_APERTURA.isoformat(),
        "empresa_id": empresa_id,
        "secciones": {},
    }
    if inventarios_csv is not None:
        acta["secciones"]["inventarios"] = cargar_inventarios_csv(conexion, inventarios_csv, aplicar=aplicar, actor=actor)
    if incidencias_csv is not None:
        acta["secciones"]["incidencias"] = cargar_incidencias_csv(conexion, incidencias_csv, aplicar=aplicar, actor=actor)
    if activos_csv is not None:
        acta["secciones"]["activos"] = cargar_activos_csv(conexion, activos_csv, aplicar=aplicar, actor=actor)
    if reservas_csv is not None:
        acta["secciones"]["reservas"] = cargar_reservas_apertura_csv(
            conexion, empresa_id, reservas_csv, aplicar=aplicar, actor=actor, nucleo=nucleo, hotel=hotel,
        )
    total_errores = sum(len(s["errores"]) for s in acta["secciones"].values())
    acta["aprobado"] = total_errores == 0
    acta["total_errores"] = total_errores
    return acta
