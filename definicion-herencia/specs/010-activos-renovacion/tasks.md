# Tareas F09

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F09-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F02-T99;F06-T99. Archivos propuestos: `specs/010-activos-renovacion/spec.md;specs/010-activos-renovacion/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F09-T01A** (MNT-001) Escribir casos TC-MNT-001-P y TC-MNT-001-N: Reejecutar scheduler del mismo día.
  - Depende de: F09-T00. Archivos propuestos: `tests/F09/MNT-001.spec.ts;tests/fixtures/F09/`. Evidencia: TC-MNT-001-P;TC-MNT-001-N.

- [ ] **F09-T01B** (MNT-001) Implementar MNT-001: Calendario genera una orden por activo/periodo; prioridad decide aviso, no bloqueo automático de todas las habitaciones. Garantía se consulta antes de contratar.
  - Depende de: F09-T01A. Archivos propuestos: `src/modules/activos-renovacion/mnt-001.ts;src/modules/activos-renovacion/schemas.ts;db/migrations/`. Evidencia: MNT-001 reglas y migración revisadas.

- [ ] **F09-T01C** (MNT-001) Ejecutar ambos casos y revisar MNT-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F09-T01B. Archivos propuestos: `evidence/F09/MNT-001/;specs/010-activos-renovacion/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F09-T02A** (MNT-002) Escribir casos TC-MNT-002-P y TC-MNT-002-N: Proveedor factura pero equipo sigue fallando.
  - Depende de: F09-T01C. Archivos propuestos: `tests/F09/MNT-002.spec.ts;tests/fixtures/F09/`. Evidencia: TC-MNT-002-P;TC-MNT-002-N.

- [ ] **F09-T02B** (MNT-002) Implementar MNT-002: Orden maneja espera de repuestos y comprobacion final; reserva afectada recibe incidente. Costo/documentos no prueban seguridad de funcionamiento.
  - Depende de: F09-T02A. Archivos propuestos: `src/modules/activos-renovacion/mnt-002.ts;src/modules/activos-renovacion/schemas.ts;db/migrations/`. Evidencia: MNT-002 reglas y migración revisadas.

- [ ] **F09-T02C** (MNT-002) Ejecutar ambos casos y revisar MNT-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F09-T02B. Archivos propuestos: `evidence/F09/MNT-002/;specs/010-activos-renovacion/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F09-T03A** (CAP-002) Escribir casos TC-CAP-002-P y TC-CAP-002-N: Importar inventario y asignar todos los bienes a Herencia automáticamente.
  - Depende de: F09-T02C. Archivos propuestos: `tests/F09/CAP-002.spec.ts;tests/fixtures/F09/`. Evidencia: TC-CAP-002-P;TC-CAP-002-N.

- [ ] **F09-T03B** (CAP-002) Implementar CAP-002: Ficha conserva propiedad y fecha sólo si acreditada. Inspección con fallas observables; historial de ubicacion y cambios.
  - Depende de: F09-T03A. Archivos propuestos: `src/modules/activos-renovacion/cap-002.ts;src/modules/activos-renovacion/schemas.ts;db/migrations/`. Evidencia: CAP-002 reglas y migración revisadas.

- [ ] **F09-T03C** (CAP-002) Ejecutar ambos casos y revisar CAP-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F09-T03B. Archivos propuestos: `evidence/F09/CAP-002/;specs/010-activos-renovacion/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F09-T04A** (CAP-003) Escribir casos TC-CAP-003-P y TC-CAP-003-N: Necesidad de mejora se interpreta como obligación del arrendatario sin contrato.
  - Depende de: F09-T03C. Archivos propuestos: `tests/F09/CAP-003.spec.ts;tests/fixtures/F09/`. Evidencia: TC-CAP-003-P;TC-CAP-003-N.

- [ ] **F09-T04B** (CAP-003) Implementar CAP-003: Inversion separada de consumibles; clasificar seguridad/calidad/eficiencia/estetica, justificar comparables y aprobación. No basar renovación sólo en antiguedad.
  - Depende de: F09-T04A. Archivos propuestos: `src/modules/activos-renovacion/cap-003.ts;src/modules/activos-renovacion/schemas.ts;db/migrations/`. Evidencia: CAP-003 reglas y migración revisadas.

- [ ] **F09-T04C** (CAP-003) Ejecutar ambos casos y revisar CAP-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F09-T04B. Archivos propuestos: `evidence/F09/CAP-003/;specs/010-activos-renovacion/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F09-T05A** (CAP-004) Escribir casos TC-CAP-004-P y TC-CAP-004-N: Equipo pagado aún en transporte libera habitación.
  - Depende de: F09-T04C. Archivos propuestos: `tests/F09/CAP-004.spec.ts;tests/fixtures/F09/`. Evidencia: TC-CAP-004-P;TC-CAP-004-N.

- [ ] **F09-T05B** (CAP-004) Implementar CAP-004: Compra, entrega, instalación y aceptacion son etapas distintas; activo se habilita después de prueba técnica. Nueva garantía inicia segun contrato verificable.
  - Depende de: F09-T05A. Archivos propuestos: `src/modules/activos-renovacion/cap-004.ts;src/modules/activos-renovacion/schemas.ts;db/migrations/`. Evidencia: CAP-004 reglas y migración revisadas.

- [ ] **F09-T05C** (CAP-004) Ejecutar ambos casos y revisar CAP-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F09-T05B. Archivos propuestos: `evidence/F09/CAP-004/;specs/010-activos-renovacion/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F09-T06A** (CAP-005) Escribir casos TC-CAP-005-P y TC-CAP-005-N: Contabilizar compra dos veces como gasto y activo, o eliminar faltante histórico.
  - Depende de: F09-T05C. Archivos propuestos: `tests/F09/CAP-005.spec.ts;tests/fixtures/F09/`. Evidencia: TC-CAP-005-P;TC-CAP-005-N.

- [ ] **F09-T06B** (CAP-005) Implementar CAP-005: Baja no borra ficha ni observacion de traspaso; distinguir venta, entrega, reparacion o desecho. Tratamiento de gasto/activo se ratifica antes de exportar.
  - Depende de: F09-T06A. Archivos propuestos: `src/modules/activos-renovacion/cap-005.ts;src/modules/activos-renovacion/schemas.ts;db/migrations/`. Evidencia: CAP-005 reglas y migración revisadas.

- [ ] **F09-T06C** (CAP-005) Ejecutar ambos casos y revisar CAP-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F09-T06B. Archivos propuestos: `evidence/F09/CAP-005/;specs/010-activos-renovacion/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F09-T07A** (CAP-006) Escribir casos TC-CAP-006-P y TC-CAP-006-N: Intervencion inicia sin bloquear y canal vende la habitación.
  - Depende de: F09-T06C. Archivos propuestos: `tests/F09/CAP-006.spec.ts;tests/fixtures/F09/`. Evidencia: TC-CAP-006-P;TC-CAP-006-N.

- [ ] **F09-T07B** (CAP-006) Implementar CAP-006: Programar bloqueo con capacidad y alternativas; estimar ingreso perdido con supuestos separados de gasto. Avisar antes de obra salvo emergencia de seguridad.
  - Depende de: F09-T07A. Archivos propuestos: `src/modules/activos-renovacion/cap-006.ts;src/modules/activos-renovacion/schemas.ts;db/migrations/`. Evidencia: CAP-006 reglas y migración revisadas.

- [ ] **F09-T07C** (CAP-006) Ejecutar ambos casos y revisar CAP-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F09-T07B. Archivos propuestos: `evidence/F09/CAP-006/;specs/010-activos-renovacion/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F09-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F09-T07C. Archivos propuestos: `specs/010-activos-renovacion/acceptance.md;evidence/F09/`. Evidencia: informe real por build; no autodeclaracion.
