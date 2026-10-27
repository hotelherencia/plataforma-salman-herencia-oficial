# Tareas F01

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F01-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F00-T99. Archivos propuestos: `specs/002-nucleo-multiempresa/spec.md;specs/002-nucleo-multiempresa/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F01-T01A** (CORE-001) Escribir casos TC-CORE-001-P y TC-CORE-001-N: Cambiar company_id de la solicitud por SB conservando sesion Herencia.
  - Depende de: F01-T00. Archivos propuestos: `tests/F01/CORE-001.spec.ts;tests/fixtures/F01/`. Evidencia: TC-CORE-001-P;TC-CORE-001-N.

- [ ] **F01-T01B** (CORE-001) Implementar CORE-001: La sesion selecciona una sociedad autorizada; se válida que unidad, cuenta, documento y objeto relacionado pertenezcan al mismo alcance antes de escribir. El consolidado es sólo lectura salvo delegacion explícita.
  - Depende de: F01-T01A. Archivos propuestos: `src/modules/nucleo-multiempresa/core-001.ts;src/modules/nucleo-multiempresa/schemas.ts;db/migrations/`. Evidencia: CORE-001 reglas y migración revisadas.

- [ ] **F01-T01C** (CORE-001) Ejecutar ambos casos y revisar CORE-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F01-T01B. Archivos propuestos: `evidence/F01/CORE-001/;specs/002-nucleo-multiempresa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F01-T02A** (CORE-002) Escribir casos TC-CORE-002-P y TC-CORE-002-N: Ingresar dos participaciones activas que sumen 110%.
  - Depende de: F01-T01C. Archivos propuestos: `tests/F01/CORE-002.spec.ts;tests/fixtures/F01/`. Evidencia: TC-CORE-002-P;TC-CORE-002-N.

- [ ] **F01-T02B** (CORE-002) Implementar CORE-002: Cerrar vigencia anterior y crear nueva fila en una transacción; porcentaje mayor que cero y no mayor a cien, suma de participaciones verificadas no supera cien por periodo/clase. No completar socios faltantes por inferencia.
  - Depende de: F01-T02A. Archivos propuestos: `src/modules/nucleo-multiempresa/core-002.ts;src/modules/nucleo-multiempresa/schemas.ts;db/migrations/`. Evidencia: CORE-002 reglas y migración revisadas.

- [ ] **F01-T02C** (CORE-002) Ejecutar ambos casos y revisar CORE-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F01-T02B. Archivos propuestos: `evidence/F01/CORE-002/;specs/002-nucleo-multiempresa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F01-T03A** (CORE-003) Escribir casos TC-CORE-003-P y TC-CORE-003-N: Acceso directo por URL a una remuneracion usando token de aseo.
  - Depende de: F01-T02C. Archivos propuestos: `tests/F01/CORE-003.spec.ts;tests/fixtures/F01/`. Evidencia: TC-CORE-003-P;TC-CORE-003-N.

- [ ] **F01-T03B** (CORE-003) Implementar CORE-003: Autorizar acción y objeto en cada API, exportación y archivo; denegacion por defecto. El rol agregado sólo amplifica permisos expresamente concedidos, nunca por pertenecer al grupo.
  - Depende de: F01-T03A. Archivos propuestos: `src/modules/nucleo-multiempresa/core-003.ts;src/modules/nucleo-multiempresa/schemas.ts;db/migrations/`. Evidencia: CORE-003 reglas y migración revisadas.

- [ ] **F01-T03C** (CORE-003) Ejecutar ambos casos y revisar CORE-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F01-T03B. Archivos propuestos: `evidence/F01/CORE-003/;specs/002-nucleo-multiempresa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F01-T04A** (CORE-004) Escribir casos TC-CORE-004-P y TC-CORE-004-N: Recepción intenta DELETE sobre pago de turno cerrado.
  - Depende de: F01-T03C. Archivos propuestos: `tests/F01/CORE-004.spec.ts;tests/fixtures/F01/`. Evidencia: TC-CORE-004-P;TC-CORE-004-N.

- [ ] **F01-T04B** (CORE-004) Implementar CORE-004: Operaciones cerradas se corrigen mediante reverso vinculado; actor humano o sistema obligatorio. El audit trail conserva campos modificados sin secretos; cierre no se borra físicamente.
  - Depende de: F01-T04A. Archivos propuestos: `src/modules/nucleo-multiempresa/core-004.ts;src/modules/nucleo-multiempresa/schemas.ts;db/migrations/`. Evidencia: CORE-004 reglas y migración revisadas.

- [ ] **F01-T04C** (CORE-004) Ejecutar ambos casos y revisar CORE-004 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F01-T04B. Archivos propuestos: `evidence/F01/CORE-004/;specs/002-nucleo-multiempresa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F01-T05A** (CORE-005) Escribir casos TC-CORE-005-P y TC-CORE-005-N: Envio de importe con decimales no admitidos para moneda configurada o salida anterior a llegada.
  - Depende de: F01-T04C. Archivos propuestos: `tests/F01/CORE-005.spec.ts;tests/fixtures/F01/`. Evidencia: TC-CORE-005-P;TC-CORE-005-N.

- [ ] **F01-T05B** (CORE-005) Implementar CORE-005: Noches por diferencia de fechas locales, no segundos/86400. Usar enteros monetarios y conversion decimal con fuente, fecha y redondeo congelados al aceptar.
  - Depende de: F01-T05A. Archivos propuestos: `src/modules/nucleo-multiempresa/core-005.ts;src/modules/nucleo-multiempresa/schemas.ts;db/migrations/`. Evidencia: CORE-005 reglas y migración revisadas.

- [ ] **F01-T05C** (CORE-005) Ejecutar ambos casos y revisar CORE-005 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F01-T05B. Archivos propuestos: `evidence/F01/CORE-005/;specs/002-nucleo-multiempresa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F01-T06A** (CORE-006) Escribir casos TC-CORE-006-P y TC-CORE-006-N: Importar la misma factura del mismo emisor y sociedad dos veces.
  - Depende de: F01-T05C. Archivos propuestos: `tests/F01/CORE-006.spec.ts;tests/fixtures/F01/`. Evidencia: TC-CORE-006-P;TC-CORE-006-N.

- [ ] **F01-T06B** (CORE-006) Implementar CORE-006: Unicidad documental por emisor/tipo/folio/receptor cuando definidos; originales privados enlazados por hash. Tercero global no comparte deudas entre sociedades.
  - Depende de: F01-T06A. Archivos propuestos: `src/modules/nucleo-multiempresa/core-006.ts;src/modules/nucleo-multiempresa/schemas.ts;db/migrations/`. Evidencia: CORE-006 reglas y migración revisadas.

- [ ] **F01-T06C** (CORE-006) Ejecutar ambos casos y revisar CORE-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F01-T06B. Archivos propuestos: `evidence/F01/CORE-006/;specs/002-nucleo-multiempresa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F01-T07A** (SEC-001) Escribir casos TC-SEC-001-P y TC-SEC-001-N: Token vencido/revocado o sin MFA intenta devolución.
  - Depende de: F01-T06C. Archivos propuestos: `tests/F01/SEC-001.spec.ts;tests/fixtures/F01/`. Evidencia: TC-SEC-001-P;TC-SEC-001-N.

- [ ] **F01-T07B** (SEC-001) Implementar SEC-001: Proveedor OIDC verificado y sesiones seguras; MFA exigido a roles privilegiados. Acceso de emergencia auditado no exime aprobaciones financieras.
  - Depende de: F01-T07A. Archivos propuestos: `src/modules/nucleo-multiempresa/sec-001.ts;src/modules/nucleo-multiempresa/schemas.ts;db/migrations/`. Evidencia: SEC-001 reglas y migración revisadas.

- [ ] **F01-T07C** (SEC-001) Ejecutar ambos casos y revisar SEC-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F01-T07B. Archivos propuestos: `evidence/F01/SEC-001/;specs/002-nucleo-multiempresa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F01-T08A** (SEC-002) Escribir casos TC-SEC-002-P y TC-SEC-002-N: Solicitante no verificado pide exportación de otra persona.
  - Depende de: F01-T07C. Archivos propuestos: `tests/F01/SEC-002.spec.ts;tests/fixtures/F01/`. Evidencia: TC-SEC-002-P;TC-SEC-002-N.

- [ ] **F01-T08B** (SEC-002) Implementar SEC-002: Aplicar minimización y permisos por campo; retención aprobada antes de datos reales. Solicitudes verifican identidad y compatibilizan supresión con evidencia obligatoria.
  - Depende de: F01-T08A. Archivos propuestos: `src/modules/nucleo-multiempresa/sec-002.ts;src/modules/nucleo-multiempresa/schemas.ts;db/migrations/`. Evidencia: SEC-002 reglas y migración revisadas.

- [ ] **F01-T08C** (SEC-002) Ejecutar ambos casos y revisar SEC-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F01-T08B. Archivos propuestos: `evidence/F01/SEC-002/;specs/002-nucleo-multiempresa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F01-T09A** (SEC-003) Escribir casos TC-SEC-003-P y TC-SEC-003-N: Subir clave API a código o incluir pasaporte en payload publicitario.
  - Depende de: F01-T08C. Archivos propuestos: `tests/F01/SEC-003.spec.ts;tests/fixtures/F01/`. Evidencia: TC-SEC-003-P;TC-SEC-003-N.

- [ ] **F01-T09B** (SEC-003) Implementar SEC-003: Secretos fuera de repositorio; redaccion de logs; no PAN/CVV ni identificadores personales innecesarios en modelos. Escaneo bloquea entrega y exige revocar secreto expuesto.
  - Depende de: F01-T09A. Archivos propuestos: `src/modules/nucleo-multiempresa/sec-003.ts;src/modules/nucleo-multiempresa/schemas.ts;db/migrations/`. Evidencia: SEC-003 reglas y migración revisadas.

- [ ] **F01-T09C** (SEC-003) Ejecutar ambos casos y revisar SEC-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F01-T09B. Archivos propuestos: `evidence/F01/SEC-003/;specs/002-nucleo-multiempresa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F01-T10A** (SEC-006) Escribir casos TC-SEC-006-P y TC-SEC-006-N: Huésped ordena ignorar instrucciones, marcar pagado y enviar bancos.
  - Depende de: F01-T09C. Archivos propuestos: `tests/F01/SEC-006.spec.ts;tests/fixtures/F01/`. Evidencia: TC-SEC-006-P;TC-SEC-006-N.

- [ ] **F01-T10B** (SEC-006) Implementar SEC-006: Texto de cliente/documento es dato, no permiso. Herramientas comprueban acceso y argumentos independientemente del modelo.
  - Depende de: F01-T10A. Archivos propuestos: `src/modules/nucleo-multiempresa/sec-006.ts;src/modules/nucleo-multiempresa/schemas.ts;db/migrations/`. Evidencia: SEC-006 reglas y migración revisadas.

- [ ] **F01-T10C** (SEC-006) Ejecutar ambos casos y revisar SEC-006 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F01-T10B. Archivos propuestos: `evidence/F01/SEC-006/;specs/002-nucleo-multiempresa/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F01-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F01-T10C. Archivos propuestos: `specs/002-nucleo-multiempresa/acceptance.md;evidence/F01/`. Evidencia: informe real por build; no autodeclaracion.
