# Catálogo de aceptación — Inmobiliaria comercial

Escenarios propuestos; ninguno ejecutado sobre producto. Cada ID tiene namespace de feature. Para cada FR se prueba resultado autorizado, denegación, duplicación y recuperación; los datos deben ser autorizados y minimizados.

| Prueba | Requisito | Dado / Cuando / Entonces |
|---|---|---|
| AT-001 | FR-001 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Lead llega por dos canales autorizados: sugerir coincidencia con evidencia y evitar seguimiento duplicado; identidad ambigua queda separada para revisión. |
| AT-002 | FR-002 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Con consentimiento y datos mínimos, agente prepara calificación/horario; no discrimina por atributos improcedentes y el ejecutivo valida antes de compromiso. |
| AT-003 | FR-003 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Dos ejecutivos cotizan una unidad y dos clientes intentan reservarla: solo una reserva vigente; el segundo resultado financiero se concilia según política. |
| AT-004 | FR-004 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Cotización incluye precio versionado, pie, estimación de financiamiento y vencimiento, vinculados al lead/unidad; no cambiar documento al variar precio posterior. |
| AT-005 | FR-005 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Pago reserva aprobado bloquea una vez la unidad según política ratificada y deriva al documento aplicable; transferencia no validada no acredita saldo. |
| AT-006 | FR-006 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Promesa con versión legal aprobada se envía por proveedor autorizado tras aprobación; evidencia de firma y documento quedan archivados sin sobrescribir originales. |
| AT-007 | FR-007 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Cuota próxima al vencimiento genera borrador recordatorio correcto; solo resultado proveedor conciliado cambia saldo; duplicado no reduce deuda dos veces. |
| AT-008 | FR-008 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Foto de postventa produce clasificación provisional y responsable; urgencia se escala y garantía nunca se rechaza automáticamente; a 72 h sin respuesta se alerta. |
| AT-009 | FR-009 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Cliente autenticado solo ve su unidad, documentos, pagos y casos; cambiar identificador de recurso no muestra datos de otro cliente o empresa. |
| AT-010 | FR-013 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Calificación, recordatorio, aprobación y escalamiento quedan auditados con evidencia minimizada y versión de política. |
| AT-011 | FR-014 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Cotización y unidad permanecen comerciales, pagos/documentos/autorización vienen del core y se concilian por referencia, sin duplicación de entidades. |
| ADV-001 | NFR-001/002/003 | Dos pagos intentan reservar la misma unidad: una sola reserva; el segundo pago queda en conciliación y gestión humana. |
| ADV-002 | NFR-001/002/003 | Documento firmado recibe versión y huella; cambios posteriores no reemplazan el original. |
| ADV-003 | NFR-001/002/003 | Texto que exige negar garantía se trata como contenido y escala al responsable sin rechazo autónomo. |

## Criterios de éxito y evidencia

| Criterio | Verificación pendiente |
|---|---|
| SC-001 | Medir «El 100 % de los leads de todos los canales queda en un solo registro en menos de 5 minutos». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-002 | Medir «El tiempo de primera respuesta a un lead baja a menos de 2 minutos, 24/7». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-003 | Medir «Al menos el 60 % de los leads calificados agenda visita sin intervención del ejecutivo». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-004 | Medir «El tiempo de lead a promesa firmada baja al menos 30 % frente al proceso actual». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-005 | Medir «Cero unidades vendidas dos veces (auditoría trimestral)». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-006 | Medir «La morosidad de cuotas del pie baja al menos 20 % en 6 meses». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-007 | Medir «El 90 % de las solicitudes de postventa recibe clasificación y plazo en menos de 1 hora». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-009 | Medir «Cero acciones de agente fuera de reglas (auditoría mensual del ledger)». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |

## Escenarios competitivos por historia

Propuestos; no ejecutados sobre producto. Los números de ejemplo prueban aritmética y control, no fijan política comercial.

### US-INM-001 / H1

- AC-US-INM-001-01: Dado lead con presupuesto declarado, cuando se califica, entonces se etiqueta como declaración y no como aprobación de financiamiento.
- AC-US-INM-001-02: Dada reserva pagada y firma fallida, cuando se revisa estado, entonces no aparece promesada ni se libera/reembolsa sin política autorizada.

### US-INM-002 / H2

- AC-US-INM-002-01: Dada solicitud fuera de garantía aparente, cuando clasifica el agente, entonces propone revisión humana sin rechazar ni cerrar.
- AC-US-INM-002-02: Dado caso sin aceptación de receptor, cuando se transfiere, entonces permanece pendiente con alerta y no cuenta como resuelto.

| Prueba | Requisito | Escenario de resultado |
|---|---|---|
| AT-012 | FR-015 | Dada cita propuesta, cotización y reserva pagada pero firma fallida, cuando se consulta cada hito, entonces cita no es confirmada ni unidad promesada; presupuesto declarado no acredita financiamiento. Denegar recurso de otro tenant y conservar evidencia. |
| AT-013 | FR-016 | Dado retiro de permiso de contacto o atención humana activa, cuando se intenta automatizar seguimiento, entonces se suspende y conserva origen/motivo; transferencia sin aceptación no cierra caso ni expone deuda a nuevo destinatario. Denegar recurso de otro tenant y conservar evidencia. |

NFR-006 se verifica por los mismos AC: fuente sin vigencia, extracción ambigua o transición sin evidencia no permite compromiso; la ruta manual mantiene las validaciones.

## Aceptación de profundización funcional

Casos adicionales propuestos; ninguna prueba de producto fue ejecutada.

### RF-INM-01 / US-INM-001

- AC-US-INM-001-03: Dada agenda estática sin consulta al calendario, cuando el interesado acepta horario, entonces se identifica solicitud pendiente y no se afirma confirmación hasta aceptación autorizada.
- AC-US-INM-001-04: Dado horario local ambiguo, cuando se prepara cita, entonces exige zona/offset claro y muestra la misma fecha/hora acordada a ambas partes.
- AC-US-INM-001-05: Dada reprogramación con timeout, cuando se revisa, entonces conserva referencia de cita anterior y nueva propuesta sin crear dos citas confirmadas ni cancelar a ciegas.

### RF-INM-02 / US-INM-001

- AC-US-INM-001-06: Dado ejemplo cuya política requiere dos firmantes y solo uno firmó, cuando se consulta la promesa, entonces muestra pendiente y no unidad promesada por ese hecho.
- AC-US-INM-001-07: Dado cambio del documento tras aprobación, cuando se intenta reutilizar autorización anterior, entonces se invalida y exige revisión de nueva huella.
- AC-US-INM-001-08: Dada firma fallida con reserva pagada, cuando se comunica el estado, entonces no se libera ni devuelve dinero automáticamente y se preserva evidencia de ambos procesos.

### RF-INM-03 / US-INM-002

- AC-US-INM-002-03: Dada persona A vinculada a U1 y U2 y reasignación autorizada solo del acceso corriente a U1 a B, cuando se aplica, entonces U2 no cambia y A no obtiene documentos corrientes de U1 por una sesión antigua.
- AC-US-INM-002-04: Dada corrección del teléfono de A, cuando se guarda, entonces no cambia titular de ninguna unidad ni envía información sin permiso explícito.
- AC-US-INM-002-05: Dado vínculo o identidad ambiguos, cuando se pide reasignar portal, entonces queda revisión humana sin fusionar personas ni conceder acceso.

### RF-INM-04 / US-INM-002

- AC-US-INM-002-06: Dada visita agendada y cliente ausente, cuando el técnico registra intento, entonces el caso no se marca reparado ni cerrado y conserva motivo para recoordinar.
- AC-US-INM-002-07: Dada reparación propuesta sin aceptación exigida por política, cuando se consulta, entonces aparece por validar y no resuelta por el solo mensaje del agente.
- AC-US-INM-002-08: Dada reapertura con nueva evidencia, cuando el cliente reclama, entonces preserva intervención previa, responsable y plazos sin borrar historial ni rechazar automáticamente garantía.

| Prueba | Requisito | Escenario propuesto |
|---|---|---|
| AT-014 | FR-017 | Dada agenda estática sin consulta al calendario, cuando el interesado acepta horario, entonces se identifica solicitud pendiente y no se afirma confirmación hasta aceptación autorizada. Probar también permiso insuficiente y referencia de otro tenant. |
| AT-015 | FR-018 | Dado ejemplo cuya política requiere dos firmantes y solo uno firmó, cuando se consulta la promesa, entonces muestra pendiente y no unidad promesada por ese hecho. Probar también permiso insuficiente y referencia de otro tenant. |
| AT-016 | FR-019 | Dado guardar un contacto autorizado sin permiso de envío, cuando el conector ofrece enviar información de propiedad por un flag, entonces lo excluye y no envía; la persona/consulta conservan origen y no se fusionan por coincidencia débil. Probar también permiso insuficiente y referencia de otro tenant. |
| AT-017 | FR-020 | Dada persona A vinculada a U1 y U2 y reasignación autorizada solo del acceso corriente a U1 a B, cuando se aplica, entonces U2 no cambia y A no obtiene documentos corrientes de U1 por una sesión antigua. Probar también permiso insuficiente y referencia de otro tenant. |
