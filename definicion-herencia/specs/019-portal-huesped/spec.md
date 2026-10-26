# F18 - Portal, solicitudes y experiencia del huésped

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Permitir autoservicio seguro y seguimiento de solicitudes con acceso limitado a cada estadía.

Actores: huésped;recepción;servicios. Entrega candidata: E2. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Enviar enlace -> validar token -> mostrar cuenta propia -> preregistrar mínimo -> solicitar -> asignar responsable -> resolver -> evaluar satisfacción.

## Reglas que no se pueden violar
Conocer numero/apellido no habilita; portal no aprueba reembolsos; no condicionar servicio a reseñas; no exponer datos de otros pasajeros.

## Condiciones y configuración
Token seguro y acciones autorizadas; identidad adicional para cambios sensibles. Decisiones pendientes: D16, D23, D28, D33. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### GEX-001 - Portal seguro del huésped
**Historia F18-US01.** Como huésped, necesito portal seguro del huésped para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: REC-001;SEC-001. Regla heredada preservada: Acceso acotado; pre-registro, saldo, servicios, solicitudes y documentos autorizados..

**Entradas y validación:** portal grant, identity verification, scopes, expiry. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Token opaco limitado y revocable; para datos/documentos sensibles exigir verificación adicional acordada. Mostrar sólo titular/reserva autorizada.

**Escenario positivo TC-GEX-001-P:** Dado Huésped consulta su cuenta y solicitud sin instalar app. Cuando se completa la acción autorizada, entonces se cumple: Conocer apellido y habitación no permite acceder; token revocado deja de funcionar. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-GEX-001-N:** Dado Conocer apellido/habitacion o token de otro huésped. Entonces 403 y sin revelacion de cuenta; registrar intento seguro.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F18-T01A` (pruebas), `F18-T01B` (implementación), `F18-T01C` (verificación). Evidencia prevista `evidence/F18/GEX-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### GEX-002 - Solicitudes, reclamos y resolución
**Historia F18-US02.** Como huésped, necesito solicitudes, reclamos y resolución para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: REC-004;MNT-002. Regla heredada preservada: Ticket con prioridad, responsable, plazo, evidencia y respuesta; privacidad mínima..

**Entradas y validación:** ticket, category, priority, owner, due, resolution. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Solicitud se convierte en tarea/orden vinculada; comunicación al huésped sin mostrar datos internos. Cierre requiere evidencia o respuesta, con reapertura posible.

**Escenario positivo TC-GEX-002-P:** Dado Reclamo de ducha crea mantenimiento y seguimiento. Cuando se completa la acción autorizada, entonces se cumple: Reclamo de ducha genera tarea de mantenimiento vinculada sin revelar datos a marketing. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-GEX-002-N:** Dado Marketing intenta acceder al relato sensible o ticket se cierra sin resolver. Entonces Acceso denegado; cierre requiere criterio y conserva pendiente.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F18-T02A` (pruebas), `F18-T02B` (implementación), `F18-T02C` (verificación). Evidencia prevista `evidence/F18/GEX-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### GEX-003 - Fidelizacion y reputacion responsables
**Historia F18-US03.** Como huésped, necesito fidelizacion y reputacion responsables para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P2; relación original: SOC-013. Regla heredada preservada: Beneficios autorizados, condiciones, historial, encuestas y respuestas aprobadas; no inventar reseñas..

**Entradas y validación:** loyalty policy, benefit, consent, survey, review approval. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Beneficios versionados y autorizados; no condicionar atención a reseña positiva ni fabricar opiniones. Baja comercial persiste incluso con fidelidad activa.

**Escenario positivo TC-GEX-003-P:** Dado Cliente con beneficio aprobado lo usa sin resuscribirse a marketing. Cuando se completa la acción autorizada, entonces se cumple: Baja de promociones persiste en programas de fidelidad y no altera derechos de la reserva. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-GEX-003-N:** Dado Agente pública reseña inventada o descuento no autorizado. Entonces Bloqueo y alerta; contenido queda borrador/rechazado.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F18-T03A` (pruebas), `F18-T03B` (implementación), `F18-T03C` (verificación). Evidencia prevista `evidence/F18/GEX-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: portal_grant, service_ticket.

Pantallas: UI-46, UI-47; especificadas en `ux/pantallas.csv`. Operaciones propias: readPortal, guestServiceRequest. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: guest.requested_service, ticket.resolved, portal.revoked. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
