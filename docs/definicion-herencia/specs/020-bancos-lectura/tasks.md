# Tareas F19

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F19-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F11-T99. Archivos propuestos: `specs/020-bancos-lectura/spec.md;specs/020-bancos-lectura/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F19-T01A** (INT-004) Escribir casos TC-INT-004-P y TC-INT-004-N: Revocar permiso mientras hay job programado.
  - Depende de: F19-T00. Archivos propuestos: `tests/F19/INT-004.spec.ts;tests/fixtures/F19/`. Evidencia: TC-INT-004-P;TC-INT-004-N.

- [ ] **F19-T01B** (INT-004) Implementar INT-004: Sólo lectura consentida; importaciones por API usan mismo normalizador y deduplicacion que archivos. Revocacion detiene tareas y elimina credencial activa.
  - Depende de: F19-T01A. Archivos propuestos: `src/modules/bancos-lectura/int-004.ts;src/modules/bancos-lectura/schemas.ts;db/migrations/`. Evidencia: INT-004 reglas y migración revisadas.

- [ ] **F19-T01C** (INT-004) Ejecutar ambos casos y revisar INT-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F19-T01B. Archivos propuestos: `evidence/F19/INT-004/;specs/020-bancos-lectura/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F19-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F19-T01C. Archivos propuestos: `specs/020-bancos-lectura/acceptance.md;evidence/F19/`. Evidencia: informe real por build; no autodeclaracion.
