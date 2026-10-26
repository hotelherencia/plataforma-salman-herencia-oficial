# F03 - Reserva directa desde enlace social

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Convertir una visita en reserva mediante el motor central; parametrizar anticipo y enlazar el pago real en F04.

Actores: huésped;recepción;empresa pagadora. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Consultar -> cotizar -> aceptar condiciones -> retener cuando aplique -> crear PENDING -> solicitar pago o validar crédito -> confirmar -> enviar comprobante -> modificar/cancelar versionando.

## Reglas que no se pueden violar
Sólo motor autoritativo confirma; manipular precio cliente no reduce total; hold vencido no autoriza sobreventa; contacto/seguimiento no obligatorio para prestar servicio.

## Condiciones y configuración
Políticas visibles y capacidad validada; contrato de pagos o crédito definido antes de confirmar. Decisiones pendientes: D01, D02, D03, D06, D14, D19, D25, D28. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### RES-001 - Motor de reserva directa móvil
**Historia F03-US01.** Como huésped, necesito motor de reserva directa móvil para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; mercado S02; P0; relación original: HOT-003. Regla heredada preservada: Precio total, inclusiones, políticas y disponibilidad.

**Entradas y validación:** dates, occupants, quote, policy acceptance, contact. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Busqueda y oferta salen del motor; confirmacion persiste antes de notificar. Recepción usa el mismo ID, no copia manual. No exigir registro de cuenta para reservar.

**Escenario positivo TC-RES-001-P:** Dado Huésped completa reserva desde enlace y recepción ve mismo precio/fechas. Cuando se completa la acción autorizada, entonces se cumple: Reserva desde enlace social aparece en recepción con el mismo ID Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-RES-001-N:** Dado Interrumpir correo después de confirmar reserva. Entonces Reserva permanece confirmada; notificación fallida en cola y alerta.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T01A` (pruebas), `F03-T01B` (implementación), `F03-T01C` (verificación). Evidencia prevista `evidence/F03/RES-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### RES-002 - Origen y campania
**Historia F03-US02.** Como huésped, necesito origen y campania para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: RES-001. Regla heredada preservada: Separar canal comercial de fuente de trafico.

**Entradas y validación:** channel_code, source, medium, campaign, landing. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Separar DIRECT/OTA/AGENT de origen comercial; saneamiento y límites de longitud en etiquetas. Sin evidencia se guarda UNKNOWN, no atribución estimada.

**Escenario positivo TC-RES-002-P:** Dado Enlace Instagram produce canal DIRECT y origen instagram. Cuando se completa la acción autorizada, entonces se cumple: Reserva directa originada en Instagram no se atribuye a Booking Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-RES-002-N:** Dado Parámetro URL contiene RUT, script o texto excesivo. Entonces Se rechaza o descarta dato de atribución inseguro sin impedir compra legitima.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T02A` (pruebas), `F03-T02B` (implementación), `F03-T02C` (verificación). Evidencia prevista `evidence/F03/RES-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### RES-003 - Cotización y retención temporal
**Historia F03-US03.** Como huésped, necesito cotización y retención temporal para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta de control; P0; relación original: HOT-003. Regla heredada preservada: Plazo de cupo configurable y pago posterior a expiración controlado.

**Entradas y validación:** quote_id, expires_at, inventory_hold, session. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Cotización no bloquea; checkout retiene por plazo parametrizado. Expiración libera con transacción y clave única; no se extiende por cada refresco sin límite.

**Escenario positivo TC-RES-003-P:** Dado Retención de prueba de quince minutos expira y devuelve una unidad. Cuando se completa la acción autorizada, entonces se cumple: Cupo expirado no se confirma si ya fue vendido Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-RES-003-N:** Dado Pago confirmado tras vencimiento y cupo vendido a otro cliente. Entonces Estado PAGO_SIN_CUPO, incidencia y alternativa/devolucion autorizada; no sobreventa silenciosa.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T03A` (pruebas), `F03-T03B` (implementación), `F03-T03C` (verificación). Evidencia prevista `evidence/F03/RES-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### RES-004 - Último cupo concurrente
**Historia F03-US04.** Como huésped, necesito último cupo concurrente para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta de control; P0; relación original: RES-003. Regla heredada preservada: Confirmacion interna atomica.

**Entradas y validación:** inventory_day rows, hold id, idempotency key. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Bloqueo ordenado por establecimiento/tipo/noche, relectura y escritura atomica con constraint. Reintento acotado para deadlock, mismo resultado por clave.

**Escenario positivo TC-RES-004-P:** Dado Veinte solicitudes al último cupo producen un sólo compromiso interno. Cuando se completa la acción autorizada, entonces se cumple: Dos solicitudes simultaneas producen una sola confirmacion interna Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-RES-004-N:** Dado Dos transacciones intentan confirmar el último cupo simultaneamente. Entonces Una obtiene 201; restantes 409 NO_AVAILABILITY, sin contadores negativos.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T04A` (pruebas), `F03-T04B` (implementación), `F03-T04C` (verificación). Evidencia prevista `evidence/F03/RES-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### RES-007 - Reservas de varias habitaciones
**Historia F03-US05.** Como huésped, necesito reservas de varias habitaciones para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Booking columnas E:F; P0; relación original: HOT-003. Regla heredada preservada: Cabecera y lineas con importes sin duplicación.

**Entradas y validación:** reservation header, lines, dates, total. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Una linea representa una unidad de alojamiento; varias unidades generan lineas separadas con importe propio. Total de cabecera se suma una sola vez en reportes.

**Escenario positivo TC-RES-007-P:** Dado Tres habitaciones con 50000,60000,70000 suman 180000. Cuando se completa la acción autorizada, entonces se cumple: Tres habitaciones suman sus lineas una sola vez Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-RES-007-N:** Dado Consulta une pasajeros y multiplica total de cabecera por filas. Entonces Prueba detecta total distinto; reporte debe agregar primero por nivel correcto.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T05A` (pruebas), `F03-T05B` (implementación), `F03-T05C` (verificación). Evidencia prevista `evidence/F03/RES-007/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### RES-008 - Empresa pagadora y convenio
**Historia F03-US06.** Como huésped, necesito empresa pagadora y convenio para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: RES-007. Regla heredada preservada: Huésped, quien reserva y quien paga pueden ser distintos.

**Entradas y validación:** booker contact, guests, payer party, agreement. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Quien reserva, quien se aloja y quien paga son relaciones independientes. Convenio verifica vigencia, límite de crédito, plazo y autorización sin revelar datos ajenos.

**Escenario positivo TC-RES-008-P:** Dado Empresa paga dos estadías y documento mantiene pasajeros vinculados privadamente. Cuando se completa la acción autorizada, entonces se cumple: Factura a empresa sin perder pasajeros y estadías asociados Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-RES-008-N:** Dado Recepción habilita crédito a empresa sin convenio vigente. Entonces Reserva puede quedar pendiente, pero no salida a crédito sin aprobación.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T06A` (pruebas), `F03-T06B` (implementación), `F03-T06C` (verificación). Evidencia prevista `evidence/F03/RES-008/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### RES-009 - Modificaciones parciales
**Historia F03-US07.** Como huésped, necesito modificaciones parciales para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; S12; P0; relación original: RES-005. Regla heredada preservada: Versionar extension, reduccion y cambio de personas.

**Entradas y validación:** reservation versión, changed lines, new quote, delta. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Extension/reduccion calcula diferencia sólo sobre noches afectadas, válida cupos y acepta nuevas condiciones. Update usa versión para no pisar cambio concurrente.

**Escenario positivo TC-RES-009-P:** Dado Agregar una noche libre aumenta una unidad de inventario y su cargo, no noches previas. Cuando se completa la acción autorizada, entonces se cumple: Extension válida cupo y sólo agrega noches y cargos aplicables Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-RES-009-N:** Dado Extender cuando última noche no esta disponible o versión ya cambio. Entonces 409; reserva previa integra y cotización alternativa visible.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T07A` (pruebas), `F03-T07B` (implementación), `F03-T07C` (verificación). Evidencia prevista `evidence/F03/RES-009/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### RES-010 - Cancelaciones y no-show
**Historia F03-US08.** Como huésped, necesito cancelaciones y no-show para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Booking L2:L106; P0; relación original: RES-005. Regla heredada preservada: Política por reserva, liberacion y cobros autorizados.

**Entradas y validación:** policy snapshot, cancellation time, no-show evidence. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Aplicar política aceptada, liberar cupo desde fechas pertinentes, registrar cargo/devolucion autorizados. No-show no genera presencia ni desayuno servido.

**Escenario positivo TC-RES-010-P:** Dado Cancelación permitida libera reserva y calcula devolución conforme a snapshot. Cuando se completa la acción autorizada, entonces se cumple: No-show no se convierte automáticamente en noche ocupada Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-RES-010-N:** Dado Mensaje antiguo de confirmacion llega después de cancelación externa nueva. Entonces No revierte cancelación; se ignora revisión obsoleta y registra motivo.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T08A` (pruebas), `F03-T08B` (implementación), `F03-T08C` (verificación). Evidencia prevista `evidence/F03/RES-010/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### RES-011 - Grupos y reparto de cargos
**Historia F03-US09.** Como huésped, necesito grupos y reparto de cargos para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta operativa; P1; relación original: RES-007. Regla heredada preservada: Agrupar cuentas sin perder detalle individual.

**Entradas y validación:** group, payer, folios, allocations. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Agrupacion visual no fusiona estadías; reparto de pago sigue montos explícitos por cuenta y conserva remanente no aplicado. Exceso no borra deuda de otra cuenta.

**Escenario positivo TC-RES-011-P:** Dado Pago de 180000 aplicado a tres cuentas por 50000,60000,70000. Cuando se completa la acción autorizada, entonces se cumple: Un pago colectivo puede aplicarse a varias cuentas sin exceso Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-RES-011-N:** Dado Aplicar 200000 de un pago de 180000. Entonces 422 ALLOCATION_EXCEEDS_AVAILABLE; ninguna aplicación parcial queda huérfana.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T09A` (pruebas), `F03-T09B` (implementación), `F03-T09C` (verificación). Evidencia prevista `evidence/F03/RES-011/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### INT-005 - Notificaciones al huésped
**Historia F03-US10.** Como huésped, necesito notificaciones al huésped para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: RES-001. Regla heredada preservada: Plantilla, finalidad, destinatario y estado de envio.

**Entradas y validación:** event, recipient, template, purpose, delivery state. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Generar notificación en outbox luego de persistir negocio; dedup por evento/destinatario/plantilla. Verificar permiso y canal al enviar.

**Escenario positivo TC-INT-005-P:** Dado Una reserva confirmada genera una confirmacion operativa. Cuando se completa la acción autorizada, entonces se cumple: Reintento no envia confirmaciones duplicadas al mismo evento Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INT-005-N:** Dado Reintentar tras timeout de proveedor sin conocer entrega. Entonces Consultar referencia cuando posible; estado incierto visible y evitar spam.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T10A` (pruebas), `F03-T10B` (implementación), `F03-T10C` (verificación). Evidencia prevista `evidence/F03/INT-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-002 - Enlaces de redes y páginas de campaña
**Historia F03-US11.** Como huésped, necesito enlaces de redes y páginas de campaña para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: RES-001;RES-002. Regla heredada preservada: Origen, medio, campaña y contenido sin datos personales en URL; entrada web no exige API de mensajes..

**Entradas y validación:** campaign link, source/medium/content, approved landing. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Enlace HTTPS apunta al motor propio; etiquetas saneadas y sin identidad. Landing no depende de API de mensajes. Se conserva oferta/origen al navegar.

**Escenario positivo TC-SOC-002-P:** Dado Click desde Instagram enlaza reserva directa con origen conocido. Cuando se completa la acción autorizada, entonces se cumple: Un clic de Instagram llega al motor y conserva fuente en la reserva; sin etiqueta queda desconocida, no inventada. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-002-N:** Dado Eliminar etiquetas al volver del checkout o inventar campaña por ausencia. Entonces Persistencia segura de origen disponible; ausencia queda UNKNOWN.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T11A` (pruebas), `F03-T11B` (implementación), `F03-T11C` (verificación). Evidencia prevista `evidence/F03/SOC-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-003 - Reserva en navegador interno móvil
**Historia F03-US12.** Como huésped, necesito reserva en navegador interno móvil para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: RES-001;PAY-003. Regla heredada preservada: Validar fechas, ocupantes, retorno de pasarela, accesibilidad y alternativa para abrir navegador externo..

**Entradas y validación:** mobile browser, quote/hold reference, payment return. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Sesion recuperable por referencia opaca; callback válida servidor. Volver atras/recargar no duplica intento ni confirmacion. Alternativa de navegador externo mantiene oferta vigente.

**Escenario positivo TC-SOC-003-P:** Dado Checkout desde navegador interno vuelve a la misma reserva. Cuando se completa la acción autorizada, entonces se cumple: Volver del pago desde un navegador interno no pierde la reserva ni duplica el cobro. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-003-N:** Dado Navegador pierde cookie después del pago. Entonces Recuperación autenticada segura, no segundo cobro; si no hay acceso deriva.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T12A` (pruebas), `F03-T12B` (implementación), `F03-T12C` (verificación). Evidencia prevista `evidence/F03/SOC-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-016 - Cotización compartida y enlace seguro
**Historia F03-US13.** Como huésped, necesito cotización compartida y enlace seguro para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: RES-003;SEC-003. Regla heredada preservada: Token opaco, alcance, expiración, precio versionado y validación final de cupo; no exponer identidad en URL..

**Entradas y validación:** quote token hash, scope, expiry, current inventory. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Enlace opaco de cotización no revela otras cuentas ni autoriza devolución. Reutilizar enlace no extiende vigencia; precio y cupo se revalidan al aceptar.

**Escenario positivo TC-SOC-016-P:** Dado Cliente abre oferta válida y completa pago segun política. Cuando se completa la acción autorizada, entonces se cumple: Un enlace vencido no mantiene cupo; compartirlo no permite ver otras reservas. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-016-N:** Dado Token vencido o perteneciente a otra reserva usado para leer deuda. Entonces 410/403 sin datos; ofrecer nueva cotización autorizada.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T13A` (pruebas), `F03-T13B` (implementación), `F03-T13C` (verificación). Evidencia prevista `evidence/F03/SOC-016/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### UX-001 - Accesibilidad verificable
**Historia F03-US14.** Como huésped, necesito accesibilidad verificable para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: RES-001. Regla heredada preservada: Objetivo WCAG 2.2 AA; teclado, foco, contraste, etiquetas y pruebas por recorrido..

**Entradas y validación:** keyboard, focus, labels, contrast, screen reader, errors. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Objetivo WCAG2.2AA se comprueba por flujo; alternativa al arrastre y controles accesibles. Pruebas automáticas no sustituyen recorridos manuales.

**Escenario positivo TC-UX-001-P:** Dado Completar reserva y cambiar habitación sólo con teclado. Cuando se completa la acción autorizada, entonces se cumple: Reserva y calendario tienen alternativa sin arrastrar; campos de error son anunciados y corregibles. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-UX-001-N:** Dado Campo con error sólo cambia color y no explica el problema. Entonces Falla de aceptacion UX; agregar mensaje y foco sin perder datos.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T14A` (pruebas), `F03-T14B` (implementación), `F03-T14C` (verificación). Evidencia prevista `evidence/F03/UX-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### UX-002 - Idiomas, formatos y estados de interfaz
**Historia F03-US15.** Como huésped, necesito idiomas, formatos y estados de interfaz para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: CORE-005. Regla heredada preservada: Espanol inicial, estructura traducible, moneda y fechas sin ambiguedad; vacío, carga, error, falta de permiso..

**Entradas y validación:** locale, date/currency format, loading/empty/error states. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Espanol inicial y textos traducibles; formato no cambia valor ni política. Error no se muestra como exito y contexto de sociedad no conserva datos de otra.

**Escenario positivo TC-UX-002-P:** Dado Cambiar idioma conserva importe exacto y fechas de reserva. Cuando se completa la acción autorizada, entonces se cumple: Traducir no cambia monto, política aceptada ni cálculo de noches; fallo no se muestra como exito. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-UX-002-N:** Dado Traducir dia/mes invierte fechas o pantalla muestra datos previos de otra cuenta. Entonces Rechazo del caso; limpiar estado y formatos inequívocos.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F03-T15A` (pruebas), `F03-T15B` (implementación), `F03-T15C` (verificación). Evidencia prevista `evidence/F03/UX-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: quote, inventory_hold, reservation, reservation_line, reservation_change, corporate_agreement.

Pantallas: UI-06, UI-07, UI-08, UI-09; especificadas en `ux/pantallas.csv`. Operaciones propias: createQuote, createHold, createReservation, amendReservation, listReservations. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: quote.created, reservation.pending, reservation.confirmed, reservation.changed, reservation.cancelled. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
