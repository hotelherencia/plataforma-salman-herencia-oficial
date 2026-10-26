# F21 - Verificación transversal y continuidad

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Aplicar controles desde el inicio y ensayar recuperación e integración de cada capacidad activada; no esperar al final para probar.

Actores: revisor;seguridad;operación;propietario. Entrega candidata: TRANSVERSAL. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Diseñar prueba antes de código -> ejecutar en build identificado -> registrar fallo -> corregir -> revisar independiente -> simular restauración -> emitir GO/NO_GO.

## Reglas que no se pueden violar
No sumar mocks como producción; pruebas descritas no ejecutadas; cobertura de lineas no cobertura de negocio; riesgo crítico bloquea liberacion.

## Condiciones y configuración
Capacidades activadas conocidas; ambientes y responsables reales. Decisiones pendientes: D16, D18, D20, D22, D37, D42, D43. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### SEC-004 - Respaldos y restauración
**Historia F21-US01.** Como revisor, necesito respaldos y restauración para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta control; P0; relación original: CORE-004. Regla heredada preservada: Objetivos aprobados y ensayo completo.

**Entradas y validación:** backup set, encryption, restore target, RPO/RTO. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Copias se prueban en ambiente aislado; restaurar base, archivos y outbox. Verificar datos recientes y conciliar sistemas externos antes de activar consumidores.

**Escenario positivo TC-SEC-004-P:** Dado Ensayo recupera reservas/saldos y opera flujo de prueba. Cuando se completa la acción autorizada, entonces se cumple: Restaurar ambiente de prueba recupera datos y permite operar Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SEC-004-N:** Dado Backup existe pero nunca se ha restaurado o faltan documentos. Entonces No supera gate de continuidad; pendiente hasta ensayo verificable.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F21-T01A` (pruebas), `F21-T01B` (implementación), `F21-T01C` (verificación). Evidencia prevista `evidence/F21/SEC-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SEC-005 - Contingencia sin conexión
**Historia F21-US02.** Como revisor, necesito contingencia sin conexión para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta operativa; P0; relación original: SEC-004. Regla heredada preservada: Datos mínimos protegidos y registro de emergencia.

**Entradas y validación:** protected daily extract, emergency sequence, reentry key. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Contingencia permite registrar hechos mínimos por responsable; no vender online sin autoridad de cupo. Reingreso revisado e idempotente.

**Escenario positivo TC-SEC-005-P:** Dado Recibo de emergencia E001 se carga una vez al volver. Cuando se completa la acción autorizada, entonces se cumple: Reingreso de operaciones de emergencia no duplica pagos Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SEC-005-N:** Dado Reimportar E001 o activar venta offline desde navegador sin cupo fiable. Entonces Duplicado rechazado; venta bloqueada, excepción supervisada.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F21-T02A` (pruebas), `F21-T02B` (implementación), `F21-T02C` (verificación). Evidencia prevista `evidence/F21/SEC-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### AI-006 - Software opera sin IA
**Historia F21-US03.** Como revisor, necesito software opera sin ia para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta arquitectura; P0; relación original: RES-004;PAY-002. Regla heredada preservada: Precios, cobros y disponibilidad son deterministas.

**Entradas y validación:** model availability, deterministic services, handoff. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Disponibilidad, precios, pagos y tareas no requieren modelo para operar. Bot deshabilitado pasa a humano y conserva mensajes.

**Escenario positivo TC-AI-006-P:** Dado Apagar proveedor IA permite reservar por web y cerrar caja. Cuando se completa la acción autorizada, entonces se cumple: Desactivar modelo no impide registrar reserva ni cerrar caja Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-AI-006-N:** Dado Endpoint de reserva depende de una llamada a modelo para calcular cupo. Entonces Prueba falla; separar motor determinista antes de liberar.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F21-T03A` (pruebas), `F21-T03B` (implementación), `F21-T03C` (verificación). Evidencia prevista `evidence/F21/AI-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SEC-009 - Verificación independiente de seguridad
**Historia F21-US04.** Como revisor, necesito verificación independiente de seguridad para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: SEC-001;SEC-003. Regla heredada preservada: Controles ASVS apropiados y versionados; riesgos, secretos, permisos, abuso y evidencia reproducible..

**Entradas y validación:** threat, ASVS applicability, independent evidence, severity. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Mapear controles y pruebas de seguridad; críticos y altos explotables bloquean salida. Aceptacion residual exige responsable y plazo, no decisión del implementador.

**Escenario positivo TC-SEC-009-P:** Dado Revisor reproduce controles de aislamiento y secretos con evidencia. Cuando se completa la acción autorizada, entonces se cumple: Vulnerabilidad crítica sin corregir impide producción aunque todas las pantallas existan. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SEC-009-N:** Dado Interfaz completa pero vulnerabilidad crítica de acceso cruzado abierta. Entonces NO_GO para producción, aunque pruebas visuales pasen.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F21-T04A` (pruebas), `F21-T04B` (implementación), `F21-T04C` (verificación). Evidencia prevista `evidence/F21/SEC-009/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SEC-010 - Cadena de suministro y cambios seguros
**Historia F21-US05.** Como revisor, necesito cadena de suministro y cambios seguros para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: SEC-004;AI-001. Regla heredada preservada: Versiones fijadas, licencias, dependencias, escaneo, migraciones ensayadas y artefactos reproducibles..

**Entradas y validación:** dependency lock, SBOM/license, scan, migration, artifact. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Versiones fijadas y origen verificado; construir artefacto reproducible. Migración ensayada y plan de compensación; rollback no borra cobros posteriores.

**Escenario positivo TC-SEC-010-P:** Dado Build identificado con lock y pruebas de migracion/recuperacion. Cuando se completa la acción autorizada, entonces se cumple: Dependencia insegura detectada detiene paquete; rollback no pierde cobros nuevos. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SEC-010-N:** Dado Dependencia vulnerable o secreto detectado antes de release. Entonces Pipeline bloqueado y remediación; no bypass por agente.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F21-T05A` (pruebas), `F21-T05B` (implementación), `F21-T05C` (verificación). Evidencia prevista `evidence/F21/SEC-010/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### QA-001 - Prueba comercial de extremo a extremo
**Historia F21-US06.** Como revisor, necesito prueba comercial de extremo a extremo para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: SOC-002;PAY-004;FIN-004. Regla heredada preservada: Campaña o consulta, oferta, cupo, pago, reserva, recepción, servicio, devolución y banco..

**Entradas y validación:** journey, fixtures, correlation, returns, bank grouping. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Prueba cruza campaña/consulta, cotización, pago, recepción, servicio, salida y banco, incluida devolución. Evidencia conserva mismo evento y saldos exactos.

**Escenario positivo TC-QA-001-P:** Dado Un ciclo sintético completo produce resultados esperados sin duplicados. Cuando se completa la acción autorizada, entonces se cumple: La misma transacción es trazable sin duplicados y con fallos simulados; no confundir prueba sintética con integración real. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-QA-001-N:** Dado Sólo se prueban pantallas o mocks y se declara integración real. Entonces Gate no superado; exigir adaptador/entorno autorizado y pruebas correspondientes.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F21-T06A` (pruebas), `F21-T06B` (implementación), `F21-T06C` (verificación). Evidencia prevista `evidence/F21/QA-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### QA-002 - Concurrencia, fraude y abuso
**Historia F21-US07.** Como revisor, necesito concurrencia, fraude y abuso para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: RES-004;SOC-010. Regla heredada preservada: Bot, recepción y web compiten por cupos; límites de retenciones y eventos repetidos; precio manipulado..

**Entradas y validación:** concurrency, manipulated amount, holds, event replay. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Probar competencia de bot/web/recepcion al mismo inventario y abuso de retenciones. Límites no sustituyen constraints transaccionales.

**Escenario positivo TC-QA-002-P:** Dado Veinte intentos y precio manipulado no crean sobreventa interna ni descuento falso. Cuando se completa la acción autorizada, entonces se cumple: Dos solicitudes al último cupo interno no crean dos confirmaciones; cliente no puede fijar monto arbitrario. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-QA-002-N:** Dado Desactivar constraint para hacer pasar prueba bajo carga. Entonces Rechazo de cambio y hallazgo crítico; mantener integridad.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F21-T07A` (pruebas), `F21-T07B` (implementación), `F21-T07C` (verificación). Evidencia prevista `evidence/F21/QA-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### QA-003 - Revisión de especificación independiente
**Historia F21-US08.** Como revisor, necesito revisión de especificación independiente para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: GOV-001;GOV-002. Regla heredada preservada: Revisar desde propietario, huésped, trabajador, contador, técnico y atacante; resolver contradicciones..

**Entradas y validación:** coverage, actors, exceptions, dependencies, independent reviewer. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Revisar propietario, huésped, trabajador, contador y técnico; cada no aplica tiene motivo. Hallazgo se cierra con regla/prueba, no frase agregada al prompt.

**Escenario positivo TC-QA-003-P:** Dado Auditoría enlaza requisito a artefactos y senala pendientes reales. Cuando se completa la acción autorizada, entonces se cumple: No se cierra maestro con dependencias sin ID, reglas contradictorias o decisiones críticas ocultas. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-QA-003-N:** Dado Declarar 100% terminado por número de archivos sin revisar contradicciones. Entonces Estado revisión pendiente; reporte honesto de alcance y evidencia.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F21-T08A` (pruebas), `F21-T08B` (implementación), `F21-T08C` (verificación). Evidencia prevista `evidence/F21/QA-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: Artefactos de gobierno, contratos y pruebas, sin tablas de negocio nuevas.

Pantallas: UI-51; especificadas en `ux/pantallas.csv`. Operaciones propias: No API productiva en este paquete; contratos documentales y validaciones internas. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: quality.gate_failed, release.authorized, recovery.completed. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
