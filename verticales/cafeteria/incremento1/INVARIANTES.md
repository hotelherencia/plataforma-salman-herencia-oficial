# Invariantes y contratos lógicos — cafetería

Fecha: 2026-10-27. Sirve a `001/T203`. Timeout, repetición y parcialidad en memoria, sin red; evidencia = pruebas citadas (todas en verde).

## Repetición (idempotencia)
- Una sola comanda por clave de pedido (AT-003).
- Venta imputada una sola vez por clave: receta mueve cada insumo una vez (AT-008).
- Ítem y parte pagados una sola vez (AT-004, ADV-001).

## Timeout / estado desconocido
- Propuesta de compra expirada a 48 h: bloquea y exige revisión (AC-US-CAF-003-02).

## Parcialidad
- Recepción con líneas erróneas: gasto en borrador hasta aprobación (AT-007).
- Reparto con partes pagadas conservadas al recalcular (AC-US-CAF-001-02).

Recuperación: corrección por reverso/registro nuevo; ningún dato aprobado se sobrescribe.
