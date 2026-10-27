# F07 - Aseo, inspección y lavandería

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Asignar trabajo y registrar textiles/insumos sin duplicar costos ni perder piezas.

Actores: aseo;supervisor;lavandería;recepción. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Salida genera tarea -> asignar -> ejecutar -> registrar insumos/textiles -> inspeccionar -> liberar habitación; enviar textiles -> recibir parcial -> resolver diferencia.

## Reglas que no se pueden violar
No liberar habitación por marcar tarea iniciada; inspección separada; uso de toalla no es baja; reenvio móvil no duplica consumos ni puntos.

## Condiciones y configuración
Checklist y dotacion conocidos; contrato de consumo y tareas implementado. Decisiones pendientes: D09, D11, D13, D14, D17. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### OPS-001 - Tareas por salida y permanencia
**Historia F07-US01.** Como aseo, necesito tareas por salida y permanencia para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: REC-003. Regla heredada preservada: Reglas por tipo de habitación y servicio.

**Entradas y validación:** checkout/service event, room, task type, checklist. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Generar tarea por causa única; permanencia usa política aprobada y solicitudes, no repeticion indiscriminada. Fechas efectivas controlan prioridad.

**Escenario positivo TC-OPS-001-P:** Dado Una salida origina una tarea de aseo con mismo source_key. Cuando se completa la acción autorizada, entonces se cumple: Checkout genera una tarea de salida sin duplicados Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-OPS-001-N:** Dado Recibir dos veces el mismo checkout. Entonces Una tarea, no dos ni doble incentivo.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F07-T01A` (pruebas), `F07-T01B` (implementación), `F07-T01C` (verificación). Evidencia prevista `evidence/F07/OPS-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### OPS-002 - Asignación y ejecución móvil
**Historia F07-US02.** Como aseo, necesito asignación y ejecución móvil para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: OPS-001. Regla heredada preservada: Responsable, tiempos y checklist.

**Entradas y validación:** task, worker, device event, start/end, checklist. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Asignación requiere trabajador habilitado; ejecución móvil registra identidad y versión. Cola offline limitada a datos operativos y resuelve conflictos al volver.

**Escenario positivo TC-OPS-002-P:** Dado Persona asignada completa checklist desde móvil y queda pendiente de inspección. Cuando se completa la acción autorizada, entonces se cumple: Ejecutor registra la tarea desde móvil con su identidad Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-OPS-002-N:** Dado Dispositivo offline envia tarea reasignada a otra persona. Entonces Conflicto visible, no sobrescritura; supervisor concilia ejecución real.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F07-T02A` (pruebas), `F07-T02B` (implementación), `F07-T02C` (verificación). Evidencia prevista `evidence/F07/OPS-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### OPS-003 - Inspección y retrabajo
**Historia F07-US03.** Como aseo, necesito inspección y retrabajo para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: OPS-002. Regla heredada preservada: Supervisor libera habitación y registra faltas.

**Entradas y validación:** inspection, findings, release permission. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Supervisor válida checklist y resultado; falla genera retrabajo vinculado, no nuevo premio por defecto. Liberacion depende también de mantenimiento.

**Escenario positivo TC-OPS-003-P:** Dado Inspección aprobada convierte habitación limpia a READY. Cuando se completa la acción autorizada, entonces se cumple: Falla de inspección no declara habitación lista Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-OPS-003-N:** Dado Checklist incompleto o falla de higiene y solicitud de liberar. Entonces No entrega disponible; hallazgo y retrabajo asignados.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F07-T03A` (pruebas), `F07-T03B` (implementación), `F07-T03C` (verificación). Evidencia prevista `evidence/F07/OPS-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### OPS-004 - Consumos por tarea
**Historia F07-US04.** Como aseo, necesito consumos por tarea para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; inventarios; P0; relación original: OPS-002. Regla heredada preservada: Uso real de amenities; textiles como movimientos.

**Entradas y validación:** task execution, product, quantity, textile change. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Consumible genera stock out; textil cambia estado. Clave source impide doble descuento. Consumo estimado se etiqueta y luego ajusta con evidencia.

**Escenario positivo TC-OPS-004-P:** Dado Dos jabones y dos toallas: baja dos jabones, mueve dos toallas. Cuando se completa la acción autorizada, entonces se cumple: Repetir tarea no descuenta insumos dos veces Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-OPS-004-N:** Dado Reenviar registro de consumo con mismo device event. Entonces Una sola afectacion y resultado previo; stock no disminuye otra vez.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F07-T04A` (pruebas), `F07-T04B` (implementación), `F07-T04C` (verificación). Evidencia prevista `evidence/F07/OPS-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### OPS-005 - Areas comunes
**Historia F07-US05.** Como aseo, necesito areas comunes para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: OPS-001. Regla heredada preservada: Cocina, banios y sala con tareas propias.

**Entradas y validación:** area code, frequency, checklist, cost center. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Cocina, baños y sala tienen tareas y centro comun; distribución posterior usa regla, no habitación arbitraria. La sala puede generar aseo por evento.

**Escenario positivo TC-OPS-005-P:** Dado Limpieza de sala se imputa a areas comunes. Cuando se completa la acción autorizada, entonces se cumple: Limpieza comun no se imputa a una habitación arbitraria Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-OPS-005-N:** Dado Usuario intenta asignar todas las limpiezas comunes a cuarto vacío para mejorar otros margenes. Entonces Exigir destino válido o ajuste gerencial aprobado, auditar.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F07-T05A` (pruebas), `F07-T05B` (implementación), `F07-T05C` (verificación). Evidencia prevista `evidence/F07/OPS-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### LIN-001 - Catálogo textil y estados
**Historia F07-US06.** Como aseo, necesito catálogo textil y estados para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Lavandería B5:B29; P0; relación original: CORE-001. Regla heredada preservada: Tipo, cantidad, ubicacion y estado.

**Entradas y validación:** textile product, location, state, count. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Mantener balance por tipo/estado; piezas enteras y no negativas. Uso, traslado y lavado no son baja definitiva; baja requiere motivo/aprobacion.

**Escenario positivo TC-LIN-001-P:** Dado Toalla pasa limpia-asignada-usada y total patrimonial no cambia. Cuando se completa la acción autorizada, entonces se cumple: Una toalla usada no desaparece del patrimonio textil Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-LIN-001-N:** Dado Restar una pieza del patrimonio cada noche ocupada. Entonces Validación rechaza movimiento de baja sin causa y autorización.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F07-T06A` (pruebas), `F07-T06B` (implementación), `F07-T06C` (verificación). Evidencia prevista `evidence/F07/LIN-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### LIN-002 - Lote enviado y recepción
**Historia F07-US07.** Como aseo, necesito lote enviado y recepción para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Lavandería; P0; relación original: LIN-001. Regla heredada preservada: Piezas enviadas, recibidas, faltantes y rechazadas.

**Entradas y validación:** lot, sent, good, rejected, lost, pending. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Envios/recepciones parciales conservan diferencia; cerrar lote sólo sin pendientes o con ajuste aprobado. Rechazado no se suma a limpio.

**Escenario positivo TC-LIN-002-P:** Dado Enviar dos sábanas, recibir una buena: una pendiente. Cuando se completa la acción autorizada, entonces se cumple: Dos piezas enviadas y una recibida dejan una pendiente Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-LIN-002-N:** Dado Intentar cerrar lote con una faltante sin resolución. Entonces 409 LOT_UNBALANCED; pendiente visible al proveedor.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F07-T07A` (pruebas), `F07-T07B` (implementación), `F07-T07C` (verificación). Evidencia prevista `evidence/F07/LIN-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### LIN-003 - Vinculo habitación y estadía
**Historia F07-US08.** Como aseo, necesito vinculo habitación y estadía para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: LIN-001;OPS-002. Regla heredada preservada: Cambio efectivo y ejecutor; no lavado supuesto por noche.

**Entradas y validación:** stay, room, execution, actual textile quantity. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Sólo el cambio confirmado crea movimiento; habitacion/estadia y ejecutor permiten costo. No usar ocupación como prueba de lavado.

**Escenario positivo TC-LIN-003-P:** Dado Permanencia sin cambio de sábanas no genera envio ficticio. Cuando se completa la acción autorizada, entonces se cumple: Una permanencia sin cambio no crea lavado ficticio Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-LIN-003-N:** Dado Tarea marcada no cambiada genera automáticamente dos sábanas usadas. Entonces Prueba detecta inconsistencia; movimiento bloqueado.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F07-T08A` (pruebas), `F07-T08B` (implementación), `F07-T08C` (verificación). Evidencia prevista `evidence/F07/LIN-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### LIN-004 - Costeo de lote
**Historia F07-US09.** Como aseo, necesito costeo de lote para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P1; relación original: LIN-002. Regla heredada preservada: Regla por piezas/kilos y costo interno/externo.

**Entradas y validación:** lot cost, pieces/weight, allocation method, shared labor. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Distribuir costo real o estimado etiquetado; suma exacta y ajuste residual declarado. Evitar sumar mismo trabajo en lavandería y bolsa salarial.

**Escenario positivo TC-LIN-004-P:** Dado Lote 10000 repartido 6000/4000 mantiene total. Cuando se completa la acción autorizada, entonces se cumple: Distribución del lote suma su costo total sin duplicar personal Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-LIN-004-N:** Dado Repartos suman 11000 o kilogramo se convierte a piezas sin base. Entonces No cerrar costeo; corregir regla o dejar costo no asignado.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F07-T09A` (pruebas), `F07-T09B` (implementación), `F07-T09C` (verificación). Evidencia prevista `evidence/F07/LIN-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: task, task_execution, inspection, textile_movement, laundry_lot, laundry_line.

Pantallas: UI-20, UI-21, UI-22; especificadas en `ux/pantallas.csv`. Operaciones propias: createTask, executeTask, inspectTask, sendLaundry, receiveLaundry, listTasks, listLaundry. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: task.completed, task.accepted, task.rework, laundry.sent, laundry.received, room.ready. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
