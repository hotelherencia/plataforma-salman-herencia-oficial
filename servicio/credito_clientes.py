"""Contable 2.2 (#392 / RES-008 / REC-003 / FIN-002): políticas de crédito por cliente
o empresa, Salida con deuda autorizada y cuentas por cobrar con antigüedad.

Reglas clave:
- Políticas disponibles por cliente: `pago_al_registrarse`, `credito_autorizado`
  (límite y plazo en días) y `garantia_salida` (garantía con tarjeta cobrada a la Salida).
- Solo `admin_hotel` puede modificar la política, límite o plazo de crédito.
- PCI: nunca se guarda número completo de tarjeta ni CVV (solo marca y últimos 4 dígitos).
- Tramos de antigüedad en cuentas por cobrar: `0-30`, `31-60`, `61-90`, `mas_90` días
  (más bandera `al_dia` cuando aún no vence).
- Abonos sobre cuentas por cobrar: estrictamente append-only e idempotentes.
"""
from __future__ import annotations

import re
import uuid
from datetime import date, timedelta

import psycopg

from . import clientes, cobro, contabilidad, hotel_sql, roles, seguridad

POLITICAS_CREDITO = ("pago_al_registrarse", "credito_autorizado", "garantia_salida")
ROLES_EDICION_CREDITO = roles.con_admin_hotel()
ROLES_CXC = roles.con_admin_hotel("caja")
ROLES_SALIDA_CREDITO = roles.con_admin_hotel("recepcion")

_RE_DIGITOS_LARGOS = re.compile(r"\d[\d\s-]{10,}\d")


class CreditoInvalido(ValueError):
    """422: datos inválidos de política de crédito o abono CxC."""


class CreditoConflicto(Exception):
    """409: exceso de cupo, política incompatible o saldo inválido."""

    def __init__(self, mensaje: str, *, supera_limite: bool = False, deuda_actual_clp: int = 0, cupo_clp: int = 0):
        super().__init__(mensaje)
        self.supera_limite = supera_limite
        self.deuda_actual_clp = deuda_actual_clp
        self.cupo_clp = cupo_clp


def _validar_sin_pci(*valores: str | None) -> None:
    for v in valores:
        if not v:
            continue
        if _RE_DIGITOS_LARGOS.search(v) or len(re.sub(r"\D", "", v)) >= 12:
            raise CreditoInvalido("PCI: nunca registres el número completo de una tarjeta ni su CVV")


def _tramo_antiguedad(dias_mora: int) -> str:
    if dias_mora <= 30:
        return "0-30"
    if dias_mora <= 60:
        return "31-60"
    if dias_mora <= 90:
        return "61-90"
    return "mas_90"


def _abonos_de_cxc(conexion: psycopg.Connection, cxc_id: str) -> list[dict]:
    filas = conexion.execute(
        "SELECT id, monto_clp, medio, comprobante, nota, actor, creado_en "
        "FROM cxc_abonos WHERE cxc_id = %s ORDER BY creado_en ASC, id ASC",
        (cxc_id,),
    ).fetchall()
    return [
        {
            "abono_id": f[0],
            "monto_clp": int(f[1]),
            "medio": f[2],
            "comprobante": f[3],
            "nota": f[4],
            "actor": f[5],
            "registrado_en": f[6].isoformat(),
        }
        for f in filas
    ]


def _construir_item_cxc(conexion: psycopg.Connection, f: tuple, hoy: date) -> dict:
    cxc_id = f[0]
    abonos = _abonos_de_cxc(conexion, cxc_id)
    abonado = sum(a["monto_clp"] for a in abonos)
    monto_orig = int(f[3])
    saldo = max(0, monto_orig - abonado)
    fecha_emision: date = f[4]
    fecha_venc: date = f[5]
    dias_desde_emision = max(0, (hoy - fecha_emision).days)
    dias_vencido = max(0, (hoy - fecha_venc).days)
    vencida = saldo > 0 and hoy > fecha_venc
    tramo = _tramo_antiguedad(dias_vencido if vencida else dias_desde_emision)
    return {
        "cxc_id": cxc_id,
        "reserva_id": f[1],
        "habitacion_id": f[10],
        "huesped_nombre": f[11],
        "cliente_id": f[2],
        "cliente_nombre": f[12],
        "cliente_rut": clientes.rut_visible(f[13]),
        "monto_original_clp": monto_orig,
        "abonado_clp": abonado,
        "saldo_pendiente_clp": saldo,
        "fecha_emision": fecha_emision.isoformat(),
        "fecha_vencimiento": fecha_venc.isoformat(),
        "dias_vencido": dias_vencido,
        "vencida": vencida,
        "tramo_antiguedad": tramo,
        "politica_aplicada": f[6],
        "estado": f[7],
        "nota": f[8],
        "registrada_en": f[9].isoformat(),
        "abonos": abonos,
    }


def configurar_credito(
    conexion: psycopg.Connection,
    empresa_id: str,
    cliente_id: str,
    *,
    politica_credito: str,
    cupo_credito_clp: int,
    plazo_dias: int,
    garantia_tarjeta_marca: str | None = None,
    garantia_tarjeta_ultimos4: str | None = None,
    actor: str,
) -> dict:
    """Fija la política de crédito de un cliente o empresa (solo admin_hotel)."""
    if politica_credito not in POLITICAS_CREDITO:
        raise CreditoInvalido("política inválida: usa pago_al_registrarse, credito_autorizado o garantia_salida")
    if cupo_credito_clp < 0:
        raise CreditoInvalido("el cupo de crédito debe ser mayor o igual a 0")
    if not (0 <= plazo_dias <= 365):
        raise CreditoInvalido("el plazo en días debe estar entre 0 y 365")
    if politica_credito == "credito_autorizado" and cupo_credito_clp <= 0:
        raise CreditoInvalido("el crédito autorizado exige un cupo de crédito mayor que $0")
    marca = (garantia_tarjeta_marca or "").strip()[:30] or None
    ult4 = (garantia_tarjeta_ultimos4 or "").strip() or None
    _validar_sin_pci(marca, ult4)
    if ult4 is not None and not re.fullmatch(r"\d{4}", ult4):
        raise CreditoInvalido("últimos 4 dígitos de tarjeta: exactamente 4 números")
    if politica_credito != "garantia_salida":
        marca = ult4 = None

    existe = conexion.execute("SELECT id FROM clientes WHERE id = %s FOR UPDATE", (cliente_id,)).fetchone()
    if not existe:
        raise clientes.ClienteInexistente("cliente inexistente")

    conexion.execute(
        "UPDATE clientes SET politica_credito = %s, cupo_credito_clp = %s, plazo_dias = %s, "
        "garantia_tarjeta_marca = %s, garantia_tarjeta_ultimos4 = %s WHERE id = %s",
        (politica_credito, cupo_credito_clp, plazo_dias, marca, ult4, cliente_id),
    )
    seguridad.auditar(
        conexion, actor, "cliente_credito", cliente_id,
        f"politica={politica_credito},cupo={cupo_credito_clp},plazo={plazo_dias}",
    )
    return estado_credito_cliente(conexion, empresa_id, cliente_id)


def estado_credito_cliente(
    conexion: psycopg.Connection,
    empresa_id: str,
    cliente_id: str,
    hoy: date | None = None,
) -> dict:
    """Estado de crédito vigente del cliente: política, cupo, deuda abierta y alertas."""
    hoy = hoy or contabilidad.hoy_chile()
    c = conexion.execute(
        "SELECT id, nombre, rut, tipo, politica_credito, cupo_credito_clp, plazo_dias, "
        "garantia_tarjeta_marca, garantia_tarjeta_ultimos4 "
        "FROM clientes WHERE id = %s",
        (cliente_id,),
    ).fetchone()
    if not c:
        raise clientes.ClienteInexistente("cliente inexistente")
    cuentas = listar_cxc(conexion, empresa_id, estado="pendientes", cliente_id=cliente_id, hoy=hoy)["cuentas_por_cobrar"]
    deuda = sum(x["saldo_pendiente_clp"] for x in cuentas)
    vencidas = [x for x in cuentas if x["vencida"]]
    cupo = int(c[5] or 0)
    supera_limite = cupo > 0 and deuda > cupo
    alertas: list[str] = []
    if supera_limite:
        alertas.append(f"Límite de crédito superado: deuda {deuda:,} CLP vs cupo {cupo:,} CLP".replace(",", "."))
    if vencidas:
        alertas.append(f"Tiene {len(vencidas)} cuenta(s) por cobrar vencida(s)")
    return {
        "cliente_id": c[0],
        "nombre": c[1],
        "rut": clientes.rut_visible(c[2]),
        "tipo": c[3],
        "politica_credito": c[4],
        "cupo_credito_clp": cupo,
        "plazo_dias": int(c[6] or 0),
        "garantia_tarjeta_marca": c[7],
        "garantia_tarjeta_ultimos4": c[8],
        "deuda_actual_clp": deuda,
        "cupo_disponible_clp": max(0, cupo - deuda) if cupo > 0 else 0,
        "supera_limite": supera_limite,
        "cuentas_vencidas": len(vencidas),
        "alertas": alertas,
        "cuentas_pendientes": cuentas,
    }


def resumen_credito_por_rut(
    conexion: psycopg.Connection,
    empresa_id: str,
    documento: str | None,
    documento_tipo: str | None,
    reserva_id: str,
    hoy: date | None = None,
) -> dict | None:
    """Resumen liviano de crédito/CxC asociado a una reserva (para ficha y Salida)."""
    hoy = hoy or contabilidad.hoy_chile()
    cxc_row = conexion.execute(
        "SELECT id, cliente_id, monto_original_clp, fecha_vencimiento, estado "
        "FROM cuentas_por_cobrar WHERE reserva_id = %s AND empresa_id = %s",
        (reserva_id, empresa_id),
    ).fetchone()
    cliente_id = cxc_row[1] if cxc_row else None
    if cliente_id is None and documento and (documento_tipo in (None, "rut")):
        try:
            rut_norm = clientes.rut_clave(documento)
        except clientes.RutInvalido:
            rut_norm = None
        if rut_norm:
            cli = clientes.buscar(conexion, rut_norm)
            if cli:
                cliente_id = cli[0]
    if not cliente_id:
        return None
    estado = estado_credito_cliente(conexion, empresa_id, cliente_id, hoy=hoy)
    return {
        "cliente_id": estado["cliente_id"],
        "politica_credito": estado["politica_credito"],
        "cupo_credito_clp": estado["cupo_credito_clp"],
        "plazo_dias": estado["plazo_dias"],
        "deuda_actual_clp": estado["deuda_actual_clp"],
        "cupo_disponible_clp": estado["cupo_disponible_clp"],
        "supera_limite": estado["supera_limite"],
        "cuentas_vencidas": estado["cuentas_vencidas"],
        "alertas": estado["alertas"],
        "cxc_id": cxc_row[0] if cxc_row else None,
        "cxc_estado": cxc_row[4] if cxc_row else None,
    }


def salida_con_credito(
    conexion: psycopg.Connection,
    hotel,
    empresa_id: str,
    reserva_id: str,
    cliente_id: str,
    actor: str,
    es_admin: bool = False,
    confirmar_exceso_cupo: bool = False,
    nota: str | None = None,
    hoy: date | None = None,
) -> dict:
    """Autoriza la Salida física dejando una cuenta por cobrar trazable (#392 / REC-003).

    Exige reserva `en_estadia` con saldo pendiente > 0 y cliente con política
    `credito_autorizado` o `garantia_salida`. Si excede el cupo configurado,
    bloquea con 409 salvo confirmación explícita de `admin_hotel`.
    """
    hoy = hoy or contabilidad.hoy_chile()
    fila_r = cobro._reserva_de_la_empresa(conexion, reserva_id, empresa_id, bloqueo=True)
    habitacion_id, estado_r = fila_r[1], fila_r[2]
    if estado_r != "en_estadia":
        raise CreditoConflicto("la Salida a crédito requiere una estadía en curso")

    neto, pagado = hotel_sql.cuenta(conexion, hotel, empresa_id, reserva_id)
    saldo = neto - pagado
    if saldo <= 0:
        raise CreditoConflicto("la cuenta no tiene saldo pendiente: usa la Salida estándar")

    estado_cli = estado_credito_cliente(conexion, empresa_id, cliente_id, hoy=hoy)
    politica = estado_cli["politica_credito"]
    if politica == "pago_al_registrarse":
        raise CreditoConflicto(
            "el cliente tiene política «pago al registrarse»: no admite Salida con deuda pendiente"
        )
    cupo = estado_cli["cupo_credito_clp"]
    deuda_proyectada = estado_cli["deuda_actual_clp"] + saldo
    if politica == "credito_autorizado" and cupo > 0 and deuda_proyectada > cupo:
        if not (es_admin and confirmar_exceso_cupo):
            raise CreditoConflicto(
                f"supera el límite de crédito del cliente (deuda proyectada {deuda_proyectada} CLP > cupo {cupo} CLP)",
                supera_limite=True,
                deuda_actual_clp=estado_cli["deuda_actual_clp"],
                cupo_clp=cupo,
            )

    plazo = estado_cli["plazo_dias"] if politica == "credito_autorizado" else 0
    fecha_venc = hoy + timedelta(days=plazo)
    cxc_id = f"CXC-{uuid.uuid4().hex[:12]}"
    nota_limpia = (nota or "").strip()[:300] or None

    with conexion.transaction():
        conexion.execute(
            "INSERT INTO cuentas_por_cobrar "
            "(id, empresa_id, reserva_id, cliente_id, monto_original_clp, fecha_emision, fecha_vencimiento, "
            "politica_aplicada, estado, nota, actor) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'abierta',%s,%s)",
            (cxc_id, empresa_id, reserva_id, cliente_id, saldo, hoy, fecha_venc, politica, nota_limpia, actor),
        )
        # Cierra estadía física: reserva finalizada, habitación disponible y sucia, tarea de limpieza pendiente.
        conexion.execute("UPDATE reservas SET estado = 'finalizada' WHERE id = %s", (reserva_id,))
        conexion.execute(
            "UPDATE habitaciones SET estado_operativo = 'disponible', estado_preparacion = 'sucia' WHERE id = %s",
            (habitacion_id,),
        )
        conexion.execute(
            "INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado) VALUES (%s, %s, 'limpieza', 'pendiente')",
            (f"TAR-{uuid.uuid4().hex[:12]}", habitacion_id),
        )
        seguridad.auditar(
            conexion, actor, "salida_credito", reserva_id,
            f"cxc={cxc_id},cliente={cliente_id},monto={saldo},politica={politica}",
        )

    return {
        "cxc_id": cxc_id,
        "reserva_id": reserva_id,
        "habitacion_id": habitacion_id,
        "cliente_id": cliente_id,
        "estado_reserva": "finalizada",
        "saldo_a_credito_clp": saldo,
        "fecha_emision": hoy.isoformat(),
        "fecha_vencimiento": fecha_venc.isoformat(),
        "politica_aplicada": politica,
        "alerta_limite": politica == "credito_autorizado" and cupo > 0 and deuda_proyectada > cupo,
    }


def listar_cxc(
    conexion: psycopg.Connection,
    empresa_id: str,
    estado: str = "pendientes",
    cliente_id: str | None = None,
    hoy: date | None = None,
) -> dict:
    """Listado de cuentas por cobrar agrupado por tramos de antigüedad (0-30, 31-60, 61-90, >90 días)."""
    hoy = hoy or contabilidad.hoy_chile()
    filtros = ["c.empresa_id = %s"]
    params: list = [empresa_id]
    if estado == "pendientes":
        filtros.append("c.estado IN ('abierta', 'parcial')")
    elif estado != "todos":
        filtros.append("c.estado = %s")
        params.append(estado)
    if cliente_id:
        filtros.append("c.cliente_id = %s")
        params.append(cliente_id)

    filas = conexion.execute(
        "SELECT c.id, c.reserva_id, c.cliente_id, c.monto_original_clp, c.fecha_emision, "
        "c.fecha_vencimiento, c.politica_aplicada, c.estado, c.nota, c.creado_en, "
        "r.habitacion_id, r.huesped_nombre, cl.nombre, cl.rut "
        "FROM cuentas_por_cobrar c "
        "JOIN reservas r ON r.id = c.reserva_id "
        "JOIN clientes cl ON cl.id = c.cliente_id "
        f"WHERE {' AND '.join(filtros)} "
        "ORDER BY c.fecha_vencimiento ASC, c.creado_en ASC",
        params,
    ).fetchall()

    items = [_construir_item_cxc(conexion, f, hoy) for f in filas]
    tramos = {
        "0-30": {"cantidad": 0, "monto_clp": 0},
        "31-60": {"cantidad": 0, "monto_clp": 0},
        "61-90": {"cantidad": 0, "monto_clp": 0},
        "mas_90": {"cantidad": 0, "monto_clp": 0},
    }
    total_pendiente = 0
    total_vencido = 0
    for it in items:
        if it["saldo_pendiente_clp"] > 0:
            total_pendiente += it["saldo_pendiente_clp"]
            t = tramos[it["tramo_antiguedad"]]
            t["cantidad"] += 1
            t["monto_clp"] += it["saldo_pendiente_clp"]
            if it["vencida"]:
                total_vencido += it["saldo_pendiente_clp"]

    return {
        "fecha_corte": hoy.isoformat(),
        "total_pendiente_clp": total_pendiente,
        "total_vencido_clp": total_vencido,
        "tramos": tramos,
        "cuentas_por_cobrar": items,
    }


def registrar_abono_cxc(
    conexion: psycopg.Connection,
    empresa_id: str,
    cxc_id: str,
    *,
    monto_clp: int,
    medio: str,
    comprobante: str | None = None,
    nota: str | None = None,
    clave_idempotencia: str,
    actor: str,
    hoy: date | None = None,
) -> dict:
    """Registra un abono append-only e idempotente sobre una cuenta por cobrar."""
    hoy = hoy or contabilidad.hoy_chile()
    if monto_clp <= 0:
        raise CreditoInvalido("el monto del abono debe ser mayor que $0")
    if medio not in ("efectivo", "debito", "credito", "transferencia"):
        raise CreditoInvalido("medio inválido: efectivo, debito, credito o transferencia")
    _validar_sin_pci(comprobante, nota)

    fila = conexion.execute(
        "SELECT c.id, c.reserva_id, c.cliente_id, c.monto_original_clp, c.fecha_emision, "
        "c.fecha_vencimiento, c.politica_aplicada, c.estado, c.nota, c.creado_en, "
        "r.habitacion_id, r.huesped_nombre, cl.nombre, cl.rut "
        "FROM cuentas_por_cobrar c "
        "JOIN reservas r ON r.id = c.reserva_id "
        "JOIN clientes cl ON cl.id = c.cliente_id "
        "WHERE c.id = %s AND c.empresa_id = %s FOR UPDATE OF c",
        (cxc_id, empresa_id),
    ).fetchone()
    if not fila:
        raise seguridad.ErrorPermiso("acceso denegado")
    if fila[7] in ("pagada", "anulada"):
        raise CreditoConflicto(f"la cuenta por cobrar ya está {fila[7]}")

    actual = _construir_item_cxc(conexion, fila, hoy)
    if monto_clp > actual["saldo_pendiente_clp"]:
        raise CreditoConflicto(
            f"el abono ({monto_clp} CLP) supera el saldo pendiente ({actual['saldo_pendiente_clp']} CLP)"
        )

    nuevo_saldo = actual["saldo_pendiente_clp"] - monto_clp
    nuevo_estado = "pagada" if nuevo_saldo == 0 else "parcial"
    abono_id = f"CXA-{uuid.uuid4().hex[:12]}"
    clave_mov = f"cxc_abono:{cxc_id}:{clave_idempotencia}"

    with conexion.transaction():
        conexion.execute(
            "INSERT INTO cxc_abonos (id, cxc_id, monto_clp, medio, comprobante, nota, clave_idempotencia, actor) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (abono_id, cxc_id, monto_clp, medio, (comprobante or "")[:60] or None,
             (nota or "")[:300] or None, clave_mov, actor),
        )
        conexion.execute(
            "UPDATE cuentas_por_cobrar SET estado = %s, actualizado_en = now() WHERE id = %s",
            (nuevo_estado, cxc_id),
        )
        seguridad.auditar(conexion, actor, "cxc_abono", cxc_id, f"monto={monto_clp},medio={medio},estado={nuevo_estado}")

    fila_post = conexion.execute(
        "SELECT c.id, c.reserva_id, c.cliente_id, c.monto_original_clp, c.fecha_emision, "
        "c.fecha_vencimiento, c.politica_aplicada, c.estado, c.nota, c.creado_en, "
        "r.habitacion_id, r.huesped_nombre, cl.nombre, cl.rut "
        "FROM cuentas_por_cobrar c JOIN reservas r ON r.id = c.reserva_id JOIN clientes cl ON cl.id = c.cliente_id "
        "WHERE c.id = %s",
        (cxc_id,),
    ).fetchone()
    return _construir_item_cxc(conexion, fila_post, hoy)
