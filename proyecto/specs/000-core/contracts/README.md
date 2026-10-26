# Contratos lógicos propuestos — Core transversal

No hay OpenAPI ni endpoints inventados. Este documento fija obligaciones derivadas de los FR para elaborar contratos técnicos tras resolver decisiones.

## Sobre común, errores y compatibilidad

Toda operación privada lleva identidad verificada, tenant resuelto, permiso, referencia de negocio, versión de contrato y correlation-id. Una mutación incluye clave de idempotencia y versión esperada. La respuesta diferencia confirmado, pendiente y rechazado; una denegación no revela existencia de otro tenant. Diferente huella con igual clave se rechaza. Errores recuperables se distinguen de rechazo de política. Solo el servicio de negocio ejecuta, nunca el texto del modelo.

No se aceptan tenant ni aprobación autodeclarados por mensaje. La aprobación liga actor autorizado, acción, monto/moneda, huella, vigencia y uso único. Un cambio invalida la aprobación. Reintentos no repiten efectos. Cambios incompatibles requieren nueva versión y prueba de consumidores; no se publica un SLA externo no contratado.

## Operaciones derivadas

- `CORE-FR-001`: Resolver identidad y pertenencia activa a una empresa antes de acceder a cualquier recurso. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `CORE-FR-002`: Autorizar por tenant, rol, recurso y acción con denegación por defecto, incluidos procesos asíncronos. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `CORE-FR-003`: Registrar intentos y estados de pago por empresa, moneda, monto y referencia de negocio, sin duplicar efectos al reintentar. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H2. Esquema exacto pendiente del modelo ratificado.
- `CORE-FR-004`: Determinar y emitir el documento tributario aplicable mediante política aprobada por contribuyente; conciliar y evitar doble emisión. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H2. Esquema exacto pendiente del modelo ratificado.
- `CORE-FR-005`: Registrar acciones críticas y de agentes con actor, tenant, evidencia, política, aprobación y resultado, con integridad verificable. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H3. Esquema exacto pendiente del modelo ratificado.
- `CORE-FR-006`: Separar secretos, almacenamiento y comunicaciones por tenant; minimizar datos y aplicar retención aprobada. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H1. Esquema exacto pendiente del modelo ratificado.
- `CORE-FR-007`: Denegar ejecuciones agénticas sin política vigente, identidad, evidencia o aprobación exigida. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H3. Esquema exacto pendiente del modelo ratificado.
- `CORE-FR-008`: Recuperar fallos de conectividad mediante estados pendientes, reconciliación y alertas sin declarar éxito ficticio. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H2. Esquema exacto pendiente del modelo ratificado.
- `CORE-FR-009`: Versionar contratos y registrar compatibilidad de productores y consumidores antes de cambios. Entrada mínima: referencia del recurso y datos de negocio validados; salida: estado y evidencia; autorización según rol de la historia H3. Esquema exacto pendiente del modelo ratificado.

## Gate para contrato ejecutable

Q-CORE-01: empresas, roles y autorización entre empresas; Q-CORE-02: tratamiento fiscal y proveedor DTE por contribuyente; Q-CORE-03: responsables de datos, retención, recuperación, presupuesto y autonomía. Deben fijarse esquema de datos, dueño, políticas, ejemplos, errores, paginación si aplica, compatibilidad y pruebas de consumidor. No conectar APIs productivas ni emitir documentos reales para validar esta documentación.

## Contratos lógicos precisados por las historias US-CORE

Interfaz lógica perfil de capacidad y resultado externo correlacionado. Entradas: contexto verificado, operación, referencia, versión, evento y huella; salida habilitado/denegado/pendiente con razón. Identidad de evento depende del proveedor, no se inventa webhook común.

Requisitos adicionales: FR-010, FR-011. Precondiciones: identidad/tenant, permiso, versión y capacidad habilitada; negativas: recurso ajeno, vigencia ausente, aprobación caducada o respuesta obsoleta. Resultado nunca convierte pendiente en confirmado por ausencia de error. Esquemas de transporte y endpoints propios siguen pendientes; no se presentan como APIs observadas de terceros. Compatibilidad se prueba por productor/consumidor cuando exista contrato técnico.

## Interfaces lógicas de recuperación y parcialidad

Contrato lógico de invocación: perfil/version, contexto verificado, intención y huella de parámetros; vista previa de efectos y resultado por efecto. Contrato incompleto o placeholder no permite habilitar. No existe endpoint nuevo ni se publica esquema del proveedor como contrato propio.

Cada operación exige identidad/tenant, permiso, referencia, versión y correlación; las mutaciones conservan idempotencia y aprobación de parámetros exactos. Reintento y nueva operación son distintos. Mensajes, payloads y respuestas del vendor no pueden otorgar permiso. Ejemplos en acceptance.md; transporte/endpoints y contratos ejecutables siguen bloqueados por decisiones.
