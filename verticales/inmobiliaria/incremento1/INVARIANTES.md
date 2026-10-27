# Invariantes y contratos lógicos — inmobiliaria

Fecha: 2026-10-27. Sirve a `003/T203`. Timeout, repetición y parcialidad en memoria, sin red; evidencia = pruebas citadas (todas en verde).

## Repetición (idempotencia)
- Reserva única de unidad: el segundo postor queda en conciliación (AT-003/ADV-001).
- Pago de cuota idempotente por clave (AT-007).

## Timeout / estado desconocido
- Firma fallida: promesa pendiente; ni liberación ni devolución automática (AC-US-INM-001-02/08).

## Parcialidad
- Firmas parciales: 1 de 2 no promete la unidad (AC-US-INM-001-06).
- Reprogramación conserva la referencia anterior (AC-US-INM-001-05).

Recuperación: corrección por reverso/registro nuevo; ningún dato aprobado se sobrescribe.
