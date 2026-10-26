# F15 - Mensajeria oficial WhatsApp/Instagram/Messenger

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Recibir mensajes autenticos, respetar reglas por canal y enlazar conversaciones con cotizaciones.

Actores: recepción;ventas;soporte. Entrega candidata: E2. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Verificar webhook -> persistir mensaje único -> actualizar ventana -> asignar hilo -> responder permitido -> recibir estado entrega -> derivar -> recuperar errores.

## Reglas que no se pueden violar
No automatizar WhatsApp Web; no enviar a seguidores arbitrariamente; un enviado no necesariamente entregado; toma humana pausa bot; proveedor determina permisos reales.

## Condiciones y configuración
Permisos API y titularidad comprobados; ventanas y plantillas vigentes. Decisiones pendientes: D19, D25, D26, D27, D28. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### SOC-007 - WhatsApp oficial y reglas de envio
**Historia F15-US01.** Como recepción, necesito whatsapp oficial y reglas de envio para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: SOC-001;SOC-006. Regla heredada preservada: Cloud API o proveedor autorizado; ventana, plantilla, finalidad, opt-in y baja según política vigente..

**Entradas y validación:** official channel, opt-in, last inbound, template, purpose. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Validar politica/ventana y plantilla en el instante de envio, no sólo al programar. Baja elimina promociones de cola; comunicación contractual usa via permitida.

**Escenario positivo TC-SOC-007-P:** Dado Respuesta libre dentro de ventana o plantilla válida fuera de ella. Cuando se completa la acción autorizada, entonces se cumple: Un mensaje fuera de ventana sin plantilla permitida se bloquea y queda explicacion; no se reintenta como spam. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-007-N:** Dado Fuera de ventana se intenta enviar texto libre promocional. Entonces BLOCKED con motivo, sin reintentos para evadir restricción.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F15-T01A` (pruebas), `F15-T01B` (implementación), `F15-T01C` (verificación). Evidencia prevista `evidence/F15/SOC-007/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-008 - Instagram y Messenger oficiales
**Historia F15-US02.** Como recepción, necesito instagram y messenger oficiales para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: SOC-001;SOC-006. Regla heredada preservada: Tipo de cuenta, método de login, permisos y restricciones de conversación por API elegida..

**Entradas y validación:** login route, scopes, tokens, subscriptions, account. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Elegir via Instagram/Messenger y documentar sus requisitos sin mezclarlos. Mensajes sólo dentro de capacidades autorizadas; token revocado cancela acceso.

**Escenario positivo TC-SOC-008-P:** Dado Mensaje entrante inicia hilo y respuesta permitida se entrega. Cuando se completa la acción autorizada, entonces se cumple: Una revocacion de acceso suspende sólo el conector afectado y alerta; no simula mensajes enviados. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-008-N:** Dado API rechaza permiso y app afirma mensaje enviado. Entonces Estado FAILED/DEGRADED, alerta y alternativa humana.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F15-T02A` (pruebas), `F15-T02B` (implementación), `F15-T02C` (verificación). Evidencia prevista `evidence/F15/SOC-008/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-011 - Webhooks sociales verificables e idempotentes
**Historia F15-US03.** Como recepción, necesito webhooks sociales verificables e idempotentes para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: SOC-006. Regla heredada preservada: Firma, evento único, respuesta rápida, cola, reintentos, mensajes fuera de orden y bandeja de fallas..

**Entradas y validación:** signature, event ID, account, timestamp, payload hash. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Verificar autenticidad, límite de tamaño y cuenta, persistir inbox y responder rápido; procesar en cola con deduplicacion y orden segun revisión. No loguear cuerpo sensible completo.

**Escenario positivo TC-SOC-011-P:** Dado Diez reenvios del mismo mensaje crean un mensaje y una oportunidad. Cuando se completa la acción autorizada, entonces se cumple: Repetir mensaje diez veces crea un mensaje y una oportunidad; firma inválida no crea nada. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-011-N:** Dado Firma inválida o misma ID con contenido alterado. Entonces 401 o cuarentena de integridad; sin creación de objetos comerciales.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F15-T03A` (pruebas), `F15-T03B` (implementación), `F15-T03C` (verificación). Evidencia prevista `evidence/F15/SOC-011/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: conversation, message.

Pantallas: UI-42; especificadas en `ux/pantallas.csv`. Operaciones propias: sendMessage, ingestVerifiedEvent. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: message.received, message.delivered, conversation.taken_over, message.rejected. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
