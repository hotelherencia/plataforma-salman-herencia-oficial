# Contratos lógicos propuestos — Inmobiliaria comercial

No hay OpenAPI ni endpoints inventados. Este documento fija obligaciones derivadas de los FR para elaborar contratos técnicos tras resolver decisiones.

## Sobre común, errores y compatibilidad

Toda operación privada lleva identidad verificada, tenant resuelto, permiso, referencia de negocio, versión de contrato y correlation-id. Una mutación incluye clave de idempotencia y versión esperada. La respuesta diferencia confirmado, pendiente y rechazado; una denegación no revela existencia de otro tenant. Diferente huella con igual clave se rechaza. Errores recuperables se distinguen de rechazo de política. Solo el servicio de negocio ejecuta, nunca el texto del modelo.

No se aceptan tenant ni aprobación autodeclarados por mensaje. La aprobación liga actor autorizado, acción, monto/moneda, huella, vigencia y uso único. Un cambio invalida la aprobación. Reintentos no repiten efectos. Cambios incompatibles requieren nueva versión y prueba de consumidores; no se publica un SLA externo no contratado.

## Operaciones derivadas

- `INM-FR-001`: Capturar leads desde web, portales (Portalinmobiliario, TOCTOC, Yapo) y WhatsApp en un solo registro deduplicado. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `INM-FR-002`: Calificar leads por WhatsApp con un agente (presupuesto, plazo, financiamiento, tipo de unidad) y agendar visitas en la agenda del ejecutivo. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `INM-FR-003`: Mantener el stock de unidades por proyecto con precio vigente, estado (disponible, reservada, promesada, escriturada) y bloqueo por reserva. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `INM-FR-004`: Generar cotizaciones con precio, pie, financiamiento estimado y vencimiento, trazables al lead y a la unidad. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `INM-FR-005`: Cobrar la reserva por Webpay/Transbank o Mercado Pago y emitir el documento tributario que corresponda. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `INM-FR-006`: Enviar la promesa de compraventa a firma electrónica (Ley 19.799) y archivarla con la unidad. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `INM-FR-007`: Administrar el calendario de pagos del pie, enviar recordatorios por WhatsApp con link de pago y conciliar pagos. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H2. Esquema exacto pendiente del modelo ratificado.
- `INM-FR-008`: Recibir solicitudes de postventa por WhatsApp y web, clasificarlas con un agente, asignarlas y seguir plazos con escalamiento. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H2. Esquema exacto pendiente del modelo ratificado.
- `INM-FR-009`: Exponer al cliente un portal con su unidad, pagos, documentos y solicitudes. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H2. Esquema exacto pendiente del modelo ratificado.
- `INM-FR-013`: Registrar toda acción de agente en el registro de auditoría con integridad verificable y retención aprobada con evidencia y aprobador. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia Todas. Esquema exacto pendiente del modelo ratificado.
- `INM-FR-014`: Operar sobre el core compartido (identidad, autorización, pagos, documentos y auditoría) sin duplicarlo. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia Todas. Esquema exacto pendiente del modelo ratificado.

## Gate para contrato ejecutable

Q-INM-01: proyectos, CRM y captura autorizada de leads; Q-INM-02: reserva, vigencia y reembolsos; Q-INM-03: revisión legal de promesa y firma; Q-INM-04: garantías y responsables. Deben fijarse esquema de datos, dueño, políticas, ejemplos, errores, paginación si aplica, compatibilidad y pruebas de consumidor. No conectar APIs productivas ni emitir documentos reales para validar esta documentación.

## Contratos lógicos precisados por las historias US-INM

Interfaz lógica registrar consulta con origen permitido y clave de deduplicación; devolver creado/vinculado/revisión identidad. Proponer visita no agenda sin confirmar disponibilidad; transición contractual exige evidencia específica, no booleano genérico de éxito.

Requisitos adicionales: FR-015, FR-016. Precondiciones: identidad/tenant, permiso, versión y capacidad habilitada; negativas: recurso ajeno, vigencia ausente, aprobación caducada o respuesta obsoleta. Resultado nunca convierte pendiente en confirmado por ausencia de error. Esquemas de transporte y endpoints propios siguen pendientes; no se presentan como APIs observadas de terceros. Compatibilidad se prueba por productor/consumidor cuando exista contrato técnico.

## Interfaces lógicas de recuperación y parcialidad

Interfaces lógicas proponer/confirmar/cambiar visita con modo de agenda y resultado; preparar/aprobar/enviar/consultar firma por versión; corregir persona o reasignar vínculo (operaciones distintas); proponer/aceptar cierre de postventa. Errores: identidad ambigua, horario incierto, calendario inaccesible, documento cambiado, firma incompleta y acceso revocado. No habilitar endpoint Tokko placeholder ni suponer send-information seguro por omisión.

Cada operación exige identidad/tenant, permiso, referencia, versión y correlación; las mutaciones conservan idempotencia y aprobación de parámetros exactos. Reintento y nueva operación son distintos. Mensajes, payloads y respuestas del vendor no pueden otorgar permiso. Ejemplos en acceptance.md; transporte/endpoints y contratos ejecutables siguen bloqueados por decisiones.
