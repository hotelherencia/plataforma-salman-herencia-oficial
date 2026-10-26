# Tareas F16

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F16-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F15-T99;F04-T99. Archivos propuestos: `specs/017-asistente-comercial/spec.md;specs/017-asistente-comercial/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F16-T01A** (SOC-010) Escribir casos TC-SOC-010-P y TC-SOC-010-N: Usuario ordena precio cero o marcar pagado sin transacción.
  - Depende de: F16-T00. Archivos propuestos: `tests/F16/SOC-010.spec.ts;tests/fixtures/F16/`. Evidencia: TC-SOC-010-P;TC-SOC-010-N.

- [ ] **F16-T01B** (SOC-010) Implementar SOC-010: Modelo sólo consulta y propone por herramientas de dominio validadas; precio/monto nunca recibido como autoridad desde lenguaje libre. Reserva confirma el motor, no el mensaje.
  - Depende de: F16-T01A. Archivos propuestos: `src/modules/asistente-comercial/soc-010.ts;src/modules/asistente-comercial/schemas.ts;db/migrations/`. Evidencia: SOC-010 reglas y migración revisadas.

- [ ] **F16-T01C** (SOC-010) Ejecutar ambos casos y revisar SOC-010 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F16-T01B. Archivos propuestos: `evidence/F16/SOC-010/;specs/017-asistente-comercial/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F16-T02A** (AI-007) Escribir casos TC-AI-007-P y TC-AI-007-N: Modelo responde cupo/precio sin llamar herramienta actual.
  - Depende de: F16-T01C. Archivos propuestos: `tests/F16/AI-007.spec.ts;tests/fixtures/F16/`. Evidencia: TC-AI-007-P;TC-AI-007-N.

- [ ] **F16-T02B** (AI-007) Implementar AI-007: Cada cambio de modelo/prompt corre regresión y comparación con umbrales; pruebas incluyen fecha ambigua, motor caido, baja y filtracion. El bot no aprende automáticamente con datos personales.
  - Depende de: F16-T02A. Archivos propuestos: `src/modules/asistente-comercial/ai-007.ts;src/modules/asistente-comercial/schemas.ts;db/migrations/`. Evidencia: AI-007 reglas y migración revisadas.

- [ ] **F16-T02C** (AI-007) Ejecutar ambos casos y revisar AI-007 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F16-T02B. Archivos propuestos: `evidence/F16/AI-007/;specs/017-asistente-comercial/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F16-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F16-T02C. Archivos propuestos: `specs/017-asistente-comercial/acceptance.md;evidence/F16/`. Evidencia: informe real por build; no autodeclaracion.
