# Análisis de consistencia Spec Kit — 002-hotel-reservas-concierge

**Fecha:** 2026-10-27
**Modo:** solo lectura. No se modificó ningún archivo del proyecto ni de RSalman.
**Origen:** ejecución manual en esta sesión, siguiendo los pasos 2–5 de la skill oficial `speckit-analyze` (`C:/Users/herre/AppData/Local/Temp/speckit_probe/probe/.claude/skills/speckit-analyze/SKILL.md`). **No es salida del CLI de Spec Kit.**
**Estado de la feature:** BLOCKED para implementación.

## Alcance y artefactos

- Paso 1 omitido: `check-prerequisites.ps1` no existe en el proyecto; se usaron las rutas directas.
- Leídos en detalle: `spec.md`, `plan.md`, `tasks.md`, `acceptance.md` (pasada de cobertura) y `.specify/memory/constitution.md`.
- Solo verificada la existencia (no leídos en esta pasada): `research.md`, `data-model.md`, `quickstart.md`, `contracts/README.md`, `checklists/requirements.md`.
- `.specify/extensions.yml` no existe: no hay hooks `before_analyze` ni `after_analyze`.
- Q-HOT-01..06 no se responden en este informe.
- Límite de 50 hallazgos: se registran 24, sin desbordamiento.

## Tabla de hallazgos

| ID | Categoría | Severidad | Ubicación | Resumen | Recomendación |
|----|-----------|-----------|-----------|---------|---------------|
| AN-002-01 | Inconsistencia (contradicción) | HIGH | spec.md L104 (SC-008) y L429 (RF-HOT-04); acceptance.md L37 | SC-008 exige que los upsells del agente conviertan al menos el 8 % (referencia Duve), mientras RF-HOT-04 dice que no se usa un porcentaje comercial del proveedor como medición propia. acceptance.md traslada SC-008 como «Medir». **Conocido; se registra sin corregir.** | Mantener ambas formulaciones. Recomendación pendiente de confirmación del propietario, según decisiones-pendientes.md. |
| AN-002-02 | Inconsistencia | HIGH | spec.md L21 y L25 (Historia 1, prueba y escenario 3) frente a SC-002 (L98) | La historia exige que la disponibilidad baje en todos los canales en menos de 5 minutos. SC-002 exige lo mismo solo en el 95 % de los cambios. Son umbrales distintos para el mismo comportamiento. | Unificar el criterio en spec.md y acceptance.md (100 % o 95 %) con confirmación del propietario. |
| AN-002-03 | Constitución (gate no materializado) | HIGH | constitution.md §IV; spec.md (sin FR para finalidad, base legal, responsable/encargado, destinatarios, residencia, retención ni derechos); plan.md L18 | §IV exige registrar esos datos y planificar el régimen vigente Ley 19.628 y la transición a Ley 21.719 al 01-12-2026 (faltan 35 días desde la fecha del análisis). El plan lo deja como «pendiente». Ningún FR ni AT lo cubre. No es CRITICAL porque la constitución es una versión propuesta sin ratificar y el texto no usa MUST; sube a CRITICAL si se ratifica con carácter normativo. | Registrar como requisito propuesto con caso de prueba, o bloquear explícitamente la implementación con dueño y fecha. |
| AN-002-04 | Constitución (redondeo) | HIGH | constitution.md §II; spec.md L23 («total con IVA») y FR-004; acceptance.md AT-001 («impuestos según política ratificada») | §II exige CLP en unidades enteras y reglas de redondeo ratificadas para cálculos derivados de UF o costo. La spec no define redondeo de IVA ni de tarifas; queda delegado. Mismo criterio de severidad que AN-002-03. | Añadir la regla de redondeo como requisito propuesto pendiente o registrarla como bloqueo ligado a T004/T202. |
| AN-002-05 | Ambigüedad (criterio no medible) | HIGH | spec.md SC-001 (L97) y L143 | «Cero sobreventas en 90 días» es una promesa absoluta sin denominador ni tratamiento de conflictos externos. L143 reconoce que el aislamiento local no garantiza cero sobreventa entre OTA independientes. | Definir denominador, ventana y si un conflicto externo cuenta como sobreventa. Mantener como propuesta. |
| AN-002-06 | Constitución (cobertura parcial) | MEDIUM | constitution.md §III; spec.md FR-010/FR-011; RF-HOT-01 | §III exige aprobaciones humanas con caducidad y uso único, ligadas a operación y parámetros. La spec solo cubre el vínculo a la propuesta (RF-HOT-01) y la invalidación al cambiar parámetros (AT-011). Faltan caducidad y uso único. | Añadir el requisito propuesto y su caso de prueba. |
| AN-002-07 | Inconsistencia (referencia cruzada) | MEDIUM | spec.md L143 («escenarios tributarios y SC de emisión en 30/60 segundos») | SC-004 solo fija 60 s para emisión. El 30 s aparece en Historia 3, escenario 1, referido a la respuesta del agente, sin SC ni AT propios. La referencia cruzada es inexacta. | Revisar la referencia de L143 para que coincida con SC-004 y con el criterio del agente. |
| AN-002-08 | Subespecificación | MEDIUM | spec.md L47 (agente: «menos de 30 segundos»); NFR-005 (L139) | El criterio de latencia del agente no tiene SC ni AT. NFR-005 exige medir desde recepción hasta resultado confirmado, incluidos errores y reintentos, pero acceptance.md no tiene ningún caso de latencia. | Crear SC o caso AT para la latencia, con muestra y denominador definidos. |
| AN-002-09 | Cobertura (promesa no cumplida) | MEDIUM | acceptance.md L3 frente a AT-001..AT-015 | La cabecera dice que para cada FR se prueba resultado autorizado, denegación, duplicación y recuperación. Solo AT-006, AT-010, AT-011 y AT-014 prueban denegación. Recuperación falta en AT-001, 003, 005, 008, 012, 013, 014 y 015. | Completar por FR las facetas prometidas o corregir la cabecera. |
| AN-002-10 | Cobertura | MEDIUM | NFR-004 (spec.md L138) y acceptance.md; tasks.md | NFR-004 (retención, restauración, RPO/RTO) no tiene AT ni tarea. Constitución §VI exige definir RPO/RTO antes de producción. | Añadir AT y tarea, o registrar el bloqueo con dueño. |
| AN-002-11 | Cobertura (tareas) | MEDIUM | SC-001, SC-002, SC-004, SC-007 (spec.md L97–103); tasks.md | Son criterios construibles (medición de sobreventa, latencia de canal, conciliación del 100 % de pagos, auditoría mensual del ledger) sin tarea explícita. T205 (costos y latencias) y T006 (carga y fallos) los tocan solo indirectamente. | Añadir tareas de instrumentación de medición en el backlog posterior a T006. |
| AN-002-12 | Cobertura (trazabilidad) | MEDIUM | tasks.md (ninguna tarea cita FR-001..FR-015 ni SC) | Los FR-001..015 solo llegan a las tareas de forma indirecta (T003, T005, T006). Solo FR-016..020 tienen tarea explícita (T102, T202, T203). | Citar los IDs de FR en las tareas que los afectan, al redactar el backlog. |
| AN-002-13 | Duplicación (tareas) | MEDIUM | tasks.md T007 y T105 | Ambas tareas piden el análisis oficial de Spec Kit, con dependencias distintas (T006 frente a T103 y Q-TOOL-01). Esta ejecución manual no cierra ninguna de las dos, porque no es la salida del CLI. | Unificar en una tarea con dependencia explícita. Dejar constancia de que este informe es manual. |
| AN-002-14 | Ambigüedad (línea base y muestra) | MEDIUM | SC-003 («nivel actual», L99), SC-005, SC-006, SC-008; acceptance.md L30–38 | Ningún SC de negocio define línea base, denominador ni muestra. acceptance.md dice «No hay medición actual» para todos. Constitución §V exige definirlos. Por el criterio de la skill (§3), estos KPI quedan fuera de la cobertura construible, pero su definición sigue siendo necesaria. | Definir línea base, denominador y muestra para cada SC medible, o declararlo como pendiente con dueño. |
| AN-002-15 | Ambigüedad (placeholders) | MEDIUM | spec.md L125–131 (7 marcadores `[NEEDS CLARIFICATION]`) | Asignación a Q: L125 a Q-HOT-03; L126 a Q-HOT-02; L127 a Q-HOT-01 (la migración de datos no figura en el texto de Q-HOT-01); L128 y L130 a Q-HOT-03. **Sin Q asignado:** L129 (factura a empresas) y L131 (housekeeping propio o externo). | Registrar los dos temas sin Q en el registro de decisiones pendientes. No se propone respuesta. |
| AN-002-16 | Terminología / duplicación | MEDIUM | spec.md §Profundización (RF-HOT-01..04) frente a FR-018..020; tasks.md T201 y T202 | Mismo requisito con dos IDs: RF-HOT-01 equivale a FR-018, RF-HOT-02 a FR-019 y RF-HOT-03 a FR-020. RF-HOT-04 no tiene FR propio (solo parcialmente FR-017). No hay tabla de equivalencia. T201 usa RF-HOT y T202 usa FR. | Añadir una tabla de equivalencia en spec.md o en trazabilidad. |
| AN-002-17 | Terminología | MEDIUM | plan.md L26, L48, L54; spec.md L84–91; RF-HOT-02 | Nombres divergentes: Cargo (spec) frente a CargoEstadia (plan); CuentaEstadía, CuentaReferencia y «Cuenta de estadía»; OcupaciónPorFecha (plan L26) frente a CupoPorFechaTipo (plan L48); Canal frente a ConexiónCanal; TareaOperativa frente a TareaCumplimiento; Plan tarifario sin correspondencia en plan. | Unificar el glosario en data-model.md antes de contratos. |
| AN-002-18 | Inconsistencia | MEDIUM | plan.md L9 frente a plan.md L42 | L9 lista Python 3.12/FastAPI, Next.js, PostgreSQL 16 y Redis como stack propuesto. L42 dice que no se justifica Redis como necesidad comprobada. Son señales en tensión, aunque L9 lo presenta como referencia de fuentes. | Aclarar en el plan que L9 es referencia de fuentes y no decisión de stack. |
| AN-002-19 | Inconsistencia (versión) | MEDIUM | plan.md L49 («no se modifica constitución») y L59 («Constitución revisada sin modificaciones») frente a constitution.md (versión propuesta 1.1.0 con registro de ampliaciones) | El plan dice que no hay cambios; la constitución propone una versión 1.1.0 con ampliaciones. | Alinear el texto del plan con el estado real de la versión propuesta. |
| AN-002-20 | Trazabilidad | MEDIUM | plan.md L32 y L48–59 (ADR-001 a ADR-006) | Los ADR se citan como base de decisiones, pero no hay archivos ADR-00x dentro de ``. Su estado no se pudo verificar en esta pasada (puede estar en RSalman). | Localizar los ADR citados o registrar que están pendientes de crear. |
| AN-002-21 | Duplicación (contenido) | MEDIUM | spec.md L182–183, L218–219, L254–255, L311–314, L354–356, L396–400, L441–443 frente a acceptance.md L46–92 | Los mismos escenarios AC-US-HOT aparecen en dos artefactos con texto idéntico. Además AT-018, AT-019 y AT-020 repiten AC-US-HOT-001-03, 002-03 y 001-06 con otro ID. Riesgo de deriva. | Mantener acceptance.md como fuente única y referenciarlo desde spec.md. |
| AN-002-22 | Formato | LOW | acceptance.md (AT-001..020, ADV-001..003); spec.md (FR-001..020 sin namespace) | AGENTS.md pide namespace de feature para FR, SC y AT; no se aplica. ADV-001..003 citan «NFR-001/002/003» de forma genérica: ADV-001 corresponde a FR-005 y ADV-003 a FR-004. Formato distinto de la plantilla oficial. | Corregir en la próxima revisión de trazabilidad. |
| AN-002-23 | Ambigüedad | LOW | spec.md L111 (supuesto «menos de 50 habitaciones») frente a L125 (pregunta abierta sobre el número de habitaciones) | Un supuesto cuantitativo convive con una pregunta abierta sobre el mismo dato. | Marcar el supuesto como provisional vinculado a Q-HOT-03. |
| AN-002-24 | Subespecificación | LOW | spec.md L32 (Historia 2, «reutiliza el módulo de pedidos ya probado en 001») | «Ya probado» es una afirmación sin evidencia enlazada en la spec. | Enlazar la evidencia de 001 o reformular como supuesto. |

## Resultado por pasada

- **A. Duplicación:** hallazgos. Tres pares de requisitos casi duplicados (AN-002-16), texto duplicado entre spec y acceptance (AN-002-21) y tareas duplicadas (AN-002-13).
- **B. Ambigüedad:** hallazgos. Criterios no medibles o sin línea base (AN-002-05, AN-002-14), placeholders (AN-002-15) y supuesto abierto (AN-002-23). No se encontraron TODO, TKTK ni `???` en los cuatro artefactos leídos; solo los marcadores `[NEEDS CLARIFICATION]`. Revisión por lectura completa, sin grep.
- **C. Subespecificación:** hallazgos. Latencia sin SC ni AT (AN-002-08), afirmación no sustentada (AN-002-24) y tareas sin FR citado (AN-002-12).
- **D. Alineación con constitución:** hallazgos, ninguno CRITICAL por las razones del AN-002-03. Brechas en privacidad (AN-002-03), redondeo CLP (AN-002-04), caducidad de aprobaciones (AN-002-06), línea base y denominadores (AN-002-14), y versión de constitución (AN-002-19).
- **E. Cobertura:** hallazgos. Ver tablas siguientes. Sin tarea explícita para 24 de 30 requisitos construibles.
- **F. Inconsistencia:** hallazgos. Contradicción SC-008 frente a RF-HOT-04 (AN-002-01), umbrales de 5 minutos (AN-002-02), referencias de 30/60 s (AN-002-07), stack y Redis (AN-002-18), versión de constitución (AN-002-19) y nombres de entidades (AN-002-17).

## Cobertura FR y SC frente a tareas

Se considera tarea explícita la que cita el ID o un alcance literal. «Indirecta» indica que la tarea genérica (T003, T005, T006) lo cubre por contexto, sin citarlo.

| Requisito | ¿Tiene tarea? | IDs de tarea | Caso de prueba | Notas |
|-----------|---------------|--------------|----------------|-------|
| FR-001 | Indirecta | T003, T005, T006 | AT-001 | Inventario y tarifas; depende de Q-HOT-03. |
| FR-002 | Indirecta | T005, T006 | AT-002 | Motor de reservas web. |
| FR-003 | Indirecta | T003 (Q-HOT-02), T006 | AT-003 | Sincronización de canales. |
| FR-004 | Indirecta | T003 (anticipos), T006 | AT-004, ADV-003 | Pago y documento SII. |
| FR-005 | Indirecta | T006 | AT-005, ADV-001 | Sobreventa concurrente. |
| FR-006 | Indirecta | T003 (datos de registro), T006 | AT-006 | Check-in online. |
| FR-007 | Indirecta | T006 | AT-007 | Interfaz opcional de cafetería. |
| FR-008 | No | Ninguna | AT-008 | Housekeeping; el responsable de housekeeping está sin Q (AN-002-15). |
| FR-009 | No | Ninguna | AT-009 | Liquidación de cuenta. |
| FR-010 | Indirecta | T003 (autonomía), T006 | AT-010 | Agente WhatsApp. |
| FR-011 | Indirecta | T003 (autonomía), T004 (permisos) | AT-011 | Reglas de autonomía. |
| FR-012 | No | Ninguna | AT-012 | Upsells. |
| FR-013 | No | Ninguna | AT-013 | Registro de auditoría; ligado a SC-007 (AN-002-11). |
| FR-014 | No | Ninguna | AT-014 | Servidor MCP de solo lectura. |
| FR-015 | Indirecta | T004, T005 | AT-015 | Core compartido. |
| FR-016 | Sí | T102 | AT-016 | Inventario y preparación. |
| FR-017 | Sí | T102, T104 | AT-017 | Estado por canal y transferencia. |
| FR-018 | Sí | T202 | AT-018 | Cambios y cancelaciones (RF-HOT-01). |
| FR-019 | Sí | T202, T203 | AT-019 | Extras (RF-HOT-02). |
| FR-020 | Sí | T202, T203 | AT-020 | Eventos de canal (RF-HOT-03). |
| NFR-001 | Parcial | T004 (permisos por empresa, por palabra clave) | ADV-001..003; AT-016..020 con otro tenant | Denegación entre empresas no cubierta en AT-001..015. |
| NFR-002 | No explícita | Ninguna | ADV-001..003 | Escritura MCP deshabilitada; sin tarea. |
| NFR-003 | Parcial | T203 | ADV-001..003 | Idempotencia y reintentos. |
| NFR-004 | No | Ninguna | Ninguno | Ver AN-002-10. |
| NFR-005 | Parcial | T205 | Ninguno | Latencia de extremo a extremo; ver AN-002-08. |
| NFR-006 | Parcial | T102, T104 | Mismos AC (AT-017) | Procedencia y vigencia de ofertas. |
| SC-001 | No | Ninguna (T205 indirecta) | Fila «Medir» en acceptance.md | Construible; ver AN-002-11 y AN-002-05. |
| SC-002 | No | Ninguna | Fila «Medir» | Construible; ver AN-002-02. |
| SC-003 | Excluido (KPI de negocio) | Ninguna | Fila «Medir» | Sin línea base (AN-002-14). |
| SC-004 | No | Ninguna | Fila «Medir» | Construible; conciliación de pagos. |
| SC-005 | Excluido (KPI de negocio) | Ninguna | Fila «Medir» | Sin muestra (AN-002-14). |
| SC-006 | Excluido (KPI de negocio) | Ninguna | Fila «Medir»; H3 prueba de 50 conversaciones | Sin denominador en el SC (AN-002-14). |
| SC-007 | No | Ninguna | Fila «Medir» | Construible; auditoría mensual del ledger. |
| SC-008 | Excluido (KPI de negocio) | Ninguna | Fila «Medir» | Contradicción con RF-HOT-04 (AN-002-01). |
| SC-009 | Excluido (KPI de formación) | Ninguna | Fila «Medir» | Sin tarea de capacitación. |

**Cobertura explícita:** 6 de 30 requisitos construibles (FR-001..020 + NFR-001..006 + SC-001, 002, 004, 007), es decir, 20 %. Cuentan 5 FR con tarea citada y NFR-001 por palabra clave; no cuentan las coberturas parciales (NFR-003, 005, 006). Con cobertura indirecta, todos los FR tienen un AT, pero solo 5 FR tienen tarea citada.

## Tareas sin requisito mapeado explícito

- **T001** (inventario de fuente). Mapeo a spec.md y trazabilidad global, sin IDs de requisito. Tarea documental, aceptable.
- **T002** (modelo, amenazas, catálogo de aceptación). Mapeo a artefactos, no a FR. Aceptable en esta fase.
- **T004** (ratificar alternativas, constitución y ADR). Sin FR; mapea a constitución y ADR (AN-002-19, AN-002-20).
- **T007** (reejecutar controles). Tarea de proceso; duplicada con T105 (AN-002-13).
- **T101** (comparar historias heredadas). Mapeo a H01..H10 y alias US-HOT, no a FR.
- **T104** (observaciones de runtime). Sin FR; depende de Q-REA, no citado en spec.md.
- **T105** (análisis oficial). Duplicada con T007 (AN-002-13).

## Conteo final

| Severidad | Cantidad | IDs |
|-----------|----------|-----|
| CRITICAL | 0 | — |
| HIGH | 5 | AN-002-01, 02, 03, 04, 05 |
| MEDIUM | 16 | AN-002-06 a AN-002-21 |
| LOW | 3 | AN-002-22, 23, 24 |
| **Total** | **24** | |

**Métricas:**
- Requisitos considerados: 30 construibles (FR-001..020, NFR-001..006, SC-001, 002, 004, 007). Más 4 RF-HOT y 3 US-HOT como alias.
- Tareas: 17 (T001..T007, T101..T105, T201..T205).
- Cobertura explícita de requisitos: 6 de 30 (20 %). Indirecta vía T003–T006: todos los FR.
- Ambigüedades: 4 (AN-002-05, 14, 15, 23).
- Duplicaciones: 3 (AN-002-13, 16, 21).
- Issues críticos: 0.

## Próximas acciones

- No hay hallazgos CRITICAL. La feature sigue BLOCKED por Q-HOT-01..06 y por T003–T007, como indica el propio tasks.md.
- Antes de implementar, resolver como mínimo AN-002-01 a AN-002-05. AN-002-01 depende de la decisión del propietario.
- Los hallazgos MEDIUM y LOW pueden tratarse en la próxima revisión de trazabilidad (T006 o T007).
- Re-ejecutar el análisis oficial del CLI de Spec Kit cuando esté disponible (T007 o T105). Este informe es manual y no lo sustituye.

¿Quiere que proponga correcciones concretas para los 5 hallazgos HIGH? No se aplicará ningún cambio sin su aprobación explícita.
