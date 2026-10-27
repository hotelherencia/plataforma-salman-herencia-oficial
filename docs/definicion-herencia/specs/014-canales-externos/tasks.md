# Tareas F13

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F13-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F03-T99;F04-T99. Archivos propuestos: `specs/014-canales-externos/spec.md;specs/014-canales-externos/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F13-T01A** (INT-001) Escribir casos TC-INT-001-P y TC-INT-001-N: Sólo existe documentación pública sin cuenta ni permisos.
  - Depende de: F13-T00. Archivos propuestos: `tests/F13/INT-001.spec.ts;tests/fixtures/F13/`. Evidencia: TC-INT-001-P;TC-INT-001-N.

- [ ] **F13-T01B** (INT-001) Implementar INT-001: Adoptar proveedor habilitado y probar por capacidad; contrato local no presume endpoint externo. En producción probar operación autorizada con evidencia.
  - Depende de: F13-T01A. Archivos propuestos: `src/modules/canales-externos/int-001.ts;src/modules/canales-externos/schemas.ts;db/migrations/`. Evidencia: INT-001 reglas y migración revisadas.

- [ ] **F13-T01C** (INT-001) Ejecutar ambos casos y revisar INT-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F13-T01B. Archivos propuestos: `evidence/F13/INT-001/;specs/014-canales-externos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F13-T02A** (INT-002) Escribir casos TC-INT-002-P y TC-INT-002-N: Evento mismo ID con contenido diferente.
  - Depende de: F13-T01C. Archivos propuestos: `tests/F13/INT-002.spec.ts;tests/fixtures/F13/`. Evidencia: TC-INT-002-P;TC-INT-002-N.

- [ ] **F13-T02B** (INT-002) Implementar INT-002: Persistir inbox antes de procesar; versión obsoleta no retrocede estado. Sin versión fiable consultar fuente y revisar conflicto.
  - Depende de: F13-T02A. Archivos propuestos: `src/modules/canales-externos/int-002.ts;src/modules/canales-externos/schemas.ts;db/migrations/`. Evidencia: INT-002 reglas y migración revisadas.

- [ ] **F13-T02C** (INT-002) Ejecutar ambos casos y revisar INT-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F13-T02B. Archivos propuestos: `evidence/F13/INT-002/;specs/014-canales-externos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F13-T03A** (INT-003) Escribir casos TC-INT-003-P y TC-INT-003-N: Conector falla pero interfaz sigue mostrando sincronizado/verde.
  - Depende de: F13-T02C. Archivos propuestos: `tests/F13/INT-003.spec.ts;tests/fixtures/F13/`. Evidencia: TC-INT-003-P;TC-INT-003-N.

- [ ] **F13-T03B** (INT-003) Implementar INT-003: Mostrar demora y falla por capacidad; activar contingencia aprobada y reconciliar al volver. No confirmar sincronización por envio sin acuse.
  - Depende de: F13-T03A. Archivos propuestos: `src/modules/canales-externos/int-003.ts;src/modules/canales-externos/schemas.ts;db/migrations/`. Evidencia: INT-003 reglas y migración revisadas.

- [ ] **F13-T03C** (INT-003) Ejecutar ambos casos y revisar INT-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F13-T03B. Archivos propuestos: `evidence/F13/INT-003/;specs/014-canales-externos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F13-T04A** (SOC-019) Escribir casos TC-SOC-019-P y TC-SOC-019-N: Anunciar sincronización de tarifas sin contrato/feed funcional.
  - Depende de: F13-T03C. Archivos propuestos: `tests/F13/SOC-019.spec.ts;tests/fixtures/F13/`. Evidencia: TC-SOC-019-P;TC-SOC-019-N.

- [ ] **F13-T04B** (SOC-019) Implementar SOC-019: Enlace público es distinto de feed de precios. Activar Google Hotels u otro canal sólo con proveedor/permiso y mapeo probados.
  - Depende de: F13-T04A. Archivos propuestos: `src/modules/canales-externos/soc-019.ts;src/modules/canales-externos/schemas.ts;db/migrations/`. Evidencia: SOC-019 reglas y migración revisadas.

- [ ] **F13-T04C** (SOC-019) Ejecutar ambos casos y revisar SOC-019 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F13-T04B. Archivos propuestos: `evidence/F13/SOC-019/;specs/014-canales-externos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F13-T05A** (INT-007) Escribir casos TC-INT-007-P y TC-INT-007-N: Conector sigue verde porque servidor HTTP responde.
  - Depende de: F13-T04C. Archivos propuestos: `tests/F13/INT-007.spec.ts;tests/fixtures/F13/`. Evidencia: TC-INT-007-P;TC-INT-007-N.

- [ ] **F13-T05B** (INT-007) Implementar INT-007: Salud por capacidad y cuenta con umbrales y runbook; estado basado en evidencia, no sólo proceso encendido. Recuperación verifica backlog y reconciliacion.
  - Depende de: F13-T05A. Archivos propuestos: `src/modules/canales-externos/int-007.ts;src/modules/canales-externos/schemas.ts;db/migrations/`. Evidencia: INT-007 reglas y migración revisadas.

- [ ] **F13-T05C** (INT-007) Ejecutar ambos casos y revisar INT-007 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F13-T05B. Archivos propuestos: `evidence/F13/INT-007/;specs/014-canales-externos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F13-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F13-T05C. Archivos propuestos: `specs/014-canales-externos/acceptance.md;evidence/F13/`. Evidencia: informe real por build; no autodeclaracion.
