# Tareas F17

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F17-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F14-T99;F12-T99. Archivos propuestos: `specs/018-contenidos-campanas/spec.md;specs/018-contenidos-campanas/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F17-T01A** (INT-006) Escribir casos TC-INT-006-P y TC-INT-006-N: Agente intenta publicar oferta o activar anuncio sin permiso.
  - Depende de: F17-T00. Archivos propuestos: `tests/F17/INT-006.spec.ts;tests/fixtures/F17/`. Evidencia: TC-INT-006-P;TC-INT-006-N.

- [ ] **F17-T01B** (INT-006) Implementar INT-006: Publicación y publicidad son capacidades separadas; sin aprobación sólo borrador o exportación manual. Gasto requiere límite ratificado.
  - Depende de: F17-T01A. Archivos propuestos: `src/modules/contenidos-campanas/int-006.ts;src/modules/contenidos-campanas/schemas.ts;db/migrations/`. Evidencia: INT-006 reglas y migración revisadas.

- [ ] **F17-T01C** (INT-006) Ejecutar ambos casos y revisar INT-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F17-T01B. Archivos propuestos: `evidence/F17/INT-006/;specs/018-contenidos-campanas/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F17-T02A** (SOC-014) Escribir casos TC-SOC-014-P y TC-SOC-014-N: Modelo aumenta presupuesto para mejorar conversion por iniciativa.
  - Depende de: F17-T01C. Archivos propuestos: `tests/F17/SOC-014.spec.ts;tests/fixtures/F17/`. Evidencia: TC-SOC-014-P;TC-SOC-014-N.

- [ ] **F17-T02B** (SOC-014) Implementar SOC-014: Aprobación cubre importe, fechas y objetivo; aumento o destino distinto requiere nueva aprobación. Parada de emergencia disponible; reportar gasto real y retraso proveedor.
  - Depende de: F17-T02A. Archivos propuestos: `src/modules/contenidos-campanas/soc-014.ts;src/modules/contenidos-campanas/schemas.ts;db/migrations/`. Evidencia: SOC-014 reglas y migración revisadas.

- [ ] **F17-T02C** (SOC-014) Ejecutar ambos casos y revisar SOC-014 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F17-T02B. Archivos propuestos: `evidence/F17/SOC-014/;specs/018-contenidos-campanas/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F17-T03A** (SOC-015) Escribir casos TC-SOC-015-P y TC-SOC-015-N: Proveedor rechaza formato pero interfaz muestra publicada.
  - Depende de: F17-T02C. Archivos propuestos: `tests/F17/SOC-015.spec.ts;tests/fixtures/F17/`. Evidencia: TC-SOC-015-P;TC-SOC-015-N.

- [ ] **F17-T03B** (SOC-015) Implementar SOC-015: Publicación requiere derechos de medios y texto veraz; precio/oferta revalidada. Estado PUBLISHED exige ID/evidencia del proveedor; formatos no soportados pasan a manual.
  - Depende de: F17-T03A. Archivos propuestos: `src/modules/contenidos-campanas/soc-015.ts;src/modules/contenidos-campanas/schemas.ts;db/migrations/`. Evidencia: SOC-015 reglas y migración revisadas.

- [ ] **F17-T03C** (SOC-015) Ejecutar ambos casos y revisar SOC-015 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F17-T03B. Archivos propuestos: `evidence/F17/SOC-015/;specs/018-contenidos-campanas/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F17-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F17-T03C. Archivos propuestos: `specs/018-contenidos-campanas/acceptance.md;evidence/F17/`. Evidencia: informe real por build; no autodeclaracion.
