# Plan de lotes (sin migración en esta pasada)

Orden global: hash → staging UTF-8 → R01–R10 → reconcile → dry-run → lote atómico → publicación selectiva.  
Esta pasada **solo** deja listos A0 y la documentación; **no** INSERT/PUT a producción.

## Lote A0 — Staging documental (APTO si G0)

| Incluye | Excluye |
|---|---|
| CSV/JSON del ZIP con hash verificado | Excel original con secretos/PII |
| `habitaciones`, tarifas inactivas, ocupación como observación | Filas inventadas |
| matriz, riesgos, pendientes, validaciones | Movimientos de stock/caja |
| diccionario, fuentes, cobertura | Plantillas reservadas con datos (vacías hoy) |

**Estado:** A0 documentado; `reporte_preflight.json` G0=true.  
**Gate:** G0, G1 (esquema_importacion), G4 (paquete ya depurado).

## Lote A1 — Warehouse analítico (opcional, aparte de Salman)

Crear (solo si hay ADR) tablas staging/mart **fuera** de las migraciones operativas V1:  
`import_batch`, `staging_record`, `source_document`, observaciones de ocupación.  
**No** crear `room_night`/`financial_event` en el esquema de `reservas` de producción.

**Estado:** NO iniciar hasta dueño pida capa C y existan hechos o unidad confirmada.

## Lote B1 — Habitaciones verificadas → Salman (#336)

**Entrada:** D1+D2 completas (id, tipo, capacidad, apta venta).  
**Acción:** `PUT /hotel/habitaciones/{id}` por administrador; retirar `HAB-SINT-*` de oferta.  
**No entra:** capacidad vacía, estado solo documental, Matrimonial +1 sin capacidad.

**Gates:** G0–G2, G4–G6 + cierre parcial #336.  
**Estado:** BLOQUEADO_HASTA_DUENO.

## Lote B2 — Tarifas activas → Salman (R04)

**Entrada:** D3 (vigencia + aprobación 2027 + expansión tipo→habitacion_id).  
**Acción:** `PUT /hotel/tarifas` por habitación.  
**No entra:** las 5 filas del ZIP tal cual; TAR-07 sin D4.

**Estado:** BLOQUEADO.

## Lote B3 — Cuádruple / composición (R01)

Solo tras D4. Si A: no hay lote. Si B: desarrollo+ADR antes de datos.

**Estado:** BLOQUEADO / gap producto.

## Lote R0 — Reservado cifrado (fuera del repo)

Plantillas: reservas, pagos, personal, garantías, liquidación traspaso, cuentas, contratos.  
Hoy: **0 filas**. Recepción futura: cifrado, roles, retención (LEEME §3).  
**Nunca** mezclar con CSV generales ni commits.

## Lote C0 — Dashboard D0 (documental)

Completitud habitaciones, tarifas inactivas, riesgos, pendientes, cobertura fuentes.  
Ya posible con el ZIP + este directorio. **No** ocupación oficial ni ingresos.

## Lote C1 — KPI (ocupación/ADR/RevPAR)

Exige D5 + noches vendibles + (ideal) reservas reconciliadas (D8).  
Con solo agregados 2026 del ZIP → **baseline documental**, no KPI publicado.

## Lote C2 — Forecast

Exige C1 confiable + historia suficiente. Con ~10 meses agregados sin reservas:  
**no** título de pronóstico comercial (G8 no aplica).

## Criterio de aprobación humana por lote

| Lote | Pregunta de sí/no |
|---|---|
| A0 | ¿Hashes y clasificación GENERAL_DEPURADO aceptados? |
| B1 | ¿Tabla D2 firmada y sin celdas de capacidad vacías para las aptas? |
| B2 | ¿Cada tarifa activa tiene habitacion_id + fechas + monto aprobados? |
| B3 | ¿Decisión D4 explícita? |
| R0 | ¿Canal cifrado y responsable de tratamiento definidos? |
| C1 | ¿Unidad de ocupación y denominador escritos? |
| C2 | ¿Backtest supera baseline fuera de muestra? |

Si la respuesta es no o en blanco → el lote no se publica.  
Ningún dato documental se vuelve vendible ni cobrable por omisión.
