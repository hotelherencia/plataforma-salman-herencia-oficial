#!/usr/bin/env python3
"""Depura datos maqueteados/de prueba conservando la configuración del hotel.

Uso seguro:
  1) Simulación (solo lectura, modo por defecto):
     .venv/bin/python scripts/limpiar_datos_prueba.py --dry-run

  2) Ejecución real (genera respaldo JSON previo y luego TRUNCATE):
     .venv/bin/python scripts/limpiar_datos_prueba.py --ejecutar --confirmar BORRAR-DATOS-PRUEBA
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
from typing import Iterable

import psycopg
from psycopg import sql

CONFIRMACION_REQUERIDA = "BORRAR-DATOS-PRUEBA"

TABLAS_CONSERVAR: tuple[str, ...] = (
    "schema_migrations",
    "usuarios",
    "roles_catalogo",
    "empresa_modulos",
    "ajustes_plataforma",
    "ajustes",
    "habitaciones",
    "tipos_habitacion",
    "tarifas",
    "excepciones_precio",
    "politicas_hotel",
    "politica_agente",
    "comisiones_medios",
    "productos",
    "core_bodegas",
    "buzones_correo",
    "avisos_preferencias",
    "checklist_plantillas",
    "activos",
    "mantenciones_plan",
    "biblioteca_documentos",
    "archivos_documentos",
)

TABLAS_DEPURAR: tuple[str, ...] = (
    # Reservas y huéspedes
    "reserva_huespedes",
    "reserva_noches",
    "reasignaciones",
    "observaciones_habitacion",
    "reservas",
    "reservas_grupo",
    "huespedes",
    # Dinero, caja, CxC/CxP y bancos
    "imputaciones_pago",
    "pagos",
    "liquidaciones",
    "cargos",
    "caja_movimientos",
    "caja_turnos",
    "cierres_diarios",
    "cierres_mensuales",
    "movimientos_directos",
    "cxc_abonos",
    "cuentas_por_cobrar",
    "cxp_movimientos",
    "cuentas_por_pagar",
    "conciliaciones_bancarias",
    "cartola_movimientos",
    "cartolas_bancarias",
    "documentos_proveedor",
    "efectos_nucleo",
    "claves_idempotencia",
    # Clientes y contactos de prueba
    "contactos",
    "clientes",
    # Movimientos y saldos de stock de prueba (conserva catálogo productos y core_bodegas)
    "movimientos_stock",
    "core_stock_bodega",
    "importaciones_productos",
    "equivalencias_proveedor",
    # Operación, CRM, agente, avisos y trazas
    "freno_solicitudes_eventos",
    "solicitudes",
    "leads",
    "mensajes_whatsapp",
    "tarea_subtareas",
    "tareas_generales",
    "tareas_operativas",
    "incidencia_evidencias",
    "incidencia_eventos",
    "incidencias",
    "turno_cambios",
    "turnos",
    "comunicado_lecturas",
    "comunicados",
    "sugerencias",
    "consultas_agente",
    "borradores_agente",
    "trazas_agente",
    "avisos_envios",
    "avisos_eventos",
    "sesiones",
    "auditoria",
    "mantenciones_realizadas",
    "doc_control_ocupacion",
    "doc_ocupacion_reportada",
    "doc_registro",
    "doc_habitacion",
    "doc_paquete",
    "doc_tarifa",
)


def obtener_tablas_existentes(conn: psycopg.Connection) -> set[str]:
    """Obtiene los nombres de tablas base existentes en el esquema public."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        return {fila[0] for fila in cur.fetchall()}


def contar_filas(conn: psycopg.Connection, tablas: Iterable[str], existentes: set[str]) -> dict[str, int]:
    """Cuenta filas de cada tabla existente de la lista entregada."""
    conteos: dict[str, int] = {}
    with conn.cursor() as cur:
        for tabla in tablas:
            if tabla not in existentes:
                continue
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(tabla)))
            conteos[tabla] = int(cur.fetchone()[0])
    return conteos


def _serializar_valor(valor: object) -> object:
    if isinstance(valor, (dt.date, dt.datetime, dt.time)):
        return valor.isoformat()
    return str(valor) if type(valor).__name__ in {"Decimal", "UUID"} else valor


def respaldar_tablas_json(
    conn: psycopg.Connection,
    tablas: Iterable[str],
    existentes: set[str],
    destino_dir: Path,
) -> Path:
    """Exporta a JSON todas las filas de las tablas existentes antes de truncar."""
    destino_dir.mkdir(parents=True, exist_ok=True)
    with conn.cursor() as cur:
        for tabla in tablas:
            if tabla not in existentes:
                continue
            cur.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(tabla)))
            columnas = [desc.name for desc in cur.description or ()]
            filas = [
                {col: _serializar_valor(val) for col, val in zip(columnas, fila)}
                for fila in cur.fetchall()
            ]
            (destino_dir / f"{tabla}.json").write_text(
                json.dumps(filas, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    return destino_dir


def ejecutar_limpieza(
    conn: psycopg.Connection,
    tablas: Iterable[str],
    existentes: set[str],
) -> list[str]:
    """Trunca en una transacción las tablas operativas existentes."""
    objetivo = [t for t in tablas if t in existentes]
    if not objetivo:
        return []
    identificadores = sql.SQL(", ").join(sql.Identifier(t) for t in objetivo)
    with conn.cursor() as cur:
        cur.execute(sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(identificadores))
    conn.commit()
    return objetivo


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parsea los argumentos de línea de comandos del script."""
    parser = argparse.ArgumentParser(description="Depura datos de prueba en PostgreSQL conservando configuración.")
    parser.add_argument("--database-url", default=None, help="URL de conexión PostgreSQL (default: DATABASE_URL).")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra conteos sin modificar datos (default).")
    parser.add_argument("--ejecutar", action="store_true", help="Ejecuta respaldo JSON + TRUNCATE de tablas operativas.")
    parser.add_argument("--confirmar", default="", help=f"Debe ser exactamente '{CONFIRMACION_REQUERIDA}' para ejecutar.")
    parser.add_argument("--respaldo-dir", default=None, help="Directorio destino del respaldo JSON previo.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada CLI del script de depuración segura."""
    args = parse_args(argv)
    if args.ejecutar and args.confirmar != CONFIRMACION_REQUERIDA:
        print(f"ERROR: para ejecutar debes pasar --confirmar {CONFIRMACION_REQUERIDA}", file=sys.stderr)
        return 2

    db_url = args.database_url or os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: falta --database-url o variable de entorno DATABASE_URL.", file=sys.stderr)
        return 2

    with psycopg.connect(db_url) as conn:
        existentes = obtener_tablas_existentes(conn)
        conteos_depurar = contar_filas(conn, TABLAS_DEPURAR, existentes)
        conteos_conservar = contar_filas(conn, TABLAS_CONSERVAR, existentes)

        print("=== TABLAS A DEPURAR ===")
        for tabla, total in conteos_depurar.items():
            print(f"  {tabla}: {total}")
        print("=== TABLAS A CONSERVAR ===")
        for tabla, total in conteos_conservar.items():
            print(f"  {tabla}: {total}")

        if not args.ejecutar or args.dry_run:
            print("Modo simulación (--dry-run): no se modificó la base de datos.")
            return 0

        ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destino = Path(args.respaldo_dir) if args.respaldo_dir else Path("_respaldos_prueba") / ts
        respaldar_tablas_json(conn, TABLAS_DEPURAR, existentes, destino)
        limpiadas = ejecutar_limpieza(conn, TABLAS_DEPURAR, existentes)
        print(f"Respaldo JSON guardado en: {destino}")
        print(f"Limpieza completada en {len(limpiadas)} tablas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
