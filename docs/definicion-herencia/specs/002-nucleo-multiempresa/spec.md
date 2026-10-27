# F01 - Sociedades, identidad, permisos y auditoría

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Operar con sociedad y unidad explícitas, permisos comprobables, documentos y cambios trazables.

Actores: propietario;administración;contador;auditor. Entrega candidata: E0. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Crear sociedad en borrador -> adjuntar respaldo -> aprobar vigencia -> otorgar rol por unidad -> operar con alcance -> auditar cambio -> revocar acceso.

## Reglas que no se pueden violar
La sociedad del token y del objeto deben coincidir; ser socio no concede acceso automático; participaciones históricas no se convierten en actuales; negacion por defecto.

## Condiciones y configuración
Sociedades y usuarios de prueba confirmados; emisor/operador reales antes de producción. Decisiones pendientes: D14, D15, D16, D24, D42, D44, D45. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### CORE-001 - Sociedades y unidades separadas
**Historia F01-US01.** Como propietario, necesito sociedades y unidades separadas para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; organigrama; P0; relación original: -. Regla heredada preservada: Cada transacción pertenece a un RUT y unidad.

**Entradas y validación:** company_id, unit_id, user scope. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** La sesion selecciona una sociedad autorizada; se válida que unidad, cuenta, documento y objeto relacionado pertenezcan al mismo alcance antes de escribir. El consolidado es sólo lectura salvo delegacion explícita.

**Escenario positivo TC-CORE-001-P:** Dado Usuario de Herencia registra una reserva del hotel y consulta su unidad, sin ver SB. Cuando se completa la acción autorizada, entonces se cumple: Un usuario de Herencia no puede registrar un cobro en SB sin permiso Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CORE-001-N:** Dado Cambiar company_id de la solicitud por SB conservando sesion Herencia. Entonces 403 y ninguna escritura ni existencia revelada; evento seguro de denegacion.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F01-T01A` (pruebas), `F01-T01B` (implementación), `F01-T01C` (verificación). Evidencia prevista `evidence/F01/CORE-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### CORE-002 - Participaciones con vigencia
**Historia F01-US02.** Como propietario, necesito participaciones con vigencia para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Organigrama Hoja 1; P1; relación original: CORE-001. Regla heredada preservada: Guardar fuente y fechas sin afirmar actualidad de 2018.

**Entradas y validación:** investor_id, percentage, valid_from/to, source_document_id. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Cerrar vigencia anterior y crear nueva fila en una transacción; porcentaje mayor que cero y no mayor a cien, suma de participaciones verificadas no supera cien por periodo/clase. No completar socios faltantes por inferencia.

**Escenario positivo TC-CORE-002-P:** Dado Participación histórica del 2018 permanece consultable después de cargar una versión respaldada. Cuando se completa la acción autorizada, entonces se cumple: Una modificación futura conserva porcentajes históricos Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CORE-002-N:** Dado Ingresar dos participaciones activas que sumen 110%. Entonces 422 con detalle de total, sin modificar versión previa.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F01-T02A` (pruebas), `F01-T02B` (implementación), `F01-T02C` (verificación). Evidencia prevista `evidence/F01/CORE-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### CORE-003 - Permisos por acción y alcance
**Historia F01-US03.** Como propietario, necesito permisos por acción y alcance para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta de control; P0; relación original: CORE-001. Regla heredada preservada: Menor privilegio por sociedad y unidad.

**Entradas y validación:** role_grant, action, company_id, unit_id. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Autorizar acción y objeto en cada API, exportación y archivo; denegacion por defecto. El rol agregado sólo amplifica permisos expresamente concedidos, nunca por pertenecer al grupo.

**Escenario positivo TC-CORE-003-P:** Dado Aseo recibe sus tareas y estados de habitaciones, no cuenta ni sueldo. Cuando se completa la acción autorizada, entonces se cumple: Aseo no puede consultar salarios, identidades o cuentas ajenas Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CORE-003-N:** Dado Acceso directo por URL a una remuneracion usando token de aseo. Entonces 403 sin payload sensible; exportación tampoco habilitada.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F01-T03A` (pruebas), `F01-T03B` (implementación), `F01-T03C` (verificación). Evidencia prevista `evidence/F01/CORE-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### CORE-004 - Historial y reversos
**Historia F01-US04.** Como propietario, necesito historial y reversos para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta de control; P0; relación original: CORE-003. Regla heredada preservada: Registrar actor, origen, cambio y motivo; no borrar cerrados.

**Entradas y validación:** actor, target, before/after versión, reason, correlation_id. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Operaciones cerradas se corrigen mediante reverso vinculado; actor humano o sistema obligatorio. El audit trail conserva campos modificados sin secretos; cierre no se borra físicamente.

**Escenario positivo TC-CORE-004-P:** Dado Revertir un pago registrado conserva original y referencia al ajuste autorizado. Cuando se completa la acción autorizada, entonces se cumple: Corregir un pago conserva original y reverso Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CORE-004-N:** Dado Recepción intenta DELETE sobre pago de turno cerrado. Entonces 405/409; solicitar ajuste con aprobación, sin cambiar saldo.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F01-T04A` (pruebas), `F01-T04B` (implementación), `F01-T04C` (verificación). Evidencia prevista `evidence/F01/CORE-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### CORE-005 - Fechas y monedas exactas
**Historia F01-US05.** Como propietario, necesito fechas y monedas exactas para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Tarifas; usuario; P0; relación original: CORE-001. Regla heredada preservada: Fecha de servicio separada de registro; moneda y cambio fechados.

**Entradas y validación:** LocalDate, UTC instant, business_date, currency, rate snapshot. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Noches por diferencia de fechas locales, no segundos/86400. Usar enteros monetarios y conversion decimal con fuente, fecha y redondeo congelados al aceptar.

**Escenario positivo TC-CORE-005-P:** Dado Dos noches en cambio de horario siguen siendo dos y el precio no varia por cambio de cotización posterior. Cuando se completa la acción autorizada, entonces se cumple: Cruce horario y cambio posterior no alteran noches ni precio pactado Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CORE-005-N:** Dado Envio de importe con decimales no admitidos para moneda configurada o salida anterior a llegada. Entonces 422, sin redondeo silencioso ni reserva creada.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F01-T05A` (pruebas), `F01-T05B` (implementación), `F01-T05C` (verificación). Evidencia prevista `evidence/F01/CORE-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### CORE-006 - Documentos y proveedores comunes
**Historia F01-US06.** Como propietario, necesito documentos y proveedores comunes para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Inventarios; P0; relación original: CORE-001. Regla heredada preservada: Documentos por emisor, tipo, folio y sociedad.

**Entradas y validación:** issuer_party_id, document_type, folio, company_id, supplier. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Unicidad documental por emisor/tipo/folio/receptor cuando definidos; originales privados enlazados por hash. Tercero global no comparte deudas entre sociedades.

**Escenario positivo TC-CORE-006-P:** Dado Dos proveedores distintos pueden tener factura folio 100 sin conflicto. Cuando se completa la acción autorizada, entonces se cumple: Factura duplicada se detecta sin bloquear otra de diferente emisor Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CORE-006-N:** Dado Importar la misma factura del mismo emisor y sociedad dos veces. Entonces 409 DUPLICATE_DOCUMENT con referencia autorizada a original, sin otra deuda.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F01-T06A` (pruebas), `F01-T06B` (implementación), `F01-T06C` (verificación). Evidencia prevista `evidence/F01/CORE-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SEC-001 - Autenticación reforzada
**Historia F01-US07.** Como propietario, necesito autenticación reforzada para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta control; P0; relación original: CORE-003. Regla heredada preservada: MFA y sesiones para administracion/finanzas.

**Entradas y validación:** issuer subject, MFA, session expiry, revocation. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Proveedor OIDC verificado y sesiones seguras; MFA exigido a roles privilegiados. Acceso de emergencia auditado no exime aprobaciones financieras.

**Escenario positivo TC-SEC-001-P:** Dado Usuario financiero con MFA accede a conciliación dentro de su sociedad. Cuando se completa la acción autorizada, entonces se cumple: Usuario sin segundo factor no ejecuta acciones protegidas Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SEC-001-N:** Dado Token vencido/revocado o sin MFA intenta devolución. Entonces 401/403 y ningun efecto; sesion puede reautenticarse.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F01-T07A` (pruebas), `F01-T07B` (implementación), `F01-T07C` (verificación). Evidencia prevista `evidence/F01/SEC-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SEC-002 - Privacidad y retención
**Historia F01-US08.** Como propietario, necesito privacidad y retención para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** S15; P0; relación original: CORE-003. Regla heredada preservada: Finalidad, minimización, derechos y plazos aprobados.

**Entradas y validación:** data class, purpose, retention, rights request. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Aplicar minimización y permisos por campo; retención aprobada antes de datos reales. Solicitudes verifican identidad y compatibilizan supresión con evidencia obligatoria.

**Escenario positivo TC-SEC-002-P:** Dado Peticion válida muestra datos propios y proceso trazable. Cuando se completa la acción autorizada, entonces se cumple: Solicitud de acceso/supresion usa flujo trazable y respeta retenciones legales Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SEC-002-N:** Dado Solicitante no verificado pide exportación de otra persona. Entonces No entrega; verificar identidad por canal seguro sin revelar existencia.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F01-T08A` (pruebas), `F01-T08B` (implementación), `F01-T08C` (verificación). Evidencia prevista `evidence/F01/SEC-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SEC-003 - Secretos y datos sensibles
**Historia F01-US09.** Como propietario, necesito secretos y datos sensibles para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** S19;S21; P0; relación original: PAY-003. Regla heredada preservada: Sin PAN/CVV, claves o identidades innecesarias en logs/prompts.

**Entradas y validación:** secret references, payment tokens, logs, prompts. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Secretos fuera de repositorio; redaccion de logs; no PAN/CVV ni identificadores personales innecesarios en modelos. Escaneo bloquea entrega y exige revocar secreto expuesto.

**Escenario positivo TC-SEC-003-P:** Dado Logs de pago contienen orden/correlacion y estado, no tarjeta. Cuando se completa la acción autorizada, entonces se cumple: Escaneo y pruebas no encuentran secretos en repo/evidencia Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SEC-003-N:** Dado Subir clave API a código o incluir pasaporte en payload publicitario. Entonces Bloqueo de pipeline/proceso, revocacion y evidencia saneada.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F01-T09A` (pruebas), `F01-T09B` (implementación), `F01-T09C` (verificación). Evidencia prevista `evidence/F01/SEC-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SEC-006 - Instrucciones externas no confiables
**Historia F01-US10.** Como propietario, necesito instrucciones externas no confiables para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** S19; P0; relación original: CORE-003. Regla heredada preservada: Mensajes y documentos no otorgan permisos a agentes.

**Entradas y validación:** untrusted messages, tool schemas, allowlist, actor. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Texto de cliente/documento es dato, no permiso. Herramientas comprueban acceso y argumentos independientemente del modelo.

**Escenario positivo TC-SEC-006-P:** Dado Mensaje malicioso se conserva como consulta y no cambia reglas. Cuando se completa la acción autorizada, entonces se cumple: Resenia maliciosa no cambia beneficiario ni ejecuta herramientas Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SEC-006-N:** Dado Huésped ordena ignorar instrucciones, marcar pagado y enviar bancos. Entonces Herramientas deniegan; bot deriva y no filtra datos.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F01-T10A` (pruebas), `F01-T10B` (implementación), `F01-T10C` (verificación). Evidencia prevista `evidence/F01/SEC-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: group, company, party, ownership, establishment, unit, cost_center, user_account, role_grant, policy, approval, file_object, document, audit_event.

Pantallas: UI-01, UI-02, UI-03; especificadas en `ux/pantallas.csv`. Operaciones propias: createOwnership, grantRole, requestApproval, decideApproval, listCompanies. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: company.activated, access.revoked, approval.decided. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
