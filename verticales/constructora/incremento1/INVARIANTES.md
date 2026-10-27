# Invariantes y contratos lógicos — constructora

Fecha: 2026-10-27. Sirve a `004/T203`. Timeout, repetición y parcialidad en memoria, sin red; evidencia = pruebas citadas (todas en verde).

## Repetición (idempotencia)
- Aportes deduplicados por clave; el reenvío no duplica (AT-010).
- Recepción idempotente por evento: repetir no recibe 12 (AT-009).

## Timeout / estado desconocido
- Reporte contradictorio: conserva ambos y exige rectificación aprobada (ADV-001).

## Parcialidad
- Recepción parcial con rechazo documentado: 6 entregadas, 5 aceptadas, 1 rechazada (AT-011).
- Programado cero: sin división por cero ni alerta inventada (AT-002).

Recuperación: corrección por reverso/registro nuevo; ningún dato aprobado se sobrescribe.
