# Tareas F05

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F05-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F03-T99;F04-T99. Archivos propuestos: `specs/006-recepcion-estadias/spec.md;specs/006-recepcion-estadias/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F05-T01A** (REC-001) Escribir casos TC-REC-001-P y TC-REC-001-N: Intentar ingresar a habitación sucia o fuera de servicio sin excepción permitida.
  - Depende de: F05-T00. Archivos propuestos: `tests/F05/REC-001.spec.ts;tests/fixtures/F05/`. Evidencia: TC-REC-001-P;TC-REC-001-N.

- [ ] **F05-T01B** (REC-001) Implementar REC-001: Registrar personas realmente presentes y datos mínimos segun finalidad; llegada parcial conserva ocupación reservada restante. Verificar habitación lista y pago/credito permitido.
  - Depende de: F05-T01A. Archivos propuestos: `src/modules/recepcion-estadias/rec-001.ts;src/modules/recepcion-estadias/schemas.ts;db/migrations/`. Evidencia: REC-001 reglas y migración revisadas.

- [ ] **F05-T01C** (REC-001) Ejecutar ambos casos y revisar REC-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F05-T01B. Archivos propuestos: `evidence/F05/REC-001/;specs/006-recepcion-estadias/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F05-T02A** (REC-002) Escribir casos TC-REC-002-P y TC-REC-002-N: Destino ocupado durante parte del intervalo solicitado.
  - Depende de: F05-T01C. Archivos propuestos: `tests/F05/REC-002.spec.ts;tests/fixtures/F05/`. Evidencia: TC-REC-002-P;TC-REC-002-N.

- [ ] **F05-T02B** (REC-002) Implementar REC-002: Cerrar segmento anterior y abrir nuevo en una transacción; conservar cuenta; generar aseo saliente. Cruce de tipo revalida inventario y diferencia autorizada.
  - Depende de: F05-T02A. Archivos propuestos: `src/modules/recepcion-estadias/rec-002.ts;src/modules/recepcion-estadias/schemas.ts;db/migrations/`. Evidencia: REC-002 reglas y migración revisadas.

- [ ] **F05-T02C** (REC-002) Ejecutar ambos casos y revisar REC-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F05-T02B. Archivos propuestos: `evidence/F05/REC-002/;specs/006-recepcion-estadias/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F05-T03A** (REC-003) Escribir casos TC-REC-003-P y TC-REC-003-N: Particular con deuda intenta salida administrativa sin autorización requerida.
  - Depende de: F05-T02C. Archivos propuestos: `tests/F05/REC-003.spec.ts;tests/fixtures/F05/`. Evidencia: TC-REC-003-P;TC-REC-003-N.

- [ ] **F05-T03B** (REC-003) Implementar REC-003: Salida física no exige falsificar pago; deuda sólo queda autorizada con pagador, plazo y permiso. Habitación genera limpieza sin cerrar receivable.
  - Depende de: F05-T03A. Archivos propuestos: `src/modules/recepcion-estadias/rec-003.ts;src/modules/recepcion-estadias/schemas.ts;db/migrations/`. Evidencia: REC-003 reglas y migración revisadas.

- [ ] **F05-T03C** (REC-003) Ejecutar ambos casos y revisar REC-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F05-T03B. Archivos propuestos: `evidence/F05/REC-003/;specs/006-recepcion-estadias/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F05-T04A** (REC-004) Escribir casos TC-REC-004-P y TC-REC-004-N: Cerrar turno dejando incidente crítico sin receptor o responsable de escalamiento.
  - Depende de: F05-T03C. Archivos propuestos: `tests/F05/REC-004.spec.ts;tests/fixtures/F05/`. Evidencia: TC-REC-004-P;TC-REC-004-N.

- [ ] **F05-T04B** (REC-004) Implementar REC-004: Pendientes se entregan con responsable y acuse; no borrar el historial al cambiar turno. Alertas vencidas escalan al rol definido.
  - Depende de: F05-T04A. Archivos propuestos: `src/modules/recepcion-estadias/rec-004.ts;src/modules/recepcion-estadias/schemas.ts;db/migrations/`. Evidencia: REC-004 reglas y migración revisadas.

- [ ] **F05-T04C** (REC-004) Ejecutar ambos casos y revisar REC-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F05-T04B. Archivos propuestos: `evidence/F05/REC-004/;specs/006-recepcion-estadias/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F05-T05A** (REC-005) Escribir casos TC-REC-005-P y TC-REC-005-N: Persona que conoce número de habitación solicita objeto sin verificación.
  - Depende de: F05-T04C. Archivos propuestos: `tests/F05/REC-005.spec.ts;tests/fixtures/F05/`. Evidencia: TC-REC-005-P;TC-REC-005-N.

- [ ] **F05-T05B** (REC-005) Implementar REC-005: Registrar emision/devolucion de llaves y objetos, con acceso mínimo y trazabilidad. Entrega de objeto exige comprobar receptor, no publicar inventario personal.
  - Depende de: F05-T05A. Archivos propuestos: `src/modules/recepcion-estadias/rec-005.ts;src/modules/recepcion-estadias/schemas.ts;db/migrations/`. Evidencia: REC-005 reglas y migración revisadas.

- [ ] **F05-T05C** (REC-005) Ejecutar ambos casos y revisar REC-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F05-T05B. Archivos propuestos: `evidence/F05/REC-005/;specs/006-recepcion-estadias/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F05-T06A** (OPS-006) Escribir casos TC-OPS-006-P y TC-OPS-006-N: Cambio horario de verano provoca repetir hora del scheduler.
  - Depende de: F05-T05C. Archivos propuestos: `tests/F05/OPS-006.spec.ts;tests/fixtures/F05/`. Evidencia: TC-OPS-006-P;TC-OPS-006-N.

- [ ] **F05-T06B** (OPS-006) Implementar OPS-006: Fecha de negocio configurable separada de UTC/calendario; cargos únicos por noche/concepto. Auditoría revisa pendientes sin cerrar estadías activas.
  - Depende de: F05-T06A. Archivos propuestos: `src/modules/recepcion-estadias/ops-006.ts;src/modules/recepcion-estadias/schemas.ts;db/migrations/`. Evidencia: OPS-006 reglas y migración revisadas.

- [ ] **F05-T06C** (OPS-006) Ejecutar ambos casos y revisar OPS-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F05-T06B. Archivos propuestos: `evidence/F05/OPS-006/;specs/006-recepcion-estadias/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F05-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F05-T06C. Archivos propuestos: `specs/006-recepcion-estadias/acceptance.md;evidence/F05/`. Evidencia: informe real por build; no autodeclaracion.
