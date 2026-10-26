# Catálogo de aceptación — Hotel

Escenarios propuestos; ninguno ejecutado sobre producto. Cada ID tiene namespace de feature. Para cada FR se prueba resultado autorizado, denegación, duplicación y recuperación; los datos deben ser autorizados y minimizados.

| Prueba | Requisito | Dado / Cuando / Entonces |
|---|---|---|
| AT-001 | FR-001 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Con fechas/ocupación se ofrece tarifa y política vigentes; habitación en mantenimiento o ocupada no se asigna; impuestos según política ratificada. |
| AT-002 | FR-002 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Consulta y pago web producen una única reserva vinculada al resultado confirmado del proveedor; pago fallido no confirma. |
| AT-003 | FR-003 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Una reserva directa y otra OTA actualizan inventario por el conector autorizado en ambos sentidos; medir desfase y detectar conflicto en vez de ocultarlo. |
| AT-004 | FR-004 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Pago de anticipo y saldo se concilian con documentos aplicables sin segunda emisión por el mismo hecho; SII caído queda pendiente y escala. |
| AT-005 | FR-005 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Intentos concurrentes por la última habitación permiten como máximo una confirmación local; eventos OTA tardíos se detectan y no se aceptan automáticamente sobre cupo. |
| AT-006 | FR-006 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Check-in con documento faltante queda incompleto y se deriva a recepción; acceder al documento exige rol autorizado y registro. |
| AT-007 | FR-007 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Pedido aprobado para habitación crea una comanda y un cargo con referencia/idempotencia; sin cafetería habilitada el servicio se declara no disponible sin bloquear reservas. |
| AT-008 | FR-008 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Check-out crea tarea limpieza; cierre autorizado habilita estado operativo; mantenimiento bloqueado impide asignación aunque termine limpieza. |
| AT-009 | FR-009 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Cuenta acumula cargos/anticipos y liquida saldo; reintentar cargo no duplica, ni se vuelve a documentar importe ya cubierto. |
| AT-010 | FR-010 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Huésped autenticado recibe datos de su reserva; consulta ajena se deniega. Sin permisos de mutación, la petición de cambio queda borrador y escala. |
| AT-011 | FR-011 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Acción fuera de política, monto o vigencia se deniega; modificar parámetros invalida aprobación y no produce cambio en PMS. |
| AT-012 | FR-012 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Oferta de desayuno a huésped elegible genera propuesta y link a flujo controlado, con tarifa comprobada; solo pago confirmado se contabiliza conversión. |
| AT-013 | FR-013 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Cada respuesta con herramienta o acción registra fuente, regla, identidad y resultado sin documento completo del huésped en logs. |
| AT-014 | FR-014 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Consulta externa MCP solo obtiene proyección pública vigente sin datos de huésped ni escritura; intento de modificar reserva se deniega. |
| AT-015 | FR-015 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Flujo hotelero usa core para identidad/pagos/documentos/auditoría y posee reserva/cuenta; probar sin catálogo ni gasto universal del core. |
| ADV-001 | NFR-001/002/003 | Cien intentos sobre la última habitación producen como máximo una confirmación local; el conflicto OTA se detecta y escala. |
| ADV-002 | NFR-001/002/003 | Desconectar canal y simular inventario obsoleto: detener confirmación automática sin asignación segura. |
| ADV-003 | NFR-001/002/003 | Anticipo y pago final mantienen trazabilidad fiscal sin emitir dos documentos por el mismo hecho. |

## Criterios de éxito y evidencia

| Criterio | Verificación pendiente |
|---|---|
| SC-001 | Medir «Cero sobreventas en 90 días de operación con al menos dos canales activos». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-002 | Medir «La disponibilidad se refleja en todos los canales en menos de 5 minutos en el 95 % de los cambios». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-003 | Medir «Las reservas directas pasan del nivel actual a al menos 30 % del total en 6 meses». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-004 | Medir «El 100 % de los pagos queda conciliado con su obligación documental aplicable; objetivo de entrega <60 s cuando proceda y haya disponibilidad externa, sujeto a ratificación; fallos quedan pendientes y alertados». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-005 | Medir «El 60 % de los huéspedes completa check-in online antes de llegar». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-006 | Medir «El agente resuelve al menos el 70 % de conversaciones de WhatsApp sin intervención humana». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-007 | Medir «Cero acciones del agente fuera de sus reglas de autonomía (auditoría mensual del ledger)». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-008 | Medir «Los upsells ofrecidos por el agente convierten al menos el 8 % (referencia Duve)». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-009 | Medir «Un empleado nuevo opera recepción con el sistema tras 2 horas de capacitación». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |

## Escenarios competitivos por historia

Propuestos; no ejecutados sobre producto. Los números de ejemplo prueban aritmética y control, no fijan política comercial.

### US-HOT-001 / H1

- AC-US-HOT-001-01: Dada última unidad y cien intentos, cuando se confirma, entonces como máximo una reserva local obtiene cupo; conflictos externos se identifican y escalan.
- AC-US-HOT-001-02: Dada habitación sucia hoy pero vendible en fecha futura, cuando se busca esa fecha, entonces limpieza actual no elimina inventario futuro por sí sola.

### US-HOT-002 / H2

- AC-US-HOT-002-01: Dada habitación limpia con mantenimiento abierto, cuando se intenta check-in, entonces se bloquea y se ofrece gestión humana de asignación.
- AC-US-HOT-002-02: Dado checkout completado, cuando housekeeping termina, entonces solo cambia preparación; reservas de otras fechas permanecen intactas.

### US-HOT-003 / H3

- AC-US-HOT-003-01: Dada solicitud de cancelación, cuando se deriva, entonces recepción recibe resumen mínimo y referencia; el agente no cancela ni marca resuelto.
- AC-US-HOT-003-02: Dado estado en atención humana, cuando llega mensaje adicional, entonces no dispara una modificación autónoma ni dos respuestas de compromiso.

| Prueba | Requisito | Escenario de resultado |
|---|---|---|
| AT-016 | FR-016 | Dada habitación sucia hoy y reserva de fecha futura, cuando se calcula inventario futuro, entonces no desaparece solo por suciedad actual; check-in presente con mantenimiento se deniega aunque esté limpia. Denegar recurso de otro tenant y conservar evidencia. |
| AT-017 | FR-017 | Dada oferta cuyo canal no acredita vigencia dentro de política aprobada, cuando se intenta confirmar, entonces queda pendiente sin prometer cupo; transferencia humana registra receptor y estado, sin marcar resuelto por enviarla. Denegar recurso de otro tenant y conservar evidencia. |

NFR-006 se verifica por los mismos AC: fuente sin vigencia, extracción ambigua o transición sin evidencia no permite compromiso; la ruta manual mantiene las validaciones.

## Aceptación de profundización funcional

Casos adicionales propuestos; ninguna prueba de producto fue ejecutada.

### RF-HOT-01 / US-HOT-001

- AC-US-HOT-001-03: Dada reserva pagada y política de ejemplo que permite devolución, cuando recepción cancela, entonces la reserva puede quedar cancelada pero el dinero permanece sin devolver hasta operación financiera autorizada y confirmada.
- AC-US-HOT-001-04: Dada nueva tarifa superior a la aceptada, cuando se previsualiza el cambio, entonces muestra diferencia y no la aplica sin nueva aceptación.
- AC-US-HOT-001-05: Dado timeout tras aplicar un cambio, cuando se reintenta, entonces consulta estado y no crea segunda reserva, cargo ni devolución.

### RF-HOT-02 / US-HOT-002

- AC-US-HOT-002-03: Dada configuración de ejemplo de desayuno por persona/noche para dos personas y tres noches y una botella por estadía, cuando se calcula, entonces desayuno tiene seis unidades y botella una, con reglas visibles.
- AC-US-HOT-002-04: Dado cargo registrado pero tarea sin entregar, cuando se consulta la cuenta, entonces distingue cobro/cargo de cumplimiento y no informa servicio entregado.
- AC-US-HOT-002-05: Dado mismo pedido/cargo reintentado, cuando el conector responde dos veces, entonces hay un cargo y una tarea vinculados, sin segunda comanda.

### RF-HOT-03 / US-HOT-001

- AC-US-HOT-001-06: Dada falla de almacenamiento antes de recepción durable, cuando llega reserva del canal, entonces no se declara acuse exitoso ni confirmación local.
- AC-US-HOT-001-07: Dada recepción durable y acuse completado pero caída antes de aplicar, cuando se recupera, entonces se reaplica desde evidencia sin perder reserva ni duplicar efectos.
- AC-US-HOT-001-08: Dados cinco eventos con igual ID notificación y una actualización nueva del mismo ID de reserva, cuando se reconcilian, entonces se deduplica notificación pero no se descarta el cambio legítimo por usar solo ID reserva.

### RF-HOT-04 / US-HOT-003

- AC-US-HOT-003-03: Dada conversación en la que el huésped pide cancelar y devolver, cuando responde concierge, entonces prepara contexto y escala; no ejecuta ninguna de las dos operaciones.
- AC-US-HOT-003-04: Dada misma modificación notificada tres veces, cuando evalúa comunicaciones, entonces no envía tres confirmaciones ni tres upsells por el mismo hecho.
- AC-US-HOT-003-05: Dada respuesta correcta con link a un motor, cuando se contabiliza éxito, entonces no figura como reserva pagada hasta evidencia de negocio independiente.

| Prueba | Requisito | Escenario propuesto |
|---|---|---|
| AT-018 | FR-018 | Dada reserva pagada y política de ejemplo que permite devolución, cuando recepción cancela, entonces la reserva puede quedar cancelada pero el dinero permanece sin devolver hasta operación financiera autorizada y confirmada. Probar también permiso insuficiente y referencia de otro tenant. |
| AT-019 | FR-019 | Dada configuración de ejemplo de desayuno por persona/noche para dos personas y tres noches y una botella por estadía, cuando se calcula, entonces desayuno tiene seis unidades y botella una, con reglas visibles. Probar también permiso insuficiente y referencia de otro tenant. |
| AT-020 | FR-020 | Dada falla de almacenamiento antes de recepción durable, cuando llega reserva del canal, entonces no se declara acuse exitoso ni confirmación local. Probar también permiso insuficiente y referencia de otro tenant. |
