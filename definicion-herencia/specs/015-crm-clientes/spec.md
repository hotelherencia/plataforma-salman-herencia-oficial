# F14 - CRM, identidad y consentimiento

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Atender oportunidades con historial y autorizaciones por finalidad, sin fusionar identidades por nombre.

Actores: ventas;recepción;administración;privacidad. Entrega candidata: E2. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Crear contacto -> enlazar identidad con evidencia -> abrir oportunidad -> asignar -> cotizar -> seguir con permiso -> convertir o perder -> baja/retencion.

## Reglas que no se pueden violar
Igual nombre no fusiona identidades; no compartir automáticamente entre sociedades; baja detiene cola; rechazo de publicidad permite reservar.

## Condiciones y configuración
Cuentas oficiales, política de finalidad y responsables. Decisiones pendientes: D16, D19, D25, D26, D28, D30. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### SOC-001 - Activos digitales y habilitacion por capacidad
**Historia F14-US01.** Como ventas, necesito activos digitales y habilitacion por capacidad para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: CORE-003. Regla heredada preservada: Duenos, administradores, recuperación, cuentas y permisos diferenciados para mensajes, contenido, anuncios y medición..

**Entradas y validación:** digital account, owner, recovery, capability permissions. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Inventario digital por cuenta y capacidad, evidencia y vigencia. Transferir permisos institucionales, no contraseñas personales; revocacion parcial no apaga funciones ajenas.

**Escenario positivo TC-SOC-001-P:** Dado Mensajeria verificada funciona mientras publicación permanece desactivada. Cuando se completa la acción autorizada, entonces se cumple: Sin permiso de publicación, mensajeria puede funcionar y publicación permanece deshabilitada. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-001-N:** Dado Marcar toda cuenta META integrada al validar un sólo permiso. Entonces Rechazo de estado agregado; cada capacidad conserva gate propio.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F14-T01A` (pruebas), `F14-T01B` (implementación), `F14-T01C` (verificación). Evidencia prevista `evidence/F14/SOC-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-004 - CRM de consultas y oportunidades
**Historia F14-US02.** Como ventas, necesito crm de consultas y oportunidades para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: RES-003. Regla heredada preservada: Consulta, calificación, cotización, reserva, pérdida y seguimiento tienen responsables y estados..

**Entradas y validación:** opportunity, owner, quote, reservation link, lost reason. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Estados comerciales no equivalen a inventario ni ingreso. Ganada exige reserva confirmada vinculada; pérdida documenta razón sin borrado de historial.

**Escenario positivo TC-SOC-004-P:** Dado Consulta se cotiza, cliente reserva y oportunidad queda GANADA. Cuando se completa la acción autorizada, entonces se cumple: Una consulta sin pago ni condiciones cumplidas no figura como reserva confirmada. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-004-N:** Dado Agente marca venta por un mensaje de interes sin reserva. Entonces Validación impide GANADA, conserva EN_ATENCION/COTIZADA.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F14-T02A` (pruebas), `F14-T02B` (implementación), `F14-T02C` (verificación). Evidencia prevista `evidence/F14/SOC-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-005 - Identidad de cliente entre canales
**Historia F14-US03.** Como ventas, necesito identidad de cliente entre canales para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: CORE-003. Regla heredada preservada: Identificadores por canal; vinculación sólo con evidencia autorizada; fusion reversible..

**Entradas y validación:** channel identity, contact evidence, merge audit. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Identidades scoped se vinculan sólo con evidencia; fusion revisable y reversible. Nunca usar coincidencia de nombre como autenticación.

**Escenario positivo TC-SOC-005-P:** Dado Mismo contacto verifica correo y telefono y se vinculan dos canales. Cuando se completa la acción autorizada, entonces se cumple: Dos personas con igual nombre no se fusionan; pasar a WhatsApp no revela otra conversación. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-005-N:** Dado Dos personas se llaman Ana y el sistema mezcla conversaciones. Entonces No fusion; datos aislados hasta evidencia autorizada.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F14-T03A` (pruebas), `F14-T03B` (implementación), `F14-T03C` (verificación). Evidencia prevista `evidence/F14/SOC-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-006 - Bandeja unificada y traspaso a recepción
**Historia F14-US04.** Como ventas, necesito bandeja unificada y traspaso a recepción para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: SOC-004;SOC-005. Regla heredada preservada: Asignación, prioridad, historial, respuesta, estados de envio y bloqueo del bot al tomar el caso una persona..

**Entradas y validación:** conversation owner_mode, handoff versión, messages. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Toma humana compare-and-set pausa bot antes de enviar respuesta; mensajes pendientes del bot se cancelan o revisan. El historial conserva responsable.

**Escenario positivo TC-SOC-006-P:** Dado Recepción toma hilo y responde sin competencia del asistente. Cuando se completa la acción autorizada, entonces se cumple: Recepción toma un caso y no recibe respuestas concurrentes contradictorias del bot. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-006-N:** Dado Respuesta bot en cola intenta salir después de handoff. Entonces Bloqueo por versión de propietario; no mensaje contradictorio.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F14-T04A` (pruebas), `F14-T04B` (implementación), `F14-T04C` (verificación). Evidencia prevista `evidence/F14/SOC-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-009 - Tiempos de atención y continuidad de turno
**Historia F14-US05.** Como ventas, necesito tiempos de atención y continuidad de turno para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: SOC-006;REC-004. Regla heredada preservada: Consulta sin respuesta, oportunidad próxima a expirar y reclamación pasan al responsable con plazo..

**Entradas y validación:** due_at, owner, priority, shift handover. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Plazos y cobertura D28 configurables; escalar consultas sin respuesta y ofertas por vencer. Cambio de turno no resetea plazo ni borra responsable anterior.

**Escenario positivo TC-SOC-009-P:** Dado Hilo pendiente pasa al turno entrante con siguiente acción. Cuando se completa la acción autorizada, entonces se cumple: Cambio de turno conserva los casos pendientes con historial y siguiente acción. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-009-N:** Dado Turno saliente cierra sesion dejando reclamo urgente sin receptor. Entonces Asignar responsable de escalamiento y alerta, nunca cerrar caso automáticamente.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F14-T05A` (pruebas), `F14-T05B` (implementación), `F14-T05C` (verificación). Evidencia prevista `evidence/F14/SOC-009/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-013 - Consentimientos y baja de comunicaciones
**Historia F14-US06.** Como ventas, necesito consentimientos y baja de comunicaciones para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: SEC-002. Regla heredada preservada: Separar operación del contrato, mensajeria y marketing; prueba de permiso, finalidad, vigencia y revocacion..

**Entradas y validación:** purpose, consent proof, notice versión, revoked_at. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Separar servicio, contacto y marketing; permiso verificable y baja efectiva antes de cada envio. Rechazar publicidad no bloquea reserva o derechos.

**Escenario positivo TC-SOC-013-P:** Dado Baja cancela mensajes promocionales en cola y permite consultar cuenta. Cuando se completa la acción autorizada, entonces se cumple: Solicitar baja impide nuevas promociones incluso si ya están en cola; no impide consultar la reserva. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-013-N:** Dado Lista antigua vuelve a suscribir al cliente sin nueva evidencia. Entonces No cambia REVOKED; incidente de importacion/permiso.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F14-T06A` (pruebas), `F14-T06B` (implementación), `F14-T06C` (verificación). Evidencia prevista `evidence/F14/SOC-013/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-017 - Seguimiento y recuperación de abandono
**Historia F14-US07.** Como ventas, necesito seguimiento y recuperación de abandono para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: SOC-013;SOC-016. Regla heredada preservada: Sólo con datos y permiso adecuados; límites de frecuencia; revalidar precio y cupo al volver..

**Entradas y validación:** contact, purpose, abandonment, frequency cap. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Seguimiento sólo con contacto obtenido legitimamente y permiso adecuado; máximo configurable y baja inmediata. Oferta vencida no mantiene cupo.

**Escenario positivo TC-SOC-017-P:** Dado Contacto con permiso recibe recordatorio aprobado y nueva validación. Cuando se completa la acción autorizada, entonces se cumple: Un visitante anonimo no recibe un mensaje inventado; una oferta vencida requiere nueva cotización. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-017-N:** Dado Visitante anonimo sin contacto se intenta contactar automáticamente. Entonces No mensaje; sólo estadistica agregada permitida.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F14-T07A` (pruebas), `F14-T07B` (implementación), `F14-T07C` (verificación). Evidencia prevista `evidence/F14/SOC-017/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SEC-007 - Privacidad de medición comercial
**Historia F14-US08.** Como ventas, necesito privacidad de medición comercial para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: SOC-012;SOC-013. Regla heredada preservada: Minimizar eventos, permisos aplicables, no RUT/pasaporte/tarjetas/conversaciones en publicidad..

**Entradas y validación:** measurement purpose, payload allowlist, opt-out. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Excluir RUT, pasaporte, tarjeta, conversaciones y restricciones sensibles de publicidad. Hash no vuelve automáticamente anonimo un identificador. Permisos antes de enviar.

**Escenario positivo TC-SEC-007-P:** Dado Opt-out permite comprar sin eventos publicitarios personales. Cuando se completa la acción autorizada, entonces se cumple: Rechazar seguimiento no impide reservar; payload de conversión no contiene datos prohibidos. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SEC-007-N:** Dado Payload conversion contiene documento del huésped. Entonces Validador de esquema rechaza y registra incidente sin copiar el dato en log.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F14-T08A` (pruebas), `F14-T08B` (implementación), `F14-T08C` (verificación). Evidencia prevista `evidence/F14/SEC-007/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: contact, channel_identity, consent, opportunity.

Pantallas: UI-40, UI-41; especificadas en `ux/pantallas.csv`. Operaciones propias: createContact, recordConsent, takeoverConversation, listConversations. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: opportunity.changed, consent.revoked, identity.linked. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
