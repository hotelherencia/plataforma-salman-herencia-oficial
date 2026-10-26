# F09 - Activos, mantenimiento y renovación

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Distinguir inventario, propiedad, desperfectos, compras, instalación y bloqueos de habitaciones.

Actores: mantenimiento;administración;propietario;compras. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Inspeccionar -> clasificar seguridad/calidad -> reparar o proponer renovación -> cotizar -> aprobar -> comprar -> recibir -> instalar -> inspeccionar -> habilitar -> dar baja anterior.

## Reglas que no se pueden violar
Bien pagado sin instalar no habilita habitación; no imponer deudas al arrendatario; bloqueo revisa reservas afectadas; seguro primero.

## Condiciones y configuración
Catastro y propietario; prioridades y presupuesto aprobados. Decisiones pendientes: D01, D13, D14, D24, D31, D32. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### MNT-001 - Activos y planes preventivos
**Historia F09-US01.** Como mantenimiento, necesito activos y planes preventivos para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: HOT-004. Regla heredada preservada: Equipo, frecuencia, tarea, responsable y costo.

**Entradas y validación:** asset, schedule, due date, responsible. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Calendario genera una orden por activo/periodo; prioridad decide aviso, no bloqueo automático de todas las habitaciones. Garantía se consulta antes de contratar.

**Escenario positivo TC-MNT-001-P:** Dado Vencimiento de revisión genera una tarea del equipo concreto. Cuando se completa la acción autorizada, entonces se cumple: Vencimiento genera tarea sin bloquear habitaciones no afectadas Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-MNT-001-N:** Dado Reejecutar scheduler del mismo día. Entonces No duplica orden; muestra ID existente.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F09-T01A` (pruebas), `F09-T01B` (implementación), `F09-T01C` (verificación). Evidencia prevista `evidence/F09/MNT-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### MNT-002 - Orden correctiva y liberacion
**Historia F09-US02.** Como mantenimiento, necesito orden correctiva y liberacion para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: HOT-004. Regla heredada preservada: Averia, repuestos, proveedor y verificación.

**Entradas y validación:** incident, asset/room, work order, verification. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Orden maneja espera de repuestos y comprobacion final; reserva afectada recibe incidente. Costo/documentos no prueban seguridad de funcionamiento.

**Escenario positivo TC-MNT-002-P:** Dado Reparacion verificada libera cuarto previamente bloqueado. Cuando se completa la acción autorizada, entonces se cumple: Habitación fuera de servicio sólo se libera con cierre autorizado Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-MNT-002-N:** Dado Proveedor factura pero equipo sigue fallando. Entonces Habitación permanece bloqueada y orden en verificacion/incidencia.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F09-T02A` (pruebas), `F09-T02B` (implementación), `F09-T02C` (verificación). Evidencia prevista `evidence/F09/MNT-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### CAP-002 - Ficha de activo y condición
**Historia F09-US03.** Como mantenimiento, necesito ficha de activo y condición para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: MNT-001. Regla heredada preservada: Ubicación, propiedad, identificador, adquisición si consta, estado, defectos, fotos y garantía..

**Entradas y validación:** asset, owner, room, condition, evidence, warranty. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Ficha conserva propiedad y fecha sólo si acreditada. Inspección con fallas observables; historial de ubicacion y cambios.

**Escenario positivo TC-CAP-002-P:** Dado Equipo del arrendatario figura como tercero, no patrimonio propio. Cuando se completa la acción autorizada, entonces se cumple: Un equipo del arrendatario no pasa automáticamente a ser activo del grupo. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CAP-002-N:** Dado Importar inventario y asignar todos los bienes a Herencia automáticamente. Entonces Staging bloquea propiedad desconocida para activación contable.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F09-T03A` (pruebas), `F09-T03B` (implementación), `F09-T03C` (verificación). Evidencia prevista `evidence/F09/CAP-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### CAP-003 - Plan de renovaciones y presupuesto
**Historia F09-US04.** Como mantenimiento, necesito plan de renovaciones y presupuesto para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: CAP-002;CAP-001. Regla heredada preservada: Seguridad, calidad, eficiencia y estética; reparar/reemplazar; justificacion, costo total y fase..

**Entradas y validación:** need, repair/replace, priority, quotes, total budget. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Inversion separada de consumibles; clasificar seguridad/calidad/eficiencia/estetica, justificar comparables y aprobación. No basar renovación sólo en antiguedad.

**Escenario positivo TC-CAP-003-P:** Dado Diez colchones tienen partida, especificación y costo total con instalación. Cuando se completa la acción autorizada, entonces se cumple: Diez colchones tienen presupuesto, propuesta, aprobación y estado separados del stock de jabon. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CAP-003-N:** Dado Necesidad de mejora se interpreta como obligación del arrendatario sin contrato. Entonces Mantener propuesta y asunto discutido separados; no deuda automática.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F09-T04A` (pruebas), `F09-T04B` (implementación), `F09-T04C` (verificación). Evidencia prevista `evidence/F09/CAP-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### CAP-004 - Adquisición e instalación de equipo
**Historia F09-US05.** Como mantenimiento, necesito adquisición e instalación de equipo para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: CAP-003;PUR-002;MNT-002. Regla heredada preservada: Comparar cotizaciones, aprobar, comprar, entregar, instalar, inspeccionar, activar garantía y aceptar..

**Entradas y validación:** order, physical receipt, installation, inspection, warranty. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Compra, entrega, instalación y aceptacion son etapas distintas; activo se habilita después de prueba técnica. Nueva garantía inicia segun contrato verificable.

**Escenario positivo TC-CAP-004-P:** Dado Equipo recibido e instalado pasa inspección antes de READY. Cuando se completa la acción autorizada, entonces se cumple: Equipo pagado pero no instalado no libera una habitación bloqueada. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CAP-004-N:** Dado Equipo pagado aún en transporte libera habitación. Entonces Validación bloquea liberacion y conserva estado ORDERED.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F09-T05A` (pruebas), `F09-T05B` (implementación), `F09-T05C` (verificación). Evidencia prevista `evidence/F09/CAP-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### CAP-005 - Baja, reparacion y trazabilidad contable
**Historia F09-US06.** Como mantenimiento, necesito baja, reparacion y trazabilidad contable para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: CAP-002;FIN-007. Regla heredada preservada: Disposición autorizada, evidencia, responsable, garantía; tratamiento contable aprobado sin doble gasto..

**Entradas y validación:** old/new asset, disposal, approval, accounting mapping. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Baja no borra ficha ni observacion de traspaso; distinguir venta, entrega, reparacion o desecho. Tratamiento de gasto/activo se ratifica antes de exportar.

**Escenario positivo TC-CAP-005-P:** Dado Reemplazo mantiene vinculo y evidencia del activo retirado. Cuando se completa la acción autorizada, entonces se cumple: Reemplazo conserva historial del activo retirado; ajuste no borra faltante de traspaso. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CAP-005-N:** Dado Contabilizar compra dos veces como gasto y activo, o eliminar faltante histórico. Entonces Control contable/trace bloquea lote y requiere corrección autorizada.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F09-T06A` (pruebas), `F09-T06B` (implementación), `F09-T06C` (verificación). Evidencia prevista `evidence/F09/CAP-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### CAP-006 - Renovación y disponibilidad hotelera
**Historia F09-US07.** Como mantenimiento, necesito renovación y disponibilidad hotelera para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: CAP-004;HOT-004. Regla heredada preservada: Planificar intervención, habitaciones afectadas, reservas, plazo y posible costo de indisponibilidad..

**Entradas y validación:** work dates, block, affected reservations, downtime estimate. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Programar bloqueo con capacidad y alternativas; estimar ingreso perdido con supuestos separados de gasto. Avisar antes de obra salvo emergencia de seguridad.

**Escenario positivo TC-CAP-006-P:** Dado Renovación prevista detecta reserva que requiere reasignar. Cuando se completa la acción autorizada, entonces se cumple: Una obra bloquea inventario aprobado y alerta reservas afectadas antes de la intervención. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CAP-006-N:** Dado Intervencion inicia sin bloquear y canal vende la habitación. Entonces Incidente crítico y stop-sell controlado; no aceptar como flujo conforme.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F09-T07A` (pruebas), `F09-T07B` (implementación), `F09-T07C` (verificación). Evidencia prevista `evidence/F09/CAP-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: asset, maintenance_order, asset_inspection, renewal_item.

Pantallas: UI-26, UI-27, UI-28; especificadas en `ux/pantallas.csv`. Operaciones propias: registerAsset, createMaintenance, planRenewal, acceptInstallation, listAssets. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: maintenance.opened, maintenance.closed, renewal.approved, asset.installed. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
