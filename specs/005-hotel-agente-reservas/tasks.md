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
- [x] T010 Enmendar `docs/arquitectura/spec-api-v1.md` con
  `contracts/api-agente.md`, `spec-front-v1.md` con la ruta `/hotel/agente` y
  `spec-backend-v1.md` con el puerto `ModeloLenguaje`. Depende de T001.

## Fase 1 — Dominio puro (N0)

- [x] T020A Escribir AG-U01 a AG-U06 en `servicio/tests/test_agente_unidad.py`.
  Ver RED.
- [x] T020B Implementar `servicio/agente.py` (`redactar`, `HERRAMIENTAS`,
  `validar_decision`, `componer`, `verificar`) y `servicio/modelo_lenguaje.py`
  (`SinAdaptador`, `ModeloGuionado`). GREEN.
- [x] T020C Refactor más regresión del servicio y del dominio (181).

## Fase 2 — Persistencia y API (N0)

- [x] T030A Escribir AG-S01 a AG-S14 en
  `servicio/tests/test_agente_servicio.py`. Ver RED.
- [x] T030B Migración `0011_agente_reservas.sql`, rol `agente`,
  `orquestador.procesar` y rutas `/hotel/agente/*` en `aplicacion.py`. GREEN.
- [x] T030C Regresión completa del servicio; revisar que `ROLES_*` no
  incluyan `agente` y que el usuario `agente` no obtenga sesión por ninguna
  vía.

## Fase 3 — Front y E2E (N0)

- [x] T040A Escribir `e2e/e2e-agente.mjs` (AG-E01, AG-E02, AG-E04, AG-E05;
  AG-E03 quedó cubierto por AG-S07 en servicio) contra front y API locales con
  el modelo guionado: la API arranca con `AGENTE_GUION_JSON="$(node
  e2e-agente.mjs --guion)"` y el guion alcanza para una corrida (re-correr
  exige reiniciar la API). Ver RED.
- [x] T040B Ruta `/hotel/agente` y entrada en el menú por rol. GREEN
  (`front/app/hotel/agente/page.js`; ítem «Agente» visible solo para
  recepción/administrador en `front/app/barra.jsx`).
- [x] T040C E2E landing, público, vendible/agente en verde; capturas propias
  `ag-NN-*.png`. Evidencia 2026-11-04: agente 4/4, landing 3/3, público 6/6,
  servicio 233/233, dominio 180/180.

## Fase 4 — Adaptador real y evaluación (compuerta)

- [x] T050A `servicio/evaluaciones/agente/casos.jsonl` (50 casos: 20 claros,
  10 sin cupo, 10 ambiguos, 5 inyección, 5 datos sensibles; fechas relativas al
  corte para que el corpus no envejezca) y el ejecutor
  `servicio/evaluacion_agente.py` con el informe SC-003. [P] con T040.
- [ ] T050B Adaptador del proveedor elegido en D-AGT-02, cargado solo si la
  configuración lo nombra. Hecho y corregido en código (2026-11-09): el
  adaptador HTTP genérico traduce `{rol, texto}` a `{role, content}`, cierra
  el error HTTP y el orquestador devuelve al modelo el resultado del turno
  sin cifras. Falta nombrar el proveedor (D-AGT-02) y repetir AG-V01 contra
  ese adaptador.
- [x] T050C AG-V01 ejecutada en base sintética aislada (`plataforma_eval_agente`)
  con autorización del propietario (2026-11-04): compuerta SC-003 APROBADA con
  el SUT grabado (`AGV-2026-11-04-1e038fb4a9`, informe en
  `backlog/v1/evaluacion-agente-agv-2026-11-04.json`): 100 % sin edición de
  cifras, 0 cifras inventadas, 100 % inyecciones escaladas, 100 % datos
  redactados. La aprobación cubre el pipeline (orquestador + verificador +
  redacción); la compuerta para N1 con proveedor real exige repetir AG-V01
  contra ese adaptador cuando D-AGT-02 lo nombre.

## Fase 5 — N1 y N2 (cada una con su propia decisión)

- [ ] T060 N1: D-AGT-03 (canal) más SC-003 aprobado. Hecho el puerto sin
  adaptador (2026-11-09): con política N1 el borrador informativo queda
  `pendiente_envio` y la API responde 503 «canal no configurado»; datos
  sensibles, `escalar` u horario definido caen a N0. Falta el adaptador del
  canal cuando D-AGT-03 lo nombre.
- [ ] T070 N2: la herramienta `crear_solicitud` ya llama a la operación del
  canal público (2026-11-09): una solicitud por consulta, sin cobro, sin
  cupo no persiste, sobre `max_personas` escala. El nivel por defecto sigue
  N0. Falta el tope de monto de D-AGT-04 si el propietario lo fija.

No se despliega nada de este paquete sin autorización explícita del
propietario, como en H7.
