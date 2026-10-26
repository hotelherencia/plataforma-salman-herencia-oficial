# F00 - Gobierno, arquitectura base y entorno seguro

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Marco de datos, contratos, pruebas, ambientes y control de agentes; no confundirlo con una aplicación de hotel terminada.

Actores: propietario;lider técnico;revisor;agentes limitados. Entrega candidata: E0. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Registrar versión de especificación -> abrir orden de trabajo -> aislar rama/entorno -> implementar pruebas y cambios -> revisar -> integrar artefacto -> registrar evidencia.

## Reglas que no se pueden violar
No activar servicios reales ni gastar por recibir el ZIP; versiones y fuentes fijadas; implementador no autoaprueba; detener tres ciclos sin converger propuestos.

## Condiciones y configuración
Repositorio y acceso aprobados; stack ADR-001 revisado; datos sintéticos. Decisiones pendientes: D18, D37, D38, D39, D40, D42, D43, D44, D45. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### AI-001 - Paquetes con contrato de trabajo
**Historia F00-US01.** Como propietario, necesito paquetes con contrato de trabajo para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; S20; P0; relación original: -. Regla heredada preservada: Requisito, archivos permitidos, pruebas, presupuesto y revisor.

**Entradas y validación:** work order, baseline, allowed files, tests, limits. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Paquete explícita fuente, dependencias, herramientas, pruebas y revisor; no iniciar con alcance ambiguo o permisos abiertos.

**Escenario positivo TC-AI-001-P:** Dado Orden válida habilita una tarea delimitada en entorno de prueba autorizado. Cuando se completa la acción autorizada, entonces se cumple: Paquete sin entrada o prueba de salida no se ejecuta Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-AI-001-N:** Dado Orden sin evidencia de aprobación o sin pruebas de salida. Entonces No implementa; entrega diagnóstico de requisito faltante.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F00-T01A` (pruebas), `F00-T01B` (implementación), `F00-T01C` (verificación). Evidencia prevista `evidence/F00/AI-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### AI-002 - Revisión independiente
**Historia F00-US02.** Como propietario, necesito revisión independiente para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; propuesta; P0; relación original: AI-001. Regla heredada preservada: Implementador distinto de funcion revisora.

**Entradas y validación:** implementer, reviewer, evidence, findings. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Revisión separada y reproducible; si misma instancia hace ambos roles se declara limitacion y no se afirma independencia. Humano ratifica gate sensible.

**Escenario positivo TC-AI-002-P:** Dado Revisor del equipo reproduce prueba y anota hallazgos. Cuando se completa la acción autorizada, entonces se cumple: Revisor reproduce pruebas y registra hallazgos antes de aceptar Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-AI-002-N:** Dado Implementador marca su checklist independiente como aprobado. Entonces Gate pendiente; se exige otro revisor identificado.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F00-T02A` (pruebas), `F00-T02B` (implementación), `F00-T02C` (verificación). Evidencia prevista `evidence/F00/AI-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### AI-003 - Evidencia y estados reales
**Historia F00-US03.** Como propietario, necesito evidencia y estados reales para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta control; P0; relación original: AI-002. Regla heredada preservada: Separar documentado, implementado, probado y aceptado.

**Entradas y validación:** spec/code/test/acceptance status, build, run log. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Estados independientes, evidencia para cada afirmacion. Mock, sandbox y producción tienen etiquetas no intercambiables.

**Escenario positivo TC-AI-003-P:** Dado Feature documentada conserva implementación NO_IMPLEMENTADO. Cuando se completa la acción autorizada, entonces se cumple: Mock no figura como integración de producción verificada Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-AI-003-N:** Dado Declarar integrado porque existe un adapter simulado. Entonces Validación bloquea cambio de estado sin evidencia de capacidad real.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F00-T03A` (pruebas), `F00-T03B` (implementación), `F00-T03C` (verificación). Evidencia prevista `evidence/F00/AI-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### AI-004 - Aprobaciones sensibles humanas
**Historia F00-US04.** Como propietario, necesito aprobaciones sensibles humanas para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** S19;S21; P0; relación original: AI-001. Regla heredada preservada: Sin pagos, contratos, DTE o despliegue autonomo.

**Entradas y validación:** action scope, approval, money/vendor/production. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Autorización de construir no autoriza pagos, contratos, publicidad, DTE o despliegue sensible. Aprobación de flujo ordinario puede permitir ejecución determinista dentro de límites.

**Escenario positivo TC-AI-004-P:** Dado Compra propuesta queda pendiente para responsable. Cuando se completa la acción autorizada, entonces se cumple: Agente solicita autorización antes de acción sensible Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-AI-004-N:** Dado Agente intenta pagar proveedor por mensaje externo. Entonces Herramienta inexistente o denegada; incidente de seguridad.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F00-T04A` (pruebas), `F00-T04B` (implementación), `F00-T04C` (verificación). Evidencia prevista `evidence/F00/AI-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### AI-005 - Presupuesto y acceso acotado
**Historia F00-US05.** Como propietario, necesito presupuesto y acceso acotado para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta control; P0; relación original: AI-001. Regla heredada preservada: Límites por ejecución, permisos y registro.

**Entradas y validación:** budget, maximum cycles, tool scope, stop condition. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Presupuesto y límite por ejecución; propuesta tres ciclos correctivos. Sin progreso, credenciales o autorización se detiene con estado guardado.

**Escenario positivo TC-AI-005-P:** Dado Al llegar límite el agente conserva archivos/evidencias y reporta bloqueo. Cuando se completa la acción autorizada, entonces se cumple: Al llegar al límite para y reporta estado sin bucle indefinido Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-AI-005-N:** Dado Bucle correctivo sigue consumiendo servicios sin límite aprobado. Entonces Parada y escalamiento; no ejecución asincrona prometida.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F00-T05A` (pruebas), `F00-T05B` (implementación), `F00-T05C` (verificación). Evidencia prevista `evidence/F00/AI-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### GOV-001 - Cobertura y trazabilidad de especificación
**Historia F00-US06.** Como propietario, necesito cobertura y trazabilidad de especificación para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: AI-003. Regla heredada preservada: Necesidad-regla-dato-pantalla-contrato-prueba; sin huérfanos y con pendientes visibles..

**Entradas y validación:** requirement IDs, source, mappings, evidence status. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Cada necesidad se relaciona a reglas/datos/interfaz/prueba; no contar padres e hijos como avance doble. Especificado no implica implementado.

**Escenario positivo TC-GOV-001-P:** Dado 153 IDs preservados tienen refinamiento local y pruebas propuestas. Cuando se completa la acción autorizada, entonces se cumple: Requisito sin excepción o criterio verificable bloquea declaracion de listo para construir. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-GOV-001-N:** Dado Requisito sin caso negativo ni dependencia identificada se marca listo. Entonces Validador/auditoria deja brecha y gate documental pendiente.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F00-T06A` (pruebas), `F00-T06B` (implementación), `F00-T06C` (verificación). Evidencia prevista `evidence/F00/GOV-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### GOV-002 - Registro de dependencias externas
**Historia F00-US07.** Como propietario, necesito registro de dependencias externas para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: INT-001;SOC-001. Regla heredada preservada: Documentado, cuenta comprobada, permiso, entorno, prueba y producción son estados distintos por capacidad..

**Entradas y validación:** provider/capability, docs/account/permission/test states. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Estado por capacidad y cuenta; acceso puede caducar. Registro público de API no prueba contrato ni producción. Gate de activación exige evidencia actual.

**Escenario positivo TC-GOV-002-P:** Dado Conector documentado permanece DOCUMENTED hasta cuenta y prueba. Cuando se completa la acción autorizada, entonces se cumple: Documentación de API sin credenciales figura como no habilitada. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-GOV-002-N:** Dado Copiar URL de proveedor y marcar PRODUCCION_VERIFICADA. Entonces Bloqueo de estado por evidencia faltante.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F00-T07A` (pruebas), `F00-T07B` (implementación), `F00-T07C` (verificación). Evidencia prevista `evidence/F00/GOV-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: outbox_event.

Pantallas: UI-00; especificadas en `ux/pantallas.csv`. Operaciones propias: No API productiva en este paquete; contratos documentales y validaciones internas. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: work_package.review_requested, release.candidate. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
