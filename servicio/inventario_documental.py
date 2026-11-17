"""Carga del inventario documental 2026-11-11 (capa B1).

Inventario real del titular: **solo HAB-01..17**. Cualquier otra id
(HAB-SINT-*, HAB-101.., etc.) queda fuera de la operación.

W16-A02 (auditoría 2026-11-16): esta carga **nunca** borra historial. Antes,
el arranque con `INVENTARIO_DOCUMENTAL=1` eliminaba reservas, pagos, cargos y
liquidaciones de las habitaciones ajenas y reactivaba habitaciones retiradas
por mantención en cada reinicio. Ahora:

- La siembra de arranque solo **inserta** las HAB-01..17 que falten
  (idempotente) y nunca cambia el estado de una habitación existente.
- El retiro de habitaciones ajenas es una **baja lógica**
  (`fuera_de_servicio` con motivo); solo se elimina físicamente una
  habitación ajena **sin ningún historial** (sin reservas, solicitudes,
  tarifas ni tareas). Se ejecuta únicamente con el comando puntual
  `scripts/aplicar_documental_desde_env.py --retirar-ajenas`.
- La reactivación de HAB-01..17 fuera de servicio también es puntual
  (`--activar-reales`) y solo toca las que quedaron así por la carga B1
  (motivo nulo o de carga), nunca las retiradas por mantención.

Decisión operativa (2026-11-11, dueño): HAB-01..17 quedan **en servicio**
(`disponible`). El lote JSON puede documentar carga FDS/sin tarifa; la
oferta pública sigue sin tarifas hasta decisión de precios (D3), pero la
ocupación no debe listarlas todas como «fuera de servicio».

Decisión precios (2026-11-12, dueño): precios fijos referenciales
Single 47000 / Doble o matrimonial 55000 / Triple 65000 para todas las
fechas. Desde la migración 0022 se guardan como precio base del tipo (fuente
única de precio), ya no como tarifas por habitación. TAR-07 cuádruple sigue
bloqueada (R01).
"""
from __future__ import annotations

import json
import re
from pathlib import Path


LOTE_RELATIVO = Path("docs/datos/herencia-revision-2026-11-11/lote_b1_inventario_propuesto.json")
ESTABLECIMIENTO_HERENCIA = "EST-HERENCIA-001"
MOTIVO_SINTETICO = "inventario de prueba; reemplazado por documental 2026-11-11"
MOTIVO_AJENA = "fuera del inventario documental HAB-01..17 (2026-11-11); no es opción operativa"
# Motivos con los que la carga B1 dejó HAB-01..17 fuera de servicio: solo esas
# se reactivan con --activar-reales (una retirada por mantención conserva su motivo).
MOTIVOS_CARGA_B1 = (MOTIVO_SINTETICO, MOTIVO_AJENA, "carga documental B1")
MARCA_HERENCIA = "Hotel Herencia"
_RE_HAB_REAL = re.compile(r"^HAB-(0[1-9]|1[0-7])$")
IDS_INVENTARIO_REAL = tuple(f"HAB-{i:02d}" for i in range(1, 18))
PRECIO_FIJO_POR_TIPO = {
    "single": 47000,
    "doble": 55000,
    "matrimonial": 55000,
    "matrimonial_mas_1": 55000,
    "triple": 65000,
}


def es_id_inventario_real(habitacion_id: str) -> bool:
    return bool(_RE_HAB_REAL.match(habitacion_id or ""))


def es_inventario_operativo(habitacion: dict) -> bool:
    """Inventario operativo del titular: HAB-01..17 más las unidades que la
    administración dio de alta por lote (`en_inventario`, entrega 1A)."""
    habitacion_id = habitacion.get("habitacion_id") or habitacion.get("id") or ""
    return es_id_inventario_real(habitacion_id) or bool(habitacion.get("en_inventario"))


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
    retirar_sinteticas: bool = False,
    activar_reales: bool = False,
    lote: dict | None = None,
) -> dict:
    """Inserta las HAB-01..17 que falten, en servicio (disponible). Idempotente.

    Nunca modifica una habitación existente: una retirada por mantención
    sigue retirada después de un reinicio (W16-A02). `activar_reales` y
    `retirar_sinteticas` solo los usa el comando puntual.
    """
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

    activadas = {"activadas": 0}
    if activar_reales:
        activadas = activar_inventario_real(conexion)

    sinteticas_retiradas = 0
    if retirar_sinteticas:
        retiro = retirar_inventario_ajeno(conexion)
        sinteticas_retiradas = retiro["eliminadas"] + retiro["fuera_de_servicio"]

    return {
        "creadas": creadas,
        "omitidas": omitidas,
        "activadas": activadas["activadas"],
        "sinteticas_retiradas": sinteticas_retiradas,
        "paquete_fecha": datos.get("paquete_fecha"),
    }


def activar_inventario_real(conexion) -> dict:
    """Reincorpora HAB-01..17 que quedaron fuera_de_servicio **por la carga B1**.

    Solo comando puntual. Una habitación retirada por mantención (motivo
    propio) no se toca (W16-A02).
    """
    ids = list(IDS_INVENTARIO_REAL)
    filas = conexion.execute(
        "UPDATE habitaciones SET estado_operativo = 'disponible', "
        "motivo_fuera_de_servicio = NULL, fuera_de_servicio_desde = NULL "
        "WHERE id = ANY(%s) AND estado_operativo = 'fuera_de_servicio' "
        "AND (motivo_fuera_de_servicio IS NULL OR motivo_fuera_de_servicio = ANY(%s)) "
        "RETURNING id",
        (ids, list(MOTIVOS_CARGA_B1)),
    ).fetchall()
    return {"activadas": len(filas), "ids": [f[0] for f in filas]}


def precio_fijo_referencial(tipo_salman: str) -> int | None:
    return PRECIO_FIJO_POR_TIPO.get((tipo_salman or "").lower().strip())


def aplicar_precios_base_referenciales(
    conexion,
    *,
    lote: dict | None = None,
    solo_sin_precio: bool = False,
) -> dict:
    """Precios fijos referenciales del dueño (2026-11-12) en la fuente única:
    el precio base del TIPO de HAB-01..17 (mantenedor «Tipos, habitaciones y
    precios»), no tarifas por habitación (migración 0022).

    Por tipo se toma el precio referencial más repetido entre sus habitaciones
    documentales (empate: el menor). Idempotente: si el tipo ya tiene ese
    precio, se omite. Con `solo_sin_precio` (arranque) solo se completa el tipo
    que no tiene precio base: un precio fijado por la administración nunca se
    pisa al reiniciar.
    """
    datos = lote or cargar_lote()
    errores: list[dict] = []
    votos: dict[str, dict[int, int]] = {}
    for hab in datos.get("habitaciones") or []:
        habitacion_id = hab["habitacion_id"]
        if not es_id_inventario_real(habitacion_id):
            continue
        tarifa_doc = hab.get("tarifa_propuesta_por_tipo") or {}
        if not tarifa_doc.get("publicar_tarifa_activa"):
            continue
        precio = precio_fijo_referencial(hab.get("tipo_salman", ""))
        if precio is None:
            precio = int(tarifa_doc.get("monto_clp") or 0) or None
        if precio is None or precio <= 0:
            errores.append({"habitacion_id": habitacion_id, "error": "sin_precio"})
            continue
        fila = conexion.execute("SELECT tipo FROM habitaciones WHERE id = %s", (habitacion_id,)).fetchone()
        if fila is None:
            errores.append({"habitacion_id": habitacion_id, "error": "habitacion_inexistente"})
            continue
        conteo = votos.setdefault(fila[0], {})
        conteo[precio] = conteo.get(precio, 0) + 1
    actualizados: dict[str, int] = {}
    omitidos = 0
    for tipo, conteo in sorted(votos.items()):
        precio = sorted(conteo.items(), key=lambda par: (-par[1], par[0]))[0][0]
        actual = conexion.execute(
            "SELECT precio_base_clp FROM tipos_habitacion WHERE id = %s", (tipo,)
        ).fetchone()
        if actual is None or actual[0] == precio or (solo_sin_precio and actual[0] is not None):
            omitidos += 1
            continue
        conexion.execute(
            "UPDATE tipos_habitacion SET precio_base_clp = %s, actualizado_en = clock_timestamp() WHERE id = %s",
            (precio, tipo),
        )
        actualizados[tipo] = precio
    return {
        "tipos_actualizados": actualizados,
        "omitidos": omitidos,
        "errores": errores,
        "precios": dict(PRECIO_FIJO_POR_TIPO),
    }


_TABLAS_HISTORIAL = ("reservas", "solicitudes", "tarifas", "tareas_operativas")


def _tiene_historial(conexion, habitacion_id: str) -> bool:
    for tabla in _TABLAS_HISTORIAL:
        if conexion.execute(
            f"SELECT 1 FROM {tabla} WHERE habitacion_id = %s LIMIT 1", (habitacion_id,)
        ).fetchone() is not None:
            return True
    return False


def retirar_inventario_ajeno(conexion) -> dict:
    """Saca de la operación todo lo que no sea HAB-01..17 **sin borrar historial**.

    W16-A02: una habitación ajena con reservas, pagos, solicitudes, tarifas o
    tareas queda `fuera_de_servicio` con MOTIVO_AJENA (baja lógica); solo la
    que no tiene ningún historial se elimina. Nunca hay DELETE sobre reservas,
    pagos, cargos ni liquidaciones. Solo comando puntual, nunca en arranque.
    """
    filas = conexion.execute("SELECT id, estado_operativo FROM habitaciones FOR UPDATE").fetchall()
    eliminadas: list[str] = []
    fuera: list[str] = []
    for habitacion_id, estado in filas:
        if es_id_inventario_real(habitacion_id):
            continue
        if _tiene_historial(conexion, habitacion_id):
            if estado != "fuera_de_servicio":
                conexion.execute(
                    "UPDATE habitaciones SET estado_operativo = 'fuera_de_servicio', "
                    "motivo_fuera_de_servicio = %s, fuera_de_servicio_desde = now() "
                    "WHERE id = %s",
                    (MOTIVO_AJENA, habitacion_id),
                )
                fuera.append(habitacion_id)
            continue
        conexion.execute("DELETE FROM habitaciones WHERE id = %s", (habitacion_id,))
        eliminadas.append(habitacion_id)
    return {
        "eliminadas": len(eliminadas),
        "fuera_de_servicio": len(fuera),
        "ids_eliminadas": eliminadas,
        "ids_fuera_de_servicio": fuera,
    }
