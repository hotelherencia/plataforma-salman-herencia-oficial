"""Convenios tarifarios por institución, delegación o evento (SPEC-CONV-01).

Reglas de negocio:
- Solo `admin_hotel` / `administrador` crea o edita convenios; recepción y caja
  pueden listar convenios vigentes para seleccionarlos en nuevas reservas o
  revisar diferencias en el cierre diario.
- El precio convenio, la tarifa lista y la diferencia (`tarifa_convenio - tarifa_lista`)
  se calculan siempre en el servidor, nunca en el front.
- Soporta tarifa fija por tipo de habitación (`reglas_precio.por_tipo`) y/o
  porcentaje de descuento (`reglas_precio.descuento_pct`).
- Auditoría sin PII.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import psycopg
from psycopg.types.json import Json

from . import precios, roles, seguridad

TIPOS_CONVENIO = ("empresa", "evento", "delegacion")
ROLES_LECTURA_CONVENIOS = roles.con_admin_hotel("recepcion", "caja")
ROLES_GESTION_CONVENIOS = roles.con_admin_hotel()


class ConvenioInvalido(ValueError):
    """422: datos inválidos al crear o editar un convenio."""


class ConvenioConflicto(Exception):
    """409: convenio inexistente, inactivo o fuera de vigencia para la estadía."""


def _limpiar_texto(valor: str | None, max_len: int) -> str | None:
    if valor is None:
        return None
    limpio = " ".join(valor.split())
    return limpio[:max_len] if limpio else None


def _normalizar_reglas(reglas: dict | None) -> dict:
    if reglas is None:
        return {}
    if not isinstance(reglas, dict):
        raise ConvenioInvalido("reglas_precio debe ser un objeto JSON")
    salida: dict = {}
    descuento = reglas.get("descuento_pct")
    if descuento is not None:
        if isinstance(descuento, bool) or not isinstance(descuento, (int, float)):
            raise ConvenioInvalido("descuento_pct debe ser un número entre 0 y 100")
        descuento_val = round(float(descuento), 2)
        if descuento_val < 0 or descuento_val > 100:
            raise ConvenioInvalido("descuento_pct debe estar entre 0 y 100")
        salida["descuento_pct"] = descuento_val
    por_tipo = reglas.get("por_tipo")
    if por_tipo is not None:
        if not isinstance(por_tipo, dict):
            raise ConvenioInvalido("por_tipo debe ser un mapa tipo_habitacion -> tarifa_clp")
        mapa: dict[str, int] = {}
        for k, v in por_tipo.items():
            clave = str(k).strip()
            if not clave:
                continue
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0 or v > 100_000_000:
                raise ConvenioInvalido(f"tarifa fija inválida para tipo '{clave}'")
            mapa[clave] = v
        if mapa:
            salida["por_tipo"] = mapa
    if not salida:
        raise ConvenioInvalido("indica descuento_pct y/o tarifas fijas por tipo de habitación en reglas_precio")
    return salida


def _validar_cliente(conexion: psycopg.Connection, empresa_id: str, cliente_id: str | None) -> str | None:
    if not cliente_id:
        return None
    cid = cliente_id.strip()
    if not cid:
        return None
    existe = conexion.execute(
        "SELECT 1 FROM clientes WHERE id = %s",
        (cid,),
    ).fetchone()
    if not existe:
        raise ConvenioInvalido("cliente_id no corresponde a un cliente registrado de esta empresa")
    return cid


def _fila_convenio(f: tuple) -> dict:
    return {
        "convenio_id": f[0],
        "nombre": f[1],
        "tipo": f[2],
        "cliente_id": f[3],
        "cliente_nombre": f[4],
        "vigencia_desde": f[5].isoformat(),
        "vigencia_hasta": f[6].isoformat(),
        "reglas_precio": f[7] or {},
        "requiere_abono_pct": int(f[8]),
        "notas": f[9],
        "activo": bool(f[10]),
        "creado_por": f[11],
        "creado_en": f[12].isoformat(),
        "actualizado_en": f[13].isoformat(),
    }


_SELECT_CONVENIO = (
    "SELECT c.id, c.nombre, c.tipo, c.cliente_id, cl.nombre, c.vigencia_desde, c.vigencia_hasta, "
    "c.reglas_precio, c.requiere_abono_pct, c.notas, c.activo, c.creado_por, c.creado_en, c.actualizado_en "
    "FROM convenios_tarifarios c LEFT JOIN clientes cl ON cl.id = c.cliente_id "
)


def listar(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    solo_vigentes: bool = False,
    fecha: date | None = None,
) -> list[dict]:
    filtros = ["c.empresa_id = %s"]
    params: list = [empresa_id]
    if solo_vigentes:
        ref = fecha or date.today()
        filtros.append("c.activo = TRUE AND c.vigencia_desde <= %s AND c.vigencia_hasta >= %s")
        params.extend([ref, ref])
    filas = conexion.execute(
        _SELECT_CONVENIO + f"WHERE {' AND '.join(filtros)} ORDER BY c.activo DESC, c.vigencia_desde DESC, c.nombre",
        params,
    ).fetchall()
    return [_fila_convenio(f) for f in filas]


def obtener(conexion: psycopg.Connection, empresa_id: str, convenio_id: str) -> dict | None:
    fila = conexion.execute(
        _SELECT_CONVENIO + "WHERE c.empresa_id = %s AND c.id = %s",
        (empresa_id, convenio_id),
    ).fetchone()
    return _fila_convenio(fila) if fila else None


def crear(
    conexion: psycopg.Connection,
    empresa_id: str,
    *,
    nombre: str,
    tipo: str,
    vigencia_desde: date,
    vigencia_hasta: date,
    reglas_precio: dict,
    cliente_id: str | None = None,
    requiere_abono_pct: int = 50,
    notas: str | None = None,
    activo: bool = True,
    actor: str = "sistema",
) -> dict:
    nombre_limpio = _limpiar_texto(nombre, 160)
    if not nombre_limpio or len(nombre_limpio) < 2:
        raise ConvenioInvalido("el nombre del convenio es obligatorio (mínimo 2 caracteres)")
    if tipo not in TIPOS_CONVENIO:
        raise ConvenioInvalido("tipo inválido: usa empresa, evento o delegacion")
    if vigencia_hasta < vigencia_desde:
        raise ConvenioInvalido("vigencia_hasta debe ser igual o posterior a vigencia_desde")
    if isinstance(requiere_abono_pct, bool) or not (0 <= int(requiere_abono_pct) <= 100):
        raise ConvenioInvalido("requiere_abono_pct debe estar entre 0 y 100")
    reglas_norm = _normalizar_reglas(reglas_precio)
    cliente_ok = _validar_cliente(conexion, empresa_id, cliente_id)
    notas_limpias = _limpiar_texto(notas, 400)

    convenio_id = f"CNV-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO convenios_tarifarios "
        "(id, empresa_id, nombre, tipo, cliente_id, vigencia_desde, vigencia_hasta, "
        "reglas_precio, requiere_abono_pct, notas, activo, creado_por) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            convenio_id, empresa_id, nombre_limpio, tipo, cliente_ok,
            vigencia_desde, vigencia_hasta, Json(reglas_norm), int(requiere_abono_pct),
            notas_limpias, bool(activo), actor,
        ),
    )
    seguridad.auditar(
        conexion, actor, "convenio_alta", convenio_id,
        f"tipo={tipo},abono_pct={int(requiere_abono_pct)},activo={bool(activo)}",
    )
    return obtener(conexion, empresa_id, convenio_id)


def actualizar(
    conexion: psycopg.Connection,
    empresa_id: str,
    convenio_id: str,
    *,
    nombre: str | None = None,
    tipo: str | None = None,
    vigencia_desde: date | None = None,
    vigencia_hasta: date | None = None,
    reglas_precio: dict | None = None,
    cliente_id: str | None = None,
    actualizar_cliente: bool = False,
    requiere_abono_pct: int | None = None,
    notas: str | None = None,
    actualizar_notas: bool = False,
    activo: bool | None = None,
    actor: str = "sistema",
) -> dict:
    actual = obtener(conexion, empresa_id, convenio_id)
    if actual is None:
        raise seguridad.ErrorPermiso("acceso denegado")

    nombre_nuevo = _limpiar_texto(nombre, 160) if nombre is not None else actual["nombre"]
    if not nombre_nuevo or len(nombre_nuevo) < 2:
        raise ConvenioInvalido("el nombre del convenio es obligatorio (mínimo 2 caracteres)")
    tipo_nuevo = tipo if tipo is not None else actual["tipo"]
    if tipo_nuevo not in TIPOS_CONVENIO:
        raise ConvenioInvalido("tipo inválido: usa empresa, evento o delegacion")
    desde_nuevo = vigencia_desde or date.fromisoformat(actual["vigencia_desde"])
    hasta_nuevo = vigencia_hasta or date.fromisoformat(actual["vigencia_hasta"])
    if hasta_nuevo < desde_nuevo:
        raise ConvenioInvalido("vigencia_hasta debe ser igual o posterior a vigencia_desde")
    reglas_nuevas = _normalizar_reglas(reglas_precio) if reglas_precio is not None else actual["reglas_precio"]
    abono_nuevo = int(requiere_abono_pct) if requiere_abono_pct is not None else actual["requiere_abono_pct"]
    if not (0 <= abono_nuevo <= 100):
        raise ConvenioInvalido("requiere_abono_pct debe estar entre 0 y 100")
    cliente_nuevo = _validar_cliente(conexion, empresa_id, cliente_id) if actualizar_cliente else actual["cliente_id"]
    notas_nuevas = _limpiar_texto(notas, 400) if actualizar_notas else actual["notas"]
    activo_nuevo = bool(activo) if activo is not None else actual["activo"]

    conexion.execute(
        "UPDATE convenios_tarifarios SET nombre = %s, tipo = %s, cliente_id = %s, "
        "vigencia_desde = %s, vigencia_hasta = %s, reglas_precio = %s, requiere_abono_pct = %s, "
        "notas = %s, activo = %s, actualizado_en = now() "
        "WHERE id = %s AND empresa_id = %s",
        (
            nombre_nuevo, tipo_nuevo, cliente_nuevo, desde_nuevo, hasta_nuevo,
            Json(reglas_nuevas), abono_nuevo, notas_nuevas, activo_nuevo, convenio_id, empresa_id,
        ),
    )
    seguridad.auditar(
        conexion, actor, "convenio_edicion", convenio_id,
        f"tipo={tipo_nuevo},abono_pct={abono_nuevo},activo={activo_nuevo}",
    )
    return obtener(conexion, empresa_id, convenio_id)


def aplicar_a_cotizacion(
    conexion: psycopg.Connection,
    empresa_id: str,
    convenio_id: str,
    habitacion_id: str,
    cotizacion_lista: precios.Cotizacion,
    inicio: date,
    fin: date,
) -> tuple[precios.Cotizacion, dict, int, int]:
    """Aplica un convenio vigente a la cotización lista de una habitación.

    Retorna `(cotizacion_convenio, convenio_dict, tarifa_lista_clp, diferencia_convenio_clp)`.
    """
    conv = obtener(conexion, empresa_id, convenio_id)
    if conv is None or not conv["activo"]:
        raise ConvenioConflicto("el convenio indicado no existe o no está activo")
    v_desde = date.fromisoformat(conv["vigencia_desde"])
    v_hasta = date.fromisoformat(conv["vigencia_hasta"])
    ultima_noche = fin - timedelta(days=1)
    if inicio < v_desde or ultima_noche > v_hasta:
        raise ConvenioConflicto(
            f"el convenio «{conv['nombre']}» solo rige del {v_desde.isoformat()} al {v_hasta.isoformat()}"
        )
    fila_hab = conexion.execute(
        "SELECT tipo FROM habitaciones WHERE id = %s", (habitacion_id,),
    ).fetchone()
    tipo_hab = fila_hab[0] if fila_hab else ""
    reglas = conv["reglas_precio"] or {}
    por_tipo = reglas.get("por_tipo") or {}
    descuento_pct = reglas.get("descuento_pct")

    noches_conv: list[tuple[date, precios.PrecioNoche]] = []
    for noche, precio_noche in cotizacion_lista.noches:
        if tipo_hab in por_tipo and isinstance(por_tipo[tipo_hab], int) and por_tipo[tipo_hab] > 0:
            precio_final = int(por_tipo[tipo_hab])
        elif descuento_pct is not None:
            precio_final = max(1, int(round(precio_noche.precio_clp * (100.0 - float(descuento_pct)) / 100.0)))
        else:
            precio_final = precio_noche.precio_clp
        noches_conv.append((noche, precios.PrecioNoche(precio_final, f"convenio:{convenio_id}")))

    cotizacion_conv = precios.Cotizacion(inicio=inicio, noches=noches_conv, sin_tarifa=None)
    tarifa_lista = cotizacion_lista.tarifa_primera or 0
    tarifa_conv = cotizacion_conv.tarifa_primera or 0
    diferencia_por_noche = tarifa_conv - tarifa_lista
    return cotizacion_conv, conv, tarifa_lista, diferencia_por_noche
