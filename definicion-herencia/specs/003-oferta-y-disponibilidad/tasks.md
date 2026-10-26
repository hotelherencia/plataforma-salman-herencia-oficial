# Tareas F02

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F02-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F01-T99. Archivos propuestos: `specs/003-oferta-y-disponibilidad/spec.md;specs/003-oferta-y-disponibilidad/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F02-T01A** (HOT-001) Escribir casos TC-HOT-001-P y TC-HOT-001-N: Intentar activar dos habitaciones con mismo código o la sala como habitación adicional.
  - Depende de: F02-T00. Archivos propuestos: `tests/F02/HOT-001.spec.ts;tests/fixtures/F02/`. Evidencia: TC-HOT-001-P;TC-HOT-001-N.

- [ ] **F02-T01B** (HOT-001) Implementar HOT-001: Activar catálogo real sólo con conteo de 17 habitaciones y validación D01. Datos sintéticos no se exportan a canal productivo; sala se modela separadamente.
  - Depende de: F02-T01A. Archivos propuestos: `src/modules/oferta-y-disponibilidad/hot-001.ts;src/modules/oferta-y-disponibilidad/schemas.ts;db/migrations/`. Evidencia: HOT-001 reglas y migración revisadas.

- [ ] **F02-T01C** (HOT-001) Ejecutar ambos casos y revisar HOT-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F02-T01B. Archivos propuestos: `evidence/F02/HOT-001/;specs/003-oferta-y-disponibilidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F02-T02A** (HOT-002) Escribir casos TC-HOT-002-P y TC-HOT-002-N: Tres adultos intentan reservar una doble con max_total=2.
  - Depende de: F02-T01C. Archivos propuestos: `tests/F02/HOT-002.spec.ts;tests/fixtures/F02/`. Evidencia: TC-HOT-002-P;TC-HOT-002-N.

- [ ] **F02-T02B** (HOT-002) Implementar HOT-002: Capacidad total y por clase de ocupante se válida en motor; una cama adicional requiere configuración y política aprobada. No usar sólo número de camas como personas.
  - Depende de: F02-T02A. Archivos propuestos: `src/modules/oferta-y-disponibilidad/hot-002.ts;src/modules/oferta-y-disponibilidad/schemas.ts;db/migrations/`. Evidencia: HOT-002 reglas y migración revisadas.

- [ ] **F02-T02C** (HOT-002) Ejecutar ambos casos y revisar HOT-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F02-T02B. Archivos propuestos: `evidence/F02/HOT-002/;specs/003-oferta-y-disponibilidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F02-T03A** (HOT-003) Escribir casos TC-HOT-003-P y TC-HOT-003-N: Asignar mismo cuarto a dos estadías con intervalos solapados.
  - Depende de: F02-T02C. Archivos propuestos: `tests/F02/HOT-003.spec.ts;tests/fixtures/F02/`. Evidencia: TC-HOT-003-P;TC-HOT-003-N.

- [ ] **F02-T03B** (HOT-003) Implementar HOT-003: Validar todos los días y tipos de forma atomica; bloquear filas ordenadamente. La asignación física utiliza intervalos excluyentes y no altera cuenta de cliente.
  - Depende de: F02-T03A. Archivos propuestos: `src/modules/oferta-y-disponibilidad/hot-003.ts;src/modules/oferta-y-disponibilidad/schemas.ts;db/migrations/`. Evidencia: HOT-003 reglas y migración revisadas.

- [ ] **F02-T03C** (HOT-003) Ejecutar ambos casos y revisar HOT-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F02-T03B. Archivos propuestos: `evidence/F02/HOT-003/;specs/003-oferta-y-disponibilidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F02-T04A** (HOT-004) Escribir casos TC-HOT-004-P y TC-HOT-004-N: Crear bloqueo sobre reserva confirmada y pretender anular automáticamente esa reserva.
  - Depende de: F02-T03C. Archivos propuestos: `tests/F02/HOT-004.spec.ts;tests/fixtures/F02/`. Evidencia: TC-HOT-004-P;TC-HOT-004-N.

- [ ] **F02-T04B** (HOT-004) Implementar HOT-004: Un bloqueo crítico puede entrar en emergencia con auditoría, pero genera incidencia de cada reserva afectada. Un bloqueo planificado válida alternativas antes de activar.
  - Depende de: F02-T04A. Archivos propuestos: `src/modules/oferta-y-disponibilidad/hot-004.ts;src/modules/oferta-y-disponibilidad/schemas.ts;db/migrations/`. Evidencia: HOT-004 reglas y migración revisadas.

- [ ] **F02-T04C** (HOT-004) Ejecutar ambos casos y revisar HOT-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F02-T04B. Archivos propuestos: `evidence/F02/HOT-004/;specs/003-oferta-y-disponibilidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F02-T05A** (HOT-005) Escribir casos TC-HOT-005-P y TC-HOT-005-N: Marcar CLEAN para intentar ignorar bloqueo por equipo inseguro.
  - Depende de: F02-T04C. Archivos propuestos: `tests/F02/HOT-005.spec.ts;tests/fixtures/F02/`. Evidencia: TC-HOT-005-P;TC-HOT-005-N.

- [ ] **F02-T05B** (HOT-005) Implementar HOT-005: Los cuatro ejes se actualizan por eventos propios. Checkout marca salida y tarea de suciedad; sólo inspección libera entrega y sólo pago ajusta cuenta.
  - Depende de: F02-T05A. Archivos propuestos: `src/modules/oferta-y-disponibilidad/hot-005.ts;src/modules/oferta-y-disponibilidad/schemas.ts;db/migrations/`. Evidencia: HOT-005 reglas y migración revisadas.

- [ ] **F02-T05C** (HOT-005) Ejecutar ambos casos y revisar HOT-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F02-T05B. Archivos propuestos: `evidence/F02/HOT-005/;specs/003-oferta-y-disponibilidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F02-T06A** (RES-005) Escribir casos TC-RES-005-P y TC-RES-005-N: Modificar precio publicado y reabrir detalle de reserva ya confirmada.
  - Depende de: F02-T05C. Archivos propuestos: `tests/F02/RES-005.spec.ts;tests/fixtures/F02/`. Evidencia: TC-RES-005-P;TC-RES-005-N.

- [ ] **F02-T06B** (RES-005) Implementar RES-005: Resolver regla mas específica y versionada; guardar desglose por noche y aceptacion. Una nueva tarifa no recalcula reservas antiguas salvo cambio aceptado.
  - Depende de: F02-T06A. Archivos propuestos: `src/modules/oferta-y-disponibilidad/res-005.ts;src/modules/oferta-y-disponibilidad/schemas.ts;db/migrations/`. Evidencia: RES-005 reglas y migración revisadas.

- [ ] **F02-T06C** (RES-005) Ejecutar ambos casos y revisar RES-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F02-T06B. Archivos propuestos: `evidence/F02/RES-005/;specs/003-oferta-y-disponibilidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F02-T07A** (RES-006) Escribir casos TC-RES-006-P y TC-RES-006-N: Aplicar 17% histórico automáticamente como descuento y comisión de toda venta.
  - Depende de: F02-T06C. Archivos propuestos: `tests/F02/RES-006.spec.ts;tests/fixtures/F02/`. Evidencia: TC-RES-006-P;TC-RES-006-N.

- [ ] **F02-T07B** (RES-006) Implementar RES-006: Descuento modifica precio cliente; comisión calcula costo segun contrato y base definida. Prohibir usar columna histórica Genius como comisión general.
  - Depende de: F02-T07A. Archivos propuestos: `src/modules/oferta-y-disponibilidad/res-006.ts;src/modules/oferta-y-disponibilidad/schemas.ts;db/migrations/`. Evidencia: RES-006 reglas y migración revisadas.

- [ ] **F02-T07C** (RES-006) Ejecutar ambos casos y revisar RES-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F02-T07B. Archivos propuestos: `evidence/F02/RES-006/;specs/003-oferta-y-disponibilidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F02-T08A** (REV-001) Escribir casos TC-REV-001-P y TC-REV-001-N: Cambiar tarifa base altera precio de reserva confirmada.
  - Depende de: F02-T07C. Archivos propuestos: `tests/F02/REV-001.spec.ts;tests/fixtures/F02/`. Evidencia: TC-REV-001-P;TC-REV-001-N.

- [ ] **F02-T08B** (REV-001) Implementar REV-001: Evaluar restricciones locales antes de cotizar; proveedor externo sólo mapea la regla, no es requisito para existir localmente. Explicar conflicto de reglas.
  - Depende de: F02-T08A. Archivos propuestos: `src/modules/oferta-y-disponibilidad/rev-001.ts;src/modules/oferta-y-disponibilidad/schemas.ts;db/migrations/`. Evidencia: REV-001 reglas y migración revisadas.

- [ ] **F02-T08C** (REV-001) Ejecutar ambos casos y revisar REV-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F02-T08B. Archivos propuestos: `evidence/F02/REV-001/;specs/003-oferta-y-disponibilidad/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F02-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F02-T08C. Archivos propuestos: `specs/003-oferta-y-disponibilidad/acceptance.md;evidence/F02/`. Evidencia: informe real por build; no autodeclaracion.
