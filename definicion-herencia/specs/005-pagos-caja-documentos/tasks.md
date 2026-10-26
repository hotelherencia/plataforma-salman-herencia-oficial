# Tareas F04

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F04-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F03-T99. Archivos propuestos: `specs/005-pagos-caja-documentos/spec.md;specs/005-pagos-caja-documentos/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F04-T01A** (PAY-001) Escribir casos TC-PAY-001-P y TC-PAY-001-N: Clasificar garantía por daños como venta del día automáticamente.
  - Depende de: F04-T00. Archivos propuestos: `tests/F04/PAY-001.spec.ts;tests/fixtures/F04/`. Evidencia: TC-PAY-001-P;TC-PAY-001-N.

- [ ] **F04-T01B** (PAY-001) Implementar PAY-001: Anticipo reduce saldo comercial al aplicarse pero no registra servicio prestado. Garantía tiene circuito separado y aplicación autorizada. Saldo heredado no es caja propia.
  - Depende de: F04-T01A. Archivos propuestos: `src/modules/pagos-caja-documentos/pay-001.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: PAY-001 reglas y migración revisadas.

- [ ] **F04-T01C** (PAY-001) Ejecutar ambos casos y revisar PAY-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T01B. Archivos propuestos: `evidence/F04/PAY-001/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T02A** (PAY-002) Escribir casos TC-PAY-002-P y TC-PAY-002-N: Dos operadores aplican simultaneamente el mismo saldo de pago.
  - Depende de: F04-T01C. Archivos propuestos: `tests/F04/PAY-002.spec.ts;tests/fixtures/F04/`. Evidencia: TC-PAY-002-P;TC-PAY-002-N.

- [ ] **F04-T02B** (PAY-002) Implementar PAY-002: Suma de asignaciones activas no excede pago disponible ni saldo elegible; conservar excedente a favor. Validar moneda y bloquear filas de pago/cuenta.
  - Depende de: F04-T02A. Archivos propuestos: `src/modules/pagos-caja-documentos/pay-002.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: PAY-002 reglas y migración revisadas.

- [ ] **F04-T02C** (PAY-002) Ejecutar ambos casos y revisar PAY-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T02B. Archivos propuestos: `evidence/F04/PAY-002/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T03A** (PAY-003) Escribir casos TC-PAY-003-P y TC-PAY-003-N: Cliente envia success=true o token de otra orden.
  - Depende de: F04-T02C. Archivos propuestos: `tests/F04/PAY-003.spec.ts;tests/fixtures/F04/`. Evidencia: TC-PAY-003-P;TC-PAY-003-N.

- [ ] **F04-T03B** (PAY-003) Implementar PAY-003: Confirmar por servidor usando flujo del proveedor; verificar orden, monto, moneda y estado. Browser return sólo inicia verificación; unknown requiere consulta.
  - Depende de: F04-T03A. Archivos propuestos: `src/modules/pagos-caja-documentos/pay-003.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: PAY-003 reglas y migración revisadas.

- [ ] **F04-T03C** (PAY-003) Ejecutar ambos casos y revisar PAY-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T03B. Archivos propuestos: `evidence/F04/PAY-003/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T04A** (PAY-004) Escribir casos TC-PAY-004-P y TC-PAY-004-N: Reintentar tras timeout sin conocer si proveedor cargo.
  - Depende de: F04-T03C. Archivos propuestos: `tests/F04/PAY-004.spec.ts;tests/fixtures/F04/`. Evidencia: TC-PAY-004-P;TC-PAY-004-N.

- [ ] **F04-T04B** (PAY-004) Implementar PAY-004: Constraint único y transacción local; eventos repetidos retornan resultado previo. Payload distinto con mismo ID se investiga; notificación no crea otro pago.
  - Depende de: F04-T04A. Archivos propuestos: `src/modules/pagos-caja-documentos/pay-004.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: PAY-004 reglas y migración revisadas.

- [ ] **F04-T04C** (PAY-004) Ejecutar ambos casos y revisar PAY-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T04B. Archivos propuestos: `evidence/F04/PAY-004/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T05A** (PAY-005) Escribir casos TC-PAY-005-P y TC-PAY-005-N: Dos devoluciones concurrentes que superan saldo disponible.
  - Depende de: F04-T04C. Archivos propuestos: `tests/F04/PAY-005.spec.ts;tests/fixtures/F04/`. Evidencia: TC-PAY-005-P;TC-PAY-005-N.

- [ ] **F04-T05B** (PAY-005) Implementar PAY-005: Reservar saldo reembolsable para impedir devoluciones simultaneas; estado desconocido no se reenvia ciegamente. Contracargo es disputa, no borrado de servicio.
  - Depende de: F04-T05A. Archivos propuestos: `src/modules/pagos-caja-documentos/pay-005.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: PAY-005 reglas y migración revisadas.

- [ ] **F04-T05C** (PAY-005) Ejecutar ambos casos y revisar PAY-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T05B. Archivos propuestos: `evidence/F04/PAY-005/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T06A** (PAY-006) Escribir casos TC-PAY-006-P y TC-PAY-006-N: Conteo 39000 y operador intenta cambiar una venta para cuadrar.
  - Depende de: F04-T05C. Archivos propuestos: `tests/F04/PAY-006.spec.ts;tests/fixtures/F04/`. Evidencia: TC-PAY-006-P;TC-PAY-006-N.

- [ ] **F04-T06B** (PAY-006) Implementar PAY-006: Calcular esperado sólo con efectivo; comparar contado, diferencia y firma de entrega. Tarjetas no incrementan cajon físico.
  - Depende de: F04-T06A. Archivos propuestos: `src/modules/pagos-caja-documentos/pay-006.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: PAY-006 reglas y migración revisadas.

- [ ] **F04-T06C** (PAY-006) Ejecutar ambos casos y revisar PAY-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T06B. Archivos propuestos: `evidence/F04/PAY-006/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T07A** (PAY-007) Escribir casos TC-PAY-007-P y TC-PAY-007-N: Depósito por 19000 para retiro de 20000.
  - Depende de: F04-T06C. Archivos propuestos: `tests/F04/PAY-007.spec.ts;tests/fixtures/F04/`. Evidencia: TC-PAY-007-P;TC-PAY-007-N.

- [ ] **F04-T07B** (PAY-007) Implementar PAY-007: Retiro/deposito se vinculan por traslado en transito, no gasto. Diferencia entre retirado y depositado se investiga con responsables.
  - Depende de: F04-T07A. Archivos propuestos: `src/modules/pagos-caja-documentos/pay-007.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: PAY-007 reglas y migración revisadas.

- [ ] **F04-T07C** (PAY-007) Ejecutar ambos casos y revisar PAY-007 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T07B. Archivos propuestos: `evidence/F04/PAY-007/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T08A** (PAY-008) Escribir casos TC-PAY-008-P y TC-PAY-008-N: Recepcionista intenta reabrir turno ya aprobado.
  - Depende de: F04-T07C. Archivos propuestos: `tests/F04/PAY-008.spec.ts;tests/fixtures/F04/`. Evidencia: TC-PAY-008-P;TC-PAY-008-N.

- [ ] **F04-T08B** (PAY-008) Implementar PAY-008: Cierre congela movimientos; corrección por reapertura autorizada o ajuste posterior segun política. Control de fecha y versión evita edicion concurrente.
  - Depende de: F04-T08A. Archivos propuestos: `src/modules/pagos-caja-documentos/pay-008.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: PAY-008 reglas y migración revisadas.

- [ ] **F04-T08C** (PAY-008) Ejecutar ambos casos y revisar PAY-008 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T08B. Archivos propuestos: `evidence/F04/PAY-008/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T09A** (TAX-001) Escribir casos TC-TAX-001-P y TC-TAX-001-N: Proveedor rechaza documento por dato tributario inválido.
  - Depende de: F04-T08C. Archivos propuestos: `tests/F04/TAX-001.spec.ts;tests/fixtures/F04/`. Evidencia: TC-TAX-001-P;TC-TAX-001-N.

- [ ] **F04-T09B** (TAX-001) Implementar TAX-001: Enviar sólo con emisor habilitado y regla aprobada; documento acepta estado real del proveedor. Factura borrador no tiene folio oficial inventado.
  - Depende de: F04-T09A. Archivos propuestos: `src/modules/pagos-caja-documentos/tax-001.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: TAX-001 reglas y migración revisadas.

- [ ] **F04-T09C** (TAX-001) Ejecutar ambos casos y revisar TAX-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T09B. Archivos propuestos: `evidence/F04/TAX-001/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T10A** (TAX-002) Escribir casos TC-TAX-002-P y TC-TAX-002-N: Huésped extranjero sin evidencia suficiente pide tarifa exenta.
  - Depende de: F04-T09C. Archivos propuestos: `tests/F04/TAX-002.spec.ts;tests/fixtures/F04/`. Evidencia: TC-TAX-002-P;TC-TAX-002-N.

- [ ] **F04-T10B** (TAX-002) Implementar TAX-002: Regla tributaria con vigencia y responsable; validar condiciones documentadas. No inferir exención de pasaporte extranjero por si sólo.
  - Depende de: F04-T10A. Archivos propuestos: `src/modules/pagos-caja-documentos/tax-002.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: TAX-002 reglas y migración revisadas.

- [ ] **F04-T10C** (TAX-002) Ejecutar ambos casos y revisar TAX-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T10B. Archivos propuestos: `evidence/F04/TAX-002/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T11A** (TAX-003) Escribir casos TC-TAX-003-P y TC-TAX-003-N: Eliminar factura para ocultar error o emitir dos notas iguales por reintento.
  - Depende de: F04-T10C. Archivos propuestos: `tests/F04/TAX-003.spec.ts;tests/fixtures/F04/`. Evidencia: TC-TAX-003-P;TC-TAX-003-N.

- [ ] **F04-T11B** (TAX-003) Implementar TAX-003: Notas corrigen documento manteniendo referencia y saldos; emision/nota no duplican cargo o pago. Rechazo de nota mantiene diferencia pendiente.
  - Depende de: F04-T11A. Archivos propuestos: `src/modules/pagos-caja-documentos/tax-003.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: TAX-003 reglas y migración revisadas.

- [ ] **F04-T11C** (TAX-003) Ejecutar ambos casos y revisar TAX-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T11B. Archivos propuestos: `evidence/F04/TAX-003/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T12A** (SEC-008) Escribir casos TC-SEC-008-P y TC-SEC-008-N: Manipular ID o amount en URL para pagar menos o leer otra cuenta.
  - Depende de: F04-T11C. Archivos propuestos: `tests/F04/SEC-008.spec.ts;tests/fixtures/F04/`. Evidencia: TC-SEC-008-P;TC-SEC-008-N.

- [ ] **F04-T12B** (SEC-008) Implementar SEC-008: Token de pago sólo inicia/consulta su intento; no concede reembolso o acceso global. Almacenamiento de hash y redaccion de URL en logs.
  - Depende de: F04-T12A. Archivos propuestos: `src/modules/pagos-caja-documentos/sec-008.ts;src/modules/pagos-caja-documentos/schemas.ts;db/migrations/`. Evidencia: SEC-008 reglas y migración revisadas.

- [ ] **F04-T12C** (SEC-008) Ejecutar ambos casos y revisar SEC-008 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F04-T12B. Archivos propuestos: `evidence/F04/SEC-008/;specs/005-pagos-caja-documentos/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F04-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F04-T12C. Archivos propuestos: `specs/005-pagos-caja-documentos/acceptance.md;evidence/F04/`. Evidencia: informe real por build; no autodeclaracion.
