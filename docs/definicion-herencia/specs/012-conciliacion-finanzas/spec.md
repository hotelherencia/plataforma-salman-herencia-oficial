# F11 - Conciliación y auxiliares financieros

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Relacionar reservas, cargos, documentos, cobros, liquidaciones y bancos con diferencias visibles.

Actores: tesorería;contador;administración;auditor. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Importar staging -> deduplicar -> aceptar -> proponer correspondencias -> revisar grupos -> clasificar diferencias -> conciliar -> cerrar período -> exportar auxiliar.

## Reglas que no se pueden violar
No fusionar movimientos iguales sin ID/evidencia; montos asignados no superan fuente; comisión separada no descontada doble; reversos preservan original.

## Condiciones y configuración
Cuentas y formatos verificados; mapping contable aprobado para exportar. Decisiones pendientes: D08, D14, D21, D34. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### FIN-001 - Ingreso devengado versus cobro
**Historia F11-US01.** Como tesorería, necesito ingreso devengado versus cobro para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: PAY-001;TAX-001. Regla heredada preservada: Vista de servicio, documento, cobro y banco separadas.

**Entradas y validación:** charge service date, fiscal doc, payment date, bank date. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Reportes separados y conciliables. Servicio de enero cobrado en diciembre aparece como ingreso de servicio enero y cobro diciembre sin sumarse.

**Escenario positivo TC-FIN-001-P:** Dado Alojamiento 140000 con anticipo 70000 refleja ingreso total una vez. Cuando se completa la acción autorizada, entonces se cumple: Mismo servicio no se suma cuatro veces al resultado Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FIN-001-N:** Dado Sumar cargo, factura, cobro y depósito en una sola columna ingresos. Entonces Validador financiero detecta duplicación; reporte no aceptable.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F11-T01A` (pruebas), `F11-T01B` (implementación), `F11-T01C` (verificación). Evidencia prevista `evidence/F11/FIN-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FIN-002 - Cuentas por cobrar y antiguedad
**Historia F11-US02.** Como tesorería, necesito cuentas por cobrar y antiguedad para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: PAY-002. Regla heredada preservada: Saldos por empresa/huesped, vencimiento y aplicaciones.

**Entradas y validación:** folio debtor, due date, allocations, aging date. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Antiguedad por fecha de vencimiento y saldo a fecha de corte; pago posterior no reescribe reporte histórico sin etiqueta restated. Grupo conserva detalle.

**Escenario positivo TC-FIN-002-P:** Dado Pago parcial reduce sólo cuentas seleccionadas y recalcula bandas de vencimiento. Cuando se completa la acción autorizada, entonces se cumple: Pago grupal reduce las cuentas correctas sin saldos ocultos Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FIN-002-N:** Dado Aplicar pago a otra empresa con nombre similar. Entonces Rechazo por ID/pagador/alcance; no saldos ocultos.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F11-T02A` (pruebas), `F11-T02B` (implementación), `F11-T02C` (verificación). Evidencia prevista `evidence/F11/FIN-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FIN-003 - Importación bancaria con vista previa
**Historia F11-US03.** Como tesorería, necesito importación bancaria con vista previa para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: CORE-001. Regla heredada preservada: Cuenta, período, moneda, id/hash y filas rechazadas.

**Entradas y validación:** bank account, file hash, external ID, row preview. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Importar a staging con tipos, fechas, moneda y control de totales. Hash evita archivo repetido; fila ambigua se revisa, no se descarta por monto igual.

**Escenario positivo TC-FIN-003-P:** Dado Misma cartola cargada dos veces no agrega movimientos. Cuando se completa la acción autorizada, entonces se cumple: Reimportar archivo identico no duplica movimientos Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FIN-003-N:** Dado Dos transferencias legitimas de 50000 mismo día tienen IDs diferentes. Entonces Ambas se conservan; deduplicacion no usa sólo monto/fecha.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F11-T03A` (pruebas), `F11-T03B` (implementación), `F11-T03C` (verificación). Evidencia prevista `evidence/F11/FIN-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FIN-004 - Conciliación muchos-a-muchos
**Historia F11-US04.** Como tesorería, necesito conciliación muchos-a-muchos para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: FIN-003;PAY-002. Regla heredada preservada: Asignaciones no superan importes disponibles.

**Entradas y validación:** group, source allocations, side, currency. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Asignaciones many-to-many bloquean saldos de fuentes; total negocio y banco deben cuadrar o tener ajuste aprobado clasificado. Reverso libera asignaciones sin borrar hechos.

**Escenario positivo TC-FIN-004-P:** Dado Abono 135000 concilia tres cobros de 50000 menos comisión total 15000. Cuando se completa la acción autorizada, entonces se cumple: Abono agrupado se aplica a tres cobros y cuadra Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FIN-004-N:** Dado Asignar un abono completo a dos grupos simultaneamente. Entonces 409 OVERALLOCATED; sólo un grupo consume saldo disponible.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F11-T04A` (pruebas), `F11-T04B` (implementación), `F11-T04C` (verificación). Evidencia prevista `evidence/F11/FIN-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FIN-005 - Liquidaciones y comisiones de canales
**Historia F11-US05.** Como tesorería, necesito liquidaciones y comisiones de canales para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Booking H:K; usuario; P0; relación original: FIN-004. Regla heredada preservada: Separar hotel cobra de canal cobra; comisión facturada aparte.

**Entradas y validación:** collection mode, settlement, fee invoice, refund. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Modo hotel cobra y canal cobra son contratos diferentes. Retención de comisión y factura separada no se descuentan ambas sin causa.

**Escenario positivo TC-FIN-005-P:** Dado Canal liquida bruto 200000 menos fee 20000, neto 180000. Cuando se completa la acción autorizada, entonces se cumple: No descontar dos veces comisión ya facturada fuera del abono Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FIN-005-N:** Dado Hotel cobra 200000 directo y sistema reduce además abono por comisión ya pagada aparte. Entonces Diferencia identificada; modelo impide doble fee mediante fuente/documento.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F11-T05A` (pruebas), `F11-T05B` (implementación), `F11-T05C` (verificación). Evidencia prevista `evidence/F11/FIN-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FIN-006 - Bandeja de diferencias
**Historia F11-US06.** Como tesorería, necesito bandeja de diferencias para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: FIN-004. Regla heredada preservada: No conciliar automáticamente sólo por monto.

**Entradas y validación:** unmatched movements, candidate matches, evidence. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Motor propone coincidencias por referencia/importe/fecha y confianza; no aprueba ambiguas. Diferencia tiene responsable, motivo y plazo, nunca se convierte en venta automáticamente.

**Escenario positivo TC-FIN-006-P:** Dado Dos candidatos del mismo importe quedan en cola de revisión. Cuando se completa la acción autorizada, entonces se cumple: Dos transferencias iguales permanecen distinguibles por evidencia Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FIN-006-N:** Dado Conciliar automáticamente sólo por monto coincidente. Entonces No publicar match; exigir referencia o aprobación documentada.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F11-T06A` (pruebas), `F11-T06B` (implementación), `F11-T06C` (verificación). Evidencia prevista `evidence/F11/FIN-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FIN-009 - Operación entre unidades y sociedades
**Historia F11-US07.** Como tesorería, necesito operación entre unidades y sociedades para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; organigrama; P0; relación original: CORE-001. Regla heredada preservada: Distinguir asignación interna de transacción entre RUT.

**Entradas y validación:** source/target company or unit, paired references. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Mismo RUT usa asignación gerencial; distintos RUT exigen documento/contrato aplicable. Consolidado elimina sólo reciprocidades identificadas y autorizadas.

**Escenario positivo TC-FIN-009-P:** Dado Desayuno interno cambia costo de unidad, no costo total del grupo. Cuando se completa la acción autorizada, entonces se cumple: Consolidado elimina sólo duplicaciones definidas con evidencia Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FIN-009-N:** Dado Eliminar factura a tercero por parecer transacción interna sin referencia pareada. Entonces Eliminación bloqueada; saldo y evidencia permanecen.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F11-T07A` (pruebas), `F11-T07B` (implementación), `F11-T07C` (verificación). Evidencia prevista `evidence/F11/FIN-009/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FIN-011 - Frontera e intercambio contable
**Historia F11-US08.** Como tesorería, necesito frontera e intercambio contable para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: FIN-001;TAX-001. Regla heredada preservada: Definir auxiliar versus libro contable; cuentas, períodos, impuestos y exportaciones con control de totales..

**Entradas y validación:** account mapping, period, batch, totals, destination ack. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Auxiliar no se declara libro legal completo. Exportar lote único validado por contabilidad y registrar acuse/rechazo; reenvio preserva ID.

**Escenario positivo TC-FIN-011-P:** Dado Segundo envio del mismo lote se reconoce como reintento. Cuando se completa la acción autorizada, entonces se cumple: Exportar dos veces el mismo período no genera asientos duplicados en destino sin detectar el reenvio. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FIN-011-N:** Dado Destino no soporta idempotencia y usuario reenvia como nuevo. Entonces Bloquear automatismo y requerir verificación manual de importación previa.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F11-T08A` (pruebas), `F11-T08B` (implementación), `F11-T08C` (verificación). Evidencia prevista `evidence/F11/FIN-011/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: bank_account, payable, payable_payment, bank_import, bank_movement, settlement, settlement_line, reconciliation_group, reconciliation_allocation, accounting_export.

Pantallas: UI-32, UI-33, UI-34; especificadas en `ux/pantallas.csv`. Operaciones propias: previewBankImport, commitBankImport, createReconciliation, postReconciliation, exportAccounting, listUnmatched. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: bank.imported, reconciliation.posted, reconciliation.reversed, accounting.exported. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
