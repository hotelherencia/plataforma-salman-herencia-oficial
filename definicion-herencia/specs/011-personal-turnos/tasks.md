# Tareas F10

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F10-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F01-T99. Archivos propuestos: `specs/011-personal-turnos/spec.md;specs/011-personal-turnos/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F10-T01A** (HR-001) Escribir casos TC-HR-001-P y TC-HR-001-N: Importar seis recepcionistas históricos como activos por defecto.
  - Depende de: F10-T00. Archivos propuestos: `tests/F10/HR-001.spec.ts;tests/fixtures/F10/`. Evidencia: TC-HR-001-P;TC-HR-001-N.

- [ ] **F10-T01B** (HR-001) Implementar HR-001: Crear activos sólo desde nómina vigente validada; históricos se almacenan segregados sin permisos. Contrato referencia documento protegido.
  - Depende de: F10-T01A. Archivos propuestos: `src/modules/personal-turnos/hr-001.ts;src/modules/personal-turnos/schemas.ts;db/migrations/`. Evidencia: HR-001 reglas y migración revisadas.

- [ ] **F10-T01C** (HR-001) Ejecutar ambos casos y revisar HR-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F10-T01B. Archivos propuestos: `evidence/F10/HR-001/;specs/011-personal-turnos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F10-T02A** (HR-002) Escribir casos TC-HR-002-P y TC-HR-002-N: Asignar mismo trabajador en dos puestos solapados.
  - Depende de: F10-T01C. Archivos propuestos: `tests/F10/HR-002.spec.ts;tests/fixtures/F10/`. Evidencia: TC-HR-002-P;TC-HR-002-N.

- [ ] **F10-T02B** (HR-002) Implementar HR-002: Cobertura por intervalos, colaciones y reemplazos; validar régimen laboral aprobado, no simple suma semanal. Alertar huecos y solapes por persona.
  - Depende de: F10-T02A. Archivos propuestos: `src/modules/personal-turnos/hr-002.ts;src/modules/personal-turnos/schemas.ts;db/migrations/`. Evidencia: HR-002 reglas y migración revisadas.

- [ ] **F10-T02C** (HR-002) Ejecutar ambos casos y revisar HR-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F10-T02B. Archivos propuestos: `evidence/F10/HR-002/;specs/011-personal-turnos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F10-T03A** (HR-003) Escribir casos TC-HR-003-P y TC-HR-003-N: Convertir automáticamente minutos de aseo en horas extra pagadas.
  - Depende de: F10-T02C. Archivos propuestos: `tests/F10/HR-003.spec.ts;tests/fixtures/F10/`. Evidencia: TC-HR-003-P;TC-HR-003-N.

- [ ] **F10-T03B** (HR-003) Implementar HR-003: Asistencia y tareas separadas; horas extras requieren politica/autorizacion. Toda corrección conserva dato original y motivo.
  - Depende de: F10-T03A. Archivos propuestos: `src/modules/personal-turnos/hr-003.ts;src/modules/personal-turnos/schemas.ts;db/migrations/`. Evidencia: HR-003 reglas y migración revisadas.

- [ ] **F10-T03C** (HR-003) Ejecutar ambos casos y revisar HR-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F10-T03B. Archivos propuestos: `evidence/F10/HR-003/;specs/011-personal-turnos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F10-T04A** (HR-004) Escribir casos TC-HR-004-P y TC-HR-004-N: Dos personas se asignan cada una el 100% de la misma tarea.
  - Depende de: F10-T03C. Archivos propuestos: `tests/F10/HR-004.spec.ts;tests/fixtures/F10/`. Evidencia: TC-HR-004-P;TC-HR-004-N.

- [ ] **F10-T04B** (HR-004) Implementar HR-004: Sólo trabajo real elegible se atribuye; participaciones suman uno. Retrabajo de error no crea premio duplicado y calidad sigue visible.
  - Depende de: F10-T04A. Archivos propuestos: `src/modules/personal-turnos/hr-004.ts;src/modules/personal-turnos/schemas.ts;db/migrations/`. Evidencia: HR-004 reglas y migración revisadas.

- [ ] **F10-T04C** (HR-004) Ejecutar ambos casos y revisar HR-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F10-T04B. Archivos propuestos: `evidence/F10/HR-004/;specs/011-personal-turnos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F10-T05A** (HR-005) Escribir casos TC-HR-005-P y TC-HR-005-N: Cambiar peso de tareas después de aprobar liquidación previa.
  - Depende de: F10-T04C. Archivos propuestos: `tests/F10/HR-005.spec.ts;tests/fixtures/F10/`. Evidencia: TC-HR-005-P;TC-HR-005-N.

- [ ] **F10-T05B** (HR-005) Implementar HR-005: Congelar regla aprobada por período; proponer monto con topes y posibilidad de revisión humana. No sancionar autonomamente por datos de productividad.
  - Depende de: F10-T05A. Archivos propuestos: `src/modules/personal-turnos/hr-005.ts;src/modules/personal-turnos/schemas.ts;db/migrations/`. Evidencia: HR-005 reglas y migración revisadas.

- [ ] **F10-T05C** (HR-005) Ejecutar ambos casos y revisar HR-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F10-T05B. Archivos propuestos: `evidence/F10/HR-005/;specs/011-personal-turnos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F10-T06A** (HR-006) Escribir casos TC-HR-006-P y TC-HR-006-N: Reenviar mismo lote como conceptos nuevos o usar tasas de 2019.
  - Depende de: F10-T05C. Archivos propuestos: `tests/F10/HR-006.spec.ts;tests/fixtures/F10/`. Evidencia: TC-HR-006-P;TC-HR-006-N.

- [ ] **F10-T06B** (HR-006) Implementar HR-006: Exportar sólo conceptos aprobados con trabajador/periodo/id único y totales; no calcular tasas legales históricas ni transferir por el modelo.
  - Depende de: F10-T06A. Archivos propuestos: `src/modules/personal-turnos/hr-006.ts;src/modules/personal-turnos/schemas.ts;db/migrations/`. Evidencia: HR-006 reglas y migración revisadas.

- [ ] **F10-T06C** (HR-006) Ejecutar ambos casos y revisar HR-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F10-T06B. Archivos propuestos: `evidence/F10/HR-006/;specs/011-personal-turnos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F10-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F10-T06C. Archivos propuestos: `specs/011-personal-turnos/acceptance.md;evidence/F10/`. Evidencia: informe real por build; no autodeclaracion.
