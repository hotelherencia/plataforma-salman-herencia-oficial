"""Carga borrador del inventario documental 2026-11-11 (capa B1).

Lee el lote propuesto (JSON) y crea habitaciones reales como
`fuera_de_servicio`, sin tarifas. Así el mantenedor las ve, pero
`/publico/disponibilidad` no las ofrece. No inventa vigencia de precios.
La capacidad viene marcada en el JSON como propuesta desde tipo; las
unidades `matrimonial_mas_1` siguen pendientes de verificación (R02).
"""
from __future__ import annotations

import json
from pathlib import Path

from .empresa_titular import EMPRESA_TITULAR_MARCA

LOTE_RELATIVO = Path("docs/datos/herencia-revision-2026-11-11/lote_b1_inventario_propuesto.json")
ESTABLECIMIENTO_HERENCIA = "EST-HERENCIA-001"
MOTIVO_SINTETICO = "inventario de prueba; reemplazado por documental 2026-11-11"


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
            f"inventario documental pendiente verificación ({EMPRESA_TITULAR_MARCA})"
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
        for n in range(1, 4):
            hid = f"HAB-SINT-10{n}"
            fila = conexion.execute(
                "SELECT estado_operativo FROM habitaciones WHERE id = %s FOR UPDATE",
                (hid,),
            ).fetchone()
            if fila is None:
                continue
            if fila[0] == "fuera_de_servicio":
                continue
            conexion.execute(
                "UPDATE habitaciones SET estado_operativo = 'fuera_de_servicio', "
                "motivo_fuera_de_servicio = %s, fuera_de_servicio_desde = now() "
                "WHERE id = %s",
                (MOTIVO_SINTETICO, hid),
            )
            sinteticas_retiradas += 1

    return {
        "creadas": creadas,
        "omitidas": omitidas,
        "sinteticas_retiradas": sinteticas_retiradas,
        "paquete_fecha": datos.get("paquete_fecha"),
    }
