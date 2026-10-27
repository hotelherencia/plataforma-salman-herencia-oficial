# Tareas — Cafetería

**Estado: BLOCKED**. Tareas ejecutables de aclaración/diseño; no constituyen backlog de implementación aprobado. Identificadores locales a `001-cafeteria-mesas-pos`. Dependencias en orden, sin paralelismo supuesto.

- [x] T001 Inventariar fuente, separar alcance y preservar IDs. Evidencia: spec.md y trazabilidad global.
- [x] T002 Derivar modelo conceptual, amenazas y catálogo de aceptación. Evidencia: data-model.md, plan.md y acceptance.md. Esto no equivale a aprobación.
- [ ] T003 Resolver Q-CAF-01: momento de pago y propina; Q-CAF-02: convivencia Eleventa y alcance offline; Q-CAF-03: carta, exportaciones, responsables de compras y sesión de cliente. Responsable: cliente y responsables de operación, con revisor tributario/legal según corresponda. Depende de T002. Salida: respuestas firmadas o registradas con fecha y evidencia.
- [ ] T004 Ratificar alternativas y constitución, actualizar ADR y permisos por empresa. Depende de T003. Salida: decisión y matriz de roles aprobadas.
- [ ] T005 Completar contratos técnicos con ejemplos, errores, idempotencia y compatibilidad. Depende de T004. Salida: contrato revisado por productor y consumidor.
- [ ] T006 Convertir acceptance.md en casos de prueba concretos previos a código, con datos autorizados, carga y fallos. Depende de T005. Salida: escenarios revisados, incluidos ADV-001 a ADV-003.
- [ ] T007 Reejecutar controles documentales y análisis de Spec Kit cuando esté disponible; cerrar hallazgos y generar backlog de desarrollo por historia. Depende de T006. Salida: informe sin bloqueos y aprobación de inicio de siguiente fase.

No se incluye implementar T008 ni tareas de despliegue. Crear tareas de implementación verificables solo tras resolver T003–T007, siguiendo las historias de spec.md.

## Tareas de refinamiento competitivo, previas a implementar

- [x] T101 Comparar historias heredadas y fuentes C02, C04, C05, C07, C08, C09, C10; salida: alias US-CAF, trazabilidad y estado documental explícito.
- [ ] T102 Validar con usuarios las reglas nuevas de FR-015/FR-016, sus datos y excepciones. Depende de T003/T004 y no sustituye sus respuestas. Salida: reglas aprobadas o cambios rechazados con motivo.
- [ ] T103 Precisar casos AC-US-CAF con muestras, permisos, errores y conectores por plan; revisar contratos/modelo. Depende de T102/T005. Salida: fixtures autorizados y matriz de casos esperados, antes de código.
- [ ] T104 Evaluar en demo autorizada las observaciones que faltan, mediante REA solo cuando disponible; conservar evidencia y límites. Depende de Q-REA-01/02 y T103. No cerrar afirmaciones de runtime con documentación.
- [ ] T105 Ejecutar análisis de consistencia oficial al contar con Spec Kit y consolidar backlog por historia ratificada. Depende de T103 y Q-TOOL-01. No iniciar desarrollo dentro de esta misión.
