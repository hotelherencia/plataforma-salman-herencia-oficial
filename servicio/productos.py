"""Catálogo de productos y stock compartido con el core (#357, #358 / V1-ISSUE-57).

- Mantenedor (administración del hotel): nombre, categoría, precio con IVA,
  activo, control de stock y stock mínimo de alerta.
- Stock por bodega/ubicación (`core_bodegas` / `core_stock_bodega`): compartido
  entre hotel (`minibar`), `cafeteria` y `bodega_principal`, usando el dominio
  transversal `core/incremento1/nucleo/stock.py`.
- El cargo se asienta con `producto_id` + cantidad y copia el precio vigente
  (histórico inmutable). Si el producto controla stock, el cargo lo descuenta
  en la misma transacción; sin stock suficiente → 409. El reverso devuelve el stock.
"""
from __future__ import annotations

import uuid

import psycopg

from core.incremento1.nucleo import stock as stock_core

CATEGORIAS = ("minibar", "cafeteria", "servicio", "extra")
_COLUMNAS = "id, nombre, categoria, precio_clp, activo, controla_stock, stock, codigo, costo_clp, stock_minimo"


class ProductoInvalido(Exception):
    """409: producto inexistente, inactivo, nombre repetido o sin stock."""


def _a_dict(f, por_bodega: dict[str, int] | None = None) -> dict:
    item = {
        "producto_id": f[0],
        "nombre": f[1],
        "categoria": f[2],
        "precio_clp": f[3],
        "activo": f[4],
        "controla_stock": f[5],
        "stock": f[6] if f[5] else None,
        "codigo": f[7],
        "costo_clp": f[8],
        "stock_minimo": f[9] if f[5] else 0,
    }
    if por_bodega is not None:
        item["por_bodega"] = por_bodega
    return item


def _bodegas_por_producto(conexion: psycopg.Connection, ids: list[str] | None = None) -> dict[str, dict[str, int]]:
    if ids is not None and not ids:
        return {}
    if ids is None:
        filas = conexion.execute(
            "SELECT producto_id, bodega_codigo, cantidad FROM core_stock_bodega WHERE cantidad > 0"
        ).fetchall()
    else:
        filas = conexion.execute(
            "SELECT producto_id, bodega_codigo, cantidad FROM core_stock_bodega "
            "WHERE producto_id = ANY(%s) AND cantidad > 0",
            (ids,),
        ).fetchall()
    mapa: dict[str, dict[str, int]] = {}
    for pid, bod, cant in filas:
        mapa.setdefault(pid, {})[bod] = int(cant)
    return mapa


def _asegurar_bodega_valida(conexion: psycopg.Connection, bodega_codigo: str) -> str:
    fila = conexion.execute(
        "SELECT codigo FROM core_bodegas WHERE codigo = %s AND activa",
        (bodega_codigo,),
    ).fetchone()
    if fila is None:
        raise ProductoInvalido(f"bodega «{bodega_codigo}» inexistente o inactiva")
    return fila[0]


def registrar_stock_bodega(
    conexion: psycopg.Connection,
    producto_id: str,
    bodega_codigo: str,
    delta: int,
    *,
    exigir_disponible_en_bodega: bool = False,
) -> None:
    """Actualiza el saldo en `core_stock_bodega` manteniendo consistencia con `productos.stock`."""
    if delta == 0:
        return
    _asegurar_bodega_valida(conexion, bodega_codigo)
    if delta > 0:
        conexion.execute(
            "INSERT INTO core_stock_bodega (producto_id, bodega_codigo, cantidad) VALUES (%s, %s, %s) "
            "ON CONFLICT (producto_id, bodega_codigo) "
            "DO UPDATE SET cantidad = core_stock_bodega.cantidad + EXCLUDED.cantidad, actualizado_en = now()",
            (producto_id, bodega_codigo, delta),
        )
        return

    pendiente = -delta
    fila = conexion.execute(
        "SELECT cantidad FROM core_stock_bodega WHERE producto_id = %s AND bodega_codigo = %s FOR UPDATE",
        (producto_id, bodega_codigo),
    ).fetchone()
    actual = int(fila[0]) if fila else 0
    if actual >= pendiente:
        conexion.execute(
            "UPDATE core_stock_bodega SET cantidad = cantidad - %s, actualizado_en = now() "
            "WHERE producto_id = %s AND bodega_codigo = %s",
            (pendiente, producto_id, bodega_codigo),
        )
        return
    if exigir_disponible_en_bodega:
        raise ProductoInvalido(f"stock insuficiente en bodega «{bodega_codigo}» (disponible: {actual})")

    # Descuento distribuido si la bodega por defecto no alcanza pero el total del producto sí.
    if actual > 0:
        conexion.execute(
            "UPDATE core_stock_bodega SET cantidad = 0, actualizado_en = now() "
            "WHERE producto_id = %s AND bodega_codigo = %s",
            (producto_id, bodega_codigo),
        )
        pendiente -= actual
    otras = conexion.execute(
        "SELECT bodega_codigo, cantidad FROM core_stock_bodega "
        "WHERE producto_id = %s AND bodega_codigo <> %s AND cantidad > 0 ORDER BY cantidad DESC FOR UPDATE",
        (producto_id, bodega_codigo),
    ).fetchall()
    for otra_bod, cant in otras:
        if pendiente <= 0:
            break
        tomar = min(int(cant), pendiente)
        conexion.execute(
            "UPDATE core_stock_bodega SET cantidad = cantidad - %s, actualizado_en = now() "
            "WHERE producto_id = %s AND bodega_codigo = %s",
            (tomar, producto_id, otra_bod),
        )
        pendiente -= tomar


def listar_bodegas(conexion: psycopg.Connection) -> list[dict]:
    filas = conexion.execute(
        "SELECT id, codigo, nombre, modulo, activa FROM core_bodegas WHERE activa ORDER BY id"
    ).fetchall()
    return [
        {"id": f[0], "codigo": f[1], "nombre": f[2], "modulo": f[3], "activa": bool(f[4])}
        for f in filas
    ]


def listar(conexion: psycopg.Connection, texto: str | None = None, categoria: str | None = None,
           incluir_inactivos: bool = False, codigo: str | None = None) -> list[dict]:
    filtros, parametros = [], []
    if codigo:
        filtros.append("lower(codigo) = lower(%s)")
        parametros.append(codigo.strip())
    if not incluir_inactivos:
        filtros.append("activo")
    if categoria:
        filtros.append("categoria = %s")
        parametros.append(categoria)
    for palabra in (texto or "").split():
        filtros.append("(nombre ILIKE %s OR categoria ILIKE %s OR codigo ILIKE %s)")
        parametros += [f"%{palabra}%", f"%{palabra}%", f"%{palabra}%"]
    consulta = f"SELECT {_COLUMNAS} FROM productos"
    if filtros:
        consulta += " WHERE " + " AND ".join(filtros)
    filas = conexion.execute(consulta + " ORDER BY categoria, nombre", parametros).fetchall()
    bodegas = _bodegas_por_producto(conexion, [f[0] for f in filas])
    return [_a_dict(f, bodegas.get(f[0], {})) for f in filas]


def crear(conexion: psycopg.Connection, nombre: str, categoria: str, precio_clp: int,
          controla_stock: bool, stock: int, actor: str, codigo: str | None = None,
          stock_minimo: int = 0) -> dict:
    producto_id = f"PRD-{uuid.uuid4().hex[:10]}"
    stock_inicial = stock if controla_stock else 0
    minimo = max(0, int(stock_minimo or 0)) if controla_stock else 0
    try:
        with conexion.transaction():
            conexion.execute(
                "INSERT INTO productos (id, nombre, categoria, precio_clp, controla_stock, stock, codigo, stock_minimo) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (producto_id, nombre.strip(), categoria, precio_clp, controla_stock, stock_inicial,
                 (codigo or "").strip() or None, minimo),
            )
    except psycopg.errors.UniqueViolation as error:
        if "codigo" in str(error):
            raise ProductoInvalido(f"el código {codigo} ya pertenece a otro producto") from error
        raise ProductoInvalido(f"ya existe un producto llamado «{nombre.strip()}»") from error
    if controla_stock and stock_inicial:
        bodega = stock_core.bodega_por_categoria(categoria)
        registrar_stock_bodega(conexion, producto_id, bodega, stock_inicial)
        _movimiento(conexion, producto_id, stock_inicial, "stock inicial", actor,
                    bodega_codigo=bodega, tipo="entrada")
    return obtener(conexion, producto_id)


def obtener(conexion: psycopg.Connection, producto_id: str, bloqueo: bool = False) -> dict:
    fila = conexion.execute(
        f"SELECT {_COLUMNAS} FROM productos WHERE id = %s" + (" FOR UPDATE" if bloqueo else ""), (producto_id,)
    ).fetchone()
    if fila is None:
        raise ProductoInvalido("ese producto no existe")
    bodegas = _bodegas_por_producto(conexion, [producto_id]).get(producto_id, {})
    return _a_dict(fila, bodegas)


def actualizar(conexion: psycopg.Connection, producto_id: str, cambios: dict) -> dict:
    obtener(conexion, producto_id, bloqueo=True)
    permitidos = {
        k: v for k, v in cambios.items()
        if k in ("nombre", "categoria", "precio_clp", "activo", "controla_stock", "codigo", "stock_minimo")
        and v is not None
    }
    if permitidos:
        asignaciones = ", ".join(f"{k} = %s" for k in permitidos)
        try:
            with conexion.transaction():
                conexion.execute(
                    f"UPDATE productos SET {asignaciones}, actualizado_en = now() WHERE id = %s",
                    (*permitidos.values(), producto_id),
                )
        except psycopg.errors.UniqueViolation as error:
            if "codigo" in str(error):
                raise ProductoInvalido("ese código ya pertenece a otro producto") from error
            raise ProductoInvalido("ya existe un producto con ese nombre") from error
    return obtener(conexion, producto_id)


def ajustar_stock(
    conexion: psycopg.Connection,
    producto_id: str,
    delta: int,
    motivo: str,
    actor: str,
    bodega_codigo: str | None = None,
) -> dict:
    """Ajuste manual (reposición o merma). El stock nunca queda negativo."""
    producto = obtener(conexion, producto_id, bloqueo=True)
    if not producto["controla_stock"]:
        raise ProductoInvalido("ese producto no controla stock")
    if producto["stock"] + delta < 0:
        raise ProductoInvalido(f"el ajuste deja el stock negativo (hay {producto['stock']})")
    bodega = bodega_codigo or stock_core.bodega_por_categoria(producto["categoria"])
    registrar_stock_bodega(conexion, producto_id, bodega, delta, exigir_disponible_en_bodega=bool(bodega_codigo and delta < 0))
    conexion.execute("UPDATE productos SET stock = stock + %s, actualizado_en = now() WHERE id = %s", (delta, producto_id))
    _movimiento(conexion, producto_id, delta, motivo, actor, bodega_codigo=bodega,
                tipo="entrada" if delta > 0 else "ajuste")
    return obtener(conexion, producto_id)


def transferir_bodega(
    conexion: psycopg.Connection,
    producto_id: str,
    origen: str,
    destino: str,
    cantidad: int,
    motivo: str,
    actor: str,
) -> dict:
    """Mueve stock entre bodegas (ej. bodega_principal → minibar o cafeteria) sin alterar el stock total."""
    if origen == destino:
        raise ProductoInvalido("la bodega de origen y destino deben ser distintas")
    if cantidad <= 0:
        raise ProductoInvalido("la cantidad a transferir debe ser mayor que cero")
    producto = obtener(conexion, producto_id, bloqueo=True)
    if not producto["controla_stock"]:
        raise ProductoInvalido("ese producto no controla stock")
    _asegurar_bodega_valida(conexion, origen)
    _asegurar_bodega_valida(conexion, destino)
    registrar_stock_bodega(conexion, producto_id, origen, -cantidad, exigir_disponible_en_bodega=True)
    registrar_stock_bodega(conexion, producto_id, destino, cantidad)
    _movimiento(conexion, producto_id, -cantidad, f"transferencia a {destino}: {motivo}", actor,
                bodega_codigo=origen, tipo="transferencia")
    _movimiento(conexion, producto_id, cantidad, f"transferencia desde {origen}: {motivo}", actor,
                bodega_codigo=destino, tipo="transferencia")
    return obtener(conexion, producto_id)


def descontar_para_cargo(conexion: psycopg.Connection, producto_id: str, cantidad: int, actor: str, cargo_id: str) -> dict:
    producto = obtener(conexion, producto_id, bloqueo=True)
    if not producto["activo"]:
        raise ProductoInvalido(f"«{producto['nombre']}» está inactivo")
    if producto["controla_stock"]:
        if producto["stock"] < cantidad:
            raise ProductoInvalido(f"sin stock de «{producto['nombre']}»: quedan {producto['stock']}")
        bodega = stock_core.bodega_por_categoria(producto["categoria"])
        registrar_stock_bodega(conexion, producto_id, bodega, -cantidad)
        conexion.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (cantidad, producto_id))
        _movimiento(conexion, producto_id, -cantidad, "cargo", actor, cargo_id,
                    bodega_codigo=bodega, tipo="salida")
    return producto


def devolver_por_reverso(conexion: psycopg.Connection, producto_id: str, cantidad: int, actor: str, cargo_id: str) -> None:
    producto = obtener(conexion, producto_id, bloqueo=True)
    if producto["controla_stock"]:
        bodega = stock_core.bodega_por_categoria(producto["categoria"])
        registrar_stock_bodega(conexion, producto_id, bodega, cantidad)
        conexion.execute("UPDATE productos SET stock = stock + %s WHERE id = %s", (cantidad, producto_id))
        _movimiento(conexion, producto_id, cantidad, "reverso de cargo", actor, cargo_id,
                    bodega_codigo=bodega, tipo="reverso")


def reporte_reposicion(
    conexion: psycopg.Connection,
    bodega: str | None = None,
    categoria: str | None = None,
    solo_alertas: bool = False,
) -> dict:
    """Reporte transversal de stock y alertas de reposición (#358)."""
    if bodega:
        _asegurar_bodega_valida(conexion, bodega)
    filtros = ["activo", "controla_stock"]
    params: list = []
    if categoria:
        filtros.append("categoria = %s")
        params.append(categoria)
    filas = conexion.execute(
        f"SELECT {_COLUMNAS} FROM productos WHERE {' AND '.join(filtros)} ORDER BY categoria, nombre",
        params,
    ).fetchall()
    bodegas_mapa = _bodegas_por_producto(conexion, [f[0] for f in filas])
    estados = []
    for f in filas:
        por_bod = bodegas_mapa.get(f[0], {})
        stock_vista = por_bod.get(bodega, 0) if bodega else int(f[6] or 0)
        estado = stock_core.evaluar_reposicion(
            producto_id=f[0],
            nombre=f[1],
            categoria=f[2],
            stock_actual=stock_vista,
            stock_minimo=int(f[9] or 0),
            costo_clp=f[8],
            por_bodega=por_bod,
        )
        if not solo_alertas or estado.nivel != "ok":
            estados.append(estado)
    estados.sort(key=lambda e: ({"sin_stock": 0, "bajo_minimo": 1, "ok": 2}[e.nivel], e.nombre.lower()))
    return {
        "bodega": bodega,
        "categoria": categoria,
        "resumen": stock_core.resumir_reposicion(estados),
        "bodegas": listar_bodegas(conexion),
        "items": [e.a_dict() for e in estados],
    }


def movimientos(conexion: psycopg.Connection, producto_id: str, limite: int = 50) -> list[dict]:
    obtener(conexion, producto_id)
    return [
        {
            "delta": f[0],
            "motivo": f[1],
            "actor": f[2],
            "cargo_id": f[3],
            "bodega_codigo": f[4],
            "tipo": f[5],
            "registrado_en": f[6].isoformat(),
        }
        for f in conexion.execute(
            "SELECT delta, motivo, actor, cargo_id, bodega_codigo, tipo, creado_en "
            "FROM movimientos_stock WHERE producto_id = %s ORDER BY creado_en DESC LIMIT %s",
            (producto_id, limite),
        ).fetchall()
    ]


def _movimiento(
    conexion,
    producto_id,
    delta,
    motivo,
    actor,
    cargo_id=None,
    importacion_id=None,
    bodega_codigo: str | None = None,
    tipo: str | None = None,
) -> None:
    bod = bodega_codigo or stock_core.BODEGA_PRINCIPAL
    tipo_mov = tipo or ("entrada" if delta > 0 else "salida")
    conexion.execute(
        "INSERT INTO movimientos_stock (id, producto_id, delta, motivo, actor, cargo_id, importacion_id, bodega_codigo, tipo) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (f"MOV-{uuid.uuid4().hex[:12]}", producto_id, delta, motivo[:200], actor, cargo_id, importacion_id, bod, tipo_mov),
    )
