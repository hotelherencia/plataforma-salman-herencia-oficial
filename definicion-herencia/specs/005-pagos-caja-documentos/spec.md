# F04 - Pagos, caja y documentos tributarios

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Verificar y aplicar cobros una vez, distinguir anticipo/garantia, cerrar caja y controlar documentos fiscales.

Actores: recepción;tesorería;contador;aprobador. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Crear intento -> procesador autentica -> servidor confirma -> registrar pago -> aplicar -> emitir documento si corresponde -> cerrar caja -> liquidar -> conciliar; devolución requiere aprobación.

## Reglas que no se pueden violar
Un pago externo se registra una vez; pago no es ingreso adicional; reembolso no excede saldo reembolsable; garantía no es anticipo; tarjeta completa/CVV nunca persisten.

## Condiciones y configuración
Proveedor y titularidad verificados; tasas/criterios tributarios aprobados; caja habilitada. Decisiones pendientes: D03, D06, D07, D08, D14, D34. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### PAY-001 - Anticipos y garantías
**Historia F04-US01.** Como recepción, necesito anticipos y garantías para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; transición; P0; relación original: RES-005. Regla heredada preservada: Distinguir fondos recibidos y servicio prestado.

**Entradas y validación:** kind, amount, currency, received_at, service period. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Anticipo reduce saldo comercial al aplicarse pero no registra servicio prestado. Garantía tiene circuito separado y aplicación autorizada. Saldo heredado no es caja propia.

**Escenario positivo TC-PAY-001-P:** Dado 100000 recibidos en diciembre para enero figuran como anticipo y obligación futura. Cuando se completa la acción autorizada, entonces se cumple: Anticipo diciembre para enero no se suma a venta enero dos veces Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PAY-001-N:** Dado Clasificar garantía por daños como venta del día automáticamente. Entonces Rechazo de regla contable y registro pendiente de clasificación.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T01A` (pruebas), `F04-T01B` (implementación), `F04-T01C` (verificación). Evidencia prevista `evidence/F04/PAY-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### PAY-002 - Pagos parciales y múltiples medios
**Historia F04-US02.** Como recepción, necesito pagos parciales y múltiples medios para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: PAY-001. Regla heredada preservada: Aplicaciones no superan saldo de pago ni cargo.

**Entradas y validación:** payment, folio, applied amount, balances. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Suma de asignaciones activas no excede pago disponible ni saldo elegible; conservar excedente a favor. Validar moneda y bloquear filas de pago/cuenta.

**Escenario positivo TC-PAY-002-P:** Dado Cuenta 140000 se cubre con 70000 transferencia y 70000 tarjeta. Cuando se completa la acción autorizada, entonces se cumple: Dos medios cancelan una cuenta sin duplicar ingresos Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PAY-002-N:** Dado Dos operadores aplican simultaneamente el mismo saldo de pago. Entonces Sólo aplicaciones permitidas; segundo recibe conflicto, nunca saldo negativo.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T02A` (pruebas), `F04-T02B` (implementación), `F04-T02C` (verificación). Evidencia prevista `evidence/F04/PAY-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### PAY-003 - Confirmacion pasarela en servidor
**Historia F04-US03.** Como recepción, necesito confirmacion pasarela en servidor para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** S14; P0; relación original: PAY-002. Regla heredada preservada: Validar estado, monto, moneda y orden.

**Entradas y validación:** provider token, order, expected amount/currency, server response. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Confirmar por servidor usando flujo del proveedor; verificar orden, monto, moneda y estado. Browser return sólo inicia verificación; unknown requiere consulta.

**Escenario positivo TC-PAY-003-P:** Dado Respuesta autorizada de proveedor coincide con orden y monto esperado. Cuando se completa la acción autorizada, entonces se cumple: Retorno del navegador sin autorización no marca pagado Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PAY-003-N:** Dado Cliente envia success=true o token de otra orden. Entonces No se marca pagado; evento de fraude y error sin revelar otra cuenta.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T03A` (pruebas), `F04-T03B` (implementación), `F04-T03C` (verificación). Evidencia prevista `evidence/F04/PAY-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### PAY-004 - Idempotencia de pagos
**Historia F04-US04.** Como recepción, necesito idempotencia de pagos para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta de control; P0; relación original: PAY-003. Regla heredada preservada: Clave única por transacción externa.

**Entradas y validación:** provider, external_transaction_id, idempotency key. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Constraint único y transacción local; eventos repetidos retornan resultado previo. Payload distinto con mismo ID se investiga; notificación no crea otro pago.

**Escenario positivo TC-PAY-004-P:** Dado Diez repeticiones identicas generan un pago y una aplicación. Cuando se completa la acción autorizada, entonces se cumple: Repetir callback diez veces registra un cobro Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PAY-004-N:** Dado Reintentar tras timeout sin conocer si proveedor cargo. Entonces Consultar estado por orden antes de otro intento; estado UNKNOWN visible.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T04A` (pruebas), `F04-T04B` (implementación), `F04-T04C` (verificación). Evidencia prevista `evidence/F04/PAY-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### PAY-005 - Devoluciones y contracargos
**Historia F04-US05.** Como recepción, necesito devoluciones y contracargos para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; S14; P0; relación original: PAY-002. Regla heredada preservada: Aprobación y vinculo con pago/documento original.

**Entradas y validación:** original payment, amount, reason, approval, fiscal reference. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Reservar saldo reembolsable para impedir devoluciones simultaneas; estado desconocido no se reenvia ciegamente. Contracargo es disputa, no borrado de servicio.

**Escenario positivo TC-PAY-005-P:** Dado Devolución parcial de 20000 sobre 70000 deja 50000 netos y evidencia. Cuando se completa la acción autorizada, entonces se cumple: Devolución parcial deja saldo y trazabilidad correctos Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PAY-005-N:** Dado Dos devoluciones concurrentes que superan saldo disponible. Entonces 409 REFUND_LIMIT; ninguna doble salida, escalamiento de incertidumbre.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T05A` (pruebas), `F04-T05B` (implementación), `F04-T05C` (verificación). Evidencia prevista `evidence/F04/PAY-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### PAY-006 - Arqueo y entrega de turno
**Historia F04-US06.** Como recepción, necesito arqueo y entrega de turno para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** RETIRO CAJA; P0; relación original: PAY-002. Regla heredada preservada: Saldo inicial, entradas, salidas y diferencia.

**Entradas y validación:** cash opening, cash events, denomination count, turnover. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Calcular esperado sólo con efectivo; comparar contado, diferencia y firma de entrega. Tarjetas no incrementan cajon físico.

**Escenario positivo TC-PAY-006-P:** Dado 10000 inicial +50000 cobros -20000 retiro =40000 esperado. Cuando se completa la acción autorizada, entonces se cumple: Arqueo concilia efectivo esperado y contado; diferencia no se borra Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PAY-006-N:** Dado Conteo 39000 y operador intenta cambiar una venta para cuadrar. Entonces Diferencia -1000 permanece; requerir motivo y revisión.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T06A` (pruebas), `F04-T06B` (implementación), `F04-T06C` (verificación). Evidencia prevista `evidence/F04/PAY-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### PAY-007 - Retiros y depósitos
**Historia F04-US07.** Como recepción, necesito retiros y depósitos para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** RETIRO CAJA; P0; relación original: PAY-006. Regla heredada preservada: Traslado de dinero distinto de gasto.

**Entradas y validación:** withdrawal, transfer group, deposit, bank evidence. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Retiro/deposito se vinculan por traslado en transito, no gasto. Diferencia entre retirado y depositado se investiga con responsables.

**Escenario positivo TC-PAY-007-P:** Dado Retiro 20000 y abono 20000 cancelan transito sin afectar resultado. Cuando se completa la acción autorizada, entonces se cumple: Retiro para depositar no reduce resultado como gasto Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PAY-007-N:** Dado Depósito por 19000 para retiro de 20000. Entonces 1000 pendiente y alerta; no ajuste automático de ingresos.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T07A` (pruebas), `F04-T07B` (implementación), `F04-T07C` (verificación). Evidencia prevista `evidence/F04/PAY-007/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### PAY-008 - Cierre y reapertura
**Historia F04-US08.** Como recepción, necesito cierre y reapertura para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta de control; P0; relación original: PAY-006. Regla heredada preservada: Cierre protegido; reapertura con motivo y permiso.

**Entradas y validación:** shift close, versión, reason, approval. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Cierre congela movimientos; corrección por reapertura autorizada o ajuste posterior segun política. Control de fecha y versión evita edicion concurrente.

**Escenario positivo TC-PAY-008-P:** Dado Supervisor reabre con motivo y deja auditoría antes/despues. Cuando se completa la acción autorizada, entonces se cumple: Recepcionista no reabre un cierre aprobado Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PAY-008-N:** Dado Recepcionista intenta reabrir turno ya aprobado. Entonces 403; original inmutable y solicitud de revisión opcional.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T08A` (pruebas), `F04-T08B` (implementación), `F04-T08C` (verificación). Evidencia prevista `evidence/F04/PAY-008/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### TAX-001 - Emisor y proveedor tributario
**Historia F04-US09.** Como recepción, necesito emisor y proveedor tributario para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; S17; P0; relación original: CORE-006. Regla heredada preservada: RUT correcto, folio oficial y estado del documento.

**Entradas y validación:** issuer, fiscal type, provider reference, totals. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Enviar sólo con emisor habilitado y regla aprobada; documento acepta estado real del proveedor. Factura borrador no tiene folio oficial inventado.

**Escenario positivo TC-TAX-001-P:** Dado Proveedor acepta emisión y se registra folio/respuesta verificables. Cuando se completa la acción autorizada, entonces se cumple: Rechazo de emisión queda pendiente, no como documento aceptado Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-TAX-001-N:** Dado Proveedor rechaza documento por dato tributario inválido. Entonces Estado REJECTED y tarea de corrección, no mostrarlo como emitido aceptado.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T09A` (pruebas), `F04-T09B` (implementación), `F04-T09C` (verificación). Evidencia prevista `evidence/F04/TAX-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### TAX-002 - Reglas de impuestos aprobadas
**Historia F04-US10.** Como recepción, necesito reglas de impuestos aprobadas para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** S17; P0; relación original: TAX-001. Regla heredada preservada: Condiciones de exención no dependen sólo de nacionalidad.

**Entradas y validación:** tax policy, tourist status, registration, currency, evidence. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Regla tributaria con vigencia y responsable; validar condiciones documentadas. No inferir exención de pasaporte extranjero por si sólo.

**Escenario positivo TC-TAX-002-P:** Dado Caso ficticio cumple política aprobada y conserva respaldo de tratamiento. Cuando se completa la acción autorizada, entonces se cumple: Extranjero sin requisitos no obtiene exención automática Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-TAX-002-N:** Dado Huésped extranjero sin evidencia suficiente pide tarifa exenta. Entonces Derivar validación y aplicar regla aprobada correspondiente, no exención automática.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T10A` (pruebas), `F04-T10B` (implementación), `F04-T10C` (verificación). Evidencia prevista `evidence/F04/TAX-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### TAX-003 - Notas y correcciones
**Historia F04-US11.** Como recepción, necesito notas y correcciones para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta contable; P0; relación original: TAX-001. Regla heredada preservada: Relacionar nota con documento y no duplicar venta/cobro.

**Entradas y validación:** original fiscal document, note type, reason, amount. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Notas corrigen documento manteniendo referencia y saldos; emision/nota no duplican cargo o pago. Rechazo de nota mantiene diferencia pendiente.

**Escenario positivo TC-TAX-003-P:** Dado Nota parcial enlazada ajusta referencia sin borrar factura original. Cuando se completa la acción autorizada, entonces se cumple: Anulación preserva documento original y saldo correcto Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-TAX-003-N:** Dado Eliminar factura para ocultar error o emitir dos notas iguales por reintento. Entonces Operación bloqueada/deduplicada, historial integro.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T11A` (pruebas), `F04-T11B` (implementación), `F04-T11C` (verificación). Evidencia prevista `evidence/F04/TAX-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SEC-008 - Enlaces de pago y acceso acotados
**Historia F04-US12.** Como recepción, necesito enlaces de pago y acceso acotados para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: SOC-016;PAY-003. Regla heredada preservada: Tokens aleatorios, expiración, revocacion, controles de acceso y no reutilizacion de secretos..

**Entradas y validación:** opaque token, hash, expiry, scope, revocation. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Token de pago sólo inicia/consulta su intento; no concede reembolso o acceso global. Almacenamiento de hash y redaccion de URL en logs.

**Escenario positivo TC-SEC-008-P:** Dado Enlace de una reserva cobra sólo monto calculado por servidor. Cuando se completa la acción autorizada, entonces se cumple: Probar enlace de otra reserva no revela cuenta; un enlace a pago no autoriza devolución. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SEC-008-N:** Dado Manipular ID o amount en URL para pagar menos o leer otra cuenta. Entonces 403/422, sin cambiar oferta ni estado financiero.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F04-T12A` (pruebas), `F04-T12B` (implementación), `F04-T12C` (verificación). Evidencia prevista `evidence/F04/SEC-008/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: folio, charge, payment_intent, payment, payment_allocation, refund, cash_shift, cash_movement, fiscal_document.

Pantallas: UI-10, UI-11, UI-12, UI-13; especificadas en `ux/pantallas.csv`. Operaciones propias: startPayment, readPaymentStatus, createCharge, recordManualPayment, allocatePayment, requestRefund, openCash, closeCash, issueFiscal, listFolios. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: payment.authorized, payment.failed, payment.unknown, payment.allocated, refund.completed, cash.closed, fiscal.updated. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
