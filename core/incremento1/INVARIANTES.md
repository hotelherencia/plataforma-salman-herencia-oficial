# Invariantes y contratos lógicos — núcleo

Fecha: 2026-10-27. Sirve a `000-core/T203`. Timeout, repetición y parcialidad en memoria, sin red; evidencia = pruebas citadas (todas en verde).

## Repetición (idempotencia)
- Efecto de pago único por clave: 10 repeticiones del mismo retorno → un efecto (test_AC_US_CORE_002_01).
- Aprobación de uso único: segunda ejecución → EfectoNoAplicable.

## Timeout / estado desconocido
- Resultado `desconocido` queda registrado; no se infiere éxito.
- Vigencia vencida → denegado.

## Parcialidad
- Rechazo posterior a operación offline: no autoriza ni borra la deuda (002_02).
- Efectos excluidos quedan registrados sin ejecutar.

Recuperación: corrección por reverso/registro nuevo; ningún dato aprobado se sobrescribe.
