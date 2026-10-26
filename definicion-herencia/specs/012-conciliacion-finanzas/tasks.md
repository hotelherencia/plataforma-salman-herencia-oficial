# Tareas F11

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F11-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F04-T99. Archivos propuestos: `specs/012-conciliacion-finanzas/spec.md;specs/012-conciliacion-finanzas/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F11-T01A** (FIN-001) Escribir casos TC-FIN-001-P y TC-FIN-001-N: Sumar cargo, factura, cobro y depósito en una sola columna ingresos.
  - Depende de: F11-T00. Archivos propuestos: `tests/F11/FIN-001.spec.ts;tests/fixtures/F11/`. Evidencia: TC-FIN-001-P;TC-FIN-001-N.

- [ ] **F11-T01B** (FIN-001) Implementar FIN-001: Reportes separados y conciliables. Servicio de enero cobrado en diciembre aparece como ingreso de servicio enero y cobro diciembre sin sumarse.
  - Depende de: F11-T01A. Archivos propuestos: `src/modules/conciliacion-finanzas/fin-001.ts;src/modules/conciliacion-finanzas/schemas.ts;db/migrations/`. Evidencia: FIN-001 reglas y migración revisadas.

- [ ] **F11-T01C** (FIN-001) Ejecutar ambos casos y revisar FIN-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F11-T01B. Archivos propuestos: `evidence/F11/FIN-001/;specs/012-conciliacion-finanzas/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F11-T02A** (FIN-002) Escribir casos TC-FIN-002-P y TC-FIN-002-N: Aplicar pago a otra empresa con nombre similar.
  - Depende de: F11-T01C. Archivos propuestos: `tests/F11/FIN-002.spec.ts;tests/fixtures/F11/`. Evidencia: TC-FIN-002-P;TC-FIN-002-N.

- [ ] **F11-T02B** (FIN-002) Implementar FIN-002: Antiguedad por fecha de vencimiento y saldo a fecha de corte; pago posterior no reescribe reporte histórico sin etiqueta restated. Grupo conserva detalle.
  - Depende de: F11-T02A. Archivos propuestos: `src/modules/conciliacion-finanzas/fin-002.ts;src/modules/conciliacion-finanzas/schemas.ts;db/migrations/`. Evidencia: FIN-002 reglas y migración revisadas.

- [ ] **F11-T02C** (FIN-002) Ejecutar ambos casos y revisar FIN-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F11-T02B. Archivos propuestos: `evidence/F11/FIN-002/;specs/012-conciliacion-finanzas/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F11-T03A** (FIN-003) Escribir casos TC-FIN-003-P y TC-FIN-003-N: Dos transferencias legitimas de 50000 mismo día tienen IDs diferentes.
  - Depende de: F11-T02C. Archivos propuestos: `tests/F11/FIN-003.spec.ts;tests/fixtures/F11/`. Evidencia: TC-FIN-003-P;TC-FIN-003-N.

- [ ] **F11-T03B** (FIN-003) Implementar FIN-003: Importar a staging con tipos, fechas, moneda y control de totales. Hash evita archivo repetido; fila ambigua se revisa, no se descarta por monto igual.
  - Depende de: F11-T03A. Archivos propuestos: `src/modules/conciliacion-finanzas/fin-003.ts;src/modules/conciliacion-finanzas/schemas.ts;db/migrations/`. Evidencia: FIN-003 reglas y migración revisadas.

- [ ] **F11-T03C** (FIN-003) Ejecutar ambos casos y revisar FIN-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F11-T03B. Archivos propuestos: `evidence/F11/FIN-003/;specs/012-conciliacion-finanzas/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F11-T04A** (FIN-004) Escribir casos TC-FIN-004-P y TC-FIN-004-N: Asignar un abono completo a dos grupos simultaneamente.
  - Depende de: F11-T03C. Archivos propuestos: `tests/F11/FIN-004.spec.ts;tests/fixtures/F11/`. Evidencia: TC-FIN-004-P;TC-FIN-004-N.

- [ ] **F11-T04B** (FIN-004) Implementar FIN-004: Asignaciones many-to-many bloquean saldos de fuentes; total negocio y banco deben cuadrar o tener ajuste aprobado clasificado. Reverso libera asignaciones sin borrar hechos.
  - Depende de: F11-T04A. Archivos propuestos: `src/modules/conciliacion-finanzas/fin-004.ts;src/modules/conciliacion-finanzas/schemas.ts;db/migrations/`. Evidencia: FIN-004 reglas y migración revisadas.

- [ ] **F11-T04C** (FIN-004) Ejecutar ambos casos y revisar FIN-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F11-T04B. Archivos propuestos: `evidence/F11/FIN-004/;specs/012-conciliacion-finanzas/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F11-T05A** (FIN-005) Escribir casos TC-FIN-005-P y TC-FIN-005-N: Hotel cobra 200000 directo y sistema reduce además abono por comisión ya pagada aparte.
  - Depende de: F11-T04C. Archivos propuestos: `tests/F11/FIN-005.spec.ts;tests/fixtures/F11/`. Evidencia: TC-FIN-005-P;TC-FIN-005-N.

- [ ] **F11-T05B** (FIN-005) Implementar FIN-005: Modo hotel cobra y canal cobra son contratos diferentes. Retención de comisión y factura separada no se descuentan ambas sin causa.
  - Depende de: F11-T05A. Archivos propuestos: `src/modules/conciliacion-finanzas/fin-005.ts;src/modules/conciliacion-finanzas/schemas.ts;db/migrations/`. Evidencia: FIN-005 reglas y migración revisadas.

- [ ] **F11-T05C** (FIN-005) Ejecutar ambos casos y revisar FIN-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F11-T05B. Archivos propuestos: `evidence/F11/FIN-005/;specs/012-conciliacion-finanzas/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F11-T06A** (FIN-006) Escribir casos TC-FIN-006-P y TC-FIN-006-N: Conciliar automáticamente sólo por monto coincidente.
  - Depende de: F11-T05C. Archivos propuestos: `tests/F11/FIN-006.spec.ts;tests/fixtures/F11/`. Evidencia: TC-FIN-006-P;TC-FIN-006-N.

- [ ] **F11-T06B** (FIN-006) Implementar FIN-006: Motor propone coincidencias por referencia/importe/fecha y confianza; no aprueba ambiguas. Diferencia tiene responsable, motivo y plazo, nunca se convierte en venta automáticamente.
  - Depende de: F11-T06A. Archivos propuestos: `src/modules/conciliacion-finanzas/fin-006.ts;src/modules/conciliacion-finanzas/schemas.ts;db/migrations/`. Evidencia: FIN-006 reglas y migración revisadas.

- [ ] **F11-T06C** (FIN-006) Ejecutar ambos casos y revisar FIN-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F11-T06B. Archivos propuestos: `evidence/F11/FIN-006/;specs/012-conciliacion-finanzas/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F11-T07A** (FIN-009) Escribir casos TC-FIN-009-P y TC-FIN-009-N: Eliminar factura a tercero por parecer transacción interna sin referencia pareada.
  - Depende de: F11-T06C. Archivos propuestos: `tests/F11/FIN-009.spec.ts;tests/fixtures/F11/`. Evidencia: TC-FIN-009-P;TC-FIN-009-N.

- [ ] **F11-T07B** (FIN-009) Implementar FIN-009: Mismo RUT usa asignación gerencial; distintos RUT exigen documento/contrato aplicable. Consolidado elimina sólo reciprocidades identificadas y autorizadas.
  - Depende de: F11-T07A. Archivos propuestos: `src/modules/conciliacion-finanzas/fin-009.ts;src/modules/conciliacion-finanzas/schemas.ts;db/migrations/`. Evidencia: FIN-009 reglas y migración revisadas.

- [ ] **F11-T07C** (FIN-009) Ejecutar ambos casos y revisar FIN-009 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F11-T07B. Archivos propuestos: `evidence/F11/FIN-009/;specs/012-conciliacion-finanzas/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F11-T08A** (FIN-011) Escribir casos TC-FIN-011-P y TC-FIN-011-N: Destino no soporta idempotencia y usuario reenvia como nuevo.
  - Depende de: F11-T07C. Archivos propuestos: `tests/F11/FIN-011.spec.ts;tests/fixtures/F11/`. Evidencia: TC-FIN-011-P;TC-FIN-011-N.

- [ ] **F11-T08B** (FIN-011) Implementar FIN-011: Auxiliar no se declara libro legal completo. Exportar lote único validado por contabilidad y registrar acuse/rechazo; reenvio preserva ID.
  - Depende de: F11-T08A. Archivos propuestos: `src/modules/conciliacion-finanzas/fin-011.ts;src/modules/conciliacion-finanzas/schemas.ts;db/migrations/`. Evidencia: FIN-011 reglas y migración revisadas.

- [ ] **F11-T08C** (FIN-011) Ejecutar ambos casos y revisar FIN-011 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F11-T08B. Archivos propuestos: `evidence/F11/FIN-011/;specs/012-conciliacion-finanzas/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F11-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F11-T08C. Archivos propuestos: `specs/012-conciliacion-finanzas/acceptance.md;evidence/F11/`. Evidencia: informe real por build; no autodeclaracion.
