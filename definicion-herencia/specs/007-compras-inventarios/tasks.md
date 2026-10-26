# Tareas F06

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F06-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F01-T99. Archivos propuestos: `specs/007-compras-inventarios/spec.md;specs/007-compras-inventarios/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F06-T01A** (INV-001) Escribir casos TC-INV-001-P y TC-INV-001-N: Producto duplicado por variacion ortografica genera dos stocks no revisados.
  - Depende de: F06-T00. Archivos propuestos: `tests/F06/INV-001.spec.ts;tests/fixtures/F06/`. Evidencia: TC-INV-001-P;TC-INV-001-N.

- [ ] **F06-T01B** (INV-001) Implementar INV-001: Catálogo separa naturaleza del articulo y no hereda errores de títulos históricos. Conversion positiva y exacta; activos no se tratan como jabon consumible.
  - Depende de: F06-T01A. Archivos propuestos: `src/modules/compras-inventarios/inv-001.ts;src/modules/compras-inventarios/schemas.ts;db/migrations/`. Evidencia: INV-001 reglas y migración revisadas.

- [ ] **F06-T01C** (INV-001) Ejecutar ambos casos y revisar INV-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F06-T01B. Archivos propuestos: `evidence/F06/INV-001/;specs/007-compras-inventarios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F06-T02A** (INV-002) Escribir casos TC-INV-002-P y TC-INV-002-N: Falla una pata de traslado o salida supera stock.
  - Depende de: F06-T01C. Archivos propuestos: `tests/F06/INV-002.spec.ts;tests/fixtures/F06/`. Evidencia: TC-INV-002-P;TC-INV-002-N.

- [ ] **F06-T02B** (INV-002) Implementar INV-002: Movimientos inmutables; dos patas de transferencia atomicas. Saldo derivado por articulo/lote/ubicacion y sociedad, sin permitir stock negativo por edicion directa.
  - Depende de: F06-T02A. Archivos propuestos: `src/modules/compras-inventarios/inv-002.ts;src/modules/compras-inventarios/schemas.ts;db/migrations/`. Evidencia: INV-002 reglas y migración revisadas.

- [ ] **F06-T02C** (INV-002) Ejecutar ambos casos y revisar INV-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F06-T02B. Archivos propuestos: `evidence/F06/INV-002/;specs/007-compras-inventarios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F06-T03A** (INV-003) Escribir casos TC-INV-003-P y TC-INV-003-N: Lote vencido propuesto para desayuno.
  - Depende de: F06-T02C. Archivos propuestos: `tests/F06/INV-003.spec.ts;tests/fixtures/F06/`. Evidencia: TC-INV-003-P;TC-INV-003-N.

- [ ] **F06-T03B** (INV-003) Implementar INV-003: Seleccionar lote utilizable de vencimiento mas próximo; vencido o cuarentena no se sirve. Excepción comercial no anula control sanitario.
  - Depende de: F06-T03A. Archivos propuestos: `src/modules/compras-inventarios/inv-003.ts;src/modules/compras-inventarios/schemas.ts;db/migrations/`. Evidencia: INV-003 reglas y migración revisadas.

- [ ] **F06-T03C** (INV-003) Ejecutar ambos casos y revisar INV-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F06-T03B. Archivos propuestos: `evidence/F06/INV-003/;specs/007-compras-inventarios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F06-T04A** (INV-004) Escribir casos TC-INV-004-P y TC-INV-004-N: Aplicar conteo antiguo como saldo 20 perdiendo las cinco recibidas.
  - Depende de: F06-T03C. Archivos propuestos: `tests/F06/INV-004.spec.ts;tests/fixtures/F06/`. Evidencia: TC-INV-004-P;TC-INV-004-N.

- [ ] **F06-T04B** (INV-004) Implementar INV-004: Conteo ciego y reconteo de diferencias; ajuste aprobado conserva referencia al corte y movimientos posteriores. No sobrescribir saldo actual con conteo antiguo.
  - Depende de: F06-T04A. Archivos propuestos: `src/modules/compras-inventarios/inv-004.ts;src/modules/compras-inventarios/schemas.ts;db/migrations/`. Evidencia: INV-004 reglas y migración revisadas.

- [ ] **F06-T04C** (INV-004) Ejecutar ambos casos y revisar INV-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F06-T04B. Archivos propuestos: `evidence/F06/INV-004/;specs/007-compras-inventarios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F06-T05A** (INV-005) Escribir casos TC-INV-005-P y TC-INV-005-N: Ejecutar compra automáticamente sin aprobación de presupuesto.
  - Depende de: F06-T04C. Archivos propuestos: `tests/F06/INV-005.spec.ts;tests/fixtures/F06/`. Evidencia: TC-INV-005-P;TC-INV-005-N.

- [ ] **F06-T05B** (INV-005) Implementar INV-005: Sugerencia muestra demanda y regla; no compra por si sola. Cantidad propuesta considera compromisos pendientes y unidades normalizadas.
  - Depende de: F06-T05A. Archivos propuestos: `src/modules/compras-inventarios/inv-005.ts;src/modules/compras-inventarios/schemas.ts;db/migrations/`. Evidencia: INV-005 reglas y migración revisadas.

- [ ] **F06-T05C** (INV-005) Ejecutar ambos casos y revisar INV-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F06-T05B. Archivos propuestos: `evidence/F06/INV-005/;specs/007-compras-inventarios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F06-T06A** (PUR-001) Escribir casos TC-PUR-001-P y TC-PUR-001-N: Solicitante se autoaprueba compra superior a su límite.
  - Depende de: F06-T05C. Archivos propuestos: `tests/F06/PUR-001.spec.ts;tests/fixtures/F06/`. Evidencia: TC-PUR-001-P;TC-PUR-001-N.

- [ ] **F06-T06B** (PUR-001) Implementar PUR-001: Solicitud se válida contra presupuesto/umbral; fuera de límite exige otro aprobador. Cambios materiales invalidan autorización anterior.
  - Depende de: F06-T06A. Archivos propuestos: `src/modules/compras-inventarios/pur-001.ts;src/modules/compras-inventarios/schemas.ts;db/migrations/`. Evidencia: PUR-001 reglas y migración revisadas.

- [ ] **F06-T06C** (PUR-001) Ejecutar ambos casos y revisar PUR-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F06-T06B. Archivos propuestos: `evidence/F06/PUR-001/;specs/007-compras-inventarios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F06-T07A** (PUR-002) Escribir casos TC-PUR-002-P y TC-PUR-002-N: Reenviar misma recepción o recibir veinte sin tolerancia aprobada.
  - Depende de: F06-T06C. Archivos propuestos: `tests/F06/PUR-002.spec.ts;tests/fixtures/F06/`. Evidencia: TC-PUR-002-P;TC-PUR-002-N.

- [ ] **F06-T07B** (PUR-002) Implementar PUR-002: Aumentar inventario sólo por cantidad aceptada en ubicacion/lote; pendiente calculado contra orden. Reversion requiere verificar consumo posterior.
  - Depende de: F06-T07A. Archivos propuestos: `src/modules/compras-inventarios/pur-002.ts;src/modules/compras-inventarios/schemas.ts;db/migrations/`. Evidencia: PUR-002 reglas y migración revisadas.

- [ ] **F06-T07C** (PUR-002) Ejecutar ambos casos y revisar PUR-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F06-T07B. Archivos propuestos: `evidence/F06/PUR-002/;specs/007-compras-inventarios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F06-T08A** (PUR-003) Escribir casos TC-PUR-003-P y TC-PUR-003-N: Factura diez cuando sólo llegaron ocho.
  - Depende de: F06-T07C. Archivos propuestos: `tests/F06/PUR-003.spec.ts;tests/fixtures/F06/`. Evidencia: TC-PUR-003-P;TC-PUR-003-N.

- [ ] **F06-T08B** (PUR-003) Implementar PUR-003: Comparación de tres fuentes conserva diferencias; factura puede registrarse para control pero pago queda bloqueado hasta aceptacion de excepción.
  - Depende de: F06-T08A. Archivos propuestos: `src/modules/compras-inventarios/pur-003.ts;src/modules/compras-inventarios/schemas.ts;db/migrations/`. Evidencia: PUR-003 reglas y migración revisadas.

- [ ] **F06-T08C** (PUR-003) Ejecutar ambos casos y revisar PUR-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F06-T08B. Archivos propuestos: `evidence/F06/PUR-003/;specs/007-compras-inventarios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F06-T09A** (PUR-004) Escribir casos TC-PUR-004-P y TC-PUR-004-N: Registrar dos veces mismo pago bancario a proveedor.
  - Depende de: F06-T08C. Archivos propuestos: `tests/F06/PUR-004.spec.ts;tests/fixtures/F06/`. Evidencia: TC-PUR-004-P;TC-PUR-004-N.

- [ ] **F06-T09B** (PUR-004) Implementar PUR-004: Saldo = deuda aprobada menos pagos aplicados y notas válidas; programación no es pago ejecutado. Reintento de registro no duplica salida.
  - Depende de: F06-T09A. Archivos propuestos: `src/modules/compras-inventarios/pur-004.ts;src/modules/compras-inventarios/schemas.ts;db/migrations/`. Evidencia: PUR-004 reglas y migración revisadas.

- [ ] **F06-T09C** (PUR-004) Ejecutar ambos casos y revisar PUR-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F06-T09B. Archivos propuestos: `evidence/F06/PUR-004/;specs/007-compras-inventarios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F06-T10A** (CAP-001) Escribir casos TC-CAP-001-P y TC-CAP-001-N: Comparar sólo precio por envase sin contenido o calidad.
  - Depende de: F06-T09C. Archivos propuestos: `tests/F06/CAP-001.spec.ts;tests/fixtures/F06/`. Evidencia: TC-CAP-001-P;TC-CAP-001-N.

- [ ] **F06-T10B** (CAP-001) Implementar CAP-001: Normalizar por unidad utilizable y calidad equivalente; separar cotización vigente de compra histórica. Costo total considera traslado y condiciones de impuesto aprobadas.
  - Depende de: F06-T10A. Archivos propuestos: `src/modules/compras-inventarios/cap-001.ts;src/modules/compras-inventarios/schemas.ts;db/migrations/`. Evidencia: CAP-001 reglas y migración revisadas.

- [ ] **F06-T10C** (CAP-001) Ejecutar ambos casos y revisar CAP-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F06-T10B. Archivos propuestos: `evidence/F06/CAP-001/;specs/007-compras-inventarios/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F06-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F06-T10C. Archivos propuestos: `specs/007-compras-inventarios/acceptance.md;evidence/F06/`. Evidencia: informe real por build; no autodeclaracion.
