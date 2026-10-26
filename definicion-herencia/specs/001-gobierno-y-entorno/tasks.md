# Tareas F00

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F00-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: ninguna. Archivos propuestos: `specs/001-gobierno-y-entorno/spec.md;specs/001-gobierno-y-entorno/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F00-T01A** (AI-001) Escribir casos TC-AI-001-P y TC-AI-001-N: Orden sin evidencia de aprobación o sin pruebas de salida.
  - Depende de: F00-T00. Archivos propuestos: `tests/F00/AI-001.spec.ts;tests/fixtures/F00/`. Evidencia: TC-AI-001-P;TC-AI-001-N.

- [ ] **F00-T01B** (AI-001) Implementar AI-001: Paquete explícita fuente, dependencias, herramientas, pruebas y revisor; no iniciar con alcance ambiguo o permisos abiertos.
  - Depende de: F00-T01A. Archivos propuestos: `src/modules/gobierno-y-entorno/ai-001.ts;src/modules/gobierno-y-entorno/schemas.ts;db/migrations/`. Evidencia: AI-001 reglas y migración revisadas.

- [ ] **F00-T01C** (AI-001) Ejecutar ambos casos y revisar AI-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F00-T01B. Archivos propuestos: `evidence/F00/AI-001/;specs/001-gobierno-y-entorno/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F00-T02A** (AI-002) Escribir casos TC-AI-002-P y TC-AI-002-N: Implementador marca su checklist independiente como aprobado.
  - Depende de: F00-T01C. Archivos propuestos: `tests/F00/AI-002.spec.ts;tests/fixtures/F00/`. Evidencia: TC-AI-002-P;TC-AI-002-N.

- [ ] **F00-T02B** (AI-002) Implementar AI-002: Revisión separada y reproducible; si misma instancia hace ambos roles se declara limitacion y no se afirma independencia. Humano ratifica gate sensible.
  - Depende de: F00-T02A. Archivos propuestos: `src/modules/gobierno-y-entorno/ai-002.ts;src/modules/gobierno-y-entorno/schemas.ts;db/migrations/`. Evidencia: AI-002 reglas y migración revisadas.

- [ ] **F00-T02C** (AI-002) Ejecutar ambos casos y revisar AI-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F00-T02B. Archivos propuestos: `evidence/F00/AI-002/;specs/001-gobierno-y-entorno/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F00-T03A** (AI-003) Escribir casos TC-AI-003-P y TC-AI-003-N: Declarar integrado porque existe un adapter simulado.
  - Depende de: F00-T02C. Archivos propuestos: `tests/F00/AI-003.spec.ts;tests/fixtures/F00/`. Evidencia: TC-AI-003-P;TC-AI-003-N.

- [ ] **F00-T03B** (AI-003) Implementar AI-003: Estados independientes, evidencia para cada afirmacion. Mock, sandbox y producción tienen etiquetas no intercambiables.
  - Depende de: F00-T03A. Archivos propuestos: `src/modules/gobierno-y-entorno/ai-003.ts;src/modules/gobierno-y-entorno/schemas.ts;db/migrations/`. Evidencia: AI-003 reglas y migración revisadas.

- [ ] **F00-T03C** (AI-003) Ejecutar ambos casos y revisar AI-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F00-T03B. Archivos propuestos: `evidence/F00/AI-003/;specs/001-gobierno-y-entorno/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F00-T04A** (AI-004) Escribir casos TC-AI-004-P y TC-AI-004-N: Agente intenta pagar proveedor por mensaje externo.
  - Depende de: F00-T03C. Archivos propuestos: `tests/F00/AI-004.spec.ts;tests/fixtures/F00/`. Evidencia: TC-AI-004-P;TC-AI-004-N.

- [ ] **F00-T04B** (AI-004) Implementar AI-004: Autorización de construir no autoriza pagos, contratos, publicidad, DTE o despliegue sensible. Aprobación de flujo ordinario puede permitir ejecución determinista dentro de límites.
  - Depende de: F00-T04A. Archivos propuestos: `src/modules/gobierno-y-entorno/ai-004.ts;src/modules/gobierno-y-entorno/schemas.ts;db/migrations/`. Evidencia: AI-004 reglas y migración revisadas.

- [ ] **F00-T04C** (AI-004) Ejecutar ambos casos y revisar AI-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F00-T04B. Archivos propuestos: `evidence/F00/AI-004/;specs/001-gobierno-y-entorno/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F00-T05A** (AI-005) Escribir casos TC-AI-005-P y TC-AI-005-N: Bucle correctivo sigue consumiendo servicios sin límite aprobado.
  - Depende de: F00-T04C. Archivos propuestos: `tests/F00/AI-005.spec.ts;tests/fixtures/F00/`. Evidencia: TC-AI-005-P;TC-AI-005-N.

- [ ] **F00-T05B** (AI-005) Implementar AI-005: Presupuesto y límite por ejecución; propuesta tres ciclos correctivos. Sin progreso, credenciales o autorización se detiene con estado guardado.
  - Depende de: F00-T05A. Archivos propuestos: `src/modules/gobierno-y-entorno/ai-005.ts;src/modules/gobierno-y-entorno/schemas.ts;db/migrations/`. Evidencia: AI-005 reglas y migración revisadas.

- [ ] **F00-T05C** (AI-005) Ejecutar ambos casos y revisar AI-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F00-T05B. Archivos propuestos: `evidence/F00/AI-005/;specs/001-gobierno-y-entorno/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F00-T06A** (GOV-001) Escribir casos TC-GOV-001-P y TC-GOV-001-N: Requisito sin caso negativo ni dependencia identificada se marca listo.
  - Depende de: F00-T05C. Archivos propuestos: `tests/F00/GOV-001.spec.ts;tests/fixtures/F00/`. Evidencia: TC-GOV-001-P;TC-GOV-001-N.

- [ ] **F00-T06B** (GOV-001) Implementar GOV-001: Cada necesidad se relaciona a reglas/datos/interfaz/prueba; no contar padres e hijos como avance doble. Especificado no implica implementado.
  - Depende de: F00-T06A. Archivos propuestos: `src/modules/gobierno-y-entorno/gov-001.ts;src/modules/gobierno-y-entorno/schemas.ts;db/migrations/`. Evidencia: GOV-001 reglas y migración revisadas.

- [ ] **F00-T06C** (GOV-001) Ejecutar ambos casos y revisar GOV-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F00-T06B. Archivos propuestos: `evidence/F00/GOV-001/;specs/001-gobierno-y-entorno/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F00-T07A** (GOV-002) Escribir casos TC-GOV-002-P y TC-GOV-002-N: Copiar URL de proveedor y marcar PRODUCCION_VERIFICADA.
  - Depende de: F00-T06C. Archivos propuestos: `tests/F00/GOV-002.spec.ts;tests/fixtures/F00/`. Evidencia: TC-GOV-002-P;TC-GOV-002-N.

- [ ] **F00-T07B** (GOV-002) Implementar GOV-002: Estado por capacidad y cuenta; acceso puede caducar. Registro público de API no prueba contrato ni producción. Gate de activación exige evidencia actual.
  - Depende de: F00-T07A. Archivos propuestos: `src/modules/gobierno-y-entorno/gov-002.ts;src/modules/gobierno-y-entorno/schemas.ts;db/migrations/`. Evidencia: GOV-002 reglas y migración revisadas.

- [ ] **F00-T07C** (GOV-002) Ejecutar ambos casos y revisar GOV-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F00-T07B. Archivos propuestos: `evidence/F00/GOV-002/;specs/001-gobierno-y-entorno/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F00-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F00-T07C. Archivos propuestos: `specs/001-gobierno-y-entorno/acceptance.md;evidence/F00/`. Evidencia: informe real por build; no autodeclaracion.
