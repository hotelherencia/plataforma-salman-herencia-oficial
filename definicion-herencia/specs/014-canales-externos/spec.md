# F13 - Booking y distribución externa

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Sincronizar capacidades verificadas por proveedor autorizado y controlar fallas de canal.

Actores: recepción;administración;soporte integraciones. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Registrar capacidad -> probar mapping -> recibir evento firmado -> deduplicar -> aplicar revisión -> confirmar recepción -> publicar inventario -> reconciliar -> alertar falla.

## Reglas que no se pueden violar
No usar API de afiliados para PMS; mensaje antiguo no revierte cancelación; sincronización externa tiene latencia; acceso documentado no es permiso real.

## Condiciones y configuración
Proveedor autorizado, contrato, cuentas, mapeos y entorno verificables. Decisiones pendientes: D04, D06, D19, D25. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### INT-001 - Proveedor Booking autorizado
**Historia F13-US01.** Como recepción, necesito proveedor booking autorizado para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** S11-S12; P0; relación original: RES-009. Regla heredada preservada: Contrato, cuenta, sandbox y evidencia antes de producción.

**Entradas y validación:** provider contract, property mapping, credentials, capabilities. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Adoptar proveedor habilitado y probar por capacidad; contrato local no presume endpoint externo. En producción probar operación autorizada con evidencia.

**Escenario positivo TC-INT-001-P:** Dado Crear/modificar/cancelar reserva de prueba autorizada verifica cada capacidad. Cuando se completa la acción autorizada, entonces se cumple: Se crea, modifica y cancela reserva real de prueba autorizada Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INT-001-N:** Dado Sólo existe documentación pública sin cuenta ni permisos. Entonces Estado DOCUMENTED/BLOCKED; no marcar integrado ni activar inventario comun.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F13-T01A` (pruebas), `F13-T01B` (implementación), `F13-T01C` (verificación). Evidencia prevista `evidence/F13/INT-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### INT-002 - Mensajes repetidos y fuera de orden
**Historia F13-US02.** Como recepción, necesito mensajes repetidos y fuera de orden para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta técnica; P0; relación original: INT-001. Regla heredada preservada: Idempotencia, versión y trazas de eventos.

**Entradas y validación:** external_event_id, reservation revisión, payload hash. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Persistir inbox antes de procesar; versión obsoleta no retrocede estado. Sin versión fiable consultar fuente y revisar conflicto.

**Escenario positivo TC-INT-002-P:** Dado Cancelación revisión 3 permanece frente a confirmacion revisión 2. Cuando se completa la acción autorizada, entonces se cumple: Cancelación no se revierte por una confirmacion antigua Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INT-002-N:** Dado Evento mismo ID con contenido diferente. Entonces Incidencia de integridad y cuarentena; no sobrescritura silenciosa.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F13-T02A` (pruebas), `F13-T02B` (implementación), `F13-T02C` (verificación). Evidencia prevista `evidence/F13/INT-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### INT-003 - Alertas y contingencia de canales
**Historia F13-US03.** Como recepción, necesito alertas y contingencia de canales para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** S11-S12; P0; relación original: INT-001. Regla heredada preservada: Estado de sincronización y responsable de inventario.

**Entradas y validación:** last success, queue age, authority, stop-sell policy. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Mostrar demora y falla por capacidad; activar contingencia aprobada y reconciliar al volver. No confirmar sincronización por envio sin acuse.

**Escenario positivo TC-INT-003-P:** Dado Caida suspende ventas o aplica cupos segregados autorizados. Cuando se completa la acción autorizada, entonces se cumple: Caida no figura como sincronizado ni vende cupos sin control Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INT-003-N:** Dado Conector falla pero interfaz sigue mostrando sincronizado/verde. Entonces Prueba falla; estado DEGRADED y alerta a responsable.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F13-T03A` (pruebas), `F13-T03B` (implementación), `F13-T03C` (verificación). Evidencia prevista `evidence/F13/INT-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-019 - Google y otros canales opcionales
**Historia F13-US04.** Como recepción, necesito google y otros canales opcionales para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P2; relación original: INT-001;RES-001. Regla heredada preservada: Distinguir enlace web/perfil de alimentación de precios a Google Hotels y otras APIs..

**Entradas y validación:** profile links, metasearch provider, rates feed capability. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Enlace público es distinto de feed de precios. Activar Google Hotels u otro canal sólo con proveedor/permiso y mapeo probados.

**Escenario positivo TC-SOC-019-P:** Dado Perfil enlaza web aún sin feed tarifario habilitado. Cuando se completa la acción autorizada, entonces se cumple: Sin proveedor habilitado no se anuncia tarifa sincronizada; enlace normal sigue operativo. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-019-N:** Dado Anunciar sincronización de tarifas sin contrato/feed funcional. Entonces Capacidad UNAVAILABLE/BLOCKED, no logo de integrado falso.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F13-T04A` (pruebas), `F13-T04B` (implementación), `F13-T04C` (verificación). Evidencia prevista `evidence/F13/SOC-019/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### INT-007 - Panel de salud de integraciones
**Historia F13-US05.** Como recepción, necesito panel de salud de integraciones para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: INT-003;GOV-002. Regla heredada preservada: Última sincronización, permisos, colas, alertas, versiones, reintentos y responsable..

**Entradas y validación:** last success, permissions expiry, queue lag, responsible. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Salud por capacidad y cuenta con umbrales y runbook; estado basado en evidencia, no sólo proceso encendido. Recuperación verifica backlog y reconciliacion.

**Escenario positivo TC-INT-007-P:** Dado Token vence: alerta y DEGRADED del conector afectado. Cuando se completa la acción autorizada, entonces se cumple: Token vencido genera alerta y estado degradado; no se muestra conectado en verde. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INT-007-N:** Dado Conector sigue verde porque servidor HTTP responde. Entonces Prueba falla; separar liveness de sincronización funcional.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F13-T05A` (pruebas), `F13-T05B` (implementación), `F13-T05C` (verificación). Evidencia prevista `evidence/F13/INT-007/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: integration_account, channel_mapping, inbox_event.

Pantallas: UI-38, UI-39; especificadas en `ux/pantallas.csv`. Operaciones propias: registerIntegration, reconcileChannel, integrationHealth. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: channel.event_applied, channel.conflict, integration.degraded, inventory.sync_requested. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
