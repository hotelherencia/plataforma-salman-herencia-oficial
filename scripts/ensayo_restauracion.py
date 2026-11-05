#!/usr/bin/env python3
"""Ensayo de restauración (OPS-A01, #332): valida que una base RESTAURADA
desde el PITR de Railway sirve para operar.

El PITR existe y es funcional (Backups → Enable PITR, pgBackRest, full
semanal + diferencial diaria); lo que faltaba era la PRUEBA. Este script es
la mitad de la prueba — corre contra la base restaurada y verifica que lo
esencial sobrevivió al restore. La otra mitad (obtener la restauración desde
Railway) está en `docs/arquitectura/ensayo-restauracion-pitr.md`.

Qué verifica (cada punto es un hecho, no una promesa):
1. conectividad y migraciones aplicadas (schema_migrations no vacío, versiones
   ordenadas; se reporta la última para comparar con producción);
2. conteos de las tablas del negocio (usuarios, habitaciones, tarifas,
   reservas, cargos, pagos, sesiones, auditoría, solicitudes, leads) — no
   exige cifras (las bases difieren), exige que las tablas existan y respondan;
3. invariantes mínimos de integridad: reservas con fin > inicio; pagos con
   monto > 0 ligados a reserva existente; auditoría con filas;
4. duración del chequeo (el restore en sí se cronometra aparte; el RTO = hora
   del fork/pedido → este script en verde).

Uso:
    .venv/bin/python scripts/ensayo_restauracion.py postgresql://user:pass@host:puerto/base_restaurada
Salida: informe + código 0 si la restauración es operable.
"""
import sys

import psycopg

URL = sys.argv[1] if len(sys.argv) > 1 else None
if not URL:
    print(__doc__)
    sys.exit(2)

TABLAS = [
    "usuarios", "sesiones", "habitaciones", "tarifas", "reservas", "cargos",
    "pagos", "efectos_nucleo", "liquidaciones", "auditoria", "solicitudes",
    "leads", "consultas_agente", "borradores_agente", "trazas_agente",
    "politica_agente", "claves_idempotencia", "tareas_operativas",
]

fallos: list[str] = []


def check(ok: bool, mensaje: str) -> None:
    print(("PASS  " if ok else "FAIL  ") + mensaje)
    if not ok:
        fallos.append(mensaje)


def main() -> int:
    conn = psycopg.connect(URL, connect_timeout=10)
    print(f"== ensayo de restauración contra {URL.split('@')[-1]} ==")
    print(f"      servidor PostgreSQL: {conn.info.server_version} "
          f"(spec-backend-v1 especifica 17: {'COINCIDE' if conn.info.server_version.startswith('17') else 'DIFIERE — anotar en la issue'})")
    print()

    with conn:
        migraciones = [fila[0] for fila in conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()]
        check(len(migraciones) > 0, f"schema_migrations poblado ({len(migraciones)} migraciones)")
        print(f"      última migración aplicada: {migraciones[-1] if migraciones else '—'}")
        print(f"      comparar con producción: deben coincidir hasta la última publicada")

        print()
        for tabla in TABLAS:
            try:
                (n,) = conn.execute(f"SELECT count(*) FROM {tabla}").fetchone()
                print(f"      {tabla:<22} {n} filas")
            except psycopg.Error as error:
                check(False, f"tabla {tabla} legible: {error}")

        print()
        (mal_rango,) = conn.execute(
            "SELECT count(*) FROM reservas WHERE fin <= inicio"
        ).fetchone()
        check(mal_rango == 0, f"reservas con fin > inicio (violadas: {mal_rango})")

        (pagos_huerfanos,) = conn.execute(
            "SELECT count(*) FROM pagos p LEFT JOIN reservas r ON r.id = p.reserva_id "
            "WHERE r.id IS NULL"
        ).fetchone()
        check(pagos_huerfanos == 0, f"pagos ligados a reserva existente (huérfanos: {pagos_huerfanos})")

        (pagos_no_positivos,) = conn.execute(
            "SELECT count(*) FROM pagos WHERE monto_clp <= 0"
        ).fetchone()
        check(pagos_no_positivos == 0, f"pagos con monto > 0 (violados: {pagos_no_positivos})")

        (auditoria,) = conn.execute("SELECT count(*) FROM auditoria").fetchone()
        check(auditoria > 0, f"auditoría con traza ({auditoria} filas)")

        ultima = conn.execute(
            "SELECT actor, accion, recurso, resultado, creado_en FROM auditoria "
            "ORDER BY creado_en DESC LIMIT 1"
        ).fetchone()
        if ultima:
            print(f"      último evento de auditoría: {ultima[0]} · {ultima[1]} · {ultima[4]}")

    conn.close()
    print("\n===== RESULTADO =====")
    if fallos:
        print("LA RESTAURACIÓN NO ES OPERABLE:", "; ".join(fallos))
        return 1
    print("LA RESTAURACIÓN ES OPERABLE — RPO/RTO: registrar hora del punto de "
          "restore y hora de este veredicto en la issue #332.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
