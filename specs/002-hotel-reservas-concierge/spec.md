# Especificación — Hotel

Feature: `002-hotel-reservas-concierge`. Fecha: 2026-10-16. Estado: **BLOCKED** para implementación.
Fuente: HOT §2–5; copia conservada en docs/originales. Todos los FR y SC son **REQUISITOS PROPUESTOS**, pendientes de ratificación. Los resultados numéricos son objetivos; no se han medido.

## Problema, actores y límites

La sincronización bidireccional está bloqueada por acceso comercial y técnico. El hotel básico no necesita que la cafetería esté en producción.

Actores: huésped, recepción, housekeeping, administrador y concierge. Las responsabilidades de aprobación no se transfieren al modelo.

## 2. Escenarios de usuario y pruebas (obligatorio)

La P1 reemplaza la dispersión actual con un solo punto de verdad para reservas; P2 y P3 construyen la operación y el agente sobre ese dato.

**Historia 1 (P1): Reservar y pagar desde la web del hotel**

Un huésped entra a la web, ve disponibilidad y tarifa real, reserva, paga con Webpay o Mercado Pago y recibe confirmación y el documento tributario que corresponda. El inventario se actualiza en todos los canales (Booking, Airbnb) sin intervención manual.

- Por qué P1: hoy todo está disperso; la reserva directa con inventario único es la base de todo lo demás y reduce comisión OTA.
- Prueba independiente: dos reservas simultáneas de la última habitación no generan sobreventa; el calendario de Booking refleja el cambio en menos de 5 minutos.
- Escenarios de aceptación:
  1. Dadas fechas y número de huéspedes, cuando el visitante consulta, entonces ve solo habitaciones disponibles con tarifa vigente y total con IVA.
  2. Dada una reserva con pago aprobado, cuando Webpay confirma, entonces se envía confirmación y se procesa el documento tributario aplicable sin duplicación; objetivo de 60 segundos sujeto a política fiscal y disponibilidad externa, con pendiente/alerta ante fallo.
  3. Dada una reserva directa confirmada, cuando el channel manager sincroniza, entonces la disponibilidad baja en todos los canales conectados en menos de 5 minutos.
  4. Dada una reserva de Booking, cuando llega por el canal, entonces aparece en el sistema de registro hotelero seleccionado con los mismos datos y bloquea inventario.

**Historia 2 (P2): Operar la estadía: check-in digital, pedidos a la habitación y housekeeping**

El huésped hace check-in desde el celular antes de llegar (datos, documento, pago pendiente), pide servicios a la habitación con el mismo módulo de pedidos de la cafetería y el personal ve tareas de limpieza y mantención por habitación.

- Por qué P2: convierte la reserva en operación; reutiliza el módulo de pedidos ya probado en `001`.
- Prueba independiente: un huésped completa check-in, pide desayuno a la habitación y lo recibe cargado a su cuenta sin pasar por recepción.
- Escenarios de aceptación:
  1. Dado un check-in online completo, cuando el huésped llega, entonces recepción solo entrega la llave y el registro queda firmado.
  2. Dado un pedido a la habitación, cuando se confirma, entonces aparece en cocina con número de habitación y se carga a la cuenta del huésped.
  3. Dado un check-out, cuando la habitación se libera, entonces se crea la tarea de limpieza y la habitación no queda preparada para el siguiente check-in hasta completar la tarea y levantar bloqueos aplicables; el inventario de fechas futuras se calcula por separado.
  4. Dado un cargo pendiente al check-out, cuando el huésped paga, entonces se concilia el saldo y se documenta el hecho aplicable sin repetir anticipos ya cubiertos.

**Historia 3 (P3): Concierge agéntico por WhatsApp con reglas de autonomía**

Un agente atiende por el WhatsApp del hotel: responde, cotiza, reserva, modifica fechas dentro de reglas, vende upsells con link de pago y escala a un humano cuando sale de su límite. Toda acción queda en el ledger.

- Por qué P3: es una hipótesis de valor a validar con el cliente, pero depende del sistema de registro hotelero seleccionado (H1) y la operación (H2).
- Prueba independiente: 50 conversaciones de prueba resueltas sin humano en al menos el 70 % y cero cambios fuera de reglas.
- Escenarios de aceptación:
  1. Dada una consulta de disponibilidad por WhatsApp, cuando el agente responde, entonces cotiza con tarifa real y ofrece link de pago en menos de 30 segundos.
  2. Dado un cambio de fechas dentro de la política (sin penalidad), cuando el huésped lo pide, entonces el sistema verifica identidad, política y autorización; inicialmente el cambio requiere aprobación humana. Solo podrá ejecutarse autónomamente tras ratificar Q-HOT-03 y superar evaluación.
  3. Dado un cambio con penalidad o cancelación, cuando se solicita, entonces el agente escala a recepción con el contexto completo y no actúa.
  4. Dada una reserva pagada 48 horas antes de llegar, cuando corre el agente, entonces ofrece un upsell (late check-out, desayuno) con link de pago.

**Casos borde**

- Reserva doble por carrera entre canal directo y OTA: se previene confirmación local incompatible; si un canal externo ya confirmó, se registra conflicto y escala para resolución humana según política pendiente, sin relocalizar automáticamente.
- Pago aprobado pero boleta rechazada por SII: la reserva se mantiene, la boleta se reintenta y se alerta.
- Huésped sin documento válido en check-in online: el registro queda incompleto y se exige en recepción.
- Agente que recibe lenguaje ofensivo o solicitud ambigua: queda pendiente de atención humana con motivo, nunca inventa tarifa.
- Caída del channel manager: se suspende confirmación automática cuando no exista cupo seguro, se conserva la solicitud y se escala para reconciliar.

## 3. Requisitos (obligatorio)

**Requisitos funcionales**

| ID | El sistema DEBE | Historia |
| --- | --- | --- |
| FR-001 | Mantener un inventario único de habitaciones con tarifas por fecha, ocupación y política de cancelación | H1 |
| FR-002 | Exponer un motor de reservas en la web propia con disponibilidad real y pago en línea | H1 |
| FR-003 | Sincronizar disponibilidad y reservas con al menos Booking y Airbnb en ambos sentidos | H1 |
| FR-004 | Cobrar por Webpay/Transbank o Mercado Pago y emitir el documento SII aplicable, sin duplicar anticipos ni documentos previos | H1 |
| FR-005 | Impedir sobreventa ante reservas concurrentes del mismo inventario | H1 |
| FR-006 | Permitir check-in online con datos del huésped, documento y firma de registro | H2 |
| FR-007 | Consumir una interfaz opcional de pedidos de cafetería para servicio a la habitación, con cargo a la cuenta del huésped | H2 |
| FR-008 | Generar y cerrar tareas de housekeeping y mantención por habitación y estado | H2 |
| FR-009 | Consolidar todos los cargos de la estadía en una cuenta y liquidarla al check-out | H2 |
| FR-010 | Atender por WhatsApp Business con un agente que consulta el sistema de registro seleccionado y propone cambios; escritura solo tras autorización y política aprobadas | H3 |
| FR-011 | Aplicar reglas de autonomía configurables: acciones permitidas, montos máximos, casos que escalan | H3 |
| FR-012 | Ofrecer upsells con link de pago en momentos definidos (pre-llegada, estadía, salida) | H3 |
| FR-013 | Registrar cada acción del agente en el registro de auditoría con integridad verificable y retención aprobada con evidencia de la conversación | H3 |
| FR-014 | Exponer disponibilidad y tarifas por un servidor MCP para agentes externos (modelo SiteMinder) | H3 |
| FR-015 | Operar sobre el core compartido (identidad, autorización, pagos, documentos y auditoría) sin duplicarlo | Todas |

**Entidades clave**

- Habitación y Tipo de habitación: capacidad, servicios, estado operativo (disponible, ocupada, limpieza, bloqueada).
- Tarifa y Plan tarifario: por fecha, ocupación, canal, política de cancelación.
- Reserva: huésped, habitaciones, fechas, canal de origen, estado, pagos, cuenta.
- Huésped: identidad, documento, preferencias, historial.
- Cuenta de estadía: cargos (alojamiento, pedidos, upsells), pagos, documentos tributarios.
- Tarea operativa: tipo (limpieza, mantención), habitación, responsable, estado.
- Canal: conector (directo, Booking, Airbnb), estado de sincronización, conflictos.
- Acción de agente: conversación, regla aplicada, acción, aprobador, resultado.

## 4. Criterios de éxito (obligatorio)

| ID | Resultado medible |
| --- | --- |
| SC-001 | Cero sobreventas en 90 días de operación con al menos dos canales activos |
| SC-002 | La disponibilidad se refleja en todos los canales en menos de 5 minutos en el 95 % de los cambios |
| SC-003 | Las reservas directas pasan del nivel actual a al menos 30 % del total en 6 meses |
| SC-004 | El 100 % de los pagos queda conciliado con su obligación documental aplicable; objetivo de entrega <60 s cuando proceda y haya disponibilidad externa, sujeto a ratificación; fallos quedan pendientes y alertados |
| SC-005 | El 60 % de los huéspedes completa check-in online antes de llegar |
| SC-006 | El agente resuelve al menos el 70 % de conversaciones de WhatsApp sin intervención humana |
| SC-007 | Cero acciones del agente fuera de sus reglas de autonomía (auditoría mensual del ledger) |
| SC-008 | Los upsells ofrecidos por el agente convierten al menos el 8 % (referencia Duve) |
| SC-009 | Un empleado nuevo opera recepción con el sistema tras 2 horas de capacitación |

## 5. Supuestos, dependencias y clarificaciones

**Supuestos**

- Hotel de menos de 50 habitaciones, un solo edificio, PMS actual y continuidad por confirmar en Q-HOT-01; no se decide abandonarlo.
- Los canales OTA relevantes son Booking y Airbnb; otros se agregan después.
- La cocina y el servicio a la habitación podrían compartir operación con la cafetería mediante interfaz opcional; no se replica su módulo por defecto.
- Recepción opera con horario; fuera de horario el agente es el primer contacto.

**Dependencias**

- Core (`000-core`) para H1; interfaz opcional de pedidos (`001` o adaptador autorizado) solo para el servicio a habitación de H2.
- Channel manager propio o integrado (evaluar en `research.md`: construir conector vs. contratar uno con API).
- Certificado SII, contrato Webpay Plus, cuenta WhatsApp Business API con plantillas aprobadas.
- Credenciales de partner de Booking y Airbnb (requieren proceso de certificación).

**Clarificaciones pendientes** (para `/speckit.clarify`)

- [ ] [NEEDS CLARIFICATION] ¿Cuántas habitaciones y tipos tiene el hotel, y hay temporada alta definida? Define tarifas y escala.
- [ ] [NEEDS CLARIFICATION] ¿Qué canales usan hoy y con qué volumen? Define el alcance de FR-003.
- [ ] [NEEDS CLARIFICATION] ¿Existe PMS actual con datos a migrar o se parte de cero?
- [ ] [NEEDS CLARIFICATION] ¿Política de cancelación y de cobro anticipado (total, parcial, garantía)?
- [ ] [NEEDS CLARIFICATION] ¿Se emite factura a empresas con frecuencia? Define si FR-004 incluye factura desde V1.
- [ ] [NEEDS CLARIFICATION] ¿Límite monetario del agente para ejecutar sin aprobación (por ejemplo, cambios sin penalidad hasta X pesos)?
- [ ] [NEEDS CLARIFICATION] ¿Housekeeping con personal propio o externo? Define acceso y notificaciones.

## Reglas normativas y de aceptación añadidas

- NFR-001: toda lectura, escritura, trabajo en cola y evidencia queda limitada por empresa y permiso; probar denegación entre empresas y roles.
- NFR-002: ningún agente ejecuta una acción financiera, tributaria o contractual sin control determinista y autorización vigente; escritura MCP deshabilitada inicialmente.
- NFR-003: reintentos conservan un solo efecto; estados desconocidos no se muestran como éxitos.
- NFR-004: retención, restauración y objetivos de recuperación requieren aprobación en Q-CORE-03; ninguna cifra de disponibilidad se asume acordada.
- NFR-005: medir latencia desde recepción hasta resultado confirmado, incluyendo errores, reintentos y desconexión. No declarar cumplimiento en muestras vacías.

Q-HOT-01: PMS actual y fuente de inventario; Q-HOT-02: acceso OTA/channel manager; Q-HOT-03: habitaciones, cancelación, anticipos, datos de registro y autonomía.

Los escenarios tributarios y SC de emisión en 30/60 segundos se conservan como aspiración de la fuente, sujetos a aplicabilidad fiscal y disponibilidad externa. No constituyen garantía del SII. El aislamiento local no garantiza por sí solo cero sobreventa entre OTA independientes.

Ver `acceptance.md` para pruebas por requisito; `../../docs/auditorias/trazabilidad.md` para origen y equivalencias. La investigación transversal está en `../../docs/investigacion/estado-del-arte.md`.


## Refinamiento competitivo de historias — 2026-10-16

Estado **PROPUESTO**, sin ratificación del cliente. Las siguientes definiciones amplían las historias originales con alias US, sin eliminarlas. Ante un caso específico se aplica la regla más explícita de esta sección; ninguna cambia los bloqueos comerciales. Evidencia por ID en `../../docs/investigacion-competitiva/matriz-evidencias.md`.

### Historia US-HOT-001 — enriquecimiento de H1 (P1)

Como huésped y recepcionista, quiero reservar una categoría disponible con cotización y estado de sincronización explícitos, para evitar sobreventa y promesas de disponibilidad basadas en datos inciertos.

**Identidad y estado:** alias de `002-hotel-reservas-concierge/H1`; conserva historia y prioridad, **REQUISITO PROPUESTO**. No hay validación del cliente ni observación de runtime.

**Descripción funcional y necesidad de negocio:** Reservar una categoría disponible con cotización y estado de sincronización explícitos. Responde a evitar sobreventa y promesas de disponibilidad basadas en datos inciertos; la evidencia competitiva precisa el comportamiento, no demuestra demanda comercial.

**Fuente de inspiración y evidencia:** H01, H02, H03, H04 en matriz-evidencias.md. Lectura documental, reconstrucción propia. Requisitos: FR-001,FR-002,FR-003,FR-004,FR-005,FR-016,FR-017 y NFR-001/002/003/006.

**Disparador:** el visitante indica fechas y ocupación y solicita cotización o confirmación de reserva.

**Precondiciones:** sistema de registro y conectores autorizados; política tarifa/cancelación/anticipo; antigüedad máxima ratificada.

**Flujo principal:** Consultar fechas/ocupación → mostrar oferta vigente → revalidar cupo/precio → retener según política → iniciar pago → confirmar una vez → registrar propagación por canal.

**Flujos alternativos y casos borde:** Cotización vence o cambia: mostrar diferencia y requerir nueva aceptación. Canal incierto sin cupo seguro: guardar solicitud pendiente y escalar, sin confirmar.

**Reglas de negocio y validaciones:** Unidad de inventario por fecha/tipo no es habitación física asignada. No habilitar sobreventa por opción de proveedor. No usar respuesta desactualizada para afirmar sincronizado.

**Datos y estados involucrados:** OfertaVersionada, TipoHabitación, cupo por fecha, retención, Reserva, referencia externa y estado por canal. Transiciones conservan actor, tenant, fecha y versión; el modelo específico detalla los estados.

**Interacción humana/agéntica:** el humano responde por revisión y aprobación; el agente solo consulta o propone dentro del permiso. Herramientas candidatas, campos mínimos, límites cero para compromiso, evidencia y reversión se detallan en [gobernanza comparada](../../docs/investigacion-competitiva/agentes.md) y [seguridad compartida](../../docs/arquitectura/seguridad.md). No se exige IA para completar este flujo.

**Dependencias:** 000, sistema de registro/PMS y canales habilitados según Q-HOT-01/02/03; pedidos de cafetería solo en servicio a habitación opcional.

**Riesgos:** Carrera local/OTA, cobro sin cupo y datos obsoletos.

**Criterios de aceptación Given/When/Then:**

- AC-US-HOT-001-01: Dada última unidad y cien intentos, cuando se confirma, entonces como máximo una reserva local obtiene cupo; conflictos externos se identifican y escalan.
- AC-US-HOT-001-02: Dada habitación sucia hoy pero vendible en fecha futura, cuando se busca esa fecha, entonces limpieza actual no elimina inventario futuro por sí sola.

**Métricas de éxito:** Sobreventas/confimaciones; desfase por canal p95; consultas bloqueadas por fuente obsoleta; latencia oferta. Valores objetivo y ventanas deben ratificarse; no hay resultados medidos ni beneficio financiero calculado.


### Historia US-HOT-002 — enriquecimiento de H2 (P2)

Como recepcionista y responsable de housekeeping, quiero asignar y preparar la habitación sin mezclar limpieza y reserva, para recibir al huésped en un recurso operativo conservando ocupación futura.

**Identidad y estado:** alias de `002-hotel-reservas-concierge/H2`; conserva historia y prioridad, **REQUISITO PROPUESTO**. No hay validación del cliente ni observación de runtime.

**Descripción funcional y necesidad de negocio:** Asignar y preparar la habitación sin mezclar limpieza y reserva. Responde a recibir al huésped en un recurso operativo conservando ocupación futura; la evidencia competitiva precisa el comportamiento, no demuestra demanda comercial.

**Fuente de inspiración y evidencia:** H05, H01 en matriz-evidencias.md. Lectura documental, reconstrucción propia. Requisitos: FR-006,FR-007,FR-008,FR-009,FR-016 y NFR-001/002/003/006.

**Disparador:** recepción prepara un check-in/check-out o housekeeping informa un cambio de preparación.

**Precondiciones:** reserva válida; roles de limpieza/inspección; integración gastronómica opcional habilitada.

**Flujo principal:** Ver reserva → verificar registro → asignar recurso físico → consultar limpieza/mantenimiento → habilitar entrada solo con condiciones cumplidas → crear cargos autorizados → liquidar y crear tarea de salida.

**Flujos alternativos y casos borde:** Limpieza completa con mantenimiento activo: no habilitar entrada. Inspección solo si política exige; discrepancia con recepción queda pendiente de supervisor.

**Reglas de negocio y validaciones:** Limpia, inspeccionada, asignada, ocupada y bloqueada son dimensiones distintas. Habitación no preparada no anula automáticamente venta futura. Pedido/cargo idempotentes y entre empresas solo mediante permiso.

**Datos y estados involucrados:** Asignación, estadoLimpieza, bloqueoTécnico, tarea/responsable, inspección opcional, cargo y cuenta. Transiciones conservan actor, tenant, fecha y versión; el modelo específico detalla los estados.

**Interacción humana/agéntica:** el humano responde por revisión y aprobación; el agente solo consulta o propone dentro del permiso. Herramientas candidatas, campos mínimos, límites cero para compromiso, evidencia y reversión se detallan en [gobernanza comparada](../../docs/investigacion-competitiva/agentes.md) y [seguridad compartida](../../docs/arquitectura/seguridad.md). No se exige IA para completar este flujo.

**Dependencias:** 000, sistema de registro/PMS y canales habilitados según Q-HOT-01/02/03; pedidos de cafetería solo en servicio a habitación opcional.

**Riesgos:** Asignación insegura, exposición de nombre huésped y cargo duplicado.

**Criterios de aceptación Given/When/Then:**

- AC-US-HOT-002-01: Dada habitación limpia con mantenimiento abierto, cuando se intenta check-in, entonces se bloquea y se ofrece gestión humana de asignación.
- AC-US-HOT-002-02: Dado checkout completado, cuando housekeeping termina, entonces solo cambia preparación; reservas de otras fechas permanecen intactas.

**Métricas de éxito:** Incidentes de asignación; tiempo checkout→preparada; tareas vencidas; discrepancias revisadas. Valores objetivo y ventanas deben ratificarse; no hay resultados medidos ni beneficio financiero calculado.


### Historia US-HOT-003 — enriquecimiento de H3 (P3)

Como huésped autenticado y recepción, quiero recibir respuesta basada en datos y transferir la atención con contexto, para resolver consultas sin cambios de reserva no autorizados.

**Identidad y estado:** alias de `002-hotel-reservas-concierge/H3`; conserva historia y prioridad, **REQUISITO PROPUESTO**. No hay validación del cliente ni observación de runtime.

**Descripción funcional y necesidad de negocio:** Recibir respuesta basada en datos y transferir la atención con contexto. Responde a resolver consultas sin cambios de reserva no autorizados; la evidencia competitiva precisa el comportamiento, no demuestra demanda comercial.

**Fuente de inspiración y evidencia:** H06, H07, H08, H09, H10 en matriz-evidencias.md. Lectura documental, reconstrucción propia. Requisitos: FR-010,FR-011,FR-012,FR-013,FR-014,FR-017 y NFR-001/002/003/006.

**Disparador:** llega una consulta WhatsApp, petición de cambio de reserva o solicitud explícita de atención humana.

**Precondiciones:** identidad cuando hay datos privados; fuente vigente, canal permitido y receptor humano configurado.

**Flujo principal:** Recibir consulta → clasificar necesidad → recuperar datos mínimos vigentes → responder o proponer → verificar límites → si hace falta transferir con motivo/contexto → registrar dueño y estado.

**Flujos alternativos y casos borde:** Cliente pide humano, información falta o reserva se modifica: abrir transferencia; sin receptor disponible dejar estado pendiente con canal de contacto aprobado, sin afirmar resuelto.

**Reglas de negocio y validaciones:** Una respuesta de texto, link o propuesta no confirma transacción. Durante atención humana se suspende respuesta automática de compromiso; reanudar solo por evento autorizado. Autopricing no se habilita.

**Datos y estados involucrados:** ConversaciónReferenciada, estadoAtención, responsable, motivo, fuente/fecha, propuesta, aprobación y resultado. Transiciones conservan actor, tenant, fecha y versión; el modelo específico detalla los estados.

**Interacción humana/agéntica:** el humano responde por revisión y aprobación; el agente solo consulta o propone dentro del permiso. Herramientas candidatas, campos mínimos, límites cero para compromiso, evidencia y reversión se detallan en [gobernanza comparada](../../docs/investigacion-competitiva/agentes.md) y [seguridad compartida](../../docs/arquitectura/seguridad.md). Fallar cerrado si faltan evidencia, permiso o conectividad.

**Dependencias:** 000, sistema de registro/PMS y canales habilitados según Q-HOT-01/02/03; pedidos de cafetería solo en servicio a habitación opcional.

**Riesgos:** Suplantación, tarifa inventada, pérdida de transferencia y doble atención.

**Criterios de aceptación Given/When/Then:**

- AC-US-HOT-003-01: Dada solicitud de cancelación, cuando se deriva, entonces recepción recibe resumen mínimo y referencia; el agente no cancela ni marca resuelto.
- AC-US-HOT-003-02: Dado estado en atención humana, cuando llega mensaje adicional, entonces no dispara una modificación autónoma ni dos respuestas de compromiso.

**Métricas de éxito:** Resoluciones correctas/elegibles con reapertura controlada; transferencias completadas/iniciadas; costo/conversación p95. Valores objetivo y ventanas deben ratificarse; no hay resultados medidos ni beneficio financiero calculado.


## Requisitos derivados de investigación competitiva

Son propuestas de comportamiento propio, sin atribuirlo como implementación observada del competidor.

| ID | El sistema DEBE | Historia |
|---|---|---|
| FR-016 | Distinguir inventario vendible por fecha/tipo, asignación física y preparación de habitación; impedir check-in con bloqueo operativo sin eliminar automáticamente inventario futuro | H1/H2 |
| FR-017 | Registrar vigencia y estado de sincronización por canal y procedencia de la oferta; no confirmar disponibilidad incierta y gestionar transferencia humana con estado explícito | H1/H3 |

- NFR-006: toda oferta, extracción o decisión derivada declara procedencia, vigencia e incertidumbre; si no hay evidencia suficiente, no genera compromiso automático ni se informa como éxito. La captura manual conserva permisos, trazabilidad e idempotencia equivalentes.

## Profundización funcional de las otras verticales

Estado **REQUISITO PROPUESTO**; evidencia adicional y límites en investigación competitiva/continuacion-01. Conserva IDs/historias previos y bloqueos.

### RF-HOT-01 — Modificar o cancelar sin confundir liquidación y devolución

**Historia US-HOT-001** (misma historia/ID, prioridad P1; no es historia nueva).

Como huésped autenticado y recepción autorizada, quiero modificar o cancelar sin confundir liquidación y devolución, para conocer diferencias de precio y resultado financiero antes de comprometer un cambio de reserva.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** H11, H12, H18, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** solicitud de nuevas fechas, categoría, habitación o cancelación.

**Precondiciones:** reserva vigente versionada, identidad validada, política de cambios/cancelación y aprobador definidos.

**Flujo principal:**

1. Recuperar reserva, versión, fuente y condiciones aceptadas.
2. Calcular propuesta con fechas/unidad, cupo, tarifa, penalidad y saldo anterior/nuevo.
3. Mostrar diferencias y obtener aceptación/aprobación ligada a la propuesta.
4. Revalidar versión/cupo y aplicar la transición en el sistema de registro seleccionado.
5. Separar resultado de cambio, actualización de canales y propuesta de devolución; informar estados.

**Flujos alternativos y excepciones:** Tarifa cambia durante revisión: invalidar propuesta. Timeout: desconocido, consultar autoridad antes de repetir. Cancelación OTA requiere proceso del canal, no se convierte en cancelación directa.

**Reglas de negocio/validaciones:** Cancelar no devuelve dinero ni borra historial. No aplicar tarifa por arrastrar una reserva sin revisar diferencia. El agente no aprueba penalidad ni reembolso; una habitación sin asignar no es una reserva inexistente.

**Datos y estados:** PropuestaCambio, versionBase, desglose anterior/nuevo, aceptación, aprobación, ResultadoCambio; SolicitudDevolucion separada de Pago y Reserva.

**Dependencias:** Q-HOT-01/02/03 y Q-CORE-02; pagos/documentos del core con referencias, sin elegir PMS.

**Riesgos:** Cambio no consentido, doble devolución, venta sin cupo y fuga de datos huésped.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-HOT-001-03: Dada reserva pagada y política de ejemplo que permite devolución, cuando recepción cancela, entonces la reserva puede quedar cancelada pero el dinero permanece sin devolver hasta operación financiera autorizada y confirmada.
- AC-US-HOT-001-04: Dada nueva tarifa superior a la aceptada, cuando se previsualiza el cambio, entonces muestra diferencia y no la aplica sin nueva aceptación.
- AC-US-HOT-001-05: Dado timeout tras aplicar un cambio, cuando se reintenta, entonces consulta estado y no crea segunda reserva, cargo ni devolución.

**Métricas:** cambios con desglose y consentimiento/cambios aplicados; devoluciones duplicadas; tiempo p95 de regularización. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


### RF-HOT-02 — Vincular extras a estadía y entrega operativa

**Historia US-HOT-002** (misma historia/ID, prioridad P2; no es historia nueva).

Como recepcionista, huésped y responsable del servicio, quiero vincular extras a estadía y entrega operativa, para cargar exactamente el servicio contratado y asignar su cumplimiento.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** H14, H16, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** aceptación de desayuno, mejora o pedido de habitación.

**Precondiciones:** reserva/cuenta válidas, producto/servicio mapeado, periodicidad y responsable aprobados.

**Flujo principal:**

1. Identificar cuenta y producto con precio/periodicidad vigentes.
2. Calcular cantidad según configuración aceptada y revalidar disponibilidad si consume cupo.
3. Registrar cargo único y su referencia al pedido/servicio.
4. Asignar tarea de cumplimiento cuando proceda y seguir su estado.
5. Conciliar cancelación o modificación mediante ajuste autorizado, no borrado.

**Flujos alternativos y excepciones:** Mapeo de producto/categoría ausente deja cargo en revisión. Pedido gastronomía no habilitado se informa sin duplicar cocina. Fallo tras cargo se concilia antes de repetir.

**Reglas de negocio/validaciones:** Una noche, persona o estadía son bases distintas. Cargo, pago, documento tributario y entrega son estados separados. Solo el servicio correspondiente conoce la periodicidad; el core no contiene catálogo hotelero ni gastronómico universal.

**Datos y estados:** ServicioEstadia, ReglaCantidad versionada, Cargo, CuentaReferencia, CategoriaExterna opcional, TareaCumplimiento y relación con PedidoExterno.

**Dependencias:** 000 y política fiscal; interfaz opcional 001 para pedidos, no dependencia de hotel H1.

**Riesgos:** Multiplicar extras por noches indebidamente, cargo a huésped ajeno y servicio pagado no entregado.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-HOT-002-03: Dada configuración de ejemplo de desayuno por persona/noche para dos personas y tres noches y una botella por estadía, cuando se calcula, entonces desayuno tiene seis unidades y botella una, con reglas visibles.
- AC-US-HOT-002-04: Dado cargo registrado pero tarea sin entregar, cuando se consulta la cuenta, entonces distingue cobro/cargo de cumplimiento y no informa servicio entregado.
- AC-US-HOT-002-05: Dado mismo pedido/cargo reintentado, cuando el conector responde dos veces, entonces hay un cargo y una tarea vinculados, sin segunda comanda.

**Métricas:** cargos conciliados/servicios aceptados; tareas vencidas; error de cantidad; costo por extra gestionado. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


### RF-HOT-03 — Recepcionar eventos y reconciliar inventario de canales

**Historia US-HOT-001** (misma historia/ID, prioridad P1; no es historia nueva).

Como recepción y operador de integración, quiero recepcionar eventos y reconciliar inventario de canales, para recuperar reservas y cambios sin perderlos ni repetir efectos por notificaciones.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** H13, H15, H17, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** llega un evento o se reanuda una ventana de sincronización tras fallo.

**Precondiciones:** conector autorizado, correspondencia de propiedad/recurso y mecanismo de autenticación/revisión definidos.

**Flujo principal:**

1. Validar origen/cuenta y correspondencia de propiedad.
2. Registrar recepción durable y referencia de notificación.
3. Emitir acuse solo en el punto permitido por el contrato del canal tras recepción durable validada; si el protocolo exige aplicación previa, respetar esa condición sin declarar éxito anticipado.
4. Recuperar el estado autoritativo cuando la notificación no incluye todos los datos.
5. Aplicar una vez la transición válida y conservar conflictos.
6. Reanudar por cursor/ventana y comparar cupos/estados.

**Flujos alternativos y excepciones:** No se puede persistir: no acusar recepción que no existe. Mapeo desconocido: recepción retenida en revisión según protocolo contratado, sin inventario ficticio. Caída tras acuse: recuperar del registro durable.

**Reglas de negocio/validaciones:** El acuse no confirma pago ni reserva local válida. Una notificación puede representar cambios sucesivos. No asumir orden total, entrega única, API directa Booking habilitada ni que Channels Plus sea el conector PMS contratado.

**Datos y estados:** RecepcionEvento, ClaveProveedor/cuenta, referenciaExterna, huella, recibidoEn, ocurrioEn si existe, estadoRecepcion, estadoAplicacion, cursor/ventana y Conflicto.

**Dependencias:** Q-HOT-02 y capacidades/contratos 000; control de cupos permanece hotelero.

**Riesgos:** Evento perdido, replay, overbooking, deduplicación incorrecta y pérdida de actualización concurrente.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-HOT-001-06: Dada falla de almacenamiento antes de recepción durable, cuando llega reserva del canal, entonces no se declara acuse exitoso ni confirmación local.
- AC-US-HOT-001-07: Dada recepción durable y acuse completado pero caída antes de aplicar, cuando se recupera, entonces se reaplica desde evidencia sin perder reserva ni duplicar efectos.
- AC-US-HOT-001-08: Dados cinco eventos con igual ID notificación y una actualización nueva del mismo ID de reserva, cuando se reconcilian, entonces se deduplica notificación pero no se descarta el cambio legítimo por usar solo ID reserva.

**Métricas:** eventos recibidos/aplicados/en revisión por canal; lag p95; conflictos detectados; duración de interrupción. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


### RF-HOT-04 — Concierge: separar conversación, propuesta y compromiso

**Historia US-HOT-003** (misma historia/ID, prioridad P3; no es historia nueva).

Como huésped y responsable de recepción, quiero concierge: separar conversación, propuesta y compromiso, para recibir respuestas útiles y atención humana sin acciones de negocio supuestas.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** H06, H07, H08, H09, H11, H13, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** consulta de reserva/extra, cambio con efecto económico o solicitud de humano.

**Precondiciones:** identidad para datos privados, datos vigentes, política de acción y receptor humano definidos.

**Flujo principal:**

1. Clasificar intención sin inferir autoridad.
2. Consultar evidencia mínima vigente.
3. Responder o preparar una propuesta diferenciada de confirmación.
4. Si requiere acción/juicio, transferir con responsable y motivo; suspender cambios automáticos.
5. Registrar aceptación humana, resultado y reapertura, distinguiendo estado del canal y del negocio.

**Flujos alternativos y excepciones:** Sin receptor: pendiente visible, sin prometer hora no aprobada. Cambio automático de reserva no dispara mensajes repetidos en cada notificación. Solicitud ambigua pide precisión sin inventar dato.

**Reglas de negocio/validaciones:** Responder, cotizar, enlazar pago, modificar PMS y cobrar son capacidades diferentes. Mensaje del cliente no autoriza devolución. No se usa un porcentaje comercial del proveedor como medición propia.

**Datos y estados:** Intencion, Respuesta/Propuesta, EvidenciaFuente, Transferencia, responsable y resultadoNegocio separado de estadoConversacion.

**Dependencias:** Q-HOT-03, política canal y perfil herramienta; sin permisos de escritura MCP por defecto.

**Riesgos:** Confundir marketing con autonomía, prompt injection, spam por eventos y falsa resolución.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-HOT-003-03: Dada conversación en la que el huésped pide cancelar y devolver, cuando responde concierge, entonces prepara contexto y escala; no ejecuta ninguna de las dos operaciones.
- AC-US-HOT-003-04: Dada misma modificación notificada tres veces, cuando evalúa comunicaciones, entonces no envía tres confirmaciones ni tres upsells por el mismo hecho.
- AC-US-HOT-003-05: Dada respuesta correcta con link a un motor, cuando se contabiliza éxito, entonces no figura como reserva pagada hasta evidencia de negocio independiente.

**Métricas:** resolución correcta sin reapertura/consultas elegibles; intervención, p95, costo total por resolución y acciones denegadas. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


## Requisitos de recuperación y semántica de dominio

| ID | El sistema DEBE | Historia |
|---|---|---|
| FR-018 | Previsualizar y aprobar cambios/cancelaciones con versión, cupo, tarifa, penalidad y saldo; separar aplicación en reserva de propagación, devolución y documento tributario | H1/H3 |
| FR-019 | Registrar extras con producto/servicio, cantidad y periodicidad aprobadas, cuenta/destino y tarea de cumplimiento; separar cargo, pago, documento y entrega sin duplicar por reintento | H2/H3 |
| FR-020 | Validar y conservar recepción de eventos de canales, recuperar datos autoritativos y reconciliar por ventana/cursor; distinguir acuse durable de aplicación, pago y confirmación comercial | H1/H3 |


### Bloqueos adicionales de la profundización

Q-HOT-04/05/06: ver [decisiones pendientes](../../docs/investigacion-competitiva/decisiones-pendientes.md). Son reglas para ratificar, no respuestas inferidas del mercado. Las historias permanecen propuestas y la feature **BLOCKED** para implementar.


Nota de protocolo: acuse de recepción y aceptación/aplicación se separan conceptualmente, pero el punto de acuse debe respetar el contrato real del canal. El ID de notificación externo se usa solo si el proveedor lo define; sin él, la clave/huella y recuperación requieren investigación, sin inventar campos ni deduplicar todos los cambios por ID de reserva.
