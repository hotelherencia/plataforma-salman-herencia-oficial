# Tareas — Constructora y control de obra

**Estado: BLOCKED**. Tareas ejecutables de aclaración/diseño; no constituyen backlog de implementación aprobado. Identificadores locales a `004-constructora-obra`. Dependencias en orden, sin paralelismo supuesto.

- [x] T001 Inventariar fuente, separar alcance y preservar IDs. Evidencia: spec.md y trazabilidad global.
- [x] T002 Derivar modelo conceptual, amenazas y catálogo de aceptación. Evidencia: data-model.md, plan.md y acceptance.md. Esto no equivale a aprobación.
- [ ] T003 Resolver Q-OBR-01: obras propias o terceros, presupuesto y módulo previo no entregado; Q-OBR-02: unidad del avance, calendario y umbral; Q-OBR-03: aprobadores, compras, seguridad e inspecciones. Responsable: cliente y responsables de operación, con revisor tributario/legal según corresponda. Depende de T002. Salida: respuestas firmadas o registradas con fecha y evidencia.
- [ ] T004 Ratificar alternativas y constitución, actualizar ADR y permisos por empresa. Depende de T003. Salida: decisión y matriz de roles aprobadas.
- [ ] T005 Completar contratos técnicos con ejemplos, errores, idempotencia y compatibilidad. Depende de T004. Salida: contrato revisado por productor y consumidor.
- [ ] T006 Convertir acceptance.md en casos de prueba concretos previos a código, con datos autorizados, carga y fallos. Depende de T005. Salida: escenarios revisados, incluidos ADV-001 a ADV-003.
- [ ] T007 Reejecutar controles documentales y análisis de Spec Kit cuando esté disponible; cerrar hallazgos y generar backlog de desarrollo por historia. Depende de T006. Salida: informe sin bloqueos y aprobación de inicio de siguiente fase.

No se incluye implementar T008 ni tareas de despliegue. Crear tareas de implementación verificables solo tras resolver T003–T007, siguiendo las historias de spec.md.

## Tareas de refinamiento competitivo, previas a implementar

- [x] T101 Comparar historias heredadas y fuentes O01, O02, O03, O05, O06, O07, O08, O09; salida: alias US-OBR, trazabilidad y estado documental explícito.
- [ ] T102 Validar con usuarios las reglas nuevas de FR-019/FR-020, sus datos y excepciones. Depende de T003/T004 y no sustituye sus respuestas. Salida: reglas aprobadas o cambios rechazados con motivo.
- [ ] T103 Precisar casos AC-US-OBR con muestras, permisos, errores y conectores por plan; revisar contratos/modelo. Depende de T102/T005. Salida: fixtures autorizados y matriz de casos esperados, antes de código.
- [ ] T104 Evaluar en demo autorizada las observaciones que faltan, mediante REA solo cuando disponible; conservar evidencia y límites. Depende de Q-REA-01/02 y T103. No cerrar afirmaciones de runtime con documentación.
- [ ] T105 Ejecutar análisis de consistencia oficial al contar con Spec Kit y consolidar backlog por historia ratificada. Depende de T103 y Q-TOOL-01. No iniciar desarrollo dentro de esta misión.

## Preparación derivada de investigación adicional

- [x] T201 Investigar y reconstruir RF-OBR-01, RF-OBR-02, RF-OBR-03, RF-OBR-04 desde fuentes primarias y registrar límites. Salida: criterios propuestos y trazabilidad adicional.
- [ ] T202 Ratificar estados, cantidades, permisos y excepciones de FR-021, FR-022, FR-023 con responsables de negocio y legales/tributarios cuando aplique. Depende de T003/T102. Salida: ejemplos aprobados con fuente de verdad y rechazo explícitos.
- [ ] T203 Revisar invariantes y contratos lógicos con casos de timeout, repetición, parcialidad y corrección; conservar resultado esperado por cada AC nuevo. Depende de T202/T005. Salida: fixtures autorizados y contrato por proveedor, sin endpoint supuesto.
- [ ] T204 Comprobar conducta en demo/entorno propio autorizado con REA cuando esté disponible; conservar captura y límites. Depende de Q-REA-01/02/03. Documentación pública no cierra esta tarea.
- [ ] T205 Revisar costos y latencias por etapa, no solo resolución final, y actualizar gate de siguiente fase. Depende de T203 y decisiones Q del dominio. Salida: plan de evaluación y backlog de desarrollo ratificado posteriormente.
