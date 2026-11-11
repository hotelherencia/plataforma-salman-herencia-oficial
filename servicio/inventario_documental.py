"""Carga del inventario documental 2026-11-11 (capa B1).

Inventario real del titular: **solo HAB-01..17**. Cualquier otra id
(HAB-SINT-*, HAB-101.., etc.) se elimina de la base operativa (con su
historial sintético/ajeno), no basta con marcarla fuera de servicio.

Decisión operativa (2026-11-11, dueño): HAB-01..17 quedan **en servicio**
(`disponible`). El lote JSON puede documentar carga FDS/sin tarifa; la
oferta pública sigue sin tarifas hasta decisión de precios (D3), pero la
ocupación no debe listarlas todas como «fuera de servicio».
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
    """Inserta HAB-01..17 en servicio (disponible). Idempotente."""
    datos = lote or cargar_lote()
    creadas = 0
    omitidas = 0
    for hab in datos.get("habitaciones") or []:
        habitacion_id = hab["habitacion_id"]
        tipo = hab["tipo_salman"]
        capacidad = int(hab["capacidad_propuesta"])
        antes = conexion.execute(
            "SELECT 1 FROM habitaciones WHERE id = %s", (habitacion_id,)
        ).fetchone()
        if antes is not None:
            omitidas += 1
            continue
        conexion.execute(
            "INSERT INTO habitaciones ("
            "id, establecimiento_id, tipo, capacidad, estado_operativo"
            ") VALUES (%s, %s, %s, %s, 'disponible')",
            (habitacion_id, establecimiento_id, tipo, capacidad),
        )
        creadas += 1

    activadas = activar_inventario_real(conexion)

    sinteticas_retiradas = 0
    if retirar_sinteticas:
        retiro = retirar_inventario_ajeno(conexion)
        sinteticas_retiradas = retiro["eliminadas"]

    return {
        "creadas": creadas,
        "omitidas": omitidas,
        "activadas": activadas["activadas"],
        "sinteticas_retiradas": sinteticas_retiradas,
        "paquete_fecha": datos.get("paquete_fecha"),
    }


def activar_inventario_real(conexion) -> dict:
    """Reincorpora HAB-01..17 si quedaron fuera_de_servicio por la carga B1."""
    ids = list(IDS_INVENTARIO_REAL)
    filas = conexion.execute(
        "UPDATE habitaciones SET estado_operativo = 'disponible', "
        "motivo_fuera_de_servicio = NULL, fuera_de_servicio_desde = NULL "
        "WHERE id = ANY(%s) AND estado_operativo = 'fuera_de_servicio' "
        "RETURNING id",
        (ids,),
    ).fetchall()
    return {"activadas": len(filas), "ids": [f[0] for f in filas]}


def _purgar_dependencias(conexion, habitacion_id: str) -> None:
    """Borra historial operativo que impide DELETE de la habitación ajena."""
    reserva_ids = [
        f[0]
        for f in conexion.execute(
            "SELECT id FROM reservas WHERE habitacion_id = %s", (habitacion_id,)
        ).fetchall()
    ]
    if reserva_ids:
        conexion.execute(
            "UPDATE solicitudes SET reserva_id = NULL WHERE reserva_id = ANY(%s)",
            (reserva_ids,),
        )
        conexion.execute("DELETE FROM liquidaciones WHERE reserva_id = ANY(%s)", (reserva_ids,))
        conexion.execute("DELETE FROM pagos WHERE reserva_id = ANY(%s)", (reserva_ids,))
        conexion.execute("DELETE FROM cargos WHERE reserva_id = ANY(%s)", (reserva_ids,))
        conexion.execute("DELETE FROM reservas WHERE id = ANY(%s)", (reserva_ids,))
    conexion.execute("DELETE FROM solicitudes WHERE habitacion_id = %s", (habitacion_id,))
    conexion.execute("DELETE FROM tarifas WHERE habitacion_id = %s", (habitacion_id,))
    conexion.execute("DELETE FROM tareas_operativas WHERE habitacion_id = %s", (habitacion_id,))


def retirar_inventario_ajeno(conexion) -> dict:
    """Elimina todo lo que no sea HAB-01..17 (incl. historial que las retenía)."""
    filas = conexion.execute("SELECT id FROM habitaciones FOR UPDATE").fetchall()
    eliminadas: list[str] = []
    for (habitacion_id,) in filas:
        if es_id_inventario_real(habitacion_id):
            continue
        _purgar_dependencias(conexion, habitacion_id)
        conexion.execute("DELETE FROM habitaciones WHERE id = %s", (habitacion_id,))
        eliminadas.append(habitacion_id)
    return {
        "eliminadas": len(eliminadas),
        "fuera_de_servicio": 0,
        "ids_eliminadas": eliminadas,
        "ids_fuera_de_servicio": [],
    }
