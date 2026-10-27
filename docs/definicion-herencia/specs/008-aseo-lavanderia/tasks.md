# Tareas F07

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F07-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F05-T99;F06-T99. Archivos propuestos: `specs/008-aseo-lavanderia/spec.md;specs/008-aseo-lavanderia/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F07-T01A** (OPS-001) Escribir casos TC-OPS-001-P y TC-OPS-001-N: Recibir dos veces el mismo checkout.
  - Depende de: F07-T00. Archivos propuestos: `tests/F07/OPS-001.spec.ts;tests/fixtures/F07/`. Evidencia: TC-OPS-001-P;TC-OPS-001-N.

- [ ] **F07-T01B** (OPS-001) Implementar OPS-001: Generar tarea por causa única; permanencia usa política aprobada y solicitudes, no repeticion indiscriminada. Fechas efectivas controlan prioridad.
  - Depende de: F07-T01A. Archivos propuestos: `src/modules/aseo-lavanderia/ops-001.ts;src/modules/aseo-lavanderia/schemas.ts;db/migrations/`. Evidencia: OPS-001 reglas y migración revisadas.

- [ ] **F07-T01C** (OPS-001) Ejecutar ambos casos y revisar OPS-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F07-T01B. Archivos propuestos: `evidence/F07/OPS-001/;specs/008-aseo-lavanderia/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F07-T02A** (OPS-002) Escribir casos TC-OPS-002-P y TC-OPS-002-N: Dispositivo offline envia tarea reasignada a otra persona.
  - Depende de: F07-T01C. Archivos propuestos: `tests/F07/OPS-002.spec.ts;tests/fixtures/F07/`. Evidencia: TC-OPS-002-P;TC-OPS-002-N.

- [ ] **F07-T02B** (OPS-002) Implementar OPS-002: Asignación requiere trabajador habilitado; ejecución móvil registra identidad y versión. Cola offline limitada a datos operativos y resuelve conflictos al volver.
  - Depende de: F07-T02A. Archivos propuestos: `src/modules/aseo-lavanderia/ops-002.ts;src/modules/aseo-lavanderia/schemas.ts;db/migrations/`. Evidencia: OPS-002 reglas y migración revisadas.

- [ ] **F07-T02C** (OPS-002) Ejecutar ambos casos y revisar OPS-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F07-T02B. Archivos propuestos: `evidence/F07/OPS-002/;specs/008-aseo-lavanderia/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F07-T03A** (OPS-003) Escribir casos TC-OPS-003-P y TC-OPS-003-N: Checklist incompleto o falla de higiene y solicitud de liberar.
  - Depende de: F07-T02C. Archivos propuestos: `tests/F07/OPS-003.spec.ts;tests/fixtures/F07/`. Evidencia: TC-OPS-003-P;TC-OPS-003-N.

- [ ] **F07-T03B** (OPS-003) Implementar OPS-003: Supervisor válida checklist y resultado; falla genera retrabajo vinculado, no nuevo premio por defecto. Liberacion depende también de mantenimiento.
  - Depende de: F07-T03A. Archivos propuestos: `src/modules/aseo-lavanderia/ops-003.ts;src/modules/aseo-lavanderia/schemas.ts;db/migrations/`. Evidencia: OPS-003 reglas y migración revisadas.

- [ ] **F07-T03C** (OPS-003) Ejecutar ambos casos y revisar OPS-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F07-T03B. Archivos propuestos: `evidence/F07/OPS-003/;specs/008-aseo-lavanderia/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F07-T04A** (OPS-004) Escribir casos TC-OPS-004-P y TC-OPS-004-N: Reenviar registro de consumo con mismo device event.
  - Depende de: F07-T03C. Archivos propuestos: `tests/F07/OPS-004.spec.ts;tests/fixtures/F07/`. Evidencia: TC-OPS-004-P;TC-OPS-004-N.

- [ ] **F07-T04B** (OPS-004) Implementar OPS-004: Consumible genera stock out; textil cambia estado. Clave source impide doble descuento. Consumo estimado se etiqueta y luego ajusta con evidencia.
  - Depende de: F07-T04A. Archivos propuestos: `src/modules/aseo-lavanderia/ops-004.ts;src/modules/aseo-lavanderia/schemas.ts;db/migrations/`. Evidencia: OPS-004 reglas y migración revisadas.

- [ ] **F07-T04C** (OPS-004) Ejecutar ambos casos y revisar OPS-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F07-T04B. Archivos propuestos: `evidence/F07/OPS-004/;specs/008-aseo-lavanderia/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F07-T05A** (OPS-005) Escribir casos TC-OPS-005-P y TC-OPS-005-N: Usuario intenta asignar todas las limpiezas comunes a cuarto vacío para mejorar otros margenes.
  - Depende de: F07-T04C. Archivos propuestos: `tests/F07/OPS-005.spec.ts;tests/fixtures/F07/`. Evidencia: TC-OPS-005-P;TC-OPS-005-N.

- [ ] **F07-T05B** (OPS-005) Implementar OPS-005: Cocina, baños y sala tienen tareas y centro comun; distribución posterior usa regla, no habitación arbitraria. La sala puede generar aseo por evento.
  - Depende de: F07-T05A. Archivos propuestos: `src/modules/aseo-lavanderia/ops-005.ts;src/modules/aseo-lavanderia/schemas.ts;db/migrations/`. Evidencia: OPS-005 reglas y migración revisadas.

- [ ] **F07-T05C** (OPS-005) Ejecutar ambos casos y revisar OPS-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F07-T05B. Archivos propuestos: `evidence/F07/OPS-005/;specs/008-aseo-lavanderia/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F07-T06A** (LIN-001) Escribir casos TC-LIN-001-P y TC-LIN-001-N: Restar una pieza del patrimonio cada noche ocupada.
  - Depende de: F07-T05C. Archivos propuestos: `tests/F07/LIN-001.spec.ts;tests/fixtures/F07/`. Evidencia: TC-LIN-001-P;TC-LIN-001-N.

- [ ] **F07-T06B** (LIN-001) Implementar LIN-001: Mantener balance por tipo/estado; piezas enteras y no negativas. Uso, traslado y lavado no son baja definitiva; baja requiere motivo/aprobacion.
  - Depende de: F07-T06A. Archivos propuestos: `src/modules/aseo-lavanderia/lin-001.ts;src/modules/aseo-lavanderia/schemas.ts;db/migrations/`. Evidencia: LIN-001 reglas y migración revisadas.

- [ ] **F07-T06C** (LIN-001) Ejecutar ambos casos y revisar LIN-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F07-T06B. Archivos propuestos: `evidence/F07/LIN-001/;specs/008-aseo-lavanderia/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F07-T07A** (LIN-002) Escribir casos TC-LIN-002-P y TC-LIN-002-N: Intentar cerrar lote con una faltante sin resolución.
  - Depende de: F07-T06C. Archivos propuestos: `tests/F07/LIN-002.spec.ts;tests/fixtures/F07/`. Evidencia: TC-LIN-002-P;TC-LIN-002-N.

- [ ] **F07-T07B** (LIN-002) Implementar LIN-002: Envios/recepciones parciales conservan diferencia; cerrar lote sólo sin pendientes o con ajuste aprobado. Rechazado no se suma a limpio.
  - Depende de: F07-T07A. Archivos propuestos: `src/modules/aseo-lavanderia/lin-002.ts;src/modules/aseo-lavanderia/schemas.ts;db/migrations/`. Evidencia: LIN-002 reglas y migración revisadas.

- [ ] **F07-T07C** (LIN-002) Ejecutar ambos casos y revisar LIN-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F07-T07B. Archivos propuestos: `evidence/F07/LIN-002/;specs/008-aseo-lavanderia/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F07-T08A** (LIN-003) Escribir casos TC-LIN-003-P y TC-LIN-003-N: Tarea marcada no cambiada genera automáticamente dos sábanas usadas.
  - Depende de: F07-T07C. Archivos propuestos: `tests/F07/LIN-003.spec.ts;tests/fixtures/F07/`. Evidencia: TC-LIN-003-P;TC-LIN-003-N.

- [ ] **F07-T08B** (LIN-003) Implementar LIN-003: Sólo el cambio confirmado crea movimiento; habitacion/estadia y ejecutor permiten costo. No usar ocupación como prueba de lavado.
  - Depende de: F07-T08A. Archivos propuestos: `src/modules/aseo-lavanderia/lin-003.ts;src/modules/aseo-lavanderia/schemas.ts;db/migrations/`. Evidencia: LIN-003 reglas y migración revisadas.

- [ ] **F07-T08C** (LIN-003) Ejecutar ambos casos y revisar LIN-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F07-T08B. Archivos propuestos: `evidence/F07/LIN-003/;specs/008-aseo-lavanderia/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F07-T09A** (LIN-004) Escribir casos TC-LIN-004-P y TC-LIN-004-N: Repartos suman 11000 o kilogramo se convierte a piezas sin base.
  - Depende de: F07-T08C. Archivos propuestos: `tests/F07/LIN-004.spec.ts;tests/fixtures/F07/`. Evidencia: TC-LIN-004-P;TC-LIN-004-N.

- [ ] **F07-T09B** (LIN-004) Implementar LIN-004: Distribuir costo real o estimado etiquetado; suma exacta y ajuste residual declarado. Evitar sumar mismo trabajo en lavandería y bolsa salarial.
  - Depende de: F07-T09A. Archivos propuestos: `src/modules/aseo-lavanderia/lin-004.ts;src/modules/aseo-lavanderia/schemas.ts;db/migrations/`. Evidencia: LIN-004 reglas y migración revisadas.

- [ ] **F07-T09C** (LIN-004) Ejecutar ambos casos y revisar LIN-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F07-T09B. Archivos propuestos: `evidence/F07/LIN-004/;specs/008-aseo-lavanderia/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F07-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F07-T09C. Archivos propuestos: `specs/008-aseo-lavanderia/acceptance.md;evidence/F07/`. Evidencia: informe real por build; no autodeclaracion.
