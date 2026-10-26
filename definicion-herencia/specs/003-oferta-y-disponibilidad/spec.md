# F02 - Habitaciones, tarifas e inventario vendible

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Consultar disponibilidad y precio con configuración de camas, fechas, bloqueos y políticas vigentes.

Actores: administración;recepción;marketing autorizado. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Definir tipo/camas -> validar capacidad -> publicar tarifa por fecha -> bloquear noche si corresponde -> consultar cupo -> versionar cambio -> sincronizar.

## Reglas que no se pueden violar
17 habitaciones confirmadas no define camas; intervalo de salida exclusivo; tarifa de reserva congelada; libre comercial no significa limpia.

## Condiciones y configuración
Ficha de habitaciones y políticas aprobadas para publicar; fixtures para diseñar. Decisiones pendientes: D01, D02, D03, D14. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### HOT-001 - Catastro de 17 habitaciones
**Historia F02-US01.** Como administración, necesito catastro de 17 habitaciones para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; ocupación; P0; relación original: CORE-001. Regla heredada preservada: Tipo, camas, capacidad, banio y equipamiento configurables.

**Entradas y validación:** room code, type, beds, capacity, private_bath, attributes. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Activar catálogo real sólo con conteo de 17 habitaciones y validación D01. Datos sintéticos no se exportan a canal productivo; sala se modela separadamente.

**Escenario positivo TC-HOT-001-P:** Dado Activar 17 códigos únicos respaldados por ficha y ver sus estados. Cuando se completa la acción autorizada, entonces se cumple: El catálogo aprobado suma 17 sin agregar la sala comun Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-HOT-001-N:** Dado Intentar activar dos habitaciones con mismo código o la sala como habitación adicional. Entonces 422/409 y catálogo sigue en revisión; no aumenta inventario.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F02-T01A` (pruebas), `F02-T01B` (implementación), `F02-T01C` (verificación). Evidencia prevista `evidence/F02/HOT-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### HOT-002 - Capacidad por personas y configuración
**Historia F02-US02.** Como administración, necesito capacidad por personas y configuración para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; tarifas; P0; relación original: HOT-001. Regla heredada preservada: No confundir camas, personas y habitaciones.

**Entradas y validación:** adults, children, ages when justified, bed configuration. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Capacidad total y por clase de ocupante se válida en motor; una cama adicional requiere configuración y política aprobada. No usar sólo número de camas como personas.

**Escenario positivo TC-HOT-002-P:** Dado Dos adultos en doble consumen una unidad y dos personas-noche por noche. Cuando se completa la acción autorizada, entonces se cumple: Una doble con dos personas ocupa una habitación Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-HOT-002-N:** Dado Tres adultos intentan reservar una doble con max_total=2. Entonces 422 CAPACITY_EXCEEDED y ofrecer alternativa válida sin inventar camas.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F02-T02A` (pruebas), `F02-T02B` (implementación), `F02-T02C` (verificación). Evidencia prevista `evidence/F02/HOT-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### HOT-003 - Inventario por tipo y asignación física
**Historia F02-US03.** Como administración, necesito inventario por tipo y asignación física para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta operativa; P0; relación original: HOT-001. Regla heredada preservada: Validar cupo del tipo y ausencia de solapes físicos.

**Entradas y validación:** type/day capacity, confirmed, holds, physical segments. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Validar todos los días y tipos de forma atomica; bloquear filas ordenadamente. La asignación física utiliza intervalos excluyentes y no altera cuenta de cliente.

**Escenario positivo TC-HOT-003-P:** Dado Una reserva del 10 al 12 reduce una unidad en cada una de las dos noches. Cuando se completa la acción autorizada, entonces se cumple: No se asigna dos veces el mismo intervalo Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-HOT-003-N:** Dado Asignar mismo cuarto a dos estadías con intervalos solapados. Entonces 409 ROOM_CONFLICT y conservar ambas reservas sin asignación doble.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F02-T03A` (pruebas), `F02-T03B` (implementación), `F02-T03C` (verificación). Evidencia prevista `evidence/F02/HOT-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### HOT-004 - Bloqueos de mantenimiento fechados
**Historia F02-US04.** Como administración, necesito bloqueos de mantenimiento fechados para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: HOT-003. Regla heredada preservada: Bloqueo genera alerta de reservas afectadas.

**Entradas y validación:** room_id, start/end, reason, approval, affected reservations. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Un bloqueo crítico puede entrar en emergencia con auditoría, pero genera incidencia de cada reserva afectada. Un bloqueo planificado válida alternativas antes de activar.

**Escenario positivo TC-HOT-004-P:** Dado Averia de ducha reduce disponibilidad y lista reservas que requieren reasignacion. Cuando se completa la acción autorizada, entonces se cumple: Una averia no cancela silenciosamente una reserva Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-HOT-004-N:** Dado Crear bloqueo sobre reserva confirmada y pretender anular automáticamente esa reserva. Entonces Bloqueo e incidencia visibles; contrato de reserva no se cancela ni se reembolsa sólo.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F02-T04A` (pruebas), `F02-T04B` (implementación), `F02-T04C` (verificación). Evidencia prevista `evidence/F02/HOT-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### HOT-005 - Estados comerciales y físicos distintos
**Historia F02-US05.** Como administración, necesito estados comerciales y físicos distintos para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: HOT-003. Regla heredada preservada: Limpieza, ocupación, mantenimiento y cuenta independientes.

**Entradas y validación:** occupancy, cleaning, maintenance, folio status. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Los cuatro ejes se actualizan por eventos propios. Checkout marca salida y tarea de suciedad; sólo inspección libera entrega y sólo pago ajusta cuenta.

**Escenario positivo TC-HOT-005-P:** Dado Habitación desocupada y sucia con saldo empresarial pendiente se muestra correctamente. Cuando se completa la acción autorizada, entonces se cumple: Checkout deja habitación sucia sin cambiar saldo contable Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-HOT-005-N:** Dado Marcar CLEAN para intentar ignorar bloqueo por equipo inseguro. Entonces No queda asignable mientras mantenimiento siga bloqueante; error explicativo.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F02-T05A` (pruebas), `F02-T05B` (implementación), `F02-T05C` (verificación). Evidencia prevista `evidence/F02/HOT-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### RES-005 - Planes y precios versionados
**Historia F02-US06.** Como administración, necesito planes y precios versionados para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** VALORES habitaciones; P0; relación original: HOT-002. Regla heredada preservada: Precio por fecha, ocupantes, moneda y canal.

**Entradas y validación:** rate_plan, date, occupancy, currency, price snapshot. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Resolver regla mas específica y versionada; guardar desglose por noche y aceptacion. Una nueva tarifa no recalcula reservas antiguas salvo cambio aceptado.

**Escenario positivo TC-RES-005-P:** Dado Reserva pactada a 70000 conserva ese valor cuando tarifa cambia a 75000. Cuando se completa la acción autorizada, entonces se cumple: Cambiar tarifa base no cambia una reserva confirmada Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-RES-005-N:** Dado Modificar precio publicado y reabrir detalle de reserva ya confirmada. Entonces El detalle conserva snapshot original; sólo nueva cotización usa nuevo precio.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F02-T06A` (pruebas), `F02-T06B` (implementación), `F02-T06C` (verificación). Evidencia prevista `evidence/F02/RES-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### RES-006 - Descuento separado de comisión
**Historia F02-US07.** Como administración, necesito descuento separado de comisión para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Tarifas I4:I5; Booking H; P0; relación original: RES-005. Regla heredada preservada: Descuentos al cliente e importes de comisión son conceptos distintos.

**Entradas y validación:** promotion, commission, gross/net, channel. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Descuento modifica precio cliente; comisión calcula costo segun contrato y base definida. Prohibir usar columna histórica Genius como comisión general.

**Escenario positivo TC-RES-006-P:** Dado Precio 100000 con descuento 10% resulta 90000; comisión se registra aparte con su base. Cuando se completa la acción autorizada, entonces se cumple: Aplicar descuento no duplica deduccion del canal Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-RES-006-N:** Dado Aplicar 17% histórico automáticamente como descuento y comisión de toda venta. Entonces Bloqueo de configuración sin política vigente; no deduccion duplicada.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F02-T07A` (pruebas), `F02-T07B` (implementación), `F02-T07C` (verificación). Evidencia prevista `evidence/F02/RES-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### REV-001 - Restricciones de venta y gestión tarifaria
**Historia F02-US08.** Como administración, necesito restricciones de venta y gestión tarifaria para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: RES-005;INT-001. Regla heredada preservada: Estadía mínima/máxima, apertura/cierre, cupos, grupos, paquetes, jerarquía y límites de descuento..

**Entradas y validación:** min/max nights, closed arrival/departure, stop-sell, hierarchy. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Evaluar restricciones locales antes de cotizar; proveedor externo sólo mapea la regla, no es requisito para existir localmente. Explicar conflicto de reglas.

**Escenario positivo TC-REV-001-P:** Dado Plan mínimo dos noches rechaza una y ofrece dos disponibles. Cuando se completa la acción autorizada, entonces se cumple: Reglas incompatibles explican bloqueo; aumentar tarifa no altera reservas confirmadas. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-REV-001-N:** Dado Cambiar tarifa base altera precio de reserva confirmada. Entonces Snapshot preservado; nueva política sólo afecta ofertas futuras.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F02-T08A` (pruebas), `F02-T08B` (implementación), `F02-T08C` (verificación). Evidencia prevista `evidence/F02/REV-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: room_type, room, room_block, inventory_day, rate_plan, rate_price, promotion, sale_restriction.

Pantallas: UI-04, UI-05; especificadas en `ux/pantallas.csv`. Operaciones propias: searchAvailability, createRoom, blockRoom, publishRate, listRooms. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: inventory.changed, rate.published, room.blocked. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
