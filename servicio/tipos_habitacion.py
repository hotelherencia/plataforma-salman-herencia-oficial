"""Tipos de habitación y alta de habitaciones por lote (entrega 1A).

Un tipo agrupa habitaciones y les da un precio base que heredan (ver
`precios.py`). Las habitaciones existentes quedaron asociadas a su tipo por
la migración 0021 sin cambiar ningún precio. El alta por lote crea N
habitaciones de un tipo con un patrón de numeración, todo o nada.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

import psycopg
from psycopg.errors import UniqueViolation

from . import precios

PATRON_ID_TIPO = r"^[a-z0-9][a-z0-9_]{0,49}$"
# En la ruta se aceptan también los tipos heredados de la migración 0021
# (cualquier texto de habitaciones.tipo, hasta 50 caracteres sin «/»).
PATRON_ID_TIPO_RUTA = r"^[^/]{1,50}$"
PATRON_PREFIJO = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,19}$"
MAX_LOTE = 100
_RE_ID_HABITACION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$")


class TipoInexistente(Exception):
    """404/422: el tipo pedido no existe."""


class TipoYaExiste(Exception):
    """409: ya hay un tipo con ese identificador."""


class TipoInactivo(Exception):
    """409: no se dan de alta habitaciones en un tipo inactivo."""


class LoteInvalido(Exception):
    """422: la numeración pedida no produce identificadores válidos."""


class HabitacionesYaExisten(Exception):
    """409: alguna habitación del lote ya existe; no se crea ninguna."""

    def __init__(self, ids: list[str]):
        super().__init__(f"ya existen: {', '.join(ids)}")
        self.ids = ids


_COLUMNAS = "id, nombre, capacidad_base, precio_base_clp, orden, activo, creado_en, actualizado_en"


def _a_dict(f) -> dict:
    return {
        "tipo_id": f[0],
        "nombre": f[1],
        "capacidad_base": f[2],
        "precio_base_clp": f[3],
        "orden": f[4],
        "activo": f[5],
        "creado_en": f[6].isoformat(),
        "actualizado_en": f[7].isoformat() if f[7] else None,
    }


def obtener(conexion: psycopg.Connection, tipo_id: str) -> dict | None:
    fila = conexion.execute(f"SELECT {_COLUMNAS} FROM tipos_habitacion WHERE id = %s", (tipo_id,)).fetchone()
    return _a_dict(fila) if fila else None


def listar(conexion: psycopg.Connection, hoy: date, filtro_inventario=None) -> list[dict]:
    """Tipos con sus habitaciones y de dónde sale el precio de hoy de cada una.

    `filtro_inventario(habitacion) -> bool` limita las habitaciones contadas
    (titular: solo su inventario operativo)."""
    tipos = [_a_dict(f) for f in conexion.execute(
        f"SELECT {_COLUMNAS} FROM tipos_habitacion ORDER BY orden, nombre, id"
    ).fetchall()]
    habitaciones = [
        {"habitacion_id": f[0], "tipo": f[1], "capacidad": f[2], "estado_operativo": f[3],
         "en_inventario": f[4], "precio_propio_clp": f[5]}
        for f in conexion.execute(
            "SELECT id, tipo, capacidad, estado_operativo, en_inventario, precio_propio_clp "
            "FROM habitaciones ORDER BY id"
        ).fetchall()
    ]
    if filtro_inventario is not None:
        habitaciones = [h for h in habitaciones if filtro_inventario(h)]
    tabla = precios.cargar(conexion, hoy, hoy + timedelta(days=1), [h["habitacion_id"] for h in habitaciones])
    por_tipo: dict[str, list[dict]] = {}
    for h in habitaciones:
        precio = tabla.precio(h["habitacion_id"], hoy)
        h["precio_hoy_clp"] = precio.precio_clp if precio else None
        h["origen_precio_hoy"] = precio.origen.split(":")[0] if precio else None
        h["en_servicio"] = h["estado_operativo"] != "fuera_de_servicio"
        por_tipo.setdefault(h["tipo"], []).append(h)
    salida = []
    for tipo in tipos:
        propias = por_tipo.get(tipo["tipo_id"], [])
        precios_hoy = [h["precio_hoy_clp"] for h in propias if h["precio_hoy_clp"]]
        tipo["habitaciones"] = propias
        tipo["resumen"] = {
            "habitaciones": len(propias),
            "en_servicio": sum(1 for h in propias if h["en_servicio"]),
            "heredan_precio_base": sum(1 for h in propias if h["origen_precio_hoy"] == precios.ORIGEN_TIPO),
            "con_precio_propio": sum(1 for h in propias if h["origen_precio_hoy"] == precios.ORIGEN_HABITACION),
            "con_tarifa_por_fechas": sum(1 for h in propias if h["origen_precio_hoy"] == precios.ORIGEN_TARIFA),
            "sin_precio_hoy": sum(1 for h in propias if h["precio_hoy_clp"] is None),
            "precio_hoy_min_clp": min(precios_hoy) if precios_hoy else None,
            "precio_hoy_max_clp": max(precios_hoy) if precios_hoy else None,
        }
        salida.append(tipo)
    return salida


def crear(
    conexion: psycopg.Connection, tipo_id: str, nombre: str, capacidad_base: int,
    precio_base_clp: int | None, orden: int,
) -> dict:
    fila = conexion.execute(
        "INSERT INTO tipos_habitacion (id, nombre, capacidad_base, precio_base_clp, orden) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING RETURNING id",
        (tipo_id, nombre, capacidad_base, precio_base_clp, orden),
    ).fetchone()
    if fila is None:
        raise TipoYaExiste(f"ya existe el tipo {tipo_id}")
    return obtener(conexion, tipo_id)


def editar(conexion: psycopg.Connection, tipo_id: str, cambios_pedidos: dict) -> dict:
    """Edita nombre, capacidad base, precio base (puede quedar null), orden o
    activo. Devuelve {"tipo": …, "cambios": {campo: [antes, después]}}."""
    actual = conexion.execute(
        f"SELECT {_COLUMNAS} FROM tipos_habitacion WHERE id = %s FOR UPDATE", (tipo_id,)
    ).fetchone()
    if actual is None:
        raise TipoInexistente(f"no existe el tipo {tipo_id}")
    antes = _a_dict(actual)
    cambios = {
        campo: [antes[campo], valor]
        for campo, valor in cambios_pedidos.items()
        if campo in ("nombre", "capacidad_base", "precio_base_clp", "orden", "activo") and antes[campo] != valor
    }
    if cambios:
        asignaciones = ", ".join(f"{campo} = %s" for campo in cambios)
        conexion.execute(
            f"UPDATE tipos_habitacion SET {asignaciones}, actualizado_en = clock_timestamp() WHERE id = %s",
            (*[v[1] for v in cambios.values()], tipo_id),
        )
    return {"tipo": obtener(conexion, tipo_id), "cambios": cambios}


def ids_del_lote(prefijo: str, desde_numero: int, cantidad: int, digitos: int) -> list[str]:
    ids = [f"{prefijo}{numero:0{digitos}d}" for numero in range(desde_numero, desde_numero + cantidad)]
    invalidos = [i for i in ids if not _RE_ID_HABITACION.match(i)]
    if invalidos:
        raise LoteInvalido(f"identificadores no válidos: {', '.join(invalidos[:3])}")
    if len(set(ids)) != len(ids):
        raise LoteInvalido("la numeración repite identificadores")
    return ids


def crear_lote(
    conexion: psycopg.Connection, *, tipo_id: str, cantidad: int, prefijo: str, desde_numero: int,
    digitos: int, capacidad: int | None, establecimiento_id: str,
) -> dict:
    """Alta de `cantidad` habitaciones del tipo, todo o nada. Nacen en
    servicio, limpias y marcadas `en_inventario`; su precio es el que
    hereden del tipo (sin precio base quedan «sin tarifa» hasta fijarlo)."""
    tipo = conexion.execute(
        "SELECT id, capacidad_base, activo, precio_base_clp FROM tipos_habitacion WHERE id = %s FOR SHARE",
        (tipo_id,),
    ).fetchone()
    if tipo is None:
        raise TipoInexistente(f"no existe el tipo {tipo_id}")
    if not tipo[2]:
        raise TipoInactivo(f"el tipo {tipo_id} está inactivo")
    ids = ids_del_lote(prefijo, desde_numero, cantidad, digitos)
    existentes = [
        f[0] for f in conexion.execute(
            "SELECT id FROM habitaciones WHERE id = ANY(%s) ORDER BY id", (ids,)
        ).fetchall()
    ]
    if existentes:
        raise HabitacionesYaExisten(existentes)
    capacidad_final = capacidad or tipo[1]
    try:
        with conexion.transaction(), conexion.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, en_inventario) "
                "VALUES (%s, %s, %s, %s, true)",
                [(i, establecimiento_id, tipo_id, capacidad_final) for i in ids],
            )
    except UniqueViolation as error:
        # Carrera con otro alta concurrente: nada de este lote queda creado.
        ocupados = [
            f[0] for f in conexion.execute(
                "SELECT id FROM habitaciones WHERE id = ANY(%s) ORDER BY id", (ids,)
            ).fetchall()
        ]
        raise HabitacionesYaExisten(ocupados or ids) from error
    return {
        "tipo_id": tipo_id,
        "capacidad": capacidad_final,
        "habitaciones": ids,
        "creadas": len(ids),
        "precio_base_clp": tipo[3],
        "sin_precio": tipo[3] is None,
    }
