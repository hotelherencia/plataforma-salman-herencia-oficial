# Tareas F15

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F15-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F14-T99. Archivos propuestos: `specs/016-mensajeria-social/spec.md;specs/016-mensajeria-social/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F15-T01A** (SOC-007) Escribir casos TC-SOC-007-P y TC-SOC-007-N: Fuera de ventana se intenta enviar texto libre promocional.
  - Depende de: F15-T00. Archivos propuestos: `tests/F15/SOC-007.spec.ts;tests/fixtures/F15/`. Evidencia: TC-SOC-007-P;TC-SOC-007-N.

- [ ] **F15-T01B** (SOC-007) Implementar SOC-007: Validar politica/ventana y plantilla en el instante de envio, no sólo al programar. Baja elimina promociones de cola; comunicación contractual usa via permitida.
  - Depende de: F15-T01A. Archivos propuestos: `src/modules/mensajeria-social/soc-007.ts;src/modules/mensajeria-social/schemas.ts;db/migrations/`. Evidencia: SOC-007 reglas y migración revisadas.

- [ ] **F15-T01C** (SOC-007) Ejecutar ambos casos y revisar SOC-007 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F15-T01B. Archivos propuestos: `evidence/F15/SOC-007/;specs/016-mensajeria-social/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F15-T02A** (SOC-008) Escribir casos TC-SOC-008-P y TC-SOC-008-N: API rechaza permiso y app afirma mensaje enviado.
  - Depende de: F15-T01C. Archivos propuestos: `tests/F15/SOC-008.spec.ts;tests/fixtures/F15/`. Evidencia: TC-SOC-008-P;TC-SOC-008-N.

- [ ] **F15-T02B** (SOC-008) Implementar SOC-008: Elegir via Instagram/Messenger y documentar sus requisitos sin mezclarlos. Mensajes sólo dentro de capacidades autorizadas; token revocado cancela acceso.
  - Depende de: F15-T02A. Archivos propuestos: `src/modules/mensajeria-social/soc-008.ts;src/modules/mensajeria-social/schemas.ts;db/migrations/`. Evidencia: SOC-008 reglas y migración revisadas.

- [ ] **F15-T02C** (SOC-008) Ejecutar ambos casos y revisar SOC-008 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F15-T02B. Archivos propuestos: `evidence/F15/SOC-008/;specs/016-mensajeria-social/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F15-T03A** (SOC-011) Escribir casos TC-SOC-011-P y TC-SOC-011-N: Firma inválida o misma ID con contenido alterado.
  - Depende de: F15-T02C. Archivos propuestos: `tests/F15/SOC-011.spec.ts;tests/fixtures/F15/`. Evidencia: TC-SOC-011-P;TC-SOC-011-N.

- [ ] **F15-T03B** (SOC-011) Implementar SOC-011: Verificar autenticidad, límite de tamaño y cuenta, persistir inbox y responder rápido; procesar en cola con deduplicacion y orden segun revisión. No loguear cuerpo sensible completo.
  - Depende de: F15-T03A. Archivos propuestos: `src/modules/mensajeria-social/soc-011.ts;src/modules/mensajeria-social/schemas.ts;db/migrations/`. Evidencia: SOC-011 reglas y migración revisadas.

- [ ] **F15-T03C** (SOC-011) Ejecutar ambos casos y revisar SOC-011 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F15-T03B. Archivos propuestos: `evidence/F15/SOC-011/;specs/016-mensajeria-social/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F15-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F15-T03C. Archivos propuestos: `specs/016-mensajeria-social/acceptance.md;evidence/F15/`. Evidencia: informe real por build; no autodeclaracion.
