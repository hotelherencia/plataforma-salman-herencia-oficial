# Tareas F21

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F21-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F00-T99. Archivos propuestos: `specs/022-calidad-continuidad/spec.md;specs/022-calidad-continuidad/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F21-T01A** (SEC-004) Escribir casos TC-SEC-004-P y TC-SEC-004-N: Backup existe pero nunca se ha restaurado o faltan documentos.
  - Depende de: F21-T00. Archivos propuestos: `tests/F21/SEC-004.spec.ts;tests/fixtures/F21/`. Evidencia: TC-SEC-004-P;TC-SEC-004-N.

- [ ] **F21-T01B** (SEC-004) Implementar SEC-004: Copias se prueban en ambiente aislado; restaurar base, archivos y outbox. Verificar datos recientes y conciliar sistemas externos antes de activar consumidores.
  - Depende de: F21-T01A. Archivos propuestos: `src/modules/calidad-continuidad/sec-004.ts;src/modules/calidad-continuidad/schemas.ts;db/migrations/`. Evidencia: SEC-004 reglas y migración revisadas.

- [ ] **F21-T01C** (SEC-004) Ejecutar ambos casos y revisar SEC-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F21-T01B. Archivos propuestos: `evidence/F21/SEC-004/;specs/022-calidad-continuidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F21-T02A** (SEC-005) Escribir casos TC-SEC-005-P y TC-SEC-005-N: Reimportar E001 o activar venta offline desde navegador sin cupo fiable.
  - Depende de: F21-T01C. Archivos propuestos: `tests/F21/SEC-005.spec.ts;tests/fixtures/F21/`. Evidencia: TC-SEC-005-P;TC-SEC-005-N.

- [ ] **F21-T02B** (SEC-005) Implementar SEC-005: Contingencia permite registrar hechos mínimos por responsable; no vender online sin autoridad de cupo. Reingreso revisado e idempotente.
  - Depende de: F21-T02A. Archivos propuestos: `src/modules/calidad-continuidad/sec-005.ts;src/modules/calidad-continuidad/schemas.ts;db/migrations/`. Evidencia: SEC-005 reglas y migración revisadas.

- [ ] **F21-T02C** (SEC-005) Ejecutar ambos casos y revisar SEC-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F21-T02B. Archivos propuestos: `evidence/F21/SEC-005/;specs/022-calidad-continuidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F21-T03A** (AI-006) Escribir casos TC-AI-006-P y TC-AI-006-N: Endpoint de reserva depende de una llamada a modelo para calcular cupo.
  - Depende de: F21-T02C. Archivos propuestos: `tests/F21/AI-006.spec.ts;tests/fixtures/F21/`. Evidencia: TC-AI-006-P;TC-AI-006-N.

- [ ] **F21-T03B** (AI-006) Implementar AI-006: Disponibilidad, precios, pagos y tareas no requieren modelo para operar. Bot deshabilitado pasa a humano y conserva mensajes.
  - Depende de: F21-T03A. Archivos propuestos: `src/modules/calidad-continuidad/ai-006.ts;src/modules/calidad-continuidad/schemas.ts;db/migrations/`. Evidencia: AI-006 reglas y migración revisadas.

- [ ] **F21-T03C** (AI-006) Ejecutar ambos casos y revisar AI-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F21-T03B. Archivos propuestos: `evidence/F21/AI-006/;specs/022-calidad-continuidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F21-T04A** (SEC-009) Escribir casos TC-SEC-009-P y TC-SEC-009-N: Interfaz completa pero vulnerabilidad crítica de acceso cruzado abierta.
  - Depende de: F21-T03C. Archivos propuestos: `tests/F21/SEC-009.spec.ts;tests/fixtures/F21/`. Evidencia: TC-SEC-009-P;TC-SEC-009-N.

- [ ] **F21-T04B** (SEC-009) Implementar SEC-009: Mapear controles y pruebas de seguridad; críticos y altos explotables bloquean salida. Aceptacion residual exige responsable y plazo, no decisión del implementador.
  - Depende de: F21-T04A. Archivos propuestos: `src/modules/calidad-continuidad/sec-009.ts;src/modules/calidad-continuidad/schemas.ts;db/migrations/`. Evidencia: SEC-009 reglas y migración revisadas.

- [ ] **F21-T04C** (SEC-009) Ejecutar ambos casos y revisar SEC-009 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F21-T04B. Archivos propuestos: `evidence/F21/SEC-009/;specs/022-calidad-continuidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F21-T05A** (SEC-010) Escribir casos TC-SEC-010-P y TC-SEC-010-N: Dependencia vulnerable o secreto detectado antes de release.
  - Depende de: F21-T04C. Archivos propuestos: `tests/F21/SEC-010.spec.ts;tests/fixtures/F21/`. Evidencia: TC-SEC-010-P;TC-SEC-010-N.

- [ ] **F21-T05B** (SEC-010) Implementar SEC-010: Versiones fijadas y origen verificado; construir artefacto reproducible. Migración ensayada y plan de compensación; rollback no borra cobros posteriores.
  - Depende de: F21-T05A. Archivos propuestos: `src/modules/calidad-continuidad/sec-010.ts;src/modules/calidad-continuidad/schemas.ts;db/migrations/`. Evidencia: SEC-010 reglas y migración revisadas.

- [ ] **F21-T05C** (SEC-010) Ejecutar ambos casos y revisar SEC-010 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F21-T05B. Archivos propuestos: `evidence/F21/SEC-010/;specs/022-calidad-continuidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F21-T06A** (QA-001) Escribir casos TC-QA-001-P y TC-QA-001-N: Sólo se prueban pantallas o mocks y se declara integración real.
  - Depende de: F21-T05C. Archivos propuestos: `tests/F21/QA-001.spec.ts;tests/fixtures/F21/`. Evidencia: TC-QA-001-P;TC-QA-001-N.

- [ ] **F21-T06B** (QA-001) Implementar QA-001: Prueba cruza campaña/consulta, cotización, pago, recepción, servicio, salida y banco, incluida devolución. Evidencia conserva mismo evento y saldos exactos.
  - Depende de: F21-T06A. Archivos propuestos: `src/modules/calidad-continuidad/qa-001.ts;src/modules/calidad-continuidad/schemas.ts;db/migrations/`. Evidencia: QA-001 reglas y migración revisadas.

- [ ] **F21-T06C** (QA-001) Ejecutar ambos casos y revisar QA-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F21-T06B. Archivos propuestos: `evidence/F21/QA-001/;specs/022-calidad-continuidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F21-T07A** (QA-002) Escribir casos TC-QA-002-P y TC-QA-002-N: Desactivar constraint para hacer pasar prueba bajo carga.
  - Depende de: F21-T06C. Archivos propuestos: `tests/F21/QA-002.spec.ts;tests/fixtures/F21/`. Evidencia: TC-QA-002-P;TC-QA-002-N.

- [ ] **F21-T07B** (QA-002) Implementar QA-002: Probar competencia de bot/web/recepcion al mismo inventario y abuso de retenciones. Límites no sustituyen constraints transaccionales.
  - Depende de: F21-T07A. Archivos propuestos: `src/modules/calidad-continuidad/qa-002.ts;src/modules/calidad-continuidad/schemas.ts;db/migrations/`. Evidencia: QA-002 reglas y migración revisadas.

- [ ] **F21-T07C** (QA-002) Ejecutar ambos casos y revisar QA-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F21-T07B. Archivos propuestos: `evidence/F21/QA-002/;specs/022-calidad-continuidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F21-T08A** (QA-003) Escribir casos TC-QA-003-P y TC-QA-003-N: Declarar 100% terminado por número de archivos sin revisar contradicciones.
  - Depende de: F21-T07C. Archivos propuestos: `tests/F21/QA-003.spec.ts;tests/fixtures/F21/`. Evidencia: TC-QA-003-P;TC-QA-003-N.

- [ ] **F21-T08B** (QA-003) Implementar QA-003: Revisar propietario, huésped, trabajador, contador y técnico; cada no aplica tiene motivo. Hallazgo se cierra con regla/prueba, no frase agregada al prompt.
  - Depende de: F21-T08A. Archivos propuestos: `src/modules/calidad-continuidad/qa-003.ts;src/modules/calidad-continuidad/schemas.ts;db/migrations/`. Evidencia: QA-003 reglas y migración revisadas.

- [ ] **F21-T08C** (QA-003) Ejecutar ambos casos y revisar QA-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F21-T08B. Archivos propuestos: `evidence/F21/QA-003/;specs/022-calidad-continuidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F21-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F21-T08C. Archivos propuestos: `specs/022-calidad-continuidad/acceptance.md;evidence/F21/`. Evidencia: informe real por build; no autodeclaracion.
