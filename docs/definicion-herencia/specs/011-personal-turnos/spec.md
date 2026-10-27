# F10 - Personal, turnos e incentivos

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Planificar cobertura y registrar trabajo/calidad con reglas aprobadas, sin decisiones laborales libres de IA.

Actores: administración;personal;contador;supervisor. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Publicar turno -> validar descansos/cobertura -> registrar asistencia -> resolver ausencia -> revisar tareas aceptadas -> calcular incentivo -> aprobar -> exportar -> registrar pago.

## Reglas que no se pueden violar
Tiempo de tarea no equivale a asistencia ni horas extras; no sancionar automático; cambios de fórmula no alteran períodos aprobados; datos salariales restringidos.

## Condiciones y configuración
Régimen laboral, contratos y regla de incentivos aprobados. Decisiones pendientes: D09, D14, D17, D21. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### HR-001 - Dotacion y contratos vigentes
**Historia F10-US01.** Como administración, necesito dotacion y contratos vigentes para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Sueldos históricos; usuario; P0; relación original: CORE-003. Regla heredada preservada: Contrato de referencia y funcion; no importar dotacion como actual.

**Entradas y validación:** worker, employer, contract, role, validity. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Crear activos sólo desde nómina vigente validada; históricos se almacenan segregados sin permisos. Contrato referencia documento protegido.

**Escenario positivo TC-HR-001-P:** Dado Nómina actual autorizada crea trabajadores; planilla 2019 sólo antecedente. Cuando se completa la acción autorizada, entonces se cumple: Los seis cargos históricos no crean empleados activos automáticos Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-HR-001-N:** Dado Importar seis recepcionistas históricos como activos por defecto. Entonces Staging exige validación y no crea cuentas operativas.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F10-T01A` (pruebas), `F10-T01B` (implementación), `F10-T01C` (verificación). Evidencia prevista `evidence/F10/HR-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### HR-002 - Planificador de turnos
**Historia F10-US02.** Como administración, necesito planificador de turnos para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; S16; P0; relación original: HR-001. Regla heredada preservada: Cobertura 24/7, descansos, ausencias y reemplazos.

**Entradas y validación:** position coverage, shifts, absences, labor policy. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Cobertura por intervalos, colaciones y reemplazos; validar régimen laboral aprobado, no simple suma semanal. Alertar huecos y solapes por persona.

**Escenario positivo TC-HR-002-P:** Dado Ausencia nocturna muestra franja descubierta y permite reemplazo habilitado. Cuando se completa la acción autorizada, entonces se cumple: Franja descubierta o turno incompatible aparece como alerta Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-HR-002-N:** Dado Asignar mismo trabajador en dos puestos solapados. Entonces 409 SHIFT_CONFLICT; cobertura no se presenta completa.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F10-T02A` (pruebas), `F10-T02B` (implementación), `F10-T02C` (verificación). Evidencia prevista `evidence/F10/HR-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### HR-003 - Asistencia y aprobación de horas
**Historia F10-US03.** Como administración, necesito asistencia y aprobación de horas para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: HR-002. Regla heredada preservada: Real versus programado y corrección aprobada.

**Entradas y validación:** scheduled, clocked, corrections, approval. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Asistencia y tareas separadas; horas extras requieren politica/autorizacion. Toda corrección conserva dato original y motivo.

**Escenario positivo TC-HR-003-P:** Dado Tiempo real difiere de plan y supervisor revisa antes de exportar. Cuando se completa la acción autorizada, entonces se cumple: Horas de tarea no se convierten automáticamente en horas extra pagables Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-HR-003-N:** Dado Convertir automáticamente minutos de aseo en horas extra pagadas. Entonces No generar concepto pagable; queda propuesta pendiente de revisión.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F10-T03A` (pruebas), `F10-T03B` (implementación), `F10-T03C` (verificación). Evidencia prevista `evidence/F10/HR-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### HR-004 - Registro de carga y calidad
**Historia F10-US04.** Como administración, necesito registro de carga y calidad para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: OPS-003;HR-001. Regla heredada preservada: Tareas ponderadas y verificadas por persona.

**Entradas y validación:** accepted task, weight, shared participation, quality. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Sólo trabajo real elegible se atribuye; participaciones suman uno. Retrabajo de error no crea premio duplicado y calidad sigue visible.

**Escenario positivo TC-HR-004-P:** Dado Tarea compartida 60/40 reparte puntos sin multiplicarlos. Cuando se completa la acción autorizada, entonces se cumple: Retrabajo no genera automáticamente un segundo incentivo Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-HR-004-N:** Dado Dos personas se asignan cada una el 100% de la misma tarea. Entonces Validación rechaza suma mayor que uno antes de preliquidar.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F10-T04A` (pruebas), `F10-T04B` (implementación), `F10-T04C` (verificación). Evidencia prevista `evidence/F10/HR-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### HR-005 - Regla de incentivos versionada
**Historia F10-US05.** Como administración, necesito regla de incentivos versionada para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P1; relación original: HR-004. Regla heredada preservada: Topes, períodos, calidad y aprobación.

**Entradas y validación:** rule versión, points, value, cap, period. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Congelar regla aprobada por período; proponer monto con topes y posibilidad de revisión humana. No sancionar autonomamente por datos de productividad.

**Escenario positivo TC-HR-005-P:** Dado Regla nueva aplica al siguiente período sin alterar premio aprobado anterior. Cuando se completa la acción autorizada, entonces se cumple: Cambio de regla no altera incentivos ya aprobados Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-HR-005-N:** Dado Cambiar peso de tareas después de aprobar liquidación previa. Entonces Nueva versión no reescribe anterior; corrección excepcional con evidencia.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F10-T05A` (pruebas), `F10-T05B` (implementación), `F10-T05C` (verificación). Evidencia prevista `evidence/F10/HR-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### HR-006 - Preliquidación y exportación
**Historia F10-US06.** Como administración, necesito preliquidación y exportación para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; sueldos; P0; relación original: HR-003. Regla heredada preservada: Datos aprobados a proceso remuneracional validado.

**Entradas y validación:** approved awards, payroll period, export batch, ack. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Exportar sólo conceptos aprobados con trabajador/periodo/id único y totales; no calcular tasas legales históricas ni transferir por el modelo.

**Escenario positivo TC-HR-006-P:** Dado Exportación validada de incentivos recibe acuse y queda EXPORTED. Cuando se completa la acción autorizada, entonces se cumple: No usa tasas de 2019 ni ejecuta pago por orden del modelo Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-HR-006-N:** Dado Reenviar mismo lote como conceptos nuevos o usar tasas de 2019. Entonces Detectar reenvio y bloquear regla sin validación vigente.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F10-T06A` (pruebas), `F10-T06B` (implementación), `F10-T06C` (verificación). Evidencia prevista `evidence/F10/HR-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: worker, shift, attendance, incentive_rule, incentive_award.

Pantallas: UI-29, UI-30, UI-31; especificadas en `ux/pantallas.csv`. Operaciones propias: scheduleShift, recordAttendance, calculateIncentive, listShifts. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: shift.published, attendance.recorded, incentive.proposed, incentive.approved. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
