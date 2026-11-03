# Tareas — Agente de reservas

**PROPUESTO (2026-11-03).** Orden TDD: cada tarea de prueba (A) se escribe y
se ve **fallar** antes de su implementación (B); la verificación (C) corre la
regresión completa. No se marca nada «Hecha» sin la salida de las pruebas.
Las tareas con [P] pueden hacerse en paralelo con la anterior.

## Fase 0 — Decisiones y spec (sin código)

- [ ] T001 Propietario: D-AGT-01 (nivel inicial; se propone N0) y D-AGT-06
  (tono e identificación del asistente). Salida: registro fechado en
  `backlog/v1`.
- [ ] T002 Propietario: D-AGT-02 (proveedor, región, retención y datos). No
  bloquea T010 a T040; sí bloquea T050.
- [ ] T010 Enmendar `docs/arquitectura/spec-api-v1.md` con
  `contracts/api-agente.md`, `spec-front-v1.md` con la ruta `/hotel/agente` y
  `spec-backend-v1.md` con el puerto `ModeloLenguaje`. Depende de T001.

## Fase 1 — Dominio puro (N0)

- [ ] T020A Escribir AG-U01 a AG-U06 en `servicio/tests/test_agente_unidad.py`.
  Ver RED.
- [ ] T020B Implementar `servicio/agente.py` (`redactar`, `HERRAMIENTAS`,
  `validar_decision`, `componer`, `verificar`) y `servicio/modelo_lenguaje.py`
  (`SinAdaptador`, `ModeloGuionado`). GREEN.
- [ ] T020C Refactor más regresión del servicio y del dominio (181).

## Fase 2 — Persistencia y API (N0)

- [ ] T030A Escribir AG-S01 a AG-S14 en
  `servicio/tests/test_agente_servicio.py`. Ver RED.
- [ ] T030B Migración `0010_agente_reservas.sql`, rol `agente`,
  `orquestador.procesar` y rutas `/hotel/agente/*` en `aplicacion.py`. GREEN.
- [ ] T030C Regresión completa del servicio; revisar que `ROLES_*` no
  incluyan `agente` y que el usuario `agente` no obtenga sesión por ninguna
  vía.

## Fase 3 — Front y E2E (N0)

- [ ] T040A Escribir `e2e/e2e-agente.mjs` (AG-E01 a AG-E05) contra front y API
  locales con el modelo guionado (variable de entorno de prueba, nunca en
  producción). Ver RED.
- [ ] T040B Ruta `/hotel/agente` y entrada en el menú por rol. GREEN.
- [ ] T040C E2E base, operación, vendible y agente en verde; capturas propias
  `ag-NN-*.png`.

## Fase 4 — Adaptador real y evaluación (compuerta)

- [ ] T050A Escribir `servicio/evaluaciones/agente/casos.jsonl` (50 casos) y
  el ejecutor del informe. [P] con T040.
- [ ] T050B Adaptador del proveedor elegido en D-AGT-02, cargado solo si la
  configuración lo nombra; prueba de contrato con respuestas grabadas
  sintéticas (sin red en CI).
- [ ] T050C Ejecutar AG-V01 en base sintética aislada con autorización
  explícita. Informe SC-003 al propietario.

## Fase 5 — N1 y N2 (cada una con su propia decisión)

- [ ] T060 N1: D-AGT-03 (canal) más SC-003 aprobado; pruebas de
  `pendiente_envio` con el puerto del canal sin adaptador; luego el adaptador
  autorizado.
- [ ] T070 N2: depende de D-PUB-01, v1-issue-22 y D-AGT-04; pruebas de la
  herramienta `crear_solicitud` (idempotencia por turno, carrera por la
  última unidad, límites) antes de habilitarla.

No se despliega nada de este paquete sin autorización explícita del
propietario, como en H7.
