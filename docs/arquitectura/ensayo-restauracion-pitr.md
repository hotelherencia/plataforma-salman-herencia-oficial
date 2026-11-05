# Ensayo de restauración del PITR (OPS-A01, #332)

El PITR del servicio PostgreSQL de Railway existe y es funcional (activado el
2026-11-02: pgBackRest, full semanal + diferencial diaria, retención ~4
semanas). Este documento cierra la parte que faltaba: **probar** que una
restauración sirve para operar, y medir RPO/RTO de verdad.

## Qué se valida

`scripts/ensayo_restauracion.py <DATABASE_URL>` verifica hechos sobre la base
restaurada: migraciones aplicadas (y cuál es la última, para comparar con
producción), legibilidad y conteo de las 18 tablas del negocio, invariantes
mínimos (reservas con fin > inicio, pagos ligados y de monto positivo,
auditoría con traza) y muestra el último evento de auditoría con su hora.
Código 0 = la restauración es operable.

La herramienta quedó validada el 2026-11-05 con un ciclo local completo
(pg_dump de una base con datos → restore a base fresca → script en verde,
"LA RESTAURACIÓN ES OPERABLE").

## Procedimiento desde Railway (a ejecutar con acceso al dashboard)

1. **Railway → servicio `postgres` → Backups**: elegir "Restore" / "Fork" con
   el punto en el tiempo deseado (o el más reciente) hacia un servicio NUEVO
   (no tocar el productivo). Anotar la hora del punto elegido (base del RPO).
2. **Obtener la URL** del servicio restaurado (Railway la expone como
   variable `DATABASE_URL` del nuevo servicio; si el script corre fuera de
   Railway, habilitar el dominio público temporal del nuevo servicio).
3. **Correr el ensayo**:
   ```bash
   .venv/bin/python scripts/ensayo_restauracion.py "$DATABASE_URL_RESTAURADA"
   ```
4. **Medir y registrar** en la issue #332: hora del punto de restore, hora del
   veredicto en verde (RTO), diferencia RPO = hora del último evento de
   auditoría visible vs hora del incidente simulado, y duración total.
5. **Destruir el servicio restaurado** (el fork cuesta por minuto).

## Alternativa con archivo de respaldo

Si se dispone de un dump (pgBackRest vía soporte de Railway, o un `pg_dump`
programado propio): crear base local, `pg_restore`/psql, y correr el mismo
script. Útil como ensayo sin tocar la cuenta, aunque no mide el pipeline de
Railway en sí.

## Frecuencia sugerida

Trimestral, o antes del primer despliegue que toque migraciones destructivas.
