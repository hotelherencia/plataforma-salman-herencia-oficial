# Decisiones de diseño F13

## Enfoque seleccionado como propuesta
Registrar capacidad -> probar mapping -> recibir evento firmado -> deduplicar -> aplicar revisión -> confirmar recepción -> publicar inventario -> reconciliar -> alertar falla. Se utiliza el núcleo comun para identidad, dinero, disponibilidad y eventos; no un sistema paralelo por interfaz. Razón: conservar invariantes y facilitar verificación por agentes.

## Alternativas descartadas para esta entrega
Un CRUD libre de tablas evita las reglas de estado y no es aceptable para transacciones. Microservicios por cada funcion agregan contratos distribuidos sin beneficio demostrado para 17 habitaciones. La hoja de cálculo histórica es evidencia, no una autoridad concurrente del sistema. Un proveedor externo puede cubrir una capacidad, pero debe conservar exportación, reconciliacion y autoridad de datos.

## Evidencia y pendientes
D04, D06, D19, D25: resolver segun registro, sin inventar parámetros. Fuentes documentales: promptV0.3, 153 requisitos y hallazgos sanitizados. Fuentes externas de implementación: registro S01-S14. Si un proveedor cambia, emitir ADR e impacto sobre operaciones y pruebas, no sustituir contrato silenciosamente.

## Criterio para adoptar
Pruebas reproducibles del recorrido del spec; costos dentro de presupuesto; permisos y datos resguardados; resultado exportable. Documento público de una API no equivale a acceso contratado.
