"""Carga borrador del inventario documental 2026-11-11 (capa B1).

Lee el lote propuesto (JSON) y crea habitaciones reales como
`fuera_de_servicio`, sin tarifas. Así el mantenedor las ve, pero
`/publico/disponibilidad` no las ofrece. No inventa vigencia de precios.
La capacidad viene marcada en el JSON como propuesta desde tipo; las
unidades `matrimonial_mas_1` siguen pendientes de verificación (R02).

Inventario real del titular: **solo HAB-01..17**. Cualquier otra id
(HAB-SINT-*, HAB-101.., etc.) se retira de la operación.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

LOTE_RELATIVO = Path("docs/datos/herencia-revision-2026-11-11/lote_b1_inventario_propuesto.json")
ESTABLECIMIENTO_HERENCIA = "EST-HERENCIA-001"
MOTIVO_SINTETICO = "inventario de prueba; reemplazado por documental 2026-11-11"
MOTIVO_AJENA = "fuera del inventario documental HAB-01..17 (2026-11-11); no es opción operativa"
MARCA_HERENCIA = "Hotel Herencia"
_RE_HAB_REAL = re.compile(r"^HAB-(0[1-9]|1[0-7])$")
IDS_INVENTARIO_REAL = tuple(f"HAB-{i:02d}" for i in range(1, 18))


def es_id_inventario_real(habitacion_id: str) -> bool:
    return bool(_RE_HAB_REAL.match(habitacion_id or ""))


def ruta_lote(raiz: Path | None = None) -> Path:
    base = raiz or Path(__file__).resolve().parents[1]
    return base / LOTE_RELATIVO


def cargar_lote(ruta: Path | None = None) -> dict:
    archivo = ruta or ruta_lote()
    return json.loads(archivo.read_text(encoding="utf-8"))


def sembrar_inventario_documental(
    conexion,
    *,
    establecimiento_id: str = ESTABLECIMIENTO_HERENCIA,
    retirar_sinteticas: bool = True,
    lote: dict | None = None,
) -> dict:
    """Inserta HAB-01..17 fuera de servicio. Idempotente (ON CONFLICT DO NOTHING)."""
    datos = lote or cargar_lote()
    creadas = 0
    omitidas = 0
    for hab in datos.get("habitaciones") or []:
        habitacion_id = hab["habitacion_id"]
        tipo = hab["tipo_salman"]
        capacidad = int(hab["capacidad_propuesta"])
        motivo = hab.get("motivo_fuera_de_servicio") or (
            f"inventario documental pendiente verificación ({MARCA_HERENCIA})"
        )
        antes = conexion.execute(
            "SELECT 1 FROM habitaciones WHERE id = %s", (habitacion_id,)
        ).fetchone()
        if antes is not None:
            omitidas += 1
            continue
        conexion.execute(
            "INSERT INTO habitaciones ("
            "id, establecimiento_id, tipo, capacidad, estado_operativo, "
            "motivo_fuera_de_servicio, fuera_de_servicio_desde"
            ") VALUES (%s, %s, %s, %s, 'fuera_de_servicio', %s, now())",
            (habitacion_id, establecimiento_id, tipo, capacidad, motivo),
        )
        creadas += 1

    sinteticas_retiradas = 0
    if retirar_sinteticas:
        retiro = retirar_inventario_ajeno(conexion)
        sinteticas_retiradas = retiro["fuera_de_servicio"] + retiro["eliminadas"]

    return {
        "creadas": creadas,
        "omitidas": omitidas,
        "sinteticas_retiradas": sinteticas_retiradas,
        "paquete_fecha": datos.get("paquete_fecha"),
    }


def retirar_inventario_ajeno(conexion) -> dict:
    """Saca de operación todo lo que no sea HAB-01..17.

    - Sin reservas/tarifas/cargos referenciados → DELETE (deja de aparecer).
    - Con historial → `fuera_de_servicio` permanente (no oferta).
    """
    filas = conexion.execute("SELECT id, estado_operativo FROM habitaciones FOR UPDATE").fetchall()
    eliminadas: list[str] = []
    fuera: list[str] = []
    for habitacion_id, estado in filas:
        if es_id_inventario_real(habitacion_id):
            continue
        refs = conexion.execute(
            "SELECT "
            "(SELECT count(*) FROM reservas WHERE habitacion_id = %s) + "
            "(SELECT count(*) FROM tarifas WHERE habitacion_id = %s) + "
            "(SELECT count(*) FROM tareas_operativas WHERE habitacion_id = %s) + "
            "(SELECT count(*) FROM solicitudes WHERE habitacion_id = %s)",
            (habitacion_id, habitacion_id, habitacion_id, habitacion_id),
        ).fetchone()[0]
        if refs == 0:
            conexion.execute("DELETE FROM habitaciones WHERE id = %s", (habitacion_id,))
            eliminadas.append(habitacion_id)
            continue
        if estado != "fuera_de_servicio":
            motivo = MOTIVO_SINTETICO if str(habitacion_id).startswith("HAB-SINT-") else MOTIVO_AJENA
            conexion.execute(
                "UPDATE habitaciones SET estado_operativo = 'fuera_de_servicio', "
                "motivo_fuera_de_servicio = %s, fuera_de_servicio_desde = now() "
                "WHERE id = %s",
                (motivo, habitacion_id),
            )
        fuera.append(habitacion_id)
    return {
        "eliminadas": len(eliminadas),
        "fuera_de_servicio": len(fuera),
        "ids_eliminadas": eliminadas,
        "ids_fuera_de_servicio": fuera,
    }
