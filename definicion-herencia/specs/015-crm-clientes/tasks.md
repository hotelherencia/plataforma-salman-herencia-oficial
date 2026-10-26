# Tareas F14

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F14-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F03-T99;F01-T99. Archivos propuestos: `specs/015-crm-clientes/spec.md;specs/015-crm-clientes/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F14-T01A** (SOC-001) Escribir casos TC-SOC-001-P y TC-SOC-001-N: Marcar toda cuenta META integrada al validar un sólo permiso.
  - Depende de: F14-T00. Archivos propuestos: `tests/F14/SOC-001.spec.ts;tests/fixtures/F14/`. Evidencia: TC-SOC-001-P;TC-SOC-001-N.

- [ ] **F14-T01B** (SOC-001) Implementar SOC-001: Inventario digital por cuenta y capacidad, evidencia y vigencia. Transferir permisos institucionales, no contraseñas personales; revocacion parcial no apaga funciones ajenas.
  - Depende de: F14-T01A. Archivos propuestos: `src/modules/crm-clientes/soc-001.ts;src/modules/crm-clientes/schemas.ts;db/migrations/`. Evidencia: SOC-001 reglas y migración revisadas.

- [ ] **F14-T01C** (SOC-001) Ejecutar ambos casos y revisar SOC-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F14-T01B. Archivos propuestos: `evidence/F14/SOC-001/;specs/015-crm-clientes/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F14-T02A** (SOC-004) Escribir casos TC-SOC-004-P y TC-SOC-004-N: Agente marca venta por un mensaje de interes sin reserva.
  - Depende de: F14-T01C. Archivos propuestos: `tests/F14/SOC-004.spec.ts;tests/fixtures/F14/`. Evidencia: TC-SOC-004-P;TC-SOC-004-N.

- [ ] **F14-T02B** (SOC-004) Implementar SOC-004: Estados comerciales no equivalen a inventario ni ingreso. Ganada exige reserva confirmada vinculada; pérdida documenta razón sin borrado de historial.
  - Depende de: F14-T02A. Archivos propuestos: `src/modules/crm-clientes/soc-004.ts;src/modules/crm-clientes/schemas.ts;db/migrations/`. Evidencia: SOC-004 reglas y migración revisadas.

- [ ] **F14-T02C** (SOC-004) Ejecutar ambos casos y revisar SOC-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F14-T02B. Archivos propuestos: `evidence/F14/SOC-004/;specs/015-crm-clientes/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F14-T03A** (SOC-005) Escribir casos TC-SOC-005-P y TC-SOC-005-N: Dos personas se llaman Ana y el sistema mezcla conversaciones.
  - Depende de: F14-T02C. Archivos propuestos: `tests/F14/SOC-005.spec.ts;tests/fixtures/F14/`. Evidencia: TC-SOC-005-P;TC-SOC-005-N.

- [ ] **F14-T03B** (SOC-005) Implementar SOC-005: Identidades scoped se vinculan sólo con evidencia; fusion revisable y reversible. Nunca usar coincidencia de nombre como autenticación.
  - Depende de: F14-T03A. Archivos propuestos: `src/modules/crm-clientes/soc-005.ts;src/modules/crm-clientes/schemas.ts;db/migrations/`. Evidencia: SOC-005 reglas y migración revisadas.

- [ ] **F14-T03C** (SOC-005) Ejecutar ambos casos y revisar SOC-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F14-T03B. Archivos propuestos: `evidence/F14/SOC-005/;specs/015-crm-clientes/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F14-T04A** (SOC-006) Escribir casos TC-SOC-006-P y TC-SOC-006-N: Respuesta bot en cola intenta salir después de handoff.
  - Depende de: F14-T03C. Archivos propuestos: `tests/F14/SOC-006.spec.ts;tests/fixtures/F14/`. Evidencia: TC-SOC-006-P;TC-SOC-006-N.

- [ ] **F14-T04B** (SOC-006) Implementar SOC-006: Toma humana compare-and-set pausa bot antes de enviar respuesta; mensajes pendientes del bot se cancelan o revisan. El historial conserva responsable.
  - Depende de: F14-T04A. Archivos propuestos: `src/modules/crm-clientes/soc-006.ts;src/modules/crm-clientes/schemas.ts;db/migrations/`. Evidencia: SOC-006 reglas y migración revisadas.

- [ ] **F14-T04C** (SOC-006) Ejecutar ambos casos y revisar SOC-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F14-T04B. Archivos propuestos: `evidence/F14/SOC-006/;specs/015-crm-clientes/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F14-T05A** (SOC-009) Escribir casos TC-SOC-009-P y TC-SOC-009-N: Turno saliente cierra sesion dejando reclamo urgente sin receptor.
  - Depende de: F14-T04C. Archivos propuestos: `tests/F14/SOC-009.spec.ts;tests/fixtures/F14/`. Evidencia: TC-SOC-009-P;TC-SOC-009-N.

- [ ] **F14-T05B** (SOC-009) Implementar SOC-009: Plazos y cobertura D28 configurables; escalar consultas sin respuesta y ofertas por vencer. Cambio de turno no resetea plazo ni borra responsable anterior.
  - Depende de: F14-T05A. Archivos propuestos: `src/modules/crm-clientes/soc-009.ts;src/modules/crm-clientes/schemas.ts;db/migrations/`. Evidencia: SOC-009 reglas y migración revisadas.

- [ ] **F14-T05C** (SOC-009) Ejecutar ambos casos y revisar SOC-009 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F14-T05B. Archivos propuestos: `evidence/F14/SOC-009/;specs/015-crm-clientes/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F14-T06A** (SOC-013) Escribir casos TC-SOC-013-P y TC-SOC-013-N: Lista antigua vuelve a suscribir al cliente sin nueva evidencia.
  - Depende de: F14-T05C. Archivos propuestos: `tests/F14/SOC-013.spec.ts;tests/fixtures/F14/`. Evidencia: TC-SOC-013-P;TC-SOC-013-N.

- [ ] **F14-T06B** (SOC-013) Implementar SOC-013: Separar servicio, contacto y marketing; permiso verificable y baja efectiva antes de cada envio. Rechazar publicidad no bloquea reserva o derechos.
  - Depende de: F14-T06A. Archivos propuestos: `src/modules/crm-clientes/soc-013.ts;src/modules/crm-clientes/schemas.ts;db/migrations/`. Evidencia: SOC-013 reglas y migración revisadas.

- [ ] **F14-T06C** (SOC-013) Ejecutar ambos casos y revisar SOC-013 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F14-T06B. Archivos propuestos: `evidence/F14/SOC-013/;specs/015-crm-clientes/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F14-T07A** (SOC-017) Escribir casos TC-SOC-017-P y TC-SOC-017-N: Visitante anonimo sin contacto se intenta contactar automáticamente.
  - Depende de: F14-T06C. Archivos propuestos: `tests/F14/SOC-017.spec.ts;tests/fixtures/F14/`. Evidencia: TC-SOC-017-P;TC-SOC-017-N.

- [ ] **F14-T07B** (SOC-017) Implementar SOC-017: Seguimiento sólo con contacto obtenido legitimamente y permiso adecuado; máximo configurable y baja inmediata. Oferta vencida no mantiene cupo.
  - Depende de: F14-T07A. Archivos propuestos: `src/modules/crm-clientes/soc-017.ts;src/modules/crm-clientes/schemas.ts;db/migrations/`. Evidencia: SOC-017 reglas y migración revisadas.

- [ ] **F14-T07C** (SOC-017) Ejecutar ambos casos y revisar SOC-017 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F14-T07B. Archivos propuestos: `evidence/F14/SOC-017/;specs/015-crm-clientes/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F14-T08A** (SEC-007) Escribir casos TC-SEC-007-P y TC-SEC-007-N: Payload conversion contiene documento del huésped.
  - Depende de: F14-T07C. Archivos propuestos: `tests/F14/SEC-007.spec.ts;tests/fixtures/F14/`. Evidencia: TC-SEC-007-P;TC-SEC-007-N.

- [ ] **F14-T08B** (SEC-007) Implementar SEC-007: Excluir RUT, pasaporte, tarjeta, conversaciones y restricciones sensibles de publicidad. Hash no vuelve automáticamente anonimo un identificador. Permisos antes de enviar.
  - Depende de: F14-T08A. Archivos propuestos: `src/modules/crm-clientes/sec-007.ts;src/modules/crm-clientes/schemas.ts;db/migrations/`. Evidencia: SEC-007 reglas y migración revisadas.

- [ ] **F14-T08C** (SEC-007) Ejecutar ambos casos y revisar SEC-007 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F14-T08B. Archivos propuestos: `evidence/F14/SEC-007/;specs/015-crm-clientes/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F14-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F14-T08C. Archivos propuestos: `specs/015-crm-clientes/acceptance.md;evidence/F14/`. Evidencia: informe real por build; no autodeclaracion.
