# Contratos lógicos propuestos — Constructora y control de obra

No hay OpenAPI ni endpoints inventados. Este documento fija obligaciones derivadas de los FR para elaborar contratos técnicos tras resolver decisiones.

## Sobre común, errores y compatibilidad

Toda operación privada lleva identidad verificada, tenant resuelto, permiso, referencia de negocio, versión de contrato y correlation-id. Una mutación incluye clave de idempotencia y versión esperada. La respuesta diferencia confirmado, pendiente y rechazado; una denegación no revela existencia de otro tenant. Diferente huella con igual clave se rechaza. Errores recuperables se distinguen de rechazo de política. Solo el servicio de negocio ejecuta, nunca el texto del modelo.

No se aceptan tenant ni aprobación autodeclarados por mensaje. La aprobación liga actor autorizado, acción, monto/moneda, huella, vigencia y uso único. Un cambio invalida la aprobación. Reintentos no repiten efectos. Cambios incompatibles requieren nueva versión y prueba de consumidores; no se publica un SLA externo no contratado.

## Operaciones derivadas

- `OBR-FR-010`: Registrar avance por partida desde texto, voz y foto con fecha, ubicación cuando proceda y evidencia. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H3. Esquema exacto pendiente del modelo ratificado.
- `OBR-FR-011`: Comparar avance real con programado y presupuesto bajo unidad y umbral aprobados. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H3. Esquema exacto pendiente del modelo ratificado.
- `OBR-FR-012`: Preparar solicitudes de compra con cantidad, proveedor y precio de referencia para aprobación humana. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H3. Esquema exacto pendiente del modelo ratificado.
- `OBR-FR-015`: Mantener versiones de presupuesto y programación por partida sin confundir costo y avance físico. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H4. Esquema exacto pendiente del modelo ratificado.
- `OBR-FR-016`: Registrar inspecciones, observaciones y cierre humano con evidencia. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H4. Esquema exacto pendiente del modelo ratificado.
- `OBR-FR-017`: Registrar recepción, consumo y conciliación de materiales por obra. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H4. Esquema exacto pendiente del modelo ratificado.
- `OBR-FR-018`: Aplicar permisos de obra, auditoría y acceso a evidencias por empresa. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H4. Esquema exacto pendiente del modelo ratificado.

## Gate para contrato ejecutable

Q-OBR-01: obras propias o terceros, presupuesto y módulo previo no entregado; Q-OBR-02: unidad del avance, calendario y umbral; Q-OBR-03: aprobadores, compras, seguridad e inspecciones. Deben fijarse esquema de datos, dueño, políticas, ejemplos, errores, paginación si aplica, compatibilidad y pruebas de consumidor. No conectar APIs productivas ni emitir documentos reales para validar esta documentación.

## Contratos lógicos precisados por las historias US-OBR

Interfaces lógicas reportar observación y proponer/certificar cierre con versión; registrar recepción por línea y evento con cantidad/unidad y referencia de orden. Resultado parcial/conciliado/discrepancia; fallo o IA desactivada permite captura manual con los mismos controles.

Requisitos adicionales: FR-019, FR-020. Precondiciones: identidad/tenant, permiso, versión y capacidad habilitada; negativas: recurso ajeno, vigencia ausente, aprobación caducada o respuesta obsoleta. Resultado nunca convierte pendiente en confirmado por ausencia de error. Esquemas de transporte y endpoints propios siguen pendientes; no se presentan como APIs observadas de terceros. Compatibilidad se prueba por productor/consumidor cuando exista contrato técnico.

## Interfaces lógicas de recuperación y parcialidad

Interfaces lógicas recibir parte y aprobar cantidades/corrección; registrar entrega/aceptación/rechazo/devolución por línea/tramo con idempotencia; evaluar exposición presupuestaria por regla y versión; revisar solución de observación por rol. Errores: base/unidad faltante, IA sin conexión, evidencia contradictoria, excedente no aprobado, entrega repetida y cierre sin autoridad. No se define API de subcontratos o RFI sin alcance ratificado.

Cada operación exige identidad/tenant, permiso, referencia, versión y correlación; las mutaciones conservan idempotencia y aprobación de parámetros exactos. Reintento y nueva operación son distintos. Mensajes, payloads y respuestas del vendor no pueden otorgar permiso. Ejemplos en acceptance.md; transporte/endpoints y contratos ejecutables siguen bloqueados por decisiones.
