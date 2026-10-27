# Tareas F18

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F18-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F05-T99;F14-T99. Archivos propuestos: `specs/019-portal-huesped/spec.md;specs/019-portal-huesped/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F18-T01A** (GEX-001) Escribir casos TC-GEX-001-P y TC-GEX-001-N: Conocer apellido/habitacion o token de otro huésped.
  - Depende de: F18-T00. Archivos propuestos: `tests/F18/GEX-001.spec.ts;tests/fixtures/F18/`. Evidencia: TC-GEX-001-P;TC-GEX-001-N.

- [ ] **F18-T01B** (GEX-001) Implementar GEX-001: Token opaco limitado y revocable; para datos/documentos sensibles exigir verificación adicional acordada. Mostrar sólo titular/reserva autorizada.
  - Depende de: F18-T01A. Archivos propuestos: `src/modules/portal-huesped/gex-001.ts;src/modules/portal-huesped/schemas.ts;db/migrations/`. Evidencia: GEX-001 reglas y migración revisadas.

- [ ] **F18-T01C** (GEX-001) Ejecutar ambos casos y revisar GEX-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F18-T01B. Archivos propuestos: `evidence/F18/GEX-001/;specs/019-portal-huesped/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F18-T02A** (GEX-002) Escribir casos TC-GEX-002-P y TC-GEX-002-N: Marketing intenta acceder al relato sensible o ticket se cierra sin resolver.
  - Depende de: F18-T01C. Archivos propuestos: `tests/F18/GEX-002.spec.ts;tests/fixtures/F18/`. Evidencia: TC-GEX-002-P;TC-GEX-002-N.

- [ ] **F18-T02B** (GEX-002) Implementar GEX-002: Solicitud se convierte en tarea/orden vinculada; comunicación al huésped sin mostrar datos internos. Cierre requiere evidencia o respuesta, con reapertura posible.
  - Depende de: F18-T02A. Archivos propuestos: `src/modules/portal-huesped/gex-002.ts;src/modules/portal-huesped/schemas.ts;db/migrations/`. Evidencia: GEX-002 reglas y migración revisadas.

- [ ] **F18-T02C** (GEX-002) Ejecutar ambos casos y revisar GEX-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F18-T02B. Archivos propuestos: `evidence/F18/GEX-002/;specs/019-portal-huesped/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F18-T03A** (GEX-003) Escribir casos TC-GEX-003-P y TC-GEX-003-N: Agente pública reseña inventada o descuento no autorizado.
  - Depende de: F18-T02C. Archivos propuestos: `tests/F18/GEX-003.spec.ts;tests/fixtures/F18/`. Evidencia: TC-GEX-003-P;TC-GEX-003-N.

- [ ] **F18-T03B** (GEX-003) Implementar GEX-003: Beneficios versionados y autorizados; no condicionar atención a reseña positiva ni fabricar opiniones. Baja comercial persiste incluso con fidelidad activa.
  - Depende de: F18-T03A. Archivos propuestos: `src/modules/portal-huesped/gex-003.ts;src/modules/portal-huesped/schemas.ts;db/migrations/`. Evidencia: GEX-003 reglas y migración revisadas.

- [ ] **F18-T03C** (GEX-003) Ejecutar ambos casos y revisar GEX-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F18-T03B. Archivos propuestos: `evidence/F18/GEX-003/;specs/019-portal-huesped/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F18-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F18-T03C. Archivos propuestos: `specs/019-portal-huesped/acceptance.md;evidence/F18/`. Evidencia: informe real por build; no autodeclaracion.
