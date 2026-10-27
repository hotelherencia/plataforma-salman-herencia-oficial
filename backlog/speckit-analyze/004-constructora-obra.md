# Análisis de consistencia Spec Kit — 004-constructora-obra

Fecha: 2026-10-27. Estado de la feature: **BLOCKED**.

Nota de procedencia: este informe se ejecutó **manualmente** en esta sesión, siguiendo los pasos 2–5 de la skill oficial `speckit-analyze` (`C:/Users/herre/AppData/Local/Temp/speckit_probe/probe/.claude/skills/speckit-analyze/SKILL.md`). **No es salida del CLI de Spec Kit.** El script `check-prerequisites.ps1` no existe en el proyecto; las rutas se tomaron directamente de `specs/004-constructora-obra/`. El archivo `.specify/extensions.yml` no existe, por lo que no hay hooks `before_analyze` ni `after_analyze` que revisar.

Artefactos leídos: `spec.md`, `plan.md`, `tasks.md`, `acceptance.md`, `data-model.md`, `checklists/requirements.md`, `.specify/memory/constitution.md`. Como referencia de cruce se consultaron `docs/arquitectura/aclaraciones.md` y `docs/investigacion-competitiva/decisiones-pendientes.md` en `F:/Code/RSalman/plataforma-salman/`. Operación de solo lectura: no se modificó ningún archivo del proyecto ni de RSalman.

Alcance: la skill exige análisis de los tres artefactos principales; `acceptance.md` se leyó porque la pasada de cobertura lo requiere. Las marcas «propuesta, no ejecutada» se tratan como intencionales y no se reportan como fallo.

## Tabla de hallazgos

| ID | Categoría | Severidad | Ubicación | Resumen | Recomendación |
|----|-----------|-----------|-----------|---------|---------------|
| AN-004-01 | Constitución (IV, privacidad) | CRITICAL | spec.md FR-010, FR-018, NFR-004 y Riesgos (L95, L186, L315); plan.md L18; checklists L10 | La constitución pide registrar finalidad, base de tratamiento, responsable/encargado, destinatarios, residencia y retención. La spec trata voz, fotos y ubicación de trabajadores sin registrar esos campos; la retención queda remitida a Q-CORE-03. No aparece la transición Ley 21.719 (01-12-2026) ni el régimen Ley 19.628. La clasificación CRITICAL se aplica por la regla de constitución; el bloqueo ya existe, así que no añade un bloqueo nuevo, pero debe quedar visible para la ratificación. | Añadir a spec.md una sección de tratamiento de datos que enumere los campos exigidos, marcados como pendientes con referencia a Q-CORE-03. No responder Q-CORE-03 en el análisis. |
| AN-004-02 | Constitución (III, aprobaciones) | HIGH | spec.md FR-012, NFR-002, US-OBR-003 (L87) | La constitución exige aprobaciones verificadas, ligadas a operación y parámetros, **con caducidad y uso único**. La spec liga la compra a la versión de líneas, pero no define caducidad ni uso único, y «autorización vigente» (NFR-002) no tiene definición. El límite autónomo de 0 CLP aparece solo en la constitución. | Añadir a NFR-002 las propiedades de caducidad y uso único como requisito pendiente y citar el límite de la constitución. |
| AN-004-03 | Trazabilidad | MEDIUM | spec.md L28–36 (tabla principal), L146–148 (FR-019/020), L330–334 (FR-021–023), L77 y L113 (listas «Requisitos» de US-OBR-003/004) | FR-021..023 no están en la tabla principal: aparecen solo en la sección de recuperación. FR-019/020 están en la tabla «derivados». Las listas de requisitos de US-OBR-003 y US-OBR-004 no incluyen FR-021 (asignado a H3) ni FR-022/FR-023 (asignados a H4). US-OBR-003 sí lista FR-015, que la tabla asigna a H4. La trazabilidad de FR-021..023 se sostiene solo por AT-010..012 y T202. **Respuesta a la pregunta de verificación: sí es un hallazgo de trazabilidad.** | Unificar la tabla de requisitos en un solo lugar o añadir una referencia cruzada, y completar las listas «Requisitos» de US-OBR-003/004 con FR-019..023 según su historia. |
| AN-004-04 | Trazabilidad / numeración | MEDIUM | spec.md (secuencia FR-010..023) | No existen FR-013 ni FR-014 en ningún artefacto de 004 ni en la línea base de RSalman. El hueco no está explicado. | Documentar el motivo del hueco (retirado o no emitido) sin renumerar los IDs heredados. |
| AN-004-05 | Duplicación | HIGH | spec.md FR-020 (L148) y FR-022 (L333) | FR-020 («sin duplicar movimientos… recepción parcial y discrepancias») y FR-022 («conciliar entregas… sin duplicar por reenvío… recepción aceptada») describen la misma conciliación de recepciones por línea. Son requisitos casi duplicados con enunciados que pueden divergir. | Dejar una sola formulación canónica (FR-022 como ampliación de FR-020, o al revés) y referenciar la otra. |
| AN-004-06 | Duplicación / solapamiento | MEDIUM | spec.md FR-016 y FR-019 (L34, L147); FR-017 y FR-022 (L35, L333); FR-010 y FR-021 (L30, L332) | Solapamientos parciales: inspección/observación (FR-016 frente a FR-019), recepción/conciliación de materiales (FR-017 frente a FR-022) y registro de avance por partes (FR-010 frente a FR-021). | Revisar si cada par debe quedar fusionado o si la diferencia (p. ej., FR-021 solo para partes de turno) debe declararse explícitamente en cada enunciado. |
| AN-004-07 | Duplicación (aceptación) | MEDIUM | acceptance.md AT-010, AT-011, AT-012 frente a AC-US-OBR-003-03, AC-US-OBR-004-03 y AC-US-OBR-004-06 | Los escenarios de AT-010..012 repiten textualmente los AC de las historias (mismo ejemplo de turnos, 10/6/5 y 100/50/20/10). Sin una fuente única, un cambio en un lado no se propaga. | Mantener un solo escenario por caso y que el otro lo referencie por ID. |
| AN-004-08 | Duplicación (texto) | LOW | spec.md L48 y L58 (bloque Q-OBR-01..03 repetido); también data-model.md L25, plan.md L36, checklists L15 | El bloque Q-OBR-01..03 aparece dos veces en la spec, y el mismo texto se repite en otros artefactos. | Dejar una copia en spec.md y remitir desde los demás. |
| AN-004-09 | Inconsistencia (terminología) | MEDIUM | spec.md L89 «Reporte», L156–196 «Parte», FR-021 «partes»; data-model.md L7 y plan.md L26 «ReporteAvance», data-model.md L37 «ParteTrabajo»; spec.md L225 «EntregaProveedor» frente a data-model.md L37 «Entrega/TramoOrden»; «Observación» frente a «Observacion»; «SolicitudCompra» frente a «SolicitudCompraVersionada» y «orden» | El mismo concepto aparece con nombres distintos según el archivo (reporte/parte/ReporteAvance/ParteTrabajo; entrega/EntregaProveedor/TramoOrden). Además, la tilde de «Observación» cambia entre artefactos. | Crear un glosario único en spec.md o data-model.md y ajustar los nombres en los demás artefactos. |
| AN-004-10 | Constitución (II, Chile) | MEDIUM | spec.md FR-011, FR-012, FR-023; AT-002; AC-US-OBR-004-06 | La constitución exige CLP en unidades enteras, con precisión y reglas de redondeo ratificadas para cálculos con UF. La spec compara presupuesto, precio y exposición sin definir moneda, redondeo ni tratamiento de UF. La dependencia de Q-CORE-02 aparece en plan.md L16 y spec.md L227, pero no en los requisitos de cálculo. checklists L23 lo reconoce como pendiente. | Citar Q-CORE-02 en FR-011, FR-012 y FR-023 como dependencia explícita, sin proponer valores. |
| AN-004-11 | Ambigüedad / métrica | MEDIUM | spec.md SC-008 (L42); acceptance.md L22 | SC-008 («avance por partida disponible el día del reporte») no define «disponible», denominador, ventana ni línea base. El texto ya marca «objetivo heredado, condicionado a revisión», pero la medición no tiene criterio en la spec. | Añadir a SC-008 la definición de «disponible» y los campos de medición (denominador, ventana, muestra) como requisito pendiente. |
| AN-004-12 | Subespecificación | MEDIUM | spec.md NFR-004 (L55) y NFR-005 (L56); acceptance.md (sin caso para NFR-004/005) | NFR-005 pide medir latencia desde recepción hasta resultado confirmado, sin umbral ni caso de prueba. NFR-004 remite a Q-CORE-03 sin escenario de restauración. Ninguno tiene caso en acceptance.md. | Añadir un caso de aceptación pendiente para cada uno, con su denominador y su condición de no-declaración en muestras vacías. |
| AN-004-13 | Ambigüedad (sección vacía) | MEDIUM | spec.md L8 («V2; FR-010 a FR-012 y H3 heredados») y L6–10 («Problema, actores y límites») | La sección «Problema» no contiene un enunciado del problema; la línea 8 es una nota de versión sin verbo ni sujeto claros. | Redactar el enunciado del problema y la nota de origen de forma explícita. |
| AN-004-14 | Ambigüedad (términos) | LOW | spec.md FR-010 («cuando proceda»), NFR-002 («vigente»), SC-008 («disponible»), FR-011 («umbral aprobado»); acceptance AT-001 («ubicación solo cuando proceda») | Términos sin criterio medible: «cuando proceda», «vigente», «disponible». Algunos apuntan a decisiones pendientes (Q-OBR-02) y están señalados, pero otros no. | Añadir una nota de dependencia o definición en cada término, sin proponer el criterio. |
| AN-004-15 | Cobertura | MEDIUM | tasks.md (T001–T205); spec.md FR-010..023, SC-008/010/011, NFR-001..006 | Ninguna tarea referencia por ID un FR, SC o NFR. La cobertura es implícita: AT-001..012 y ADV-001..003 cubren FR-010..023 y NFR-001/002/003; SC-010 y SC-011 no tienen tarea propia, y NFR-004 y NFR-005 solo aparecen de forma genérica en T205. | Añadir a las tareas la lista de IDs que cubren (p. ej., T006 → AT-001..012, ADV-001..003; T205 → NFR-005; T203 → SC-010/SC-011). |
| AN-004-16 | Inconsistencia (dependencias externas) | MEDIUM | tasks.md T104, T105, T204 (Q-REA-01/02/03, Q-TOOL-01, REA); T007 | Las tareas dependen de REA y de la instalación de Spec Kit v1.2.0. Ni spec.md ni plan.md mencionan REA ni Q-TOOL-01. Q-REA-01 exige Node >= 22.19 y el runtime actual es Node 18.19.1 (aclaraciones.md L7). Esto impide ejecutar el análisis oficial (T007/T105). | Mencionar en plan.md la dependencia de herramientas externas como condición de la fase 2, sin fijar versiones. |
| AN-004-17 | Ordenación / duplicación de tareas | MEDIUM | tasks.md T007 (depende de T006) y T105 (depende de T103 y Q-TOOL-01) | T007 y T105 tienen la misma salida (análisis de consistencia de Spec Kit y backlog por historia). T007 se declara posterior solo a T006, pero T102–T103 modifican los casos que el análisis debe revisar. | Unificar en una sola tarea o hacer que T007 dependa también de T103 y T104. |
| AN-004-18 | Referencia huérfana | LOW | tasks.md L13 («No se incluye implementar T008») | T008 no existe en la lista de tareas. | Eliminar la referencia o renombrarla. |
| AN-004-19 | Trazabilidad (enlaces) | MEDIUM | spec.md L62 (`../../docs/...`, `estado-del-arte.md`); plan.md L32, L48, L58 (ADR-001..006, `arquitectura/dependencias.md`) | Las rutas relativas `../../docs/...` no resuelven dentro de `` (no existe `docs`). `docs/investigacion/estado-del-arte.md` no se encontró con ese nombre (en RSalman existe bajo `investigacion-competitiva/`). Los ADR-001..006 no se encontraron en ``; no se buscaron en RSalman. Estado de los ADR: INFORMACIÓN NO VERIFICADA. | Corregir las rutas o indicar la raíz de referencia. Confirmar la ubicación de los ADR. |
| AN-004-20 | Inconsistencia (stack) | LOW | plan.md L9 frente a plan.md L42 | L9 presenta Redis como propuesta de la base de referencia; L42 indica que no se justifica Redis como necesidad comprobada. No es contradicción dura, pero el lector no sabe si Redis entra en el diseño. | Indicar en L9 que Redis queda fuera de la decisión de fase 0. |
| AN-004-21 | Inconsistencia (checklist) | LOW | checklists/requirements.md L3 («requisitos con namespace») frente a spec.md y acceptance.md | El checklist marca como cumplido el namespace de feature, pero FR-, SC-, NFR- y AT- no llevan prefijo 004. AGENTS.md pide namespace de feature para FR/SC/AT sin renumerar IDs heredados. | Documentar la equivalencia del namespace (p. ej., la carpeta) en la spec o ajustar la marca del checklist. |
| AN-004-22 | Formato | LOW | spec.md (estructura general) | Formato distinto de la plantilla oficial de Spec Kit: no hay sección Edge Cases, la tabla de requisitos usa «El sistema DEBE» y la historia usa campos propios. Según el encargo, LOW de formato. | Ninguna acción obligatoria; alinear con la plantilla en la ratificación. |
| AN-004-23 | Inconsistencia (referencias Q-*) | LOW | spec.md L55 (Q-CORE-03), L227 (Q-CORE-02); tasks.md T104, T204 (Q-REA-01/02/03), T105 (Q-TOOL-01) | Los IDs se citan sin indicar el archivo donde se definen. Existen en `RSalman/.../docs/arquitectura/aclaraciones.md` (Q-CORE-02/03, Q-REA-01/02/03, Q-TOOL-01); no están en la spec. | Añadir una referencia de origen (archivo y sección) para cada ID citado fuera de Q-OBR. |

## Cobertura FR y SC → tareas

Ninguna tarea cita un FR, SC o NFR por ID. La columna «Caso de aceptación» muestra la cobertura real encontrada.

| Requisito | Tiene tarea (ID explícito) | Caso de aceptación | Notas |
|-----------|----------------------------|--------------------|-------|
| FR-010 | No (implícito en T006, T103) | AT-001 | |
| FR-011 | No | AT-002 | Depende de Q-OBR-02 |
| FR-012 | No | AT-003 | |
| FR-013 | — | — | No existe (AN-004-04) |
| FR-014 | — | — | No existe (AN-004-04) |
| FR-015 | No | AT-004 | Listado en US-OBR-003 y asignado a H4 |
| FR-016 | No | AT-005 | Solapa con FR-019 (AN-004-06) |
| FR-017 | No | AT-006 | Solapa con FR-022 (AN-004-06) |
| FR-018 | No | AT-007 | Depende de Q-OBR-03 |
| FR-019 | No (T102) | AT-008 | Fuera de la tabla principal (AN-004-03) |
| FR-020 | No (T102) | AT-009 | Duplica FR-022 (AN-004-05) |
| FR-021 | No (T202) | AT-010 | Fuera de la tabla principal; no listado en US-OBR-003 (AN-004-03) |
| FR-022 | No (T202) | AT-011 | Duplica FR-020; no listado en US-OBR-004 (AN-004-03/05) |
| FR-023 | No (T202) | AT-012 | No listado en US-OBR-004 (AN-004-03) |
| SC-008 | No | Fila de verificación pendiente (sin AT) | Ambigüo (AN-004-11) |
| SC-010 | No | Fila de verificación pendiente (sin AT) | Sin tarea propia (AN-004-15) |
| SC-011 | No | Fila de verificación pendiente (sin AT) | Sin tarea propia (AN-004-15) |
| NFR-001 | No (T004 implícito) | ADV-001..003 | |
| NFR-002 | No | ADV-002 | Caducidad y uso único ausentes (AN-004-02) |
| NFR-003 | No (T203 implícito) | ADV-001..003 | |
| NFR-004 | No | Ninguno | Remite a Q-CORE-03 (AN-004-12) |
| NFR-005 | No (T205 implícito) | Ninguno | Sin umbral (AN-004-12) |
| NFR-006 | No | Referencia textual en acceptance.md L45 | |

## Tareas sin requisito mapeado

Sin ID de requisito, historia o RF explícito: T001, T002, T004, T005, T006, T007, T104, T105, T204, T205.

Con referencia a historia o RF, pero sin ID de requisito: T101 (fuentes O01..O09), T102 (FR-019/020 solo en texto), T103 (AC-US-OBR), T201 (RF-OBR-01..04), T202 (FR-021..023 solo en texto), T203 (AC nuevos).

Solo T104 y T204 dependen de REA sin requisito asociado (AN-004-16).

## Constitución: resultado por principio

- I. Core primero: sin hallazgos.
- II. Chile operativo: AN-004-10 (MEDIUM).
- III. Agentes gobernados: AN-004-02 (HIGH). El límite de 0 CLP no aparece en la spec.
- IV. Seguridad y privacidad: AN-004-01 (CRITICAL).
- V. Pruebas verificables: AN-004-11 y AN-004-12 (MEDIUM). Los denominadores y las muestras de SC-008 no están en la spec.
- VI. Simplicidad, observabilidad y medición: sin hallazgos. RPO/RTO se declara pendiente (Q-CORE-03) y bloquea implementación, consistente con la constitución.

## Métricas

- Requisitos inventariados: 21 (12 FR, 3 SC, 6 NFR). FR-013 y FR-014 no existen.
- Tareas: 17 (T001–T007, T101–T105, T201–T205). Marcadas como hechas: 4 (T001, T002, T101, T201).
- Cobertura con ID explícito de tarea: 0 de 21 (0 %).
- Cobertura con caso de aceptación (AT/ADV): 16 de 21 (76 %). Los 5 restantes son SC-008, SC-010, SC-011 (fila de verificación sin AT), NFR-004 y NFR-005 (sin caso).
- Ambigüedades: 3 (AN-004-11, AN-004-13, AN-004-14).
- Duplicaciones: 4 (AN-004-05, AN-004-06, AN-004-07, AN-004-08).
- Hallazgos por severidad: CRITICAL 1, HIGH 2, MEDIUM 13, LOW 7. Total 23 (dentro del límite de 50).
- Issues críticos: 1.

## Próximas acciones

- Hay un CRITICAL (AN-004-01). Debe quedar resuelto o explícitamente aceptado antes de cualquier paso de implementación. El bloqueo ya está vigente, así que no hay cambio de estado.
- Los HIGH (AN-004-02 y AN-004-05) deben corregirse en la próxima revisión de la spec, antes de la ratificación.
- Los MEDIUM y LOW pueden tratarse en la revisión de T007 o en la fase 1.
- Esta ejecución no modificó archivos del proyecto ni de RSalman. Si se quiere, puede prepararse una propuesta de remediación para los 5 hallazgos de mayor severidad. Ninguna respuesta a Q-* se propone aquí.
