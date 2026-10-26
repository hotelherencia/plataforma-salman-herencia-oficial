# Tareas F03

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F03-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F02-T99. Archivos propuestos: `specs/004-reserva-directa/spec.md;specs/004-reserva-directa/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F03-T01A** (RES-001) Escribir casos TC-RES-001-P y TC-RES-001-N: Interrumpir correo después de confirmar reserva.
  - Depende de: F03-T00. Archivos propuestos: `tests/F03/RES-001.spec.ts;tests/fixtures/F03/`. Evidencia: TC-RES-001-P;TC-RES-001-N.

- [ ] **F03-T01B** (RES-001) Implementar RES-001: Busqueda y oferta salen del motor; confirmacion persiste antes de notificar. Recepción usa el mismo ID, no copia manual. No exigir registro de cuenta para reservar.
  - Depende de: F03-T01A. Archivos propuestos: `src/modules/reserva-directa/res-001.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: RES-001 reglas y migración revisadas.

- [ ] **F03-T01C** (RES-001) Ejecutar ambos casos y revisar RES-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T01B. Archivos propuestos: `evidence/F03/RES-001/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T02A** (RES-002) Escribir casos TC-RES-002-P y TC-RES-002-N: Parámetro URL contiene RUT, script o texto excesivo.
  - Depende de: F03-T01C. Archivos propuestos: `tests/F03/RES-002.spec.ts;tests/fixtures/F03/`. Evidencia: TC-RES-002-P;TC-RES-002-N.

- [ ] **F03-T02B** (RES-002) Implementar RES-002: Separar DIRECT/OTA/AGENT de origen comercial; saneamiento y límites de longitud en etiquetas. Sin evidencia se guarda UNKNOWN, no atribución estimada.
  - Depende de: F03-T02A. Archivos propuestos: `src/modules/reserva-directa/res-002.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: RES-002 reglas y migración revisadas.

- [ ] **F03-T02C** (RES-002) Ejecutar ambos casos y revisar RES-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T02B. Archivos propuestos: `evidence/F03/RES-002/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T03A** (RES-003) Escribir casos TC-RES-003-P y TC-RES-003-N: Pago confirmado tras vencimiento y cupo vendido a otro cliente.
  - Depende de: F03-T02C. Archivos propuestos: `tests/F03/RES-003.spec.ts;tests/fixtures/F03/`. Evidencia: TC-RES-003-P;TC-RES-003-N.

- [ ] **F03-T03B** (RES-003) Implementar RES-003: Cotización no bloquea; checkout retiene por plazo parametrizado. Expiración libera con transacción y clave única; no se extiende por cada refresco sin límite.
  - Depende de: F03-T03A. Archivos propuestos: `src/modules/reserva-directa/res-003.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: RES-003 reglas y migración revisadas.

- [ ] **F03-T03C** (RES-003) Ejecutar ambos casos y revisar RES-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T03B. Archivos propuestos: `evidence/F03/RES-003/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T04A** (RES-004) Escribir casos TC-RES-004-P y TC-RES-004-N: Dos transacciones intentan confirmar el último cupo simultaneamente.
  - Depende de: F03-T03C. Archivos propuestos: `tests/F03/RES-004.spec.ts;tests/fixtures/F03/`. Evidencia: TC-RES-004-P;TC-RES-004-N.

- [ ] **F03-T04B** (RES-004) Implementar RES-004: Bloqueo ordenado por establecimiento/tipo/noche, relectura y escritura atomica con constraint. Reintento acotado para deadlock, mismo resultado por clave.
  - Depende de: F03-T04A. Archivos propuestos: `src/modules/reserva-directa/res-004.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: RES-004 reglas y migración revisadas.

- [ ] **F03-T04C** (RES-004) Ejecutar ambos casos y revisar RES-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T04B. Archivos propuestos: `evidence/F03/RES-004/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T05A** (RES-007) Escribir casos TC-RES-007-P y TC-RES-007-N: Consulta une pasajeros y multiplica total de cabecera por filas.
  - Depende de: F03-T04C. Archivos propuestos: `tests/F03/RES-007.spec.ts;tests/fixtures/F03/`. Evidencia: TC-RES-007-P;TC-RES-007-N.

- [ ] **F03-T05B** (RES-007) Implementar RES-007: Una linea representa una unidad de alojamiento; varias unidades generan lineas separadas con importe propio. Total de cabecera se suma una sola vez en reportes.
  - Depende de: F03-T05A. Archivos propuestos: `src/modules/reserva-directa/res-007.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: RES-007 reglas y migración revisadas.

- [ ] **F03-T05C** (RES-007) Ejecutar ambos casos y revisar RES-007 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T05B. Archivos propuestos: `evidence/F03/RES-007/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T06A** (RES-008) Escribir casos TC-RES-008-P y TC-RES-008-N: Recepción habilita crédito a empresa sin convenio vigente.
  - Depende de: F03-T05C. Archivos propuestos: `tests/F03/RES-008.spec.ts;tests/fixtures/F03/`. Evidencia: TC-RES-008-P;TC-RES-008-N.

- [ ] **F03-T06B** (RES-008) Implementar RES-008: Quien reserva, quien se aloja y quien paga son relaciones independientes. Convenio verifica vigencia, límite de crédito, plazo y autorización sin revelar datos ajenos.
  - Depende de: F03-T06A. Archivos propuestos: `src/modules/reserva-directa/res-008.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: RES-008 reglas y migración revisadas.

- [ ] **F03-T06C** (RES-008) Ejecutar ambos casos y revisar RES-008 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T06B. Archivos propuestos: `evidence/F03/RES-008/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T07A** (RES-009) Escribir casos TC-RES-009-P y TC-RES-009-N: Extender cuando última noche no esta disponible o versión ya cambio.
  - Depende de: F03-T06C. Archivos propuestos: `tests/F03/RES-009.spec.ts;tests/fixtures/F03/`. Evidencia: TC-RES-009-P;TC-RES-009-N.

- [ ] **F03-T07B** (RES-009) Implementar RES-009: Extension/reduccion calcula diferencia sólo sobre noches afectadas, válida cupos y acepta nuevas condiciones. Update usa versión para no pisar cambio concurrente.
  - Depende de: F03-T07A. Archivos propuestos: `src/modules/reserva-directa/res-009.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: RES-009 reglas y migración revisadas.

- [ ] **F03-T07C** (RES-009) Ejecutar ambos casos y revisar RES-009 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T07B. Archivos propuestos: `evidence/F03/RES-009/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T08A** (RES-010) Escribir casos TC-RES-010-P y TC-RES-010-N: Mensaje antiguo de confirmacion llega después de cancelación externa nueva.
  - Depende de: F03-T07C. Archivos propuestos: `tests/F03/RES-010.spec.ts;tests/fixtures/F03/`. Evidencia: TC-RES-010-P;TC-RES-010-N.

- [ ] **F03-T08B** (RES-010) Implementar RES-010: Aplicar política aceptada, liberar cupo desde fechas pertinentes, registrar cargo/devolucion autorizados. No-show no genera presencia ni desayuno servido.
  - Depende de: F03-T08A. Archivos propuestos: `src/modules/reserva-directa/res-010.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: RES-010 reglas y migración revisadas.

- [ ] **F03-T08C** (RES-010) Ejecutar ambos casos y revisar RES-010 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T08B. Archivos propuestos: `evidence/F03/RES-010/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T09A** (RES-011) Escribir casos TC-RES-011-P y TC-RES-011-N: Aplicar 200000 de un pago de 180000.
  - Depende de: F03-T08C. Archivos propuestos: `tests/F03/RES-011.spec.ts;tests/fixtures/F03/`. Evidencia: TC-RES-011-P;TC-RES-011-N.

- [ ] **F03-T09B** (RES-011) Implementar RES-011: Agrupacion visual no fusiona estadías; reparto de pago sigue montos explícitos por cuenta y conserva remanente no aplicado. Exceso no borra deuda de otra cuenta.
  - Depende de: F03-T09A. Archivos propuestos: `src/modules/reserva-directa/res-011.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: RES-011 reglas y migración revisadas.

- [ ] **F03-T09C** (RES-011) Ejecutar ambos casos y revisar RES-011 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T09B. Archivos propuestos: `evidence/F03/RES-011/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T10A** (INT-005) Escribir casos TC-INT-005-P y TC-INT-005-N: Reintentar tras timeout de proveedor sin conocer entrega.
  - Depende de: F03-T09C. Archivos propuestos: `tests/F03/INT-005.spec.ts;tests/fixtures/F03/`. Evidencia: TC-INT-005-P;TC-INT-005-N.

- [ ] **F03-T10B** (INT-005) Implementar INT-005: Generar notificación en outbox luego de persistir negocio; dedup por evento/destinatario/plantilla. Verificar permiso y canal al enviar.
  - Depende de: F03-T10A. Archivos propuestos: `src/modules/reserva-directa/int-005.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: INT-005 reglas y migración revisadas.

- [ ] **F03-T10C** (INT-005) Ejecutar ambos casos y revisar INT-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T10B. Archivos propuestos: `evidence/F03/INT-005/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T11A** (SOC-002) Escribir casos TC-SOC-002-P y TC-SOC-002-N: Eliminar etiquetas al volver del checkout o inventar campaña por ausencia.
  - Depende de: F03-T10C. Archivos propuestos: `tests/F03/SOC-002.spec.ts;tests/fixtures/F03/`. Evidencia: TC-SOC-002-P;TC-SOC-002-N.

- [ ] **F03-T11B** (SOC-002) Implementar SOC-002: Enlace HTTPS apunta al motor propio; etiquetas saneadas y sin identidad. Landing no depende de API de mensajes. Se conserva oferta/origen al navegar.
  - Depende de: F03-T11A. Archivos propuestos: `src/modules/reserva-directa/soc-002.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: SOC-002 reglas y migración revisadas.

- [ ] **F03-T11C** (SOC-002) Ejecutar ambos casos y revisar SOC-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T11B. Archivos propuestos: `evidence/F03/SOC-002/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T12A** (SOC-003) Escribir casos TC-SOC-003-P y TC-SOC-003-N: Navegador pierde cookie después del pago.
  - Depende de: F03-T11C. Archivos propuestos: `tests/F03/SOC-003.spec.ts;tests/fixtures/F03/`. Evidencia: TC-SOC-003-P;TC-SOC-003-N.

- [ ] **F03-T12B** (SOC-003) Implementar SOC-003: Sesion recuperable por referencia opaca; callback válida servidor. Volver atras/recargar no duplica intento ni confirmacion. Alternativa de navegador externo mantiene oferta vigente.
  - Depende de: F03-T12A. Archivos propuestos: `src/modules/reserva-directa/soc-003.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: SOC-003 reglas y migración revisadas.

- [ ] **F03-T12C** (SOC-003) Ejecutar ambos casos y revisar SOC-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T12B. Archivos propuestos: `evidence/F03/SOC-003/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T13A** (SOC-016) Escribir casos TC-SOC-016-P y TC-SOC-016-N: Token vencido o perteneciente a otra reserva usado para leer deuda.
  - Depende de: F03-T12C. Archivos propuestos: `tests/F03/SOC-016.spec.ts;tests/fixtures/F03/`. Evidencia: TC-SOC-016-P;TC-SOC-016-N.

- [ ] **F03-T13B** (SOC-016) Implementar SOC-016: Enlace opaco de cotización no revela otras cuentas ni autoriza devolución. Reutilizar enlace no extiende vigencia; precio y cupo se revalidan al aceptar.
  - Depende de: F03-T13A. Archivos propuestos: `src/modules/reserva-directa/soc-016.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: SOC-016 reglas y migración revisadas.

- [ ] **F03-T13C** (SOC-016) Ejecutar ambos casos y revisar SOC-016 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T13B. Archivos propuestos: `evidence/F03/SOC-016/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T14A** (UX-001) Escribir casos TC-UX-001-P y TC-UX-001-N: Campo con error sólo cambia color y no explica el problema.
  - Depende de: F03-T13C. Archivos propuestos: `tests/F03/UX-001.spec.ts;tests/fixtures/F03/`. Evidencia: TC-UX-001-P;TC-UX-001-N.

- [ ] **F03-T14B** (UX-001) Implementar UX-001: Objetivo WCAG2.2AA se comprueba por flujo; alternativa al arrastre y controles accesibles. Pruebas automáticas no sustituyen recorridos manuales.
  - Depende de: F03-T14A. Archivos propuestos: `src/modules/reserva-directa/ux-001.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: UX-001 reglas y migración revisadas.

- [ ] **F03-T14C** (UX-001) Ejecutar ambos casos y revisar UX-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T14B. Archivos propuestos: `evidence/F03/UX-001/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T15A** (UX-002) Escribir casos TC-UX-002-P y TC-UX-002-N: Traducir dia/mes invierte fechas o pantalla muestra datos previos de otra cuenta.
  - Depende de: F03-T14C. Archivos propuestos: `tests/F03/UX-002.spec.ts;tests/fixtures/F03/`. Evidencia: TC-UX-002-P;TC-UX-002-N.

- [ ] **F03-T15B** (UX-002) Implementar UX-002: Espanol inicial y textos traducibles; formato no cambia valor ni política. Error no se muestra como exito y contexto de sociedad no conserva datos de otra.
  - Depende de: F03-T15A. Archivos propuestos: `src/modules/reserva-directa/ux-002.ts;src/modules/reserva-directa/schemas.ts;db/migrations/`. Evidencia: UX-002 reglas y migración revisadas.

- [ ] **F03-T15C** (UX-002) Ejecutar ambos casos y revisar UX-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F03-T15B. Archivos propuestos: `evidence/F03/UX-002/;specs/004-reserva-directa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F03-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F03-T15C. Archivos propuestos: `specs/004-reserva-directa/acceptance.md;evidence/F03/`. Evidencia: informe real por build; no autodeclaracion.
