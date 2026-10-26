# F20 - Traspaso, migración y apertura

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Cargar saldos y compromisos conciliados, incluyendo fondos del operador saliente y estadías cruzadas.

Actores: operador saliente;administración;contador;propietario. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Levantar -> validar staging -> cotejar fuentes -> simular -> firmar observaciones -> cortar autoridad -> cargar -> reconciliar -> seguir diferencias tardias.

## Reglas que no se pueden violar
No cobrar anticipo dos veces; fondos por rendir separados; no traer datos históricos sin finalidad; corte reversible por compensación no borra pagos reales.

## Condiciones y configuración
Acta y responsables; acceso y saldos conciliados antes de activar. Decisiones pendientes: D05, D13, D14, D15, D16, D19, D22, D24, D31, D36, D44. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### MIG-001 - Catálogo de fuentes y errores
**Historia F20-US01.** Como operador saliente, necesito catálogo de fuentes y errores para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** 15 archivos; P0; relación original: CORE-006. Regla heredada preservada: Hash, hoja, procedencia y transformaciones.

**Entradas y validación:** source hash, sheet/row, schema, transform, rejects. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Conservar original y mapa de transformacion; fechas invalidas a cola. No corregir 31-6 suponiendo otro mes. Datos personales sólo con finalidad.

**Escenario positivo TC-MIG-001-P:** Dado Fuente con encabezado ambiguo queda observada antes de migrar. Cuando se completa la acción autorizada, entonces se cumple: Fuente con fecha 31-6 se marca para revisión, no se inventa fecha Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-MIG-001-N:** Dado Inventar fecha válida para una fila 31-6. Entonces Fila rechazada con motivo y sin escritura productiva.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F20-T01A` (pruebas), `F20-T01B` (implementación), `F20-T01C` (verificación). Evidencia prevista `evidence/F20/MIG-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### MIG-002 - Reservas futuras y anticipos heredados
**Historia F20-US02.** Como operador saliente, necesito reservas futuras y anticipos heredados para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; corte 2027; P0; relación original: PAY-001;FIN-004. Regla heredada preservada: Acta con obligaciones de servicio y fondos.

**Entradas y validación:** future reservations, prior collector, credit, funds due. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Reconocer crédito del huésped documentado sin fabricar banco propio; fondo por rendir es relación de traspaso. Reserva conserva servicio futuro.

**Escenario positivo TC-MIG-002-P:** Dado Reserva enero pagada 100000 al saliente muestra crédito y fondo pendiente. Cuando se completa la acción autorizada, entonces se cumple: Reserva enero cobrada antes queda trazable sin doble venta Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-MIG-002-N:** Dado Cobrar nuevamente 100000 al huésped porque aún no se entrego dinero. Entonces Bloqueo de cobro duplicado; diferencia se gestiona contra saliente segun acta.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F20-T02A` (pruebas), `F20-T02B` (implementación), `F20-T02C` (verificación). Evidencia prevista `evidence/F20/MIG-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### MIG-003 - Inventario y saldos de apertura
**Historia F20-US03.** Como operador saliente, necesito inventario y saldos de apertura para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: INV-004;FIN-003. Regla heredada preservada: Conteo físico y conciliación al corte.

**Entradas y validación:** physical inventory, opening balances, cutoff, approved batch. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Carga staging con totales por moneda, unidad y categoría; publicar sólo con acta y conciliación. Saldo inicial no es compra nueva.

**Escenario positivo TC-MIG-003-P:** Dado Conteo y anticipos aprobados coinciden exactamente con lote cargado. Cuando se completa la acción autorizada, entonces se cumple: Suma de saldos aprobados coincide con importación y excepciones Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-MIG-003-N:** Dado Diferencia de cantidades o saldos no explicada. Entonces No aprobar lote; conservar excepciones y volver a validar.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F20-T03A` (pruebas), `F20-T03B` (implementación), `F20-T03C` (verificación). Evidencia prevista `evidence/F20/MIG-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### MIG-004 - Capacitación y ensayo de operación
**Historia F20-US04.** Como operador saliente, necesito capacitación y ensayo de operación para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: KPI-003;SEC-005. Regla heredada preservada: Ejercicios por rol y fallas simuladas.

**Entradas y validación:** role training, drill, scripts, evidence. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Ensayo por rol incluye errores y recuperación, no sólo demo. Usuario operativo realiza ciclo sin guía constante del desarrollador.

**Escenario positivo TC-MIG-004-P:** Dado Recepción registra llegada, cobro, salida y turno en ejercicio ficticio. Cuando se completa la acción autorizada, entonces se cumple: Recepción completa ciclo sin depender de instrucciones del desarrollador Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-MIG-004-N:** Dado Sólo presentacion de pantallas sin operador realizando tareas. Entonces Capacitación no aceptada; repetir prácticas y registrar resultado.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F20-T04A` (pruebas), `F20-T04B` (implementación), `F20-T04C` (verificación). Evidencia prevista `evidence/F20/MIG-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### MIG-005 - Corte ampliado de obligaciones
**Historia F20-US05.** Como operador saliente, necesito corte ampliado de obligaciones para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: MIG-002;FIN-004. Regla heredada preservada: Acta con fondos, reservas, noche del 31, desayunos, comisiones tardias, proveedores, personal y accesos..

**Entradas y validación:** cutoff, stay split, advances, collector, late settlements. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Acta distingue obligaciones de servicio y fondos; noche31/desayunos/comisiones con regla firmada. Cliente mantiene crédito probado aunque fondos pendientes.

**Escenario positivo TC-MIG-005-P:** Dado Reserva cruzada conserva cuenta y asignación aprobada por período. Cuando se completa la acción autorizada, entonces se cumple: Una reserva cobrada por operador saliente conserva pago histórico y monto por rendir sin cobrar de nuevo al cliente. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-MIG-005-N:** Dado Abono enero por venta diciembre se registra automáticamente como nueva venta enero. Entonces Clasificar en conciliacion/traspaso, no duplicar ingreso.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F20-T05A` (pruebas), `F20-T05B` (implementación), `F20-T05C` (verificación). Evidencia prevista `evidence/F20/MIG-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### MIG-006 - Bienes y pendientes de entrega
**Historia F20-US06.** Como operador saliente, necesito bienes y pendientes de entrega para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: CAP-002;MIG-003. Regla heredada preservada: Propiedad, estado, diferencias contra inventario anterior, obligaciones discutidas y mejoras nuevas..

**Entradas y validación:** asset owner, original inventory, condition, disputed obligation. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Comparar entrega anterior y actual sin concluir responsabilidad jurídica automáticamente. Faltante, mejora nueva y reparacion son categorías distintas.

**Escenario positivo TC-MIG-006-P:** Dado Colchón faltante queda observado con respaldo y responsable propuesto. Cuando se completa la acción autorizada, entonces se cumple: Un faltante queda abierto con responsable sin convertirse automáticamente en compra aprobada. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-MIG-006-N:** Dado Sistema aprueba compra para cerrar artificialmente discrepancia. Entonces Observacion permanece abierta; nueva compra necesita autorización independiente.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F20-T06A` (pruebas), `F20-T06B` (implementación), `F20-T06C` (verificación). Evidencia prevista `evidence/F20/MIG-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: migration_batch, handover_item.

Pantallas: UI-49, UI-50; especificadas en `ux/pantallas.csv`. Operaciones propias: stageMigration, commitMigration, listMigration. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: migration.validated, migration.committed, handover.exception. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
