# Tareas F20

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F20-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F05-T99;F06-T99;F11-T99. Archivos propuestos: `specs/021-traspaso-apertura/spec.md;specs/021-traspaso-apertura/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F20-T01A** (MIG-001) Escribir casos TC-MIG-001-P y TC-MIG-001-N: Inventar fecha válida para una fila 31-6.
  - Depende de: F20-T00. Archivos propuestos: `tests/F20/MIG-001.spec.ts;tests/fixtures/F20/`. Evidencia: TC-MIG-001-P;TC-MIG-001-N.

- [ ] **F20-T01B** (MIG-001) Implementar MIG-001: Conservar original y mapa de transformacion; fechas invalidas a cola. No corregir 31-6 suponiendo otro mes. Datos personales sólo con finalidad.
  - Depende de: F20-T01A. Archivos propuestos: `src/modules/traspaso-apertura/mig-001.ts;src/modules/traspaso-apertura/schemas.ts;db/migrations/`. Evidencia: MIG-001 reglas y migración revisadas.

- [ ] **F20-T01C** (MIG-001) Ejecutar ambos casos y revisar MIG-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F20-T01B. Archivos propuestos: `evidence/F20/MIG-001/;specs/021-traspaso-apertura/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F20-T02A** (MIG-002) Escribir casos TC-MIG-002-P y TC-MIG-002-N: Cobrar nuevamente 100000 al huésped porque aún no se entrego dinero.
  - Depende de: F20-T01C. Archivos propuestos: `tests/F20/MIG-002.spec.ts;tests/fixtures/F20/`. Evidencia: TC-MIG-002-P;TC-MIG-002-N.

- [ ] **F20-T02B** (MIG-002) Implementar MIG-002: Reconocer crédito del huésped documentado sin fabricar banco propio; fondo por rendir es relación de traspaso. Reserva conserva servicio futuro.
  - Depende de: F20-T02A. Archivos propuestos: `src/modules/traspaso-apertura/mig-002.ts;src/modules/traspaso-apertura/schemas.ts;db/migrations/`. Evidencia: MIG-002 reglas y migración revisadas.

- [ ] **F20-T02C** (MIG-002) Ejecutar ambos casos y revisar MIG-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F20-T02B. Archivos propuestos: `evidence/F20/MIG-002/;specs/021-traspaso-apertura/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F20-T03A** (MIG-003) Escribir casos TC-MIG-003-P y TC-MIG-003-N: Diferencia de cantidades o saldos no explicada.
  - Depende de: F20-T02C. Archivos propuestos: `tests/F20/MIG-003.spec.ts;tests/fixtures/F20/`. Evidencia: TC-MIG-003-P;TC-MIG-003-N.

- [ ] **F20-T03B** (MIG-003) Implementar MIG-003: Carga staging con totales por moneda, unidad y categoría; publicar sólo con acta y conciliación. Saldo inicial no es compra nueva.
  - Depende de: F20-T03A. Archivos propuestos: `src/modules/traspaso-apertura/mig-003.ts;src/modules/traspaso-apertura/schemas.ts;db/migrations/`. Evidencia: MIG-003 reglas y migración revisadas.

- [ ] **F20-T03C** (MIG-003) Ejecutar ambos casos y revisar MIG-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F20-T03B. Archivos propuestos: `evidence/F20/MIG-003/;specs/021-traspaso-apertura/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F20-T04A** (MIG-004) Escribir casos TC-MIG-004-P y TC-MIG-004-N: Sólo presentacion de pantallas sin operador realizando tareas.
  - Depende de: F20-T03C. Archivos propuestos: `tests/F20/MIG-004.spec.ts;tests/fixtures/F20/`. Evidencia: TC-MIG-004-P;TC-MIG-004-N.

- [ ] **F20-T04B** (MIG-004) Implementar MIG-004: Ensayo por rol incluye errores y recuperación, no sólo demo. Usuario operativo realiza ciclo sin guía constante del desarrollador.
  - Depende de: F20-T04A. Archivos propuestos: `src/modules/traspaso-apertura/mig-004.ts;src/modules/traspaso-apertura/schemas.ts;db/migrations/`. Evidencia: MIG-004 reglas y migración revisadas.

- [ ] **F20-T04C** (MIG-004) Ejecutar ambos casos y revisar MIG-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F20-T04B. Archivos propuestos: `evidence/F20/MIG-004/;specs/021-traspaso-apertura/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F20-T05A** (MIG-005) Escribir casos TC-MIG-005-P y TC-MIG-005-N: Abono enero por venta diciembre se registra automáticamente como nueva venta enero.
  - Depende de: F20-T04C. Archivos propuestos: `tests/F20/MIG-005.spec.ts;tests/fixtures/F20/`. Evidencia: TC-MIG-005-P;TC-MIG-005-N.

- [ ] **F20-T05B** (MIG-005) Implementar MIG-005: Acta distingue obligaciones de servicio y fondos; noche31/desayunos/comisiones con regla firmada. Cliente mantiene crédito probado aunque fondos pendientes.
  - Depende de: F20-T05A. Archivos propuestos: `src/modules/traspaso-apertura/mig-005.ts;src/modules/traspaso-apertura/schemas.ts;db/migrations/`. Evidencia: MIG-005 reglas y migración revisadas.

- [ ] **F20-T05C** (MIG-005) Ejecutar ambos casos y revisar MIG-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F20-T05B. Archivos propuestos: `evidence/F20/MIG-005/;specs/021-traspaso-apertura/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F20-T06A** (MIG-006) Escribir casos TC-MIG-006-P y TC-MIG-006-N: Sistema aprueba compra para cerrar artificialmente discrepancia.
  - Depende de: F20-T05C. Archivos propuestos: `tests/F20/MIG-006.spec.ts;tests/fixtures/F20/`. Evidencia: TC-MIG-006-P;TC-MIG-006-N.

- [ ] **F20-T06B** (MIG-006) Implementar MIG-006: Comparar entrega anterior y actual sin concluir responsabilidad jurídica automáticamente. Faltante, mejora nueva y reparacion son categorías distintas.
  - Depende de: F20-T06A. Archivos propuestos: `src/modules/traspaso-apertura/mig-006.ts;src/modules/traspaso-apertura/schemas.ts;db/migrations/`. Evidencia: MIG-006 reglas y migración revisadas.

- [ ] **F20-T06C** (MIG-006) Ejecutar ambos casos y revisar MIG-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F20-T06B. Archivos propuestos: `evidence/F20/MIG-006/;specs/021-traspaso-apertura/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F20-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F20-T06C. Archivos propuestos: `specs/021-traspaso-apertura/acceptance.md;evidence/F20/`. Evidencia: informe real por build; no autodeclaracion.
