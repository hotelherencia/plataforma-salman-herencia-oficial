# Tareas F22

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F22-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F01-T99. Archivos propuestos: `specs/023-evolucion-grupo/spec.md;specs/023-evolucion-grupo/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F22-T01A** (CORE-007) Escribir casos TC-CORE-007-P y TC-CORE-007-N: Futura aplicación pide acceso global por conocer party_id.
  - Depende de: F22-T00. Archivos propuestos: `tests/F22/CORE-007.spec.ts;tests/fixtures/F22/`. Evidencia: TC-CORE-007-P;TC-CORE-007-N.

- [ ] **F22-T01B** (CORE-007) Implementar CORE-007: Futuros módulos intercambian referencias y hechos autorizados; no comparten datos personales por proveedor comun. Cafe completo y otras verticales son fase posterior.
  - Depende de: F22-T01A. Archivos propuestos: `src/modules/evolucion-grupo/core-007.ts;src/modules/evolucion-grupo/schemas.ts;db/migrations/`. Evidencia: CORE-007 reglas y migración revisadas.

- [ ] **F22-T01C** (CORE-007) Ejecutar ambos casos y revisar CORE-007 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F22-T01B. Archivos propuestos: `evidence/F22/CORE-007/;specs/023-evolucion-grupo/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F22-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F22-T01C. Archivos propuestos: `specs/023-evolucion-grupo/acceptance.md;evidence/F22/`. Evidencia: informe real por build; no autodeclaracion.
