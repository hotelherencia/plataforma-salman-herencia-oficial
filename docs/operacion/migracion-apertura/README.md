# Migración de apertura operativa — Corte 31-12-2026 (`F20` / `MIG-002..006`)

Scripts idempotentes y plantillas CSV saneadas (sin contraseñas, claves ni PII real en el repositorio) para ejecutar la carga inicial operativa antes del corte **01-01-2027**.

## Reglas de seguridad y saneamiento
- **Nunca** subir planillas originales con datos personales reales, contraseñas o credenciales al repositorio.
- Trabajar con copias CSV saneadas fuera del repo (o en ruta local temporal) y ejecutar primero `--dry-run` para emitir y revisar el **acta de validación**.
- Toda carga es **idempotente**: volver a ejecutar `--aplicar` sobre el mismo CSV no duplica productos, movimientos de stock, incidencias, reservas ni anticipos.

## Plantillas incluidas
1. `inventario_inicial_ejemplo.csv` — Carga en `0055` (`productos`, `core_stock_bodega` y `movimientos_stock`) para las 4 bodegas operativas:
   - `lavanderia` (`Lavandería`)
   - `insumos_aseo` (`Insumos Aseo`)
   - `insumos_desayuno` (`Insumos Desayuno`)
   - `cocina` (`Cocina`)
   > Los insumos internos no vendibles en minibar se cargan con `activo=false` para no aparecer como cargo de huésped en recepción, conservando su control de stock y stock mínimo.
2. `incidencias_iniciales_ejemplo.csv` — Carga en `0059` (`incidencias` + bitácora `incidencia_eventos`) con `id` determinístico por `codigo_externo` (`INC-APR-...`).
3. `reservas_y_anticipos_corte_2026_12_31_plantilla.csv` — Plantilla validada para reservas futuras (`salida > 2026-12-31`) y anticipos heredados al corte `31-12-2026` (exige `anticipo_medio` en `efectivo|debito|credito|transferencia` cuando `anticipo_clp > 0`, en línea con `#401`).

## Uso del script (`scripts/cargar_apertura_operativa.py`)

### 1. Validación previa sin escribir en la base (`--dry-run`, modo por defecto)
```bash
python scripts/cargar_apertura_operativa.py \
  --dry-run \
  --inventarios /ruta/saneada/inventarios.csv \
  --incidencias /ruta/saneada/incidencias.csv \
  --reservas /ruta/saneada/reservas_2027.csv \
  --acta-salida /tmp/acta-apertura.json
```

### 2. Aplicación idempotente (`--aplicar`)
```bash
python scripts/cargar_apertura_operativa.py \
  --aplicar \
  --inventarios /ruta/saneada/inventarios.csv \
  --incidencias /ruta/saneada/incidencias.csv \
  --reservas /ruta/saneada/reservas_2027.csv \
  --acta-salida /tmp/acta-apertura-aplicada.json
```

La conexión se toma desde `DATABASE_URL` (o `--database-url` apuntando a una BD de prueba). El script nunca imprime valores de variables de entorno ni credenciales.
