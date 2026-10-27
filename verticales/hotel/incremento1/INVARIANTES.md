# Invariantes y contratos lógicos — hotel

Fecha: 2026-10-27. Sirve a `002/T203`. Timeout, repetición y parcialidad en memoria, sin red; evidencia = pruebas citadas (todas en verde).

## Repetición (idempotencia)
- Reserva concurrente: cerrojo, máximo una confirmación de la última unidad (AT-005/ADV-001).
- Cargos, pagos y pedidos con clave: repetición devuelve el efecto existente (AT-009, AC-US-HOT-002-05).
- Reintento del cambio de tarifa: consulta de estado, sin segundo cargo (AC-US-HOT-001-05).

## Timeout / estado desconocido
- Oferta vencida: reserva PENDIENTE sin prometer cupo + transferencia humana (AT-017).

## Parcialidad
- Acuse separado de la aceptación (FR-020; puerto en implementación).
- Reverso como corrección: el asiento original es inmutable.

Recuperación: corrección por reverso/registro nuevo; ningún dato aprobado se sobrescribe.
