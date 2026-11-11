"""Carga y consulta del paquete documental Herencia (no operativo)."""
from __future__ import annotations

import json
from pathlib import Path  # noqa: I001 — stdlib

PAQUETE_ID = "DOC-PKG-2026-11-11"

TABLAS_EN_REGISTRO = (
    "condiciones_habitacion",
    "textiles",
    "activos_comunes",
    "insumos",
    "proveedores",
    "politicas_declaradas",
    "activos_digitales",
    "servicios",
    "observaciones_operativas",
    "matriz_cumplimiento",
    "riesgos",
    "pendientes",
    "validaciones",
    "fuentes",
    "cobertura_hojas",
    "diccionario_datos",
)


def ruta_paquete(raiz: Path | None = None) -> Path:
    # servicio/documental.py → servicio/datos/documental/…
    base = raiz or Path(__file__).resolve().parent
    return base / "datos" / "documental" / "paquete_2026-11-11.json"


def cargar_json_paquete(ruta: Path | None = None) -> dict:
    return json.loads((ruta or ruta_paquete()).read_text(encoding="utf-8"))


def _num(valor):
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _int(valor):
    n = _num(valor)
    return int(n) if n is not None and float(n) == int(n) else (int(n) if n is not None else None)


def _bool(valor):
    if isinstance(valor, bool):
        return valor
    if valor is None or valor == "":
        return False
    return str(valor).lower() in ("true", "1", "si", "sí")


def _clave(tabla: str, fila: dict, idx: int) -> str:
    # IDs específicos primero: habitacion_id se repite en condiciones (442 filas).
    for cand in (
        "observacion_id",
        "textil_registro_id",
        "tarifa_id",
        "registro_id",
        "proveedor_id",
        "politica_id",
        "pendiente_id",
        "riesgo_id",
        "validacion_id",
        "requisito_id",
        "fuente_id",
        "activo_digital_id",
        "servicio_id",
        "activo_id",
        "insumo_id",
        "periodo",
        "habitacion_id",
    ):
        if fila.get(cand):
            return str(fila[cand])
    return f"{tabla}-{idx}"


def sembrar_paquete_documental(conexion, paquete: dict | None = None) -> dict:
    """Idempotente: si el paquete_id ya existe, no duplica (return ya_cargado)."""
    datos = paquete or cargar_json_paquete()
    pid = datos.get("id") or PAQUETE_ID
    existe = conexion.execute("SELECT 1 FROM doc_paquete WHERE id = %s", (pid,)).fetchone()
    if existe:
        return {"paquete_id": pid, "ya_cargado": True}

    conexion.execute(
        "INSERT INTO doc_paquete (id, fecha, sha256_zip, clasificacion, timezone) "
        "VALUES (%s, %s, %s, %s, %s)",
        (
            pid,
            datos.get("fecha") or "2026-11-11",
            datos.get("sha256_zip") or "",
            datos.get("clasificacion") or "GENERAL_DEPURADO",
            datos.get("timezone") or "America/Santiago",
        ),
    )

    bloque = datos.get("datos") or {}
    n_hab = 0
    for h in bloque.get("habitaciones") or []:
        conexion.execute(
            "INSERT INTO doc_habitacion ("
            "paquete_id, habitacion_id, numero, tipo_declarado, tipo_salman, "
            "capacidad_propuesta, capacidad_requiere_verificacion, capacidad_personas_origen, "
            "estado_venta_origen, fuente, estado_evidencia, verificado_en_terreno, payload"
            ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
            (
                pid,
                h.get("habitacion_id"),
                h.get("numero"),
                h.get("tipo_declarado"),
                h.get("tipo_salman"),
                h.get("capacidad_propuesta"),
                bool(h.get("capacidad_requiere_verificacion")),
                h.get("capacidad_personas") or None,
                h.get("estado_venta") or None,
                h.get("fuente"),
                h.get("estado_evidencia"),
                _bool(h.get("verificado_en_terreno")),
                json.dumps(h, ensure_ascii=False),
            ),
        )
        n_hab += 1

    n_tar = 0
    for t in bloque.get("tarifas_declaradas") or []:
        conexion.execute(
            "INSERT INTO doc_tarifa ("
            "paquete_id, tarifa_id, tipo_comercial, monto_clp, moneda, iva_incluido_declarado, "
            "canal, vigente_desde, vigente_hasta, aprobada_2027, nota, publicar_activa, payload"
            ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE,%s::jsonb)",
            (
                pid,
                t.get("tarifa_id"),
                t.get("tipo_comercial"),
                _int(t.get("monto_clp")),
                t.get("moneda"),
                _bool(t.get("iva_incluido_declarado")),
                t.get("canal"),
                t.get("vigente_desde") or None,
                t.get("vigente_hasta") or None,
                _bool(t.get("aprobada_2027")),
                t.get("nota") or None,
                json.dumps(t, ensure_ascii=False),
            ),
        )
        n_tar += 1

    n_ocu = 0
    for r in bloque.get("ocupacion_reportada") or []:
        conexion.execute(
            "INSERT INTO doc_ocupacion_reportada ("
            "paquete_id, registro_id, habitacion_id, periodo, valor_reportado, unidad_confirmada, "
            "interpretacion_propuesta, dias_calendario, estado_valor, es_kpi, fuente, payload"
            ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE,%s,%s::jsonb)",
            (
                pid,
                r.get("registro_id"),
                r.get("habitacion_id"),
                r.get("periodo"),
                _num(r.get("valor_reportado")),
                r.get("unidad_confirmada") or None,
                r.get("interpretacion_propuesta"),
                _int(r.get("dias_calendario")),
                r.get("estado_valor"),
                r.get("fuente"),
                json.dumps(r, ensure_ascii=False),
            ),
        )
        n_ocu += 1

    n_ctrl = 0
    for c in bloque.get("control_ocupacion") or []:
        conexion.execute(
            "INSERT INTO doc_control_ocupacion ("
            "paquete_id, periodo, suma_reportada, porcentaje_guardado_fuente, "
            "porcentaje_calendario_hipotetico, denominador_hipotetico, supuesto, fuente, payload"
            ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
            (
                pid,
                c.get("periodo"),
                _num(c.get("suma_reportada")),
                _num(c.get("porcentaje_guardado_fuente")),
                _num(c.get("porcentaje_calendario_hipotetico")),
                _num(c.get("denominador_hipotetico")),
                c.get("supuesto"),
                c.get("fuente"),
                json.dumps(c, ensure_ascii=False),
            ),
        )
        n_ctrl += 1

    n_reg = 0
    for tabla in TABLAS_EN_REGISTRO:
        for i, fila in enumerate(bloque.get(tabla) or []):
            conexion.execute(
                "INSERT INTO doc_registro (paquete_id, tabla, clave, payload) "
                "VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING",
                (pid, tabla, _clave(tabla, fila, i), json.dumps(fila, ensure_ascii=False)),
            )
            n_reg += 1

    return {
        "paquete_id": pid,
        "ya_cargado": False,
        "habitaciones": n_hab,
        "tarifas": n_tar,
        "ocupacion_reportada": n_ocu,
        "control_ocupacion": n_ctrl,
        "registros": n_reg,
    }


def resumen(conexion) -> dict:
    fila = conexion.execute(
        "SELECT id, fecha::text, sha256_zip, clasificacion, timezone, cargado_en "
        "FROM doc_paquete ORDER BY fecha DESC LIMIT 1"
    ).fetchone()
    if not fila:
        return {"cargado": False, "paquete": None}
    pid = fila[0]
    conteos = {
        "habitaciones": conexion.execute(
            "SELECT count(*) FROM doc_habitacion WHERE paquete_id=%s", (pid,)
        ).fetchone()[0],
        "tarifas": conexion.execute(
            "SELECT count(*) FROM doc_tarifa WHERE paquete_id=%s", (pid,)
        ).fetchone()[0],
        "ocupacion_reportada": conexion.execute(
            "SELECT count(*) FROM doc_ocupacion_reportada WHERE paquete_id=%s", (pid,)
        ).fetchone()[0],
        "ocupacion_con_valor": conexion.execute(
            "SELECT count(*) FROM doc_ocupacion_reportada WHERE paquete_id=%s AND valor_reportado IS NOT NULL",
            (pid,),
        ).fetchone()[0],
        "control_ocupacion": conexion.execute(
            "SELECT count(*) FROM doc_control_ocupacion WHERE paquete_id=%s", (pid,)
        ).fetchone()[0],
        "registros": conexion.execute(
            "SELECT count(*) FROM doc_registro WHERE paquete_id=%s", (pid,)
        ).fetchone()[0],
    }
    por_tabla = conexion.execute(
        "SELECT tabla, count(*) FROM doc_registro WHERE paquete_id=%s GROUP BY tabla ORDER BY tabla",
        (pid,),
    ).fetchall()
    return {
        "cargado": True,
        "paquete": {
            "id": fila[0],
            "fecha": fila[1],
            "sha256_zip": fila[2],
            "clasificacion": fila[3],
            "timezone": fila[4],
            "cargado_en": fila[5].isoformat() if fila[5] else None,
        },
        "conteos": conteos,
        "tablas_registro": {t: n for t, n in por_tabla},
        "aviso": (
            "Datos documentales: no son oferta ni cobro. "
            "Ocupación reportada no es KPI (unidad no confirmada)."
        ),
    }


def listar_habitaciones(conexion) -> list[dict]:
    filas = conexion.execute(
        "SELECT habitacion_id, numero, tipo_declarado, tipo_salman, capacidad_propuesta, "
        "capacidad_requiere_verificacion, estado_evidencia, verificado_en_terreno, payload "
        "FROM doc_habitacion ORDER BY habitacion_id"
    ).fetchall()
    return [
        {
            "habitacion_id": f[0],
            "numero": f[1],
            "tipo_declarado": f[2],
            "tipo_salman": f[3],
            "capacidad_propuesta": f[4],
            "capacidad_requiere_verificacion": f[5],
            "estado_evidencia": f[6],
            "verificado_en_terreno": f[7],
            "detalle": f[8],
        }
        for f in filas
    ]


def listar_tarifas(conexion) -> list[dict]:
    filas = conexion.execute(
        "SELECT tarifa_id, tipo_comercial, monto_clp, moneda, iva_incluido_declarado, canal, "
        "vigente_desde::text, vigente_hasta::text, aprobada_2027, nota, publicar_activa, payload "
        "FROM doc_tarifa ORDER BY tarifa_id"
    ).fetchall()
    return [
        {
            "tarifa_id": f[0],
            "tipo_comercial": f[1],
            "monto_clp": f[2],
            "moneda": f[3],
            "iva_incluido_declarado": f[4],
            "canal": f[5],
            "vigente_desde": f[6],
            "vigente_hasta": f[7],
            "aprobada_2027": f[8],
            "nota": f[9],
            "publicar_activa": f[10],
            "detalle": f[11],
        }
        for f in filas
    ]


def listar_ocupacion(conexion, periodo: str | None = None, habitacion_id: str | None = None) -> list[dict]:
    sql = (
        "SELECT registro_id, habitacion_id, periodo, valor_reportado, unidad_confirmada, "
        "interpretacion_propuesta, dias_calendario, estado_valor, es_kpi, fuente "
        "FROM doc_ocupacion_reportada WHERE 1=1"
    )
    params: list = []
    if periodo:
        sql += " AND periodo = %s"
        params.append(periodo)
    if habitacion_id:
        sql += " AND habitacion_id = %s"
        params.append(habitacion_id)
    sql += " ORDER BY periodo, habitacion_id"
    filas = conexion.execute(sql, params).fetchall()
    return [
        {
            "registro_id": f[0],
            "habitacion_id": f[1],
            "periodo": f[2],
            "valor_reportado": float(f[3]) if f[3] is not None else None,
            "unidad_confirmada": f[4],
            "interpretacion_propuesta": f[5],
            "dias_calendario": f[6],
            "estado_valor": f[7],
            "es_kpi": f[8],
            "fuente": f[9],
        }
        for f in filas
    ]


def listar_control_ocupacion(conexion) -> list[dict]:
    filas = conexion.execute(
        "SELECT periodo, suma_reportada, porcentaje_guardado_fuente, porcentaje_calendario_hipotetico, "
        "denominador_hipotetico, supuesto, fuente FROM doc_control_ocupacion ORDER BY periodo"
    ).fetchall()
    return [
        {
            "periodo": f[0],
            "suma_reportada": float(f[1]) if f[1] is not None else None,
            "porcentaje_guardado_fuente": float(f[2]) if f[2] is not None else None,
            "porcentaje_calendario_hipotetico": float(f[3]) if f[3] is not None else None,
            "denominador_hipotetico": float(f[4]) if f[4] is not None else None,
            "supuesto": f[5],
            "fuente": f[6],
            "es_kpi": False,
        }
        for f in filas
    ]


def listar_tabla(conexion, tabla: str, limite: int = 500) -> dict:
    if tabla in ("habitaciones", "tarifas_declaradas", "ocupacion_reportada", "control_ocupacion"):
        raise ValueError("use el endpoint tipado de esa tabla")
    if tabla not in TABLAS_EN_REGISTRO:
        raise ValueError("tabla desconocida")
    filas = conexion.execute(
        "SELECT clave, payload FROM doc_registro WHERE tabla = %s ORDER BY clave LIMIT %s",
        (tabla, limite),
    ).fetchall()
    total = conexion.execute(
        "SELECT count(*) FROM doc_registro WHERE tabla = %s", (tabla,)
    ).fetchone()[0]
    return {"tabla": tabla, "total": total, "filas": [{"clave": c, "payload": p} for c, p in filas]}
