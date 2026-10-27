# Historias de usuario del Manual Maestro — cola de construcción

Fuente: `Manual_Maestro_Conceptual_Grupo_Salman_V1.docx` (V1.0, 27-10-2026), leído
completo. Fecha de esta cola: 2026-10-27. Clase de evidencia: **REQUISITO PROPUESTO**;
ninguna historia se construye ni ratifica aquí y ninguna decisión que el manual deja
pendiente en su §9 se firma: las reglas pendientes se anotan como pendientes.
Trazabilidad de ids: las que ya existen en `specs/002-hotel-reservas-concierge/spec.md`
reutilizan su id (US-HOT o el FR que las cubre); las nuevas usan `HU-HOT-n` correlativo.
El resultado que debe poder contarse es el recorrido del huésped (Manual §3):
descubrimiento, cotización y reserva, pago y confirmación, estadía y salida, cierre
financiero; no es un sitio de reservas suelto ni una contabilidad suelta (Manual §1).

## Fase 1 — Hotel Herencia (17 habitaciones, Herencia SpA)

Orden: el que un huésped y luego recepción, caja y gerencia las necesitan.

### HU-HOT-01 — Configurar habitación y tarifa

- **Id:** HU-HOT-01 (nueva; satisface FR-001 de `specs/002-hotel-reservas-concierge/spec.md`)
- **Fase:** 1 Hotel Herencia
- **Actor y objetivo:** el administrador del hotel da de alta las 17 habitaciones, sus tipos, tarifas por fecha y políticas, para que el motor de reservas opere sobre datos autorizados.
- **Por qué existe:** el Manual §10 exige como primer paso del resultado mínimo que «un usuario autorizado configura habitaciones y tarifas», y el §3 (cotización y reserva) requiere que el motor consulte «disponibilidad real, tarifas, ocupación permitida, restricciones y políticas».
- **Paso anterior:** ninguno; es la primera de la cola. **Paso siguiente:** consultar disponibilidad y cotizar (US-HOT-001).
- **Datos que usa y fuente de verdad:** habitaciones, tipos, capacidad, tarifas por fecha y ocupación, temporadas, restricciones y política de cancelación. Fuente de verdad: la plataforma, registro autorizado de inventario y tarifas (Manual §1: «una sola fuente de verdad por dato»).
- **Excepciones:** usuario sin permiso (solo rol administrador; la denegación queda auditada); tarifas superpuestas para la misma fecha y tipo (rechazo con motivo); modificación con reservas existentes (no altera el precio ya aceptado por un huésped).
- **Criterio de aceptación:** Dado un usuario administrador autenticado, cuando configura las habitaciones con tipo y tarifa vigente para una fecha, entonces el inventario queda consultable por el motor con tarifa y política visibles; dado un usuario sin rol administrador, cuando intenta configurar, entonces es denegado y el intento queda auditado.
- **Dependencia:** ninguna; es la primera de la cola.
- **Regla definitiva:** temporadas, tarifas 2027, mínimos de estadía, anticipos y descuentos son decisión del Manual §9 (políticas 2027): no codificar la cifra ni el proveedor; la historia existe y la regla queda pendiente.

### US-HOT-001 — Consultar disponibilidad y cotizar

- **Id:** US-HOT-001 (ya existe en `specs/002-hotel-reservas-concierge/spec.md`; H1, P1)
- **Fase:** 1 Hotel Herencia
- **Actor y objetivo:** el visitante de la web consulta fechas y ocupación y recibe una oferta real, para decidir la reserva con datos ciertos.
- **Por qué existe:** Manual §3 (cotización y reserva): «el motor consulta disponibilidad real, tarifas, ocupación permitida, restricciones y políticas»; Manual §10: «un cliente consulta disponibilidad y reserva».
- **Paso anterior:** configurar habitación y tarifa (HU-HOT-01). **Paso siguiente:** reservar sin sobreventa (US-HOT-001).
- **Datos que usa y fuente de verdad:** disponibilidad por fecha y tipo, tarifa vigente, impuestos y política. Fuente de verdad: inventario y tarifas de la plataforma dados de alta en HU-HOT-01.
- **Excepciones:** canal caído (sin cupo seguro se guarda la solicitud pendiente y se escala, sin confirmar — flujo alterno de US-HOT-001 en spec); cotización que vence o cambia (se muestra la diferencia y se requiere nueva aceptación); usuario sin permiso para consultar tarifas internas.
- **Criterio de aceptación:** Dadas fechas y número de huéspedes, cuando el visitante consulta, entonces ve solo habitaciones disponibles con tarifa vigente y total con IVA (escenario 1 de H1 en spec).
- **Dependencia:** HU-HOT-01.
- **Regla definitiva:** la oferta se calcula solo desde la fuente autorizada y declara vigencia; las temporadas y tarifas son decisión del Manual §9: no codificar la cifra; la historia existe y la regla queda pendiente.

### US-HOT-001 — Reservar sin sobreventa

- **Id:** US-HOT-001 (ya existe; misma historia H1; no se renombra)
- **Fase:** 1 Hotel Herencia
- **Actor y objetivo:** el huésped confirma la reserva y el sistema retiene el cupo de forma consistente, para que el inventario prometido exista.
- **Por qué existe:** Manual §3: «bloquea inventario de forma consistente, evita sobreventas y genera una reserva con identificador único y estado definido»; Manual §1: cada función debe formar parte de un proceso trazable, no de un sitio de reservas suelto.
- **Paso anterior:** consultar disponibilidad y cotizar (US-HOT-001). **Paso siguiente:** pago y confirmación (US-HOT-001).
- **Datos que usa y fuente de verdad:** retención de cupo, reserva con identificador único, estado, canal de origen. Fuente de verdad: la plataforma (inventario único, FR-001/FR-005).
- **Excepciones:** sobreventa (carrera por la última unidad: como máximo una reserva obtiene cupo y el conflicto se identifica y escala — AC-US-HOT-001-01); canal caído (solicitud pendiente sin confirmar); usuario sin permiso; reserva doble por carrera entre canal directo y OTA (se registra conflicto y se escala, sin relocalizar automáticamente — caso borde de la spec).
- **Criterio de aceptación:** Dada la última unidad disponible y cien intentos simultáneos, cuando se confirma, entonces como máximo una reserva local obtiene cupo y los conflictos externos se identifican y escalan (AC-US-HOT-001-01).
- **Dependencia:** US-HOT-001 (consulta y cotización).
- **Regla definitiva:** el bloqueo de inventario, el identificador único y el estado definido se construyen; la política de anticipo y penalidad que condiciona la retención es decisión del Manual §9: no codificar la cifra ni el contrato; la historia existe y la regla queda pendiente.

### US-HOT-001 — Pago y confirmación

- **Id:** US-HOT-001 (ya existe; misma historia H1)
- **Fase:** 1 Hotel Herencia
- **Actor y objetivo:** el huésped paga en línea y recibe confirmación y comprobante; caja queda con el cobro registrado sin datos sensibles de tarjeta.
- **Por qué existe:** Manual §3 (pago y confirmación): «se calcula el importe, anticipos, impuestos y condiciones aplicables; se registra la operación del proveedor de pagos, sin almacenar datos sensibles de tarjeta; se confirma según reglas y se envía comprobante o mensaje».
- **Paso anterior:** reservar sin sobreventa (US-HOT-001). **Paso siguiente:** check-in (US-HOT-002).
- **Datos que usa y fuente de verdad:** importe, anticipo, impuestos, referencia de la operación del proveedor de pagos (nunca la tarjeta), confirmación y documento tributario aplicable. Fuentes: el proveedor de pagos para el resultado del cobro; la plataforma para reserva, confirmación y documento (SC-004).
- **Excepciones:** pago duplicado (un solo efecto financiero ante repeticiones — NFR-003); pago aprobado pero documento rechazado (la reserva se mantiene, se reintenta y se alerta — caso borde de la spec); canal caído (confirmación pendiente, jamás declarada como éxito); cancelación con devolución (la devolución queda separada de la liquidación y no se ejecuta sin operación financiera autorizada — RF-HOT-01, AC-US-HOT-001-03); usuario sin permiso.
- **Criterio de aceptación:** Dada una reserva con pago aprobado, cuando el proveedor confirma, entonces se envía la confirmación y se procesa el documento tributario aplicable sin duplicación, con estado pendiente y alerta ante fallo (escenario 2 de H1 en spec); dada la misma reserva cobrada dos veces, cuando se registra, entonces queda un solo efecto financiero.
- **Dependencia:** US-HOT-001 (reserva).
- **Regla definitiva:** la pasarela de pago y la facturación/DTE son decisión del Manual §9 (canales e integraciones): no codificar la cifra ni el proveedor; la historia existe y la regla queda pendiente (el cobro queda detrás de un puerto sin adaptador real hasta entonces).

### US-HOT-002 — Check-in con asignación y registro

- **Id:** US-HOT-002 (ya existe en spec; H2, P2)
- **Fase:** 1 Hotel Herencia
- **Actor y objetivo:** recepción realiza el check-in del huésped confirmado, le asigna habitación y completa el registro requerido (o verifica el check-in online previo).
- **Por qué existe:** Manual §3 (estadía y salida): «recepción realiza check-in, asignación de habitación y registro requerido».
- **Paso anterior:** pago y confirmación (US-HOT-001). **Paso siguiente:** consumos y extras a la cuenta (US-HOT-002).
- **Datos que usa y fuente de verdad:** reserva confirmada, registro del huésped, asignación física de habitación, estado operativo y de preparación de la habitación. Fuente de verdad: la plataforma.
- **Excepciones:** habitación no preparada o con mantenimiento abierto (se bloquea el check-in y se ofrece gestión humana de asignación — AC-US-HOT-002-01); huésped sin documento válido en el registro (el registro queda incompleto y se exige en recepción — caso borde de la spec); usuario sin permiso (solo recepción).
- **Criterio de aceptación:** Dada una habitación limpia con mantenimiento abierto, cuando se intenta el check-in, entonces se bloquea y se ofrece gestión humana de asignación (AC-US-HOT-002-01).
- **Dependencia:** US-HOT-001 (pago y confirmación).
- **Regla definitiva:** la documentación mínima de registro se toma de la resolución registrada de Q-HOT-03 (nombre, documento de identidad, nacionalidad, correo y teléfono, 2026-10-27) y su ajuste fino es decisión del Manual §9; no se inventan ni piden datos adicionales.

### US-HOT-002 — Consumos y extras a la cuenta

- **Id:** US-HOT-002 (ya existe; cubierta por FR-019 y RF-HOT-02 en spec)
- **Fase:** 1 Hotel Herencia
- **Actor y objetivo:** recepción, servicio y housekeeping cargan consumos adicionales y extras a la cuenta de la estadía, imputándolos correctamente al huésped.
- **Por qué existe:** Manual §3: «consumos adicionales se imputan correctamente»; Manual §4 (caja, pagos, facturación y conciliación): cobros por canal y medio con trazabilidad.
- **Paso anterior:** check-in (US-HOT-002). **Paso siguiente:** check-out y liquidación (US-HOT-002).
- **Datos que usa y fuente de verdad:** producto o servicio, cantidad, periodicidad, cuenta de estadía, tarea de cumplimiento y pedido externo de origen. Fuente de verdad: la cuenta de estadía en la plataforma; el pedido de cafetería es origen del cargo, no un segundo registro.
- **Excepciones:** cargo duplicado por reintento del conector (un solo cargo y una sola tarea, sin segunda comanda — AC-US-HOT-002-05); producto sin mapeo (el cargo queda en revisión); servicio cobrado pero no entregado (la cuenta distingue cobro de cumplimiento — AC-US-HOT-002-04); usuario sin permiso.
- **Criterio de aceptación:** Dada una configuración aprobada de desayuno por persona y noche (dos personas, tres noches) y una botella por estadía, cuando se calcula el cargo, entonces el desayuno tiene seis unidades y la botella una, con las reglas visibles (AC-US-HOT-002-03).
- **Dependencia:** US-HOT-002 (check-in).
- **Regla definitiva:** el cálculo de cantidades se construye; los precios y el catálogo de extras no se inventan (fuente: la operación autorizada; el vínculo con Cafetería Fadwa es fase 2) y la aprobación de reglas es decisión del Manual §9 (operación y presupuesto): no codificar la cifra; la historia existe y la regla queda pendiente.

### US-HOT-002 — Check-out y liquidación

- **Id:** US-HOT-002 (ya existe; cubierta por FR-009 en spec)
- **Fase:** 1 Hotel Herencia
- **Actor y objetivo:** recepción liquida la cuenta consolidada de la estadía y emite los documentos que corresponden; el huésped paga el saldo.
- **Por qué existe:** Manual §3: «check-out liquida saldo y emite documentos según corresponda»; Manual §4: cuentas por cobrar y reembolsos con evidencia.
- **Paso anterior:** consumos y extras (US-HOT-002). **Paso siguiente:** conciliación y cierre financiero (HU-HOT-02).
- **Datos que usa y fuente de verdad:** cuenta de estadía consolidada (alojamiento, consumos, extras), saldo, pagos aplicados, documentos tributarios. Fuente de verdad: la plataforma.
- **Excepciones:** cargo pendiente al salir (se concilia el saldo y se documenta el hecho sin repetir anticipos ya cubiertos — escenario 4 de H2 en spec); cancelación o devolución (la liquidación se separa de la devolución y esta última exige operación financiera autorizada — RF-HOT-01, AC-US-HOT-001-03); pago duplicado (un solo efecto); usuario sin permiso (solo recepción/caja).
- **Criterio de aceptación:** Dado un cargo pendiente al check-out, cuando el huésped paga, entonces se concilia el saldo y se documenta el hecho aplicable sin repetir anticipos ya cubiertos (escenario 4 de H2 en spec).
- **Dependencia:** US-HOT-002 (consumos).
- **Regla definitiva:** la emisión de documentos «según corresponda» queda supeditada a la política fiscal aprobada, que es decisión del Manual §9 (facturación): no codificar el proveedor ni la política; la historia existe y la regla queda pendiente.

### HU-HOT-02 — Conciliación y cierre financiero diario

- **Id:** HU-HOT-02 (nueva; alineada con SC-004 de la spec y con el cierre financiero del Manual §3)
- **Fase:** 1 Hotel Herencia
- **Actor y objetivo:** caja y gerencia cierran el día relacionando cada pago con su reserva, documento, caja y movimiento, para que el ciclo termine con reportes verificables.
- **Por qué existe:** Manual §3 (cierre financiero): «cada pago debe poder relacionarse con reserva, documento, caja, movimiento bancario y conciliación; cancelaciones, devoluciones, no-show y ajustes deben dejar evidencia»; Manual §10: «caja y conciliación presentan trazabilidad».
- **Paso anterior:** check-out y liquidación (US-HOT-002). **Paso siguiente:** indicador mínimo de gerencia (HU-HOT-03).
- **Datos que usa y fuente de verdad:** pagos, documentos, caja, movimientos bancarios, cancelaciones, devoluciones, no-show y ajustes. Fuentes: los registros operativos de la plataforma y el extracto bancario; la conciliación es la comprobación entre ambos (Manual §12).
- **Excepciones:** pago duplicado (un solo efecto); diferencia de caja (queda como ajuste con evidencia y autorización, no como borrado); devolución parcial (separada de la cancelación y de la liquidación); canal caído (pagos y eventos quedan pendientes, nunca declarados conciliados); usuario sin permiso (solo caja/gerencia).
- **Criterio de aceptación:** Dado un día con reservas pagadas, una cancelación con devolución parcial y un cobro duplicado corregido, cuando caja cierra el día, entonces cada pago queda relacionado con reserva, documento y caja, y las diferencias quedan como ajustes con evidencia y autorización.
- **Dependencia:** US-HOT-002 (check-out y liquidación).
- **Regla definitiva:** la integración contable y el proveedor bancario o pasarela son decisión del Manual §9: no codificar el proveedor; la historia existe y la regla queda pendiente.

### HU-HOT-03 — Indicador mínimo de gerencia

- **Id:** HU-HOT-03 (nueva; alineada con el Manual §4 y los SC de la spec)
- **Fase:** 1 Hotel Herencia
- **Actor y objetivo:** gerencia consulta al cierre del día los indicadores mínimos (ocupación, ADR, RevPAR e ingresos por canal), para dirigir la operación con datos verificables.
- **Por qué existe:** Manual §4 (indicadores y control): «ocupación, ADR, RevPAR, ingresos por canal, cancelaciones…; cada indicador necesita fórmula, periodo, fuente y responsable»; Manual §10: «gerencia consulta indicadores».
- **Paso anterior:** conciliación y cierre financiero (HU-HOT-02). **Paso siguiente:** fin del recorrido; la operación diaria vuelve a configurar, consultar y reservar.
- **Datos que usa y fuente de verdad:** reservas, ocupación, tarifas efectivas, ingresos por canal y cancelaciones del día. Fuente de verdad: el cierre financiero y las reservas de la plataforma.
- **Excepciones:** día con datos incompletos (el indicador declara su fórmula, periodo y fuente, y no informa éxito sin muestra); usuario sin permiso (solo gerencia).
- **Criterio de aceptación:** Dado el cierre diario completado, cuando gerencia consulta los indicadores del día, entonces ve ocupación, ADR y RevPAR con fórmula, periodo, fuente y responsable declarados.
- **Dependencia:** HU-HOT-02 (conciliación).
- **Regla definitiva:** las fórmulas base se construyen; los objetivos numéricos se ratifican con la gerencia y no se inventan (los SC de la spec son objetivos propuestos, no medidos). El resto de indicadores del Manual §4 (costos, margen, productividad, alertas) queda para la lista posterior.

## Fase 2 — Cafetería Fadwa (solo el vínculo con el hotel)

### FR-007 — Pedido de Cafetería Fadwa cargado a la habitación

- **Id:** FR-007 (ya existe en spec; historia US-HOT-002; interfaz opcional de pedidos)
- **Fase:** 2 Cafetería Fadwa
- **Actor y objetivo:** el huésped pide a la habitación desde el módulo de pedidos de Cafetería Fadwa y el cargo queda en su cuenta de estadía, sin pasar por recepción.
- **Por qué existe:** Manual §2: «fase 2: Cafetería Fadwa y su relación con el hotel»; Manual §3: «consumos adicionales se imputan correctamente»; spec H2: pedidos a la habitación con el módulo de pedidos de la cafetería.
- **Paso anterior:** consumos y extras a la cuenta (US-HOT-002, fase 1). **Paso siguiente:** fin; las fases posteriores exigen aprobación específica (Manual §2).
- **Datos que usa y fuente de verdad:** pedido, número de habitación, cuenta de estadía y comanda de cocina. Fuentes: el pedido nace en el módulo de pedidos (cafetería); la cuenta de estadía es de la plataforma hotel; una sola fuente por dato (Manual §1).
- **Excepciones:** pedido duplicado por reintento del conector (un solo cargo y una sola comanda — AC-US-HOT-002-05); interfaz no habilitada (se informa al huésped sin duplicar cocina — flujo alterno de RF-HOT-02); usuario sin permiso.
- **Criterio de aceptación:** Dado un pedido a la habitación, cuando se confirma, entonces aparece en cocina con número de habitación y se carga una sola vez a la cuenta del huésped (escenario 2 de H2 en spec y AC-US-HOT-002-05).
- **Dependencia:** US-HOT-002 (consumos y extras, fase 1).
- **Regla definitiva:** se consume la interfaz opcional; no se replica el módulo de la cafetería dentro del hotel (supuesto de la spec). Precios y catálogo de Fadwa se aprueban con la fase 2 (Manual §2 y §9): no codificar la cifra; la historia existe y la regla queda pendiente.

## Fases posteriores — lista corta, sin desarrollar

Cada una exige aprobación específica (Manual §2) y se traduce a su propia spec cuando se autorice:

- **Comercial y canales** (Manual §3 descubrimiento y captación, §4 comercial y canales): campañas, contactos, mensajes, embudo y atribución de origen; las integraciones con redes y OTA dependen de permisos y API reales (§9).
- **Concierge agéntico por WhatsApp** (spec US-HOT-003, P3): atención, cotización y upsells con link de pago; escritura solo tras autorización; depende de reglas del Manual §9 y de la operación de fase 1.
- **Compras, inventario y activos** (Manual §4): proveedores, órdenes, recepción, existencias, consumos y reposición de activos; precios unitarios son decisión del §9.
- **Personas y permisos ampliados** (Manual §4): usuarios, roles, turnos, tareas, aprobaciones, bitácoras y segregación de funciones; la gestión laboral requiere reglas y tratamiento de datos específicos.
- **Administración multiempresa y consolidación** (Manual §2 y §4): separación de datos y permisos por sociedad y consolidación gerencial con eliminaciones; la estructura societaria vigente es decisión del §9.
- **Inmuebles, arriendos, inversiones, construcción y tableros consolidados** (Manual §2, fases siguientes): cada etapa requiere aprobación específica.
- **Traspaso y migración al 1 de enero de 2027** (Manual §8): inventario de habitaciones y activos, reservas futuras, saldos y anticipos, plan de corte, operación paralela y reversión; es un proyecto de traspazo, no una historia del recorrido del huésped.
- **Indicadores ampliados** (Manual §4): costos, margen, productividad y alertas, cada uno con fórmula, periodo, fuente y responsable.
