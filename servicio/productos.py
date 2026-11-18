"""Catálogo de productos para los cargos (#357, 2026-11-18).

- Mantenedor (administración del hotel): nombre, categoría, precio con IVA,
  activo y control de stock.
- El cargo se asienta con `producto_id` + cantidad y copia el precio vigente
  (histórico inmutable). Si el producto controla stock, el cargo lo descuenta
  en la misma transacción; sin stock suficiente → 409 (no se vende lo que no
  hay). El reverso del cargo devuelve el stock.
"""
from __future__ import annotations

import uuid

import psycopg

CATEGORIAS = ("minibar", "cafeteria", "servicio", "extra")
_COLUMNAS = "id, nombre, categoria, precio_clp, activo, controla_stock, stock"


class ProductoInvalido(Exception):
    """409: producto inexistente, inactivo, nombre repetido o sin stock."""


def _a_dict(f) -> dict:
    return {"producto_id": f[0], "nombre": f[1], "categoria": f[2], "precio_clp": f[3],
            "activo": f[4], "controla_stock": f[5], "stock": f[6] if f[5] else None}


def listar(conexion: psycopg.Connection, texto: str | None = None, categoria: str | None = None,
           incluir_inactivos: bool = False) -> list[dict]:
    filtros, parametros = [], []
    if not incluir_inactivos:
        filtros.append("activo")
    if categoria:
        filtros.append("categoria = %s")
        parametros.append(categoria)
    for palabra in (texto or "").split():
        filtros.append("(nombre ILIKE %s OR categoria ILIKE %s)")
        parametros += [f"%{palabra}%", f"%{palabra}%"]
    consulta = f"SELECT {_COLUMNAS} FROM productos"
    if filtros:
        consulta += " WHERE " + " AND ".join(filtros)
    return [_a_dict(f) for f in conexion.execute(consulta + " ORDER BY categoria, nombre", parametros).fetchall()]


def crear(conexion: psycopg.Connection, nombre: str, categoria: str, precio_clp: int,
          controla_stock: bool, stock: int, actor: str) -> dict:
    producto_id = f"PRD-{uuid.uuid4().hex[:10]}"
    try:
        with conexion.transaction():
            conexion.execute(
                "INSERT INTO productos (id, nombre, categoria, precio_clp, controla_stock, stock) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (producto_id, nombre.strip(), categoria, precio_clp, controla_stock, stock if controla_stock else 0),
            )
    except psycopg.errors.UniqueViolation as error:
        raise ProductoInvalido(f"ya existe un producto llamado «{nombre.strip()}»") from error
    if controla_stock and stock:
        _movimiento(conexion, producto_id, stock, "stock inicial", actor)
    return obtener(conexion, producto_id)


def obtener(conexion: psycopg.Connection, producto_id: str, bloqueo: bool = False) -> dict:
    fila = conexion.execute(
        f"SELECT {_COLUMNAS} FROM productos WHERE id = %s" + (" FOR UPDATE" if bloqueo else ""), (producto_id,)
    ).fetchone()
    if fila is None:
        raise ProductoInvalido("ese producto no existe")
    return _a_dict(fila)


def actualizar(conexion: psycopg.Connection, producto_id: str, cambios: dict) -> dict:
    obtener(conexion, producto_id, bloqueo=True)
    permitidos = {k: v for k, v in cambios.items() if k in ("nombre", "categoria", "precio_clp", "activo", "controla_stock")
                  and v is not None}
    if permitidos:
        asignaciones = ", ".join(f"{k} = %s" for k in permitidos)
        try:
            with conexion.transaction():
                conexion.execute(
                    f"UPDATE productos SET {asignaciones}, actualizado_en = now() WHERE id = %s",
                    (*permitidos.values(), producto_id),
                )
        except psycopg.errors.UniqueViolation as error:
            raise ProductoInvalido("ya existe un producto con ese nombre") from error
    return obtener(conexion, producto_id)


def ajustar_stock(conexion: psycopg.Connection, producto_id: str, delta: int, motivo: str, actor: str) -> dict:
    """Ajuste manual (reposición o merma). El stock nunca queda negativo."""
    producto = obtener(conexion, producto_id, bloqueo=True)
    if not producto["controla_stock"]:
        raise ProductoInvalido("ese producto no controla stock")
    if producto["stock"] + delta < 0:
        raise ProductoInvalido(f"el ajuste deja el stock negativo (hay {producto['stock']})")
    conexion.execute("UPDATE productos SET stock = stock + %s, actualizado_en = now() WHERE id = %s", (delta, producto_id))
    _movimiento(conexion, producto_id, delta, motivo, actor)
    return obtener(conexion, producto_id)


def descontar_para_cargo(conexion: psycopg.Connection, producto_id: str, cantidad: int, actor: str, cargo_id: str) -> dict:
    producto = obtener(conexion, producto_id, bloqueo=True)
    if not producto["activo"]:
        raise ProductoInvalido(f"«{producto['nombre']}» está inactivo")
    if producto["controla_stock"]:
        if producto["stock"] < cantidad:
            raise ProductoInvalido(f"sin stock de «{producto['nombre']}»: quedan {producto['stock']}")
        conexion.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (cantidad, producto_id))
        _movimiento(conexion, producto_id, -cantidad, "cargo", actor, cargo_id)
    return producto


def devolver_por_reverso(conexion: psycopg.Connection, producto_id: str, cantidad: int, actor: str, cargo_id: str) -> None:
    producto = obtener(conexion, producto_id, bloqueo=True)
    if producto["controla_stock"]:
        conexion.execute("UPDATE productos SET stock = stock + %s WHERE id = %s", (cantidad, producto_id))
        _movimiento(conexion, producto_id, cantidad, "reverso de cargo", actor, cargo_id)


def movimientos(conexion: psycopg.Connection, producto_id: str, limite: int = 50) -> list[dict]:
    obtener(conexion, producto_id)
    return [
        {"delta": f[0], "motivo": f[1], "actor": f[2], "cargo_id": f[3], "registrado_en": f[4].isoformat()}
        for f in conexion.execute(
            "SELECT delta, motivo, actor, cargo_id, creado_en FROM movimientos_stock WHERE producto_id = %s "
            "ORDER BY creado_en DESC LIMIT %s",
            (producto_id, limite),
        ).fetchall()
    ]


def _movimiento(conexion, producto_id, delta, motivo, actor, cargo_id=None) -> None:
    conexion.execute(
        "INSERT INTO movimientos_stock (id, producto_id, delta, motivo, actor, cargo_id) VALUES (%s, %s, %s, %s, %s, %s)",
        (f"MOV-{uuid.uuid4().hex[:12]}", producto_id, delta, motivo[:200], actor, cargo_id),
    )
