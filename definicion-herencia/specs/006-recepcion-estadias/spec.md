# F05 - Recepción, estadías y auditoría nocturna

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Registrar pasajeros, cambios, servicios, salida y pendientes con una fecha de negocio controlada.

Actores: recepción;auditor nocturno;administración. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Ver llegadas -> comprobar identidad mínima -> asignar habitación lista -> checkin -> registrar servicios -> mover/extender -> auditar noche -> checkout -> limpiar y cerrar pendientes.

## Reglas que no se pueden violar
Estadía, habitación, limpieza y cuenta son estados distintos; un cambio no duplica noches; salida con deuda necesita crédito aprobado; cargos nocturnos únicos.

## Condiciones y configuración
Reserva confirmada o ingreso directo validado; habitación lista; reglas de deuda. Decisiones pendientes: D01, D03, D09, D14, D36. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### REC-001 - Pasajeros efectivos y check-in
**Historia F05-US01.** Como recepción, necesito pasajeros efectivos y check-in para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: RES-007. Regla heredada preservada: Registro mínimo necesario y fechas reales.

**Entradas y validación:** reservation line, guest identity, arrived_at, room. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Registrar personas realmente presentes y datos mínimos segun finalidad; llegada parcial conserva ocupación reservada restante. Verificar habitación lista y pago/credito permitido.

**Escenario positivo TC-REC-001-P:** Dado Reserva de dos personas: llega una hoy, la segunda queda esperada. Cuando se completa la acción autorizada, entonces se cumple: Reserva de dos pasajeros admite llegada parcial sin inventar el segundo Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-REC-001-N:** Dado Intentar ingresar a habitación sucia o fuera de servicio sin excepción permitida. Entonces 409 ROOM_NOT_READY; alternativa y escalamiento, sin check-in falso.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F05-T01A` (pruebas), `F05-T01B` (implementación), `F05-T01C` (verificación). Evidencia prevista `evidence/F05/REC-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### REC-002 - Cambio de habitación
**Historia F05-US02.** Como recepción, necesito cambio de habitación para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: REC-001. Regla heredada preservada: Segmentos de ocupación dentro de misma estadía.

**Entradas y validación:** stay_id, current/new room, time, reason. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Cerrar segmento anterior y abrir nuevo en una transacción; conservar cuenta; generar aseo saliente. Cruce de tipo revalida inventario y diferencia autorizada.

**Escenario positivo TC-REC-002-P:** Dado Cambiar 101 por 102 mantiene una estadía y una cuenta. Cuando se completa la acción autorizada, entonces se cumple: Cambio conserva cuenta y genera aseo en habitación liberada Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-REC-002-N:** Dado Destino ocupado durante parte del intervalo solicitado. Entonces 409 y segmento original permanece activo; no movimiento a medias.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F05-T02A` (pruebas), `F05-T02B` (implementación), `F05-T02C` (verificación). Evidencia prevista `evidence/F05/REC-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### REC-003 - Check-out con deuda autorizada
**Historia F05-US03.** Como recepción, necesito check-out con deuda autorizada para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: REC-001. Regla heredada preservada: Salida física no equivale a pago total.

**Entradas y validación:** actual checkout, folio balance, corporate approval. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Salida física no exige falsificar pago; deuda sólo queda autorizada con pagador, plazo y permiso. Habitación genera limpieza sin cerrar receivable.

**Escenario positivo TC-REC-003-P:** Dado Empresa con crédito aprobado sale con 80000 pendientes. Cuando se completa la acción autorizada, entonces se cumple: Cuenta empresarial pendiente permanece por cobrar tras salida Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-REC-003-N:** Dado Particular con deuda intenta salida administrativa sin autorización requerida. Entonces Alerta a administrador; registrar realidad de salida sin marcar saldo pagado ni borrar deuda.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F05-T03A` (pruebas), `F05-T03B` (implementación), `F05-T03C` (verificación). Evidencia prevista `evidence/F05/REC-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### REC-004 - Bitacora e incidencias
**Historia F05-US04.** Como recepción, necesito bitacora e incidencias para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta operativa; P0; relación original: CORE-003. Regla heredada preservada: Turno, responsable, prioridad y cierre.

**Entradas y validación:** shift log, incident, owner, priority, due_at. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Pendientes se entregan con responsable y acuse; no borrar el historial al cambiar turno. Alertas vencidas escalan al rol definido.

**Escenario positivo TC-REC-004-P:** Dado Turno nocturno recibe llegada tardia y reclamo sin resolver. Cuando se completa la acción autorizada, entonces se cumple: Incidencia pendiente pasa al siguiente turno con evidencia Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-REC-004-N:** Dado Cerrar turno dejando incidente crítico sin receptor o responsable de escalamiento. Entonces Cierre exige responsable alterno y conserva pendiente visible.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F05-T04A` (pruebas), `F05-T04B` (implementación), `F05-T04C` (verificación). Evidencia prevista `evidence/F05/REC-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### REC-005 - Llaves y objetos olvidados
**Historia F05-US05.** Como recepción, necesito llaves y objetos olvidados para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta operativa; P1; relación original: REC-004. Regla heredada preservada: Custodia y entrega documentada.

**Entradas y validación:** key/item, custody location, recipient evidence. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Registrar emision/devolucion de llaves y objetos, con acceso mínimo y trazabilidad. Entrega de objeto exige comprobar receptor, no publicar inventario personal.

**Escenario positivo TC-REC-005-P:** Dado Objeto olvidado pasa a custodia y se entrega con respaldo al titular. Cuando se completa la acción autorizada, entonces se cumple: Entrega registra receptor y responsable sin mostrarla publicamente Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-REC-005-N:** Dado Persona que conoce número de habitación solicita objeto sin verificación. Entonces Entrega bloqueada; caso reservado para responsable, sin revelar contenido.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F05-T05A` (pruebas), `F05-T05B` (implementación), `F05-T05C` (verificación). Evidencia prevista `evidence/F05/REC-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### OPS-006 - Auditoría nocturna y fecha de negocio
**Historia F05-US06.** Como recepción, necesito auditoría nocturna y fecha de negocio para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: CORE-005;PAY-008. Regla heredada preservada: Noches, llegadas tardias, pendientes, cargos y cierre operacional separado del cierre bancario..

**Entradas y validación:** business_date, nightly charges, late arrivals, close evidence. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Fecha de negocio configurable separada de UTC/calendario; cargos únicos por noche/concepto. Auditoría revisa pendientes sin cerrar estadías activas.

**Escenario positivo TC-OPS-006-P:** Dado Repetir cierre nocturno genera mismos cargos, no duplicados. Cuando se completa la acción autorizada, entonces se cumple: Cruce de medianoche y horario de verano no duplica cargos ni fuerza cerrar una estadía activa. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-OPS-006-N:** Dado Cambio horario de verano provoca repetir hora del scheduler. Entonces Clave de noche/servicio evita duplicado; ejecución registrada una vez.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F05-T06A` (pruebas), `F05-T06B` (implementación), `F05-T06C` (verificación). Evidencia prevista `evidence/F05/OPS-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: guest, stay, stay_guest, room_assignment, service_night, shift_log, custody_item, night_audit.

Pantallas: UI-14, UI-15, UI-16; especificadas en `ux/pantallas.csv`. Operaciones propias: checkin, moveRoom, checkout, runNightAudit, listStays. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: stay.checked_in, stay.room_changed, stay.checked_out, night.closed. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
