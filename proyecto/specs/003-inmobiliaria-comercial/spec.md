# Especificación — Inmobiliaria comercial

Feature: `003-inmobiliaria-comercial`. Fecha: 2026-10-16. Estado: **BLOCKED** para implementación.
Fuente: INM §2–5; copia conservada en docs/originales. Todos los FR y SC son **REQUISITOS PROPUESTOS**, pendientes de ratificación. Los resultados numéricos son objetivos; no se han medido.

## Problema, actores y límites

Escrituración y crédito hipotecario fuera de V1; solo hitos. H3 y FR-010 a FR-012 de la fuente se trasladan a 004.

Actores: interesado, ejecutivo, responsable legal y jefe de postventa. Las responsabilidades de aprobación no se transfieren al modelo.

## 2. Escenarios de usuario y pruebas (obligatorio)

La P1 ordena el dato fragmentado (Excel, WhatsApp, portales) en un solo flujo de lead a promesa; sin eso ningún agente puede actuar con permisos claros (brecha e del estado del arte).

**Historia 1 (P1): De lead a promesa en un solo flujo**

Un interesado llega por web, portal o WhatsApp; un agente lo califica (presupuesto, plazo, financiamiento), agenda la visita y lo entrega al ejecutivo. El ejecutivo cotiza desde el stock real de unidades, el cliente reserva con pago en línea y firma la promesa electrónicamente.

- Por qué P1: es el ciclo de ingresos; se propone reducir el trabajo manual de calificación y documentación y la cotización y la promesa son manuales.
- Prueba independiente: un lead de prueba recorre calificación, visita, cotización, reserva pagada y promesa firmada sin planilla externa, en menos de 48 horas de tiempo de proceso.
- Escenarios de aceptación:
  1. Dado un mensaje de WhatsApp de un interesado, cuando el agente responde, entonces emite primera respuesta en menos de 2 minutos y solicita los campos faltantes; presupuesto, plazo y tipo solo se registran si el interesado los proporciona. No se garantiza tiempo de respuesta del cliente.
  2. Dada una unidad disponible, cuando el ejecutivo genera cotización, entonces el documento sale con precio vigente, pie, financiamiento estimado y vence a una fecha.
  3. Dada una cotización aceptada, cuando el cliente paga la reserva por Webpay, entonces la unidad queda bloqueada y se emite boleta o comprobante.
  4. Dada una reserva pagada, cuando se envía la promesa, entonces el cliente firma electrónicamente y el documento queda archivado con la unidad.

**Historia 2 (P2): Cobranza y postventa con agente**

Tras la promesa, el sistema controla el calendario de pagos del pie, recuerda cuotas por WhatsApp, concilia pagos y, tras la entrega, recibe y gestiona solicitudes de postventa con un agente que clasifica, asigna y hace seguimiento.

- Por qué P2: cobranza y postventa son el dolor crónico de las inmobiliarias chilenas ; la cobertura real de proveedores no se ha verificado.
- Prueba independiente: 20 clientes con cuotas pendientes reciben recordatorios, 10 solicitudes de postventa reciben propuesta de clasificación/asignación; la revisión humana inicial se contabiliza y no se presenta como automatización autónoma.
- Escenarios de aceptación:
  1. Dada una cuota que vence en 5 días, cuando corre el agente, entonces envía recordatorio con monto y link de pago, y registra la gestión.
  2. Dado un pago recibido, cuando se concilia, entonces el estado de la cuota cambia y el cliente recibe comprobante.
  3. Dada una solicitud de postventa por WhatsApp con foto, cuando el agente la recibe, entonces la clasifica (urgente, garantía, no cubierta), la asigna y responde plazo estimado.
  4. Dada una solicitud sin respuesta del responsable en 72 horas, cuando vence, entonces el agente escala al jefe de postventa.

**Casos borde**

- Dos ejecutivos cotizan la misma unidad: la primera reserva pagada bloquea; la otra cotización se invalida y se avisa.
- Lead que contacta por dos canales: se propone coincidencia con evidencia; identidad ambigua queda en revisión, sin fusión automática por teléfono/nombre.
- Pago de reserva aprobado y promesa no firmada en el plazo: la expiración se avisa y la liberación/devolución requiere política y autorización humana; no se reembolsa automáticamente.
- Solicitud de postventa fuera de garantía: el agente responde con la política, no la rechaza solo.

## 3. Requisitos (obligatorio)

**Requisitos funcionales**

| ID | El sistema DEBE | Historia |
| --- | --- | --- |
| FR-001 | Capturar leads desde web, portales (Portalinmobiliario, TOCTOC, Yapo) y WhatsApp en un solo registro deduplicado | H1 |
| FR-002 | Calificar leads por WhatsApp con un agente (presupuesto, plazo, financiamiento, tipo de unidad) y agendar visitas en la agenda del ejecutivo | H1 |
| FR-003 | Mantener el stock de unidades por proyecto con precio vigente, estado (disponible, reservada, promesada, escriturada) y bloqueo por reserva | H1 |
| FR-004 | Generar cotizaciones con precio, pie, financiamiento estimado y vencimiento, trazables al lead y a la unidad | H1 |
| FR-005 | Cobrar la reserva por Webpay/Transbank o Mercado Pago y emitir el documento tributario que corresponda | H1 |
| FR-006 | Enviar la promesa de compraventa a firma electrónica (Ley 19.799) y archivarla con la unidad | H1 |
| FR-007 | Administrar el calendario de pagos del pie, enviar recordatorios por WhatsApp con link de pago y conciliar pagos | H2 |
| FR-008 | Recibir solicitudes de postventa por WhatsApp y web, clasificarlas con un agente, asignarlas y seguir plazos con escalamiento | H2 |
| FR-009 | Exponer al cliente un portal con su unidad, pagos, documentos y solicitudes | H2 |
| FR-013 | Registrar toda acción de agente en el registro de auditoría con integridad verificable y retención aprobada con evidencia y aprobador | Todas |
| FR-014 | Operar sobre el core compartido (identidad, autorización, pagos, documentos y auditoría) sin duplicarlo | Todas |

**Entidades clave**

- Proyecto: nombre, ubicación, etapas, unidades, estado comercial y de obra.
- Unidad: tipo, superficie, precio vigente, estado, reserva, promesa, escritura.
- Lead y Cliente: origen, canal, calificación, ejecutivo, historial de contacto.
- Cotización: unidad, precio, pie, financiamiento, vencimiento, estado.
- Reserva y Promesa: pagos, documentos firmados, plazos.
- Calendario de pagos y Cuota: monto, vencimiento, estado, conciliación.
- Solicitud de postventa: unidad, tipo, clasificación, responsable, plazo, estado.
- Acción de agente: conversación, regla, acción, aprobador, resultado.

## 4. Criterios de éxito (obligatorio)

| ID | Resultado medible |
| --- | --- |
| SC-001 | El 100 % de los leads de todos los canales queda en un solo registro en menos de 5 minutos |
| SC-002 | El tiempo de primera respuesta a un lead baja a menos de 2 minutos, 24/7 |
| SC-003 | Al menos el 60 % de los leads calificados agenda visita sin intervención del ejecutivo |
| SC-004 | El tiempo de lead a promesa firmada baja al menos 30 % frente al proceso actual |
| SC-005 | Cero unidades vendidas dos veces (auditoría trimestral) |
| SC-006 | La morosidad de cuotas del pie baja al menos 20 % en 6 meses |
| SC-007 | El 90 % de las solicitudes de postventa recibe clasificación y plazo en menos de 1 hora |
| SC-009 | Cero acciones de agente fuera de reglas (auditoría mensual del ledger) |

## 5. Supuestos, dependencias y clarificaciones

**Supuestos**

- Inmobiliaria y constructora son del mismo grupo; comparten proyectos y unidades, pero tienen usuarios distintos.
- Hay entre 1 y 5 proyectos activos con menos de 200 unidades en total.
- Los ejecutivos comerciales usan WhatsApp como canal principal; los portales inmobiliarios entregan leads por correo o API.
- La escrituración y el crédito hipotecario siguen fuera del sistema en V1 (solo se registran hitos).

**Dependencias**

- Core (`000-core`) en producción.
- Proveedor de firma electrónica avanzada con API (evaluar en `research.md`).
- Credenciales de portales para captura de leads; cuenta WhatsApp Business API; contrato Webpay Plus; certificado SII.
- H3 de obra se trasladó a 004; presupuesto y supuesto módulo previo son bloqueos de esa feature, no dependencia del comercial.

**Clarificaciones pendientes** (para `/speckit.clarify`)

- [ ] [NEEDS CLARIFICATION] ¿Cuántos proyectos y unidades activas hoy, y en qué etapa (verde, blanco, entrega)?
- [ ] [NEEDS CLARIFICATION] ¿Qué CRM o planillas usan hoy y qué historial se migra?
- [ ] [NEEDS CLARIFICATION] ¿La reserva es con pago en línea obligatorio o se acepta transferencia? Afecta FR-005 y el bloqueo de unidad.
- [ ] [NEEDS CLARIFICATION] ¿Quién redacta y aprueba la promesa (abogado interno o externo) y cuál es el plazo máximo entre reserva y promesa?
- [ ] [NEEDS CLARIFICATION] ¿Política de postventa: plazos de garantía por tipo de falla y responsables?
- [ ] [NEEDS CLARIFICATION] ¿La constructora ejecuta solo obras propias o también para terceros? Afecta el alcance de `004`.
- [ ] [NEEDS CLARIFICATION] ¿Límite monetario para que el asistente prepare compras sin revisión del administrador?

## Reglas normativas y de aceptación añadidas

- NFR-001: toda lectura, escritura, trabajo en cola y evidencia queda limitada por empresa y permiso; probar denegación entre empresas y roles.
- NFR-002: ningún agente ejecuta una acción financiera, tributaria o contractual sin control determinista y autorización vigente; escritura MCP deshabilitada inicialmente.
- NFR-003: reintentos conservan un solo efecto; estados desconocidos no se muestran como éxitos.
- NFR-004: retención, restauración y objetivos de recuperación requieren aprobación en Q-CORE-03; ninguna cifra de disponibilidad se asume acordada.
- NFR-005: medir latencia desde recepción hasta resultado confirmado, incluyendo errores, reintentos y desconexión. No declarar cumplimiento en muestras vacías.

Q-INM-01: proyectos, CRM y captura autorizada de leads; Q-INM-02: reserva, vigencia y reembolsos; Q-INM-03: revisión legal de promesa y firma; Q-INM-04: garantías y responsables.

Los escenarios tributarios y SC de emisión en 30/60 segundos se conservan como aspiración de la fuente, sujetos a aplicabilidad fiscal y disponibilidad externa. No constituyen garantía del SII. El aislamiento local no garantiza por sí solo cero sobreventa entre OTA independientes.

Ver `acceptance.md` para pruebas por requisito; `../../docs/auditorias/trazabilidad.md` para origen y equivalencias. La investigación transversal está en `../../docs/investigacion/estado-del-arte.md`.


## Refinamiento competitivo de historias — 2026-10-16

Estado **PROPUESTO**, sin ratificación del cliente. Las siguientes definiciones amplían las historias originales con alias US, sin eliminarlas. Ante un caso específico se aplica la regla más explícita de esta sección; ninguna cambia los bloqueos comerciales. Evidencia por ID en `../../docs/investigacion-competitiva/matriz-evidencias.md`.

### Historia US-INM-001 — enriquecimiento de H1 (P1)

Como interesado y ejecutivo comercial, quiero pasar de un contacto autorizado a una promesa mediante hitos comprobables, para reservar la unidad correcta y firmar la versión legal aceptada.

**Identidad y estado:** alias de `003-inmobiliaria-comercial/H1`; conserva historia y prioridad, **REQUISITO PROPUESTO**. No hay validación del cliente ni observación de runtime.

**Descripción funcional y necesidad de negocio:** Pasar de un contacto autorizado a una promesa mediante hitos comprobables. Responde a reservar la unidad correcta y firmar la versión legal aceptada; la evidencia competitiva precisa el comportamiento, no demuestra demanda comercial.

**Fuente de inspiración y evidencia:** I01, I03, I04, I05, I09, I10 en matriz-evidencias.md. Lectura documental, reconstrucción propia. Requisitos: FR-001,FR-002,FR-003,FR-004,FR-005,FR-006,FR-015,FR-016 y NFR-001/002/003/006.

**Disparador:** ingresa una consulta desde un canal autorizado o el ejecutivo avanza un hito de la oportunidad.

**Precondiciones:** canales autorizados y alcance de conector; identidad de contacto revisada; precios, políticas de reserva y promesa aprobados.

**Flujo principal:** Capturar contacto con origen → distinguir persona y consulta → calificar con dato declarado → proponer visita → confirmar agenda → emitir cotización versionada → revalidar unidad → reserva/pago conciliados → revisión legal/firma.

**Flujos alternativos y casos borde:** Identidad ambigua queda para revisión, no fusión automática. Plan sin webhook usa solo vía autorizada acordada, no scraping. Precio cambió: nueva cotización. Firma fallida no equivale a promesa vigente.

**Reglas de negocio y validaciones:** Presupuesto declarado no es solvencia verificada. Cotización no reserva; cita propuesta no confirmada; reserva pagada no promesa firmada. Renuncia de contacto suspende automatización permitida según política.

**Datos y estados involucrados:** Contacto, consulta/origen, consentimiento/preferencia, declaraciónCalificación, cita/estado, cotización/versión, reserva y evidenciaFirma. Transiciones conservan actor, tenant, fecha y versión; el modelo específico detalla los estados.

**Interacción humana/agéntica:** el humano responde por revisión y aprobación; el agente solo consulta o propone dentro del permiso. Herramientas candidatas, campos mínimos, límites cero para compromiso, evidencia y reversión se detallan en [gobernanza comparada](../../docs/investigacion-competitiva/agentes.md) y [seguridad compartida](../../docs/arquitectura/seguridad.md). No se exige IA para completar este flujo.

**Dependencias:** 000, canales de leads autorizados, agenda y proveedor de firma/política legal según Q-INM-01/02/03/04. Sin dependencia obligatoria de obra.

**Riesgos:** Discriminación, duplicados de persona, doble reserva y contrato sin versión.

**Criterios de aceptación Given/When/Then:**

- AC-US-INM-001-01: Dado lead con presupuesto declarado, cuando se califica, entonces se etiqueta como declaración y no como aprobación de financiamiento.
- AC-US-INM-001-02: Dada reserva pagada y firma fallida, cuando se revisa estado, entonces no aparece promesada ni se libera/reembolsa sin política autorizada.

**Métricas de éxito:** Leads con origen/total; primera respuesta; visitas confirmadas/elegibles; tiempo por hito; reservas duplicadas. Valores objetivo y ventanas deben ratificarse; no hay resultados medidos ni beneficio financiero calculado.


### Historia US-INM-002 — enriquecimiento de H2 (P2)

Como cliente y responsable de postventa/cobranza, quiero seguir cuotas y casos con responsable, evidencia y escalamiento, para evitar cobros indebidos y solicitudes perdidas o cerradas sin validación.

**Identidad y estado:** alias de `003-inmobiliaria-comercial/H2`; conserva historia y prioridad, **REQUISITO PROPUESTO**. No hay validación del cliente ni observación de runtime.

**Descripción funcional y necesidad de negocio:** Seguir cuotas y casos con responsable, evidencia y escalamiento. Responde a evitar cobros indebidos y solicitudes perdidas o cerradas sin validación; la evidencia competitiva precisa el comportamiento, no demuestra demanda comercial.

**Fuente de inspiración y evidencia:** I02, I06 en matriz-evidencias.md. Lectura documental, reconstrucción propia. Requisitos: FR-007,FR-008,FR-009,FR-016 y NFR-001/002/003/006.

**Disparador:** vence una cuota próxima, ingresa una solicitud de postventa o expira su plazo de respuesta.

**Precondiciones:** cliente autorizado; cuotas reconciliadas; políticas garantía/plazo; destinatario de transferencia.

**Flujo principal:** Consultar cuota/caso → preparar recordatorio o clasificación provisional → validar destinatario → asignar responsable y plazo según catálogo → registrar atención → resolver con evidencia → validar cierre humano.

**Flujos alternativos y casos borde:** Solicitud urgente requiere intervención; receptor ausente queda en cola visible con escalamiento. Caso reabierto conserva historial. Cambio contacto obliga a revalidar destino antes de exponer deuda.

**Reglas de negocio y validaciones:** Clasificar no decide cobertura; prometer fecha requiere política. Transferencia no cuenta como resolución. Cobranza no modifica monto ni concilia una imagen de transferencia.

**Datos y estados involucrados:** Cuota, comunicación autorizada, CasoPostventa, estado, responsable, vencimiento, resolución, evidenciaCierre y reapertura. Transiciones conservan actor, tenant, fecha y versión; el modelo específico detalla los estados.

**Interacción humana/agéntica:** el humano responde por revisión y aprobación; el agente solo consulta o propone dentro del permiso. Herramientas candidatas, campos mínimos, límites cero para compromiso, evidencia y reversión se detallan en [gobernanza comparada](../../docs/investigacion-competitiva/agentes.md) y [seguridad compartida](../../docs/arquitectura/seguridad.md). No se exige IA para completar este flujo.

**Dependencias:** 000, canales de leads autorizados, agenda y proveedor de firma/política legal según Q-INM-01/02/03/04. Sin dependencia obligatoria de obra.

**Riesgos:** Divulgar deuda, perder urgencia, denegar garantía y duplicar atención.

**Criterios de aceptación Given/When/Then:**

- AC-US-INM-002-01: Dada solicitud fuera de garantía aparente, cuando clasifica el agente, entonces propone revisión humana sin rechazar ni cerrar.
- AC-US-INM-002-02: Dado caso sin aceptación de receptor, cuando se transfiere, entonces permanece pendiente con alerta y no cuenta como resuelto.

**Métricas de éxito:** Recall urgentes; primera clasificación; casos reabiertos/cerrados; tasa de transferencia completada y costo/caso. Valores objetivo y ventanas deben ratificarse; no hay resultados medidos ni beneficio financiero calculado.


## Requisitos derivados de investigación competitiva

Son propuestas de comportamiento propio, sin atribuirlo como implementación observada del competidor.

| ID | El sistema DEBE | Historia |
|---|---|---|
| FR-015 | Distinguir contacto, visita propuesta/confirmada, cotización versionada, reserva vigente y promesa con firma comprobada; exigir evidencia de cada transición y no inferir solvencia desde datos declarados | H1 |
| FR-016 | Registrar origen y permiso de contacto, incertidumbre de identidad, responsable y estado de transferencia; suspender automatización ante retiro o revisión humana sin cerrar falsamente el caso | H1/H2 |

- NFR-006: toda oferta, extracción o decisión derivada declara procedencia, vigencia e incertidumbre; si no hay evidencia suficiente, no genera compromiso automático ni se informa como éxito. La captura manual conserva permisos, trazabilidad e idempotencia equivalentes.

## Profundización funcional de las otras verticales

Estado **REQUISITO PROPUESTO**; evidencia adicional y límites en investigación competitiva/continuacion-01. Conserva IDs/historias previos y bloqueos.

### RF-INM-01 — Proponer, confirmar y cambiar visitas con modo de agenda explícito

**Historia US-INM-001** (misma historia/ID, prioridad P1; no es historia nueva).

Como interesado y ejecutivo comercial, quiero proponer, confirmar y cambiar visitas con modo de agenda explícito, para saber si existe una cita confirmada o solo una solicitud de horario.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** I12, I14, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** el lead pide visitar o cambiar/cancelar una visita.

**Precondiciones:** ejecutivo/canal autorizado, zona horaria, duración y modalidad de agenda revisadas.

**Flujo principal:**

1. Consultar preferencias y declarar modo calendario sincronizado o ventana estática.
2. Proponer horarios con zona y duración.
3. Verificar disponibilidad autorizada o pedir confirmación al ejecutivo si no hay calendario.
4. Confirmar cita e identificar referencia y destinatarios válidos.
5. Gestionar cambio/cancelación por vía admitida; conservar estado previo hasta resultado conocido.

**Flujos alternativos y excepciones:** Calendario caído o agenda estática: pendiente de confirmación humana, sin afirmar disponibilidad real. Horario ambiguo por zona/cambio horario: pedir precisión. Choque de citas: ofrecer alternativas sin duplicar.

**Reglas de negocio/validaciones:** Invitación enviada no comprueba disponibilidad en calendarios no conectados. Calificación no es aprobación crediticia. No copiar reglas de zona/horario de un proveedor extranjero.

**Datos y estados:** Cita, modoAgenda, zona/offset y duración, horarioPropuesto, horarioConfirmado, referenciaCalendario, responsable y solicitudCambio.

**Dependencias:** Q-INM-01, calendario o proceso manual ratificado; 000 comunicaciones controladas.

**Riesgos:** Doble cita, fecha interpretada erróneamente, contacto no permitido y falsa confirmación.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-INM-001-03: Dada agenda estática sin consulta al calendario, cuando el interesado acepta horario, entonces se identifica solicitud pendiente y no se afirma confirmación hasta aceptación autorizada.
- AC-US-INM-001-04: Dado horario local ambiguo, cuando se prepara cita, entonces exige zona/offset claro y muestra la misma fecha/hora acordada a ambas partes.
- AC-US-INM-001-05: Dada reprogramación con timeout, cuando se revisa, entonces conserva referencia de cita anterior y nueva propuesta sin crear dos citas confirmadas ni cancelar a ciegas.

**Métricas:** citas confirmadas/solicitadas, conflictos/confirmadas, reprogramaciones resueltas y costo por cita. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


### RF-INM-02 — Versionar promesa y evidencias de firma

**Historia US-INM-001** (misma historia/ID, prioridad P1; no es historia nueva).

Como ejecutivo, responsable legal y firmantes autorizados, quiero versionar promesa y evidencias de firma, para distinguir reserva pagada de documento contractual aprobado y firmado.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** I15, I18, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** reserva permite preparar promesa o se modifica el documento antes de completar firma.

**Precondiciones:** plantilla y formalidades revisadas por abogado, proveedor/identificación de firmantes y política de conservación aprobados.

**Flujo principal:**

1. Seleccionar versión legal y datos de unidad/precio aceptados.
2. Generar borrador y revisar representación/firmantes requeridos.
3. Aprobar huella exacta del documento y enviar por canal autorizado.
4. Registrar estado por firmante y evidencia del proveedor.
5. Declarar contrato completado solo cuando condiciones jurídicas y firmas exigidas se verifican.

**Flujos alternativos y excepciones:** Firma parcial/expirada/rechazada mantiene estado no completado. Cambiar el documento tras enviar requiere nueva versión y revisión. Webhook firmado no sustituye revisar identidad/estado del documento.

**Reglas de negocio/validaciones:** Ley o producto de firma no prueba por sí solo formalidad válida de esta promesa. Pago y firma son estados independientes. Conservar originales y no reescribir historia al cambiar precio. Si precio UF se acuerda, conservar unidad y referencia de conversión sin inventar valor vigente.

**Datos y estados:** DocumentoVersionado, huella, versionPlantillaLegal, participantes/representación, SolicitudFirma, EvidenciaFirma, precioAceptado y referenciaReserva.

**Dependencias:** Q-INM-02/03 y Q-CORE-02/03; no se selecciona firma ni se asegura API.

**Riesgos:** Contrato equivocado, firma incompleta, suplantación, filtración y precio no aceptado.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-INM-001-06: Dado ejemplo cuya política requiere dos firmantes y solo uno firmó, cuando se consulta la promesa, entonces muestra pendiente y no unidad promesada por ese hecho.
- AC-US-INM-001-07: Dado cambio del documento tras aprobación, cuando se intenta reutilizar autorización anterior, entonces se invalida y exige revisión de nueva huella.
- AC-US-INM-001-08: Dada firma fallida con reserva pagada, cuando se comunica el estado, entonces no se libera ni devuelve dinero automáticamente y se preserva evidencia de ambos procesos.

**Métricas:** documentos completados válidamente/enviados; fallos por versión/firmante, tiempo por hito y costo por documento válido. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


### RF-INM-03 — Mantener persona, vínculo a unidad y permisos del portal

**Historia US-INM-002** (misma historia/ID, prioridad P2; no es historia nueva).

Como administrador autorizado y cliente titular del acceso, quiero mantener persona, vínculo a unidad y permisos del portal, para corregir o reasignar accesos sin modificar otras unidades ni divulgar documentos.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** I11, I16, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** cambio autorizado de contacto/vínculo de portal, corrección de datos o intento de acceso a unidad.

**Precondiciones:** identidad de personas revisada, vínculo actual y política de acceso/historial aprobados.

**Flujo principal:**

1. Identificar si se corrige Persona o se cambia VínculoUnidad.
2. Previsualizar unidades/documentos afectados y validar aprobador.
3. Actualizar solo el objeto previsto y versionar vínculo/acceso.
4. Invalidar permisos previos de consulta corriente según política y habilitar destinatario revisado.
5. Notificar por vía autorizada y conservar historial sin envío implícito.

**Flujos alternativos y excepciones:** Coincidencia de nombre/teléfono o identidad dudosa bloquea reasignación. Archivo compartido o sesión anterior debe revalidar permisos; derechos históricos no se adivinan.

**Reglas de negocio/validaciones:** Editar una persona no transfiere propiedad ni vínculo. Cambiar acceso no ejecuta compraventa/escritura. Opciones de envío de API se validan explícitamente; no enviar deuda/documentos al guardar un contacto.

**Datos y estados:** Persona, ConsultaOrigen, VinculoUnidad con vigencia/versión, PermisoPortal, EvidenciaCambio y autorizaciónComunicacion.

**Dependencias:** Q-CORE-01/03, Q-INM-01/04; propiedad comercial sigue 003, no base compartida con obra.

**Riesgos:** Acceso del titular anterior, cambio global accidental, exposición financiera y transferencia jurídica aparente.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-INM-002-03: Dada persona A vinculada a U1 y U2 y reasignación autorizada solo del acceso corriente a U1 a B, cuando se aplica, entonces U2 no cambia y A no obtiene documentos corrientes de U1 por una sesión antigua.
- AC-US-INM-002-04: Dada corrección del teléfono de A, cuando se guarda, entonces no cambia titular de ninguna unidad ni envía información sin permiso explícito.
- AC-US-INM-002-05: Dado vínculo o identidad ambiguos, cuando se pide reasignar portal, entonces queda revisión humana sin fusionar personas ni conceder acceso.

**Métricas:** accesos indebidos por vínculo; cambios aprobados/cambios; incidentes de envío y tiempo de revisión. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


### RF-INM-04 — Coordinar visita, trabajo y aceptación de postventa

**Historia US-INM-002** (misma historia/ID, prioridad P2; no es historia nueva).

Como cliente, coordinador de postventa y técnico asignado, quiero coordinar visita, trabajo y aceptación de postventa, para seguir un caso desde clasificación provisional hasta reparación aceptada, manteniendo urgencias e historial.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** I13, I16, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** solicitud de postventa, fecha de visita, solución propuesta o reapertura del cliente.

**Precondiciones:** cliente/unidad autorizados, catálogo de fallas y reglas de plazo/garantía ratificados.

**Flujo principal:**

1. Recibir caso y evidencia con información mínima.
2. Clasificar provisionalmente, separar urgencia y verificar responsable.
3. Coordinar visita y confirmar acceso/horario.
4. Registrar inspección/trabajo y propuesta de resolución.
5. Revisar cierre por rol autorizado y conservar reapertura o inconformidad.

**Flujos alternativos y excepciones:** Cliente ausente no implica falla solucionada. Receptor técnico no acepta: caso pendiente y escala. Foto o relato contradictorios requieren inspección humana; urgencia no espera clasificación exhaustiva.

**Reglas de negocio/validaciones:** No rechazar garantía desde IA ni convertir visita agendada en solución. Estados de cobro y postventa independientes. Plazo y exclusiones deben venir de política legal/operativa, no del vendor.

**Datos y estados:** CasoPostventa, ClasificacionProvisional, Visita/estado, trabajo, propuestaSolucion, evidencia, revisor, motivosReapertura.

**Dependencias:** Q-INM-04; agenda/canal con permisos; referencia opcional a obra mediante interfaz autorizada, sin acceso automático a trabajadores/presupuesto.

**Riesgos:** Garantía rechazada indebidamente, falsa resolución, acceso a hogar y documentos ajenos.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-INM-002-06: Dada visita agendada y cliente ausente, cuando el técnico registra intento, entonces el caso no se marca reparado ni cerrado y conserva motivo para recoordinar.
- AC-US-INM-002-07: Dada reparación propuesta sin aceptación exigida por política, cuando se consulta, entonces aparece por validar y no resuelta por el solo mensaje del agente.
- AC-US-INM-002-08: Dada reapertura con nueva evidencia, cuando el cliente reclama, entonces preserva intervención previa, responsable y plazos sin borrar historial ni rechazar automáticamente garantía.

**Métricas:** tiempo recepción→responsable y visita→aceptación, reaperturas/cierres, recall urgentes y costo por caso aceptado. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


## Requisitos de recuperación y semántica de dominio

| ID | El sistema DEBE | Historia |
|---|---|---|
| FR-017 | Distinguir modo de agenda, propuesta y confirmación de visita con zona/duración; verificar conflictos por vía autorizada y conservar referencia/estado en cambios o cancelación con resultado desconocido | H1 |
| FR-018 | Vincular promesa a versión legal, huella, participantes y evidencias de firma; impedir completarla con firma parcial, fallida o documento cambiado y mantener independientes reserva/pago/firma | H1 |
| FR-019 | Separar persona, consulta y asociación de interés por propiedad con procedencia; controlar explícitamente efectos de envío al registrar o actualizar contactos, sin fusión ni comunicación implícitas | H1/H2 |
| FR-020 | Distinguir corrección de persona de reasignación autorizada del acceso a una unidad, conservando vigencia/historial y revocando accesos corrientes previos según política sin ejecutar transferencia jurídica | H2 |


### Bloqueos adicionales de la profundización

Q-INM-05/06/07: ver [decisiones pendientes](../../docs/investigacion-competitiva/decisiones-pendientes.md). Son reglas para ratificar, no respuestas inferidas del mercado. Las historias permanecen propuestas y la feature **BLOCKED** para implementar.
