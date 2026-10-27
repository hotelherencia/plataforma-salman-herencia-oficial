# Tareas F12

Todas pendientes; ninguna ejecutada. TESTS REQUIRED. IDs globalmente únicos. El orden inicial es conservador; paralelizar sólo tareas sin dependencia y sin escritura de los mismos archivos/esquemas. Las pruebas de integración adicionales se exigen para liberar, no producen ciclos de tareas.

- [ ] **F12-T00** (BASE) Revisar paquete, ADR, decisiones bloqueantes, contratos y fixture; obtener autorización de trabajo
  - Depende de: F04-T99;F06-T99;F11-T99. Archivos propuestos: `specs/013-costos-indicadores/spec.md;specs/013-costos-indicadores/plan.md`. Evidencia: orden autorizada y checklist.

- [ ] **F12-T01A** (FIN-007) Escribir casos TC-FIN-007-P y TC-FIN-007-N: Cargar mismo costo como linea directa y otra copia por reporte.
  - Depende de: F12-T00. Archivos propuestos: `tests/F12/FIN-007.spec.ts;tests/fixtures/F12/`. Evidencia: TC-FIN-007-P;TC-FIN-007-N.

- [ ] **F12-T01B** (FIN-007) Implementar FIN-007: Todo costo apunta a compra, tarea, lote o servicio; separar estimado, medido y pendiente. Un costo faltante no vale cero ni acredita margen completo.
  - Depende de: F12-T01A. Archivos propuestos: `src/modules/costos-indicadores/fin-007.ts;src/modules/costos-indicadores/schemas.ts;db/migrations/`. Evidencia: FIN-007 reglas y migración revisadas.

- [ ] **F12-T01C** (FIN-007) Ejecutar ambos casos y revisar FIN-007 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F12-T01B. Archivos propuestos: `evidence/F12/FIN-007/;specs/013-costos-indicadores/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F12-T02A** (FIN-008) Escribir casos TC-FIN-008-P y TC-FIN-008-N: Sumar sueldos completos y además horas directas ya incluidas sin descontar.
  - Depende de: F12-T01C. Archivos propuestos: `tests/F12/FIN-008.spec.ts;tests/fixtures/F12/`. Evidencia: TC-FIN-008-P;TC-FIN-008-N.

- [ ] **F12-T02B** (FIN-008) Implementar FIN-008: Bolsa neta excluye lo ya directo; asignaciones calculadas con decimal y residuo controlado. Base cero deja no asignado, no division por cero.
  - Depende de: F12-T02A. Archivos propuestos: `src/modules/costos-indicadores/fin-008.ts;src/modules/costos-indicadores/schemas.ts;db/migrations/`. Evidencia: FIN-008 reglas y migración revisadas.

- [ ] **F12-T02C** (FIN-008) Ejecutar ambos casos y revisar FIN-008 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F12-T02B. Archivos propuestos: `evidence/F12/FIN-008/;specs/013-costos-indicadores/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F12-T03A** (KPI-001) Escribir casos TC-KPI-001-P y TC-KPI-001-N: Mes parcialmente informado presentado como ocupación mensual completa.
  - Depende de: F12-T02C. Archivos propuestos: `tests/F12/KPI-001.spec.ts;tests/fixtures/F12/`. Evidencia: TC-KPI-001-P;TC-KPI-001-N.

- [ ] **F12-T03B** (KPI-001) Implementar KPI-001: Definir denominador físico y disponible por separado; excluir noches no informadas del cálculo parcial y mostrar cobertura. No-show no es ocupado.
  - Depende de: F12-T03A. Archivos propuestos: `src/modules/costos-indicadores/kpi-001.ts;src/modules/costos-indicadores/schemas.ts;db/migrations/`. Evidencia: KPI-001 reglas y migración revisadas.

- [ ] **F12-T03C** (KPI-001) Ejecutar ambos casos y revisar KPI-001 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F12-T03B. Archivos propuestos: `evidence/F12/KPI-001/;specs/013-costos-indicadores/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F12-T04A** (KPI-002) Escribir casos TC-KPI-002-P y TC-KPI-002-N: Denominador cero o ingreso incluye garantía e impuesto no configurado.
  - Depende de: F12-T03C. Archivos propuestos: `tests/F12/KPI-002.spec.ts;tests/fixtures/F12/`. Evidencia: TC-KPI-002-P;TC-KPI-002-N.

- [ ] **F12-T04B** (KPI-002) Implementar KPI-002: ADR y RevPAR usan conceptos/version aprobados; desayuno de paquete requiere asignación declarada. Permitir reconstruir cada sumatoria.
  - Depende de: F12-T04A. Archivos propuestos: `src/modules/costos-indicadores/kpi-002.ts;src/modules/costos-indicadores/schemas.ts;db/migrations/`. Evidencia: KPI-002 reglas y migración revisadas.

- [ ] **F12-T04C** (KPI-002) Ejecutar ambos casos y revisar KPI-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F12-T04B. Archivos propuestos: `evidence/F12/KPI-002/;specs/013-costos-indicadores/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F12-T05A** (KPI-003) Escribir casos TC-KPI-003-P y TC-KPI-003-N: Aseo intenta abrir desde tablero una cuenta de huésped.
  - Depende de: F12-T04C. Archivos propuestos: `tests/F12/KPI-003.spec.ts;tests/fixtures/F12/`. Evidencia: TC-KPI-003-P;TC-KPI-003-N.

- [ ] **F12-T05B** (KPI-003) Implementar KPI-003: Tablero accionable por rol y unidad; cada tarjeta abre registros y responsable. Alerta con estado de cierre, no número sin origen.
  - Depende de: F12-T05A. Archivos propuestos: `src/modules/costos-indicadores/kpi-003.ts;src/modules/costos-indicadores/schemas.ts;db/migrations/`. Evidencia: KPI-003 reglas y migración revisadas.

- [ ] **F12-T05C** (KPI-003) Ejecutar ambos casos y revisar KPI-003 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F12-T05B. Archivos propuestos: `evidence/F12/KPI-003/;specs/013-costos-indicadores/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F12-T06A** (SOC-012) Escribir casos TC-SOC-012-P y TC-SOC-012-N: Pixel y servidor usan IDs diferentes para el mismo hecho.
  - Depende de: F12-T05C. Archivos propuestos: `tests/F12/SOC-012.spec.ts;tests/fixtures/F12/`. Evidencia: TC-SOC-012-P;TC-SOC-012-N.

- [ ] **F12-T06B** (SOC-012) Implementar SOC-012: Definir conversion canónica reservation.confirmed y valor total pactado; payment.received es financiero, no segunda compra publicitaria. Doble canal browser/server usa mismo ID cuando habilitado.
  - Depende de: F12-T06A. Archivos propuestos: `src/modules/costos-indicadores/soc-012.ts;src/modules/costos-indicadores/schemas.ts;db/migrations/`. Evidencia: SOC-012 reglas y migración revisadas.

- [ ] **F12-T06C** (SOC-012) Ejecutar ambos casos y revisar SOC-012 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F12-T06B. Archivos propuestos: `evidence/F12/SOC-012/;specs/013-costos-indicadores/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F12-T07A** (SOC-018) Escribir casos TC-SOC-018-P y TC-SOC-018-N: Sumar comisión de canal y deducirla otra vez del neto recibido.
  - Depende de: F12-T06C. Archivos propuestos: `tests/F12/SOC-018.spec.ts;tests/fixtures/F12/`. Evidencia: TC-SOC-018-P;TC-SOC-018-N.

- [ ] **F12-T07B** (SOC-018) Implementar SOC-018: Separar captacion de estadía prestada y costo comercial; comision/fee fuente única. Origen desconocido y cobertura visibles; atribución no prueba causalidad.
  - Depende de: F12-T07A. Archivos propuestos: `src/modules/costos-indicadores/soc-018.ts;src/modules/costos-indicadores/schemas.ts;db/migrations/`. Evidencia: SOC-018 reglas y migración revisadas.

- [ ] **F12-T07C** (SOC-018) Ejecutar ambos casos y revisar SOC-018 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F12-T07B. Archivos propuestos: `evidence/F12/SOC-018/;specs/013-costos-indicadores/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F12-T08A** (REV-002) Escribir casos TC-REV-002-P y TC-REV-002-N: Datos escasos y cifra precisa presentada como certeza o actualizacion automática.
  - Depende de: F12-T07C. Archivos propuestos: `tests/F12/REV-002.spec.ts;tests/fixtures/F12/`. Evidencia: TC-REV-002-P;TC-REV-002-N.

- [ ] **F12-T08B** (REV-002) Implementar REV-002: Pronostico temporal sin fuga de futuro, comparación con método simple y cobertura suficiente. Recomendacion no modifica tarifa sin permiso.
  - Depende de: F12-T08A. Archivos propuestos: `src/modules/costos-indicadores/rev-002.ts;src/modules/costos-indicadores/schemas.ts;db/migrations/`. Evidencia: REV-002 reglas y migración revisadas.

- [ ] **F12-T08C** (REV-002) Ejecutar ambos casos y revisar REV-002 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F12-T08B. Archivos propuestos: `evidence/F12/REV-002/;specs/013-costos-indicadores/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F12-T09A** (FIN-010) Escribir casos TC-FIN-010-P y TC-FIN-010-N: Reporte suma compromiso+pago y muestra 200000 gastados.
  - Depende de: F12-T08C. Archivos propuestos: `tests/F12/FIN-010.spec.ts;tests/fixtures/F12/`. Evidencia: TC-FIN-010-P;TC-FIN-010-N.

- [ ] **F12-T09B** (FIN-010) Implementar FIN-010: Mostrar etapas sin sumarlas como costos acumulados; inversion/tecnologia/anuncios separados de gasto operativo. Nulo significa sin presupuesto, no cero aprobado.
  - Depende de: F12-T09A. Archivos propuestos: `src/modules/costos-indicadores/fin-010.ts;src/modules/costos-indicadores/schemas.ts;db/migrations/`. Evidencia: FIN-010 reglas y migración revisadas.

- [ ] **F12-T09C** (FIN-010) Ejecutar ambos casos y revisar FIN-010 con permiso correcto/incorrecto; capturar efecto y regresión
  - Depende de: F12-T09B. Archivos propuestos: `evidence/F12/FIN-010/;specs/013-costos-indicadores/acceptance.md`. Evidencia: build+salida+revisor+fecha.

- [ ] **F12-T99** (CIERRE) Revisión independiente, regresión y convergencia; clasificar brechas y no activar hasta aprobación
  - Depende de: F12-T09C. Archivos propuestos: `specs/013-costos-indicadores/acceptance.md;evidence/F12/`. Evidencia: informe real por build; no autodeclaracion.
