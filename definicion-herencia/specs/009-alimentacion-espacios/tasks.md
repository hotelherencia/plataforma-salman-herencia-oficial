# Tareas F08

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F08-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F05-T99;F06-T99. Archivos propuestos: `specs/009-alimentacion-espacios/spec.md;specs/009-alimentacion-espacios/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F08-T01A** (FNB-001) Escribir casos TC-FNB-001-P y TC-FNB-001-N: Dos reservas duplicadas del mismo pasajero/dia causan doble derecho para misma estadía.
  - Depende de: F08-T00. Archivos propuestos: `tests/F08/FNB-001.spec.ts;tests/fixtures/F08/`. Evidencia: TC-FNB-001-P;TC-FNB-001-N.

- [ ] **F08-T01B** (FNB-001) Implementar FNB-001: Propuesta: manana siguiente a noche prestada, incluida salida; excepciones aprobadas se versionan. Previsión no descuenta ingredientes ni marca servido.
  - Depende de: F08-T01A. Archivos propuestos: `src/modules/alimentacion-espacios/fnb-001.ts;src/modules/alimentacion-espacios/schemas.ts;db/migrations/`. Evidencia: FNB-001 reglas y migración revisadas.

- [ ] **F08-T01C** (FNB-001) Ejecutar ambos casos y revisar FNB-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F08-T01B. Archivos propuestos: `evidence/F08/FNB-001/;specs/009-alimentacion-espacios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F08-T02A** (FNB-002) Escribir casos TC-FNB-002-P y TC-FNB-002-N: No-show se marca servido automáticamente o merma se borra.
  - Depende de: F08-T01C. Archivos propuestos: `tests/F08/FNB-002.spec.ts;tests/fixtures/F08/`. Evidencia: TC-FNB-002-P;TC-FNB-002-N.

- [ ] **F08-T02B** (FNB-002) Implementar FNB-002: Descontar ingredientes al producir confirmado; servir consume porción, no ingredientes otra vez. Distinguir previsto, producido, servido y merma.
  - Depende de: F08-T02A. Archivos propuestos: `src/modules/alimentacion-espacios/fnb-002.ts;src/modules/alimentacion-espacios/schemas.ts;db/migrations/`. Evidencia: FNB-002 reglas y migración revisadas.

- [ ] **F08-T02C** (FNB-002) Ejecutar ambos casos y revisar FNB-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F08-T02B. Archivos propuestos: `evidence/F08/FNB-002/;specs/009-alimentacion-espacios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F08-T03A** (FNB-003) Escribir casos TC-FNB-003-P y TC-FNB-003-N: Unidad incompatible como litros contra unidades sin factor aprobado.
  - Depende de: F08-T02C. Archivos propuestos: `tests/F08/FNB-003.spec.ts;tests/fixtures/F08/`. Evidencia: TC-FNB-003-P;TC-FNB-003-N.

- [ ] **F08-T03B** (FNB-003) Implementar FNB-003: Usar unidad base y conversion exacta; cambios conservan receta utilizada. Sustitución de ingrediente requiere equivalencia y alérgeno revisado.
  - Depende de: F08-T03A. Archivos propuestos: `src/modules/alimentacion-espacios/fnb-003.ts;src/modules/alimentacion-espacios/schemas.ts;db/migrations/`. Evidencia: FNB-003 reglas y migración revisadas.

- [ ] **F08-T03C** (FNB-003) Ejecutar ambos casos y revisar FNB-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F08-T03B. Archivos propuestos: `evidence/F08/FNB-003/;specs/009-alimentacion-espacios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F08-T04A** (FNB-004) Escribir casos TC-FNB-004-P y TC-FNB-004-N: Proveedor no entrega pero pedido figura confirmado.
  - Depende de: F08-T03C. Archivos propuestos: `tests/F08/FNB-004.spec.ts;tests/fixtures/F08/`. Evidencia: TC-FNB-004-P;TC-FNB-004-N.

- [ ] **F08-T04B** (FNB-004) Implementar FNB-004: Pedido y entrega separados; cargo y deuda se generan conforme a servicio aceptado. Cancelación coordina proveedor y cliente con reglas pactadas.
  - Depende de: F08-T04A. Archivos propuestos: `src/modules/alimentacion-espacios/fnb-004.ts;src/modules/alimentacion-espacios/schemas.ts;db/migrations/`. Evidencia: FNB-004 reglas y migración revisadas.

- [ ] **F08-T04C** (FNB-004) Ejecutar ambos casos y revisar FNB-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F08-T04B. Archivos propuestos: `evidence/F08/FNB-004/;specs/009-alimentacion-espacios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F08-T05A** (FNB-005) Escribir casos TC-FNB-005-P y TC-FNB-005-N: Registrar venta externa extra por 4000 sin cliente ni servicio adicional.
  - Depende de: F08-T04C. Archivos propuestos: `tests/F08/FNB-005.spec.ts;tests/fixtures/F08/`. Evidencia: TC-FNB-005-P;TC-FNB-005-N.

- [ ] **F08-T05B** (FNB-005) Implementar FNB-005: Dentro de Herencia asignar costos internos con contrapartida gerencial eliminable; no nueva venta externa por desayuno incluido. Distinto RUT usa contrato intercompania real.
  - Depende de: F08-T05A. Archivos propuestos: `src/modules/alimentacion-espacios/fnb-005.ts;src/modules/alimentacion-espacios/schemas.ts;db/migrations/`. Evidencia: FNB-005 reglas y migración revisadas.

- [ ] **F08-T05C** (FNB-005) Ejecutar ambos casos y revisar FNB-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F08-T05B. Archivos propuestos: `evidence/F08/FNB-005/;specs/009-alimentacion-espacios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F08-T06A** (SPA-001) Escribir casos TC-SPA-001-P y TC-SPA-001-N: Segundo evento comienza 16:00 sin respetar limpieza.
  - Depende de: F08-T05C. Archivos propuestos: `tests/F08/SPA-001.spec.ts;tests/fixtures/F08/`. Evidencia: TC-SPA-001-P;TC-SPA-001-N.

- [ ] **F08-T06B** (SPA-001) Implementar SPA-001: Intervalo incluye montaje y limpieza; bloquear solapes y aforo. Sala no aumenta inventario de habitaciones, ni se cobra sin política D23.
  - Depende de: F08-T06A. Archivos propuestos: `src/modules/alimentacion-espacios/spa-001.ts;src/modules/alimentacion-espacios/schemas.ts;db/migrations/`. Evidencia: SPA-001 reglas y migración revisadas.

- [ ] **F08-T06C** (SPA-001) Ejecutar ambos casos y revisar SPA-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F08-T06B. Archivos propuestos: `evidence/F08/SPA-001/;specs/009-alimentacion-espacios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F08-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F08-T06C. Archivos propuestos: `specs/009-alimentacion-espacios/acceptance.md;evidence/F08/`. Evidencia: informe real por build; no autodeclaracion.
