# Contratos lógicos propuestos — Hotel

No hay OpenAPI ni endpoints inventados. Este documento fija obligaciones derivadas de los FR para elaborar contratos técnicos tras resolver decisiones.

## Sobre común, errores y compatibilidad

Toda operación privada lleva identidad verificada, tenant resuelto, permiso, referencia de negocio, versión de contrato y correlation-id. Una mutación incluye clave de idempotencia y versión esperada. La respuesta diferencia confirmado, pendiente y rechazado; una denegación no revela existencia de otro tenant. Diferente huella con igual clave se rechaza. Errores recuperables se distinguen de rechazo de política. Solo el servicio de negocio ejecuta, nunca el texto del modelo.

No se aceptan tenant ni aprobación autodeclarados por mensaje. La aprobación liga actor autorizado, acción, monto/moneda, huella, vigencia y uso único. Un cambio invalida la aprobación. Reintentos no repiten efectos. Cambios incompatibles requieren nueva versión y prueba de consumidores; no se publica un SLA externo no contratado.

## Operaciones derivadas

- `HOT-FR-001`: Mantener un inventario único de habitaciones con tarifas por fecha, ocupación y política de cancelación. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-002`: Exponer un motor de reservas en la web propia con disponibilidad real y pago en línea. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-003`: Sincronizar disponibilidad y reservas con al menos Booking y Airbnb en ambos sentidos. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-004`: Cobrar por Webpay/Transbank o Mercado Pago y emitir el documento SII aplicable, sin duplicar anticipos ni documentos previos. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-005`: Impedir sobreventa ante reservas concurrentes del mismo inventario. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-006`: Permitir check-in online con datos del huésped, documento y firma de registro. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H2. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-007`: Consumir una interfaz opcional de pedidos de cafetería para servicio a la habitación, con cargo a la cuenta del huésped. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H2. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-008`: Generar y cerrar tareas de housekeeping y mantención por habitación y estado. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H2. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-009`: Consolidar todos los cargos de la estadía en una cuenta y liquidarla al check-out. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H2. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-010`: Atender por WhatsApp Business con un agente que consulta y escribe en el PMS vía API. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H3. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-011`: Aplicar reglas de autonomía configurables: acciones permitidas, montos máximos, casos que escalan. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H3. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-012`: Ofrecer upsells con link de pago en momentos definidos (pre-llegada, estadía, salida). Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H3. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-013`: Registrar cada acción del agente en el registro de auditoría con integridad verificable y retención aprobada con evidencia de la conversación. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H3. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-014`: Exponer disponibilidad y tarifas por un servidor MCP para agentes externos (modelo SiteMinder). Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H3. Esquema exacto pendiente del modelo ratificado.
- `HOT-FR-015`: Operar sobre el core compartido (identidad, autorización, pagos, documentos y auditoría) sin duplicarlo. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia Todas. Esquema exacto pendiente del modelo ratificado.

## Gate para contrato ejecutable

Q-HOT-01: PMS actual y fuente de inventario; Q-HOT-02: acceso OTA/channel manager; Q-HOT-03: habitaciones, cancelación, anticipos, datos de registro y autonomía. Deben fijarse esquema de datos, dueño, políticas, ejemplos, errores, paginación si aplica, compatibilidad y pruebas de consumidor. No conectar APIs productivas ni emitir documentos reales para validar esta documentación.

## Contratos lógicos precisados por las historias US-HOT

Interfaz lógica consultar oferta con vigencia y revalidar antes de confirmar. Transferencia: referencia conversación, motivo, receptor y contexto minimizado; salida pendiente/aceptada/en atención/cerrada. No asumir que cotización ejecuta reserva. Cada conector declara su alcance.

Requisitos adicionales: FR-016, FR-017. Precondiciones: identidad/tenant, permiso, versión y capacidad habilitada; negativas: recurso ajeno, vigencia ausente, aprobación caducada o respuesta obsoleta. Resultado nunca convierte pendiente en confirmado por ausencia de error. Esquemas de transporte y endpoints propios siguen pendientes; no se presentan como APIs observadas de terceros. Compatibilidad se prueba por productor/consumidor cuando exista contrato técnico.

## Interfaces lógicas de recuperación y parcialidad

Tres interfaces lógicas: previsualizar/aplicar cambio contra versión/cupo y aprobación; registrar cargo periódico/único con destino y cumplimiento; recibir/acusar/reconciliar evento con estados distintos. Errores: fuente obsoleta, versión en conflicto, falta mapeo, permiso insuficiente, persistencia fallida o resultado desconocido. Confirmación comercial nunca se deduce del acuse.

Cada operación exige identidad/tenant, permiso, referencia, versión y correlación; las mutaciones conservan idempotencia y aprobación de parámetros exactos. Reintento y nueva operación son distintos. Mensajes, payloads y respuestas del vendor no pueden otorgar permiso. Ejemplos en acceptance.md; transporte/endpoints y contratos ejecutables siguen bloqueados por decisiones.


Nota de protocolo: acuse de recepción y aceptación/aplicación se separan conceptualmente, pero el punto de acuse debe respetar el contrato real del canal. El ID de notificación externo se usa solo si el proveedor lo define; sin él, la clave/huella y recuperación requieren investigación, sin inventar campos ni deduplicar todos los cambios por ID de reserva.
