# Informe de análisis de consistencia — 001-cafeteria-mesas-pos

**Fecha:** 2026-10-27
**Ejecución:** manual, siguiendo en esta sesión la skill oficial `speckit-analyze` (pasos 2–5 y salida del paso 6). No es salida del CLI de Spec Kit.
**Modo:** solo lectura. No se modificó ningún archivo del proyecto ni de RSalman. No se ejecutaron `init`, `implement` ni `converge`. No se leyeron `.env` ni `Untitled`.
**Estado de la feature:** BLOCKED para implementación.

**Artefactos analizados:**
- `specs/001-cafeteria-mesas-pos/spec.md`
- `specs/001-cafeteria-mesas-pos/plan.md`
- `specs/001-cafeteria-mesas-pos/tasks.md`
- `specs/001-cafeteria-mesas-pos/acceptance.md` (pasada de cobertura)
- `.specify/memory/constitution.md` (versión propuesta 1.1.0, pendiente de ratificación; los hallazgos de la pasada D se evalúan contra ese texto)

**Notas de método:**
- `check-prerequisites.ps1` no existe en el proyecto; se usaron las rutas directas indicadas.
- `.specify/extensions.yml` no existe; no hay hooks `before_analyze` ni `after_analyze` que ejecutar.
- La skill define seis pasadas (A–F). Se aplicaron las seis; las inconsistencias de la pasada F se registran con categoría «ambigüedad», por ser la más cercana de las categorías pedidas.
- Se respetaron las marcas de «propuesta, no ejecutada» y el formato «Historia N». Las preguntas Q-CAF-01/02/03 se citan como dependencias y no se responden.
- No se ejecutó `scripts/validar_documentacion.py`; no fue solicitado.

---

## Specification Analysis Report

| ID | Categoría | Severidad | Ubicación(es) | Resumen | Recomendación |
|----|-----------|-----------|---------------|---------|---------------|
| AN-001-01 | alineación constitución | CRITICAL | spec.md §3 Entidades clave (L79–87) y §5 (L104–117); plan.md Constitution Check, fila «Seguridad y privacidad» | El spec no define finalidad, base de tratamiento, responsable/encargado, destinatarios, residencia ni retención para los datos personales que el sistema trata (comensales por QR, teléfono de WhatsApp, pagos, facturas con proveedor). La constitución IV lo exige. La retención solo aparece como dependencia de Q-CORE-03 (NFR-004). El plan lo deja pendiente. | Añadir en el spec un bloque de tratamiento de datos por categoría de dato (finalidad, base, responsable/encargado, destinatarios, residencia, retención, derechos). Resolverlo en T004 con revisión legal. No se propone la respuesta jurídica. |
| AN-001-02 | cobertura | HIGH | tasks.md (ausencia de T201–T205); spec.md §3 FR-015 y FR-016 (L259–262) | FR-015 y FR-016 (derivados de investigación competitiva) solo tienen tareas de validación previa (T102, T103, T105). No hay tareas de implementación equivalentes a T201–T205. **Hallazgo conocido, registrado sin corregir.** | Crear la serie de tareas de implementación de FR-015/FR-016 al levantar el bloqueo. No se modificó tasks.md. |
| AN-001-03 | alineación constitución | HIGH | spec.md FR-011 (L74), H3 escenario 1 (L46); acceptance.md AT-011 (L17) | La constitución III exige aprobaciones humanas verificadas, ligadas a operación y parámetros, con caducidad y uso único. El spec solo exige «aprobación humana por WhatsApp». AT-011 pide «autenticada» y caducidad de 48 h, pero no uso único ni vinculación a operación/parámetros. El plan (L17) declara la política «definida», y el spec no la contiene. | Añadir a FR-011/FR-016 y AT-011 los criterios de verificación del canal de aprobación, vinculación, caducidad y uso único. Ratificar en T004. Si se implementa sin ello, escalaría a CRITICAL. |
| AN-001-04 | ambigüedad | HIGH | spec.md FR-001 (L64); acceptance.md AT-001 (L7); plan.md L30 | «QR único por mesa» no define vigencia, rotación, revocación ni validación de sesión. AT-001 prueba «QR revocado o modificado», pero el spec no dice cómo se revoca. El plan lista «QR adulterado» como amenaza. Atributo de seguridad sin criterio medible. | Especificar en FR-001 el criterio de vigencia y revocación y el mecanismo mínimo de validación. Ratificar en T004. |
| AN-001-05 | ambigüedad (inconsistencia) | HIGH | spec.md H1 escenario 1 (L23) vs SC-001 (L95); acceptance.md AT-003 (L9) | El escenario de H1 exige «en menos de 5 segundos» sin porcentaje, lo que implica 100 %. SC-001 fija el 90 %. AT-003 pide medir «en la muestra definida», pero ningún artefacto define esa muestra. Los criterios se contradicen y uno no es verificable. | Unificar en H1 y SC-001 el denominador y el percentil. Definir en AT-003 la muestra, la ventana y la forma de contar fallos (T006). |
| AN-001-06 | ambigüedad | HIGH | spec.md SC-006 (L100); sin definición en spec §3–§5 ni en acceptance.md | «Insumos críticos» no tiene criterio de criticidad ni lista. SC-006 no es verificable. | Definir el criterio de criticidad y el denominador en el spec o en data-model.md antes de T006. |
| AN-001-07 | ambigüedad | HIGH | spec.md FR-012 (L75) y H3 escenario 2 (L47); acceptance.md AT-012 (L18) | FR-012 usa «fuera de patrón» sin criterio. H3 fija «superior a 3 veces el promedio diario», pero FR-012 no lo recoge y AT-012 dice «umbral definido» sin cifra. No hay ventana temporal ni tolerancia. Es un control antifraude con atributo ambiguo. | Fijar en FR-012 y AT-012 el criterio cuantitativo, la ventana y la tolerancia. Mantener el 3× como valor propuesto, sin ratificar. |
| AN-001-08 | alineación constitución | MEDIUM | spec.md FR-005 (L68), H1 escenario 3 (L25); acceptance.md AT-005 (L11); plan.md L28 | La constitución II exige separar aprobación bancaria, emisión, aceptación y entrega documental. FR-005 agrupa emisión y entrega y no define estados de aceptación. El plan menciona solo un estado independiente para la emisión. | Definir estados separados para cada etapa en FR-005 y en data-model.md (T004/T005). |
| AN-001-09 | alineación constitución | MEDIUM | spec.md FR-013 (L76), FR-014 (L77); constitución VI | La constitución VI exige auditoría con actor, empresa, correlación, acción, parámetros minimizados, política, aprobación, evidencia y resultado, y también logs estructurados y métricas. FR-013 limita el registro a «acciones de agente» y no lista campos. Pagos y documentos no agénticos no tienen requisito explícito de auditoría, y FR-014 delega en el core sin criterio. | Ampliar FR-013 con los campos mínimos y el alcance a operaciones financieras y tributarias. Añadir requisito de observabilidad (logs y métricas). |
| AN-001-10 | alineación constitución | MEDIUM | plan.md Constitution Check (L16, principio II) vs plan.md L50 (gate) | La tabla incluye «Chile operativo» (principio II), pero la frase de gate cita «principios I/III/IV/V/VI» y omite el II. | Alinear la frase de gate para incluir el principio II. |
| AN-001-11 | subespecificación | MEDIUM | spec.md US-CAF-001 precondiciones (L159), AC-US-CAF-001-01 (L177), AT-015 (L59) | La regla de redondeo y de residuo es precondición de H1 y de FR-015, pero no está en Q-CAF-01..03 ni en tasks.md. El ejemplo 3333/3333/3334 se llama «regla de ejemplo». La constitución II exige reglas de redondeo ratificadas. | Asignar dueño y tarea para la regla de redondeo y residuo, por ejemplo en T102. No se propone la regla. |
| AN-001-12 | duplicación | MEDIUM | spec.md US-CAF-001/003 (L147–252); acceptance.md AT-015/AT-016 (L59–60) y AC-US-CAF (L44–55) | Los escenarios se repiten en tres lugares: AC-US-CAF-001-01 ≡ AT-015 (mismo ejemplo 10000/3), AC-US-CAF-003-01 ≡ AT-016 (misma detección), y la historia alias US-CAF-001 repite H1. Riesgo de deriva al editar uno solo. | Mantener una sola fuente de escenarios y que las otras referencias apunten a ella. |
| AN-001-13 | duplicación | MEDIUM | tasks.md T007 (L11) y T105 (L21) | Ambas tareas generan el backlog por historia y ejecutan el análisis de Spec Kit. T105 depende de Q-TOOL-01 y T007 de «cuando esté disponible». Solapamiento con condiciones distintas. | Consolidar en una sola tarea. Esta corrida puede servir como evidencia parcial de T007. |
| AN-001-14 | ambigüedad (inconsistencia) | MEDIUM | spec.md §5 Supuestos (L108–109) vs Clarificaciones (L121–126) y Q-CAF-02/03 | Los supuestos «Eleventa convive en V1 solo como caja de respaldo» y «la carta es editable y exportable» tratan como supuesto algo que Q-CAF-02 y Q-CAF-03 dejan abierto. FR-006 depende de esa decisión. | Marcar esos supuestos como no ratificados y vinculados a Q-CAF-02/03, o retirarlos. No se decide aquí. |
| AN-001-15 | subespecificación | MEDIUM | spec.md §5 Supuestos (L111: «fallos ocasionales menores a 30 minutos») vs FR-006 (L69), edge case (L52) y AT-006 | El supuesto de internet estable no define qué pasa con una caída de más de 30 minutos. FR-006 y AT-006 exigen modo degradado sin límite temporal. | Declarar en FR-006 o en Q-CAF-02 el tratamiento y la ventana de la cola offline. |
| AN-001-16 | subespecificación | MEDIUM | spec.md §2 casos borde (L53–54) | «Mesa que se junta o se divide a mitad del servicio» y «cliente que cierra el navegador antes de pagar» no tienen FR ni AT. | Añadir FR y AT, o declarar explícitamente fuera de V1. |
| AN-001-17 | ambigüedad (inconsistencia) | MEDIUM | spec.md §3 Entidades (L86) vs FR-014 (L77); plan.md L26 | «Pago y Documento tributario» aparecen como entidades del feature con estado propio. FR-014 y el plan dicen que pagos y documentos viven en el core y que el pedido «no replica el estado bancario». | Aclarar en el spec qué entidad local es solo referencia y cuál es propiedad del core. |
| AN-001-18 | ambigüedad (inconsistencia) | MEDIUM | spec.md §3 Entidades clave vs US-CAF-001/002/003 «Datos y estados» (L167, L203, L239) y plan.md L48 | AsignaciónCuenta, ParteSaldo, IntentoPago, LoteImportación, EjecuciónRegla, Detección, Propuesta/Alerta y Revisión aparecen en US-CAF y en el plan, pero no en la sección de entidades clave del spec. | Incorporar esas entidades en §3 o referenciar data-model.md desde el spec. |
| AN-001-19 | ambigüedad (terminología) | MEDIUM | spec.md FR-013 («registro de auditoría»), H3 escenario 3 y SC-007 («ledger»); H1 y plan («comanda», «pedido», «orden») | «Ledger» y «registro de auditoría» se usan como sinónimos. «Comanda», «pedido» y «orden» también se mezclan (orden de compra vs orden de cocina). | Glosario único en spec §3 con los términos canónicos. |
| AN-001-20 | ambigüedad (terminología) | MEDIUM | spec.md NFR-001 («empresa»), NFR-002 y acceptance.md/plan.md L30 («tenant»); constitución I y IV («empresa», «tenant») | «Empresa» y «tenant» se usan como si fueran el mismo concepto sin definirlo. | Definir la relación en el glosario (una empresa es un tenant, o no). |
| AN-001-21 | cobertura | MEDIUM | spec.md SC-001, SC-003, SC-004, SC-005, SC-007, SC-008 vs tasks.md | Seis SC son construibles (latencia, conciliación, precisión de margen e inventario, ledger, tiempo de dashboard) y no tienen tarea. acceptance.md las deja como «verificación pendiente». SC-002 y SC-006 se excluyen por ser resultados de negocio. | Añadir tarea de instrumentación y medición (T006 o backlog), con muestra, ventana y línea base. |
| AN-001-22 | cobertura | MEDIUM | spec.md NFR-004 (L133) y NFR-005 (L134) vs tasks.md | NFR-004 (retención, RPO/RTO) y NFR-005 (medición desde recepción) no tienen tarea. La constitución VI exige RPO/RTO antes de producción. | Incluir RPO/RTO y retención en T004, y la medición NFR-005 en T006. |
| AN-001-23 | cobertura | MEDIUM | spec.md §5 Dependencias (L115–117); plan.md L7 («muestras y credenciales no entregadas») | Dependencias externas (certificado SII, contrato Webpay/Mercado Pago, cuenta WhatsApp Business API) y muestras (carta, recetas, exportación Eleventa) no tienen tarea de obtención ni responsable. | Añadir tareas de gestión de dependencias y de datos autorizados con dueño, en T003 o T004. |
| AN-001-24 | cobertura | MEDIUM | FR-001 a FR-014 vs tasks.md | Ningún FR-001..014 aparece por ID en tasks.md. La cobertura es solo indirecta, vía T006 → acceptance.md AT-001..014. La trazabilidad por requisito no se puede verificar desde las tareas. | En el backlog de T007/T105, una tarea por FR con su ID. |
| AN-001-25 | subespecificación | MEDIUM | tasks.md T104 (Q-REA-01/02, «REA»), T105 (Q-TOOL-01); spec.md NFR-004 (Q-CORE-03); plan.md L16 (Q-CORE-02) | Identificadores definidos fuera de los cuatro artefactos. Verificados en RSalman (corrección de la versión anterior de este hallazgo): Q-REA-01 y Q-REA-03 en `plataforma-salman/docs/arquitectura/decisiones-pendientes.md` y `docs/investigacion-competitiva/decisiones-pendientes.md`; Q-REA-02 en el segundo; Q-TOOL-01 y Q-CORE-02/03 en `docs/arquitectura/aclaraciones.md`. Q-CORE-03 tiene además un segundo significado en `docs/investigacion-competitiva/decisiones-pendientes.md` («Q-COMP-05 / Q-CORE-03», medición y priorización). | Conflicto de definición en Q-CORE-03: resolver cuál significado rige antes de cerrar NFR-004 y la decisión de core. Q-REA-01 requiere aprobación para actualizar Node a v22+ y Q-REA-03 requiere aprobación antes de cambios globales de MCP/skills; ninguno se resuelve desde el análisis. No se infiere contenido adicional. |
| AN-001-26 | cobertura | MEDIUM | spec.md §5 Clarificaciones (L126: «¿Proveedores con catálogo digital…?») vs Q-CAF-01..03 y T003 | La pregunta de proveedores no aparece en la enumeración de Q-CAF-01..03 ni en T003. | Incluirla en Q-CAF-03 o registrarla como pregunta nueva en la fuente. No se responde aquí. |
| AN-001-27 | subespecificación | MEDIUM | spec.md H1 escenarios 2–3 (L24–25) y casos borde (L54) vs Q-CAF-01 (L121) | Los escenarios de H1 (pago parte a parte, paso a cobro en caja) presuponen un momento de pago que Q-CAF-01 deja abierto. No son ejecutables hasta resolver Q-CAF-01, y no están marcados como dependientes. | Marcar en acceptance.md los escenarios H1 dependientes de Q-CAF-01. |
| AN-001-28 | ambigüedad (inconsistencia) | MEDIUM | spec.md H1 escenario 3 (L25) y SC-003 (L97): «30 segundos»; spec.md nota final (L138): «30/60 segundos» | El objetivo de emisión es 30 s en el escenario y en SC-003, pero la nota final menciona 60 s sin que ningún requisito lo defina. Además depende de una «política fiscal aprobada» que no existe todavía (FR-005). | Unificar la cifra en el spec. Si el 60 s es una aspiración de la fuente, dejarlo solo en la nota y explicarlo. |
| AN-001-29 | cobertura | MEDIUM | tasks.md T007 (L11) y T102–T104 (L18–20) | T007 depende solo de T006, pero su salida exige «informe sin bloqueos». T102–T104 se llaman «previas a implementar», pero no están en la cadena de dependencias de T007. T007 podría cerrarse antes que ellas. | Añadir T102–T104 como dependencias de T007 o aclarar el orden. |
| AN-001-30 | ambigüedad (inconsistencia) | LOW | plan.md L9 | El plan dice «No fijar versiones» y a la vez nombra Python 3.12, PostgreSQL 16, FastAPI, Next.js y Redis. Están marcadas como propuesta. | Retirar las versiones hasta ADR-003 o mantener la marca de propuesta de forma explícita. |
| AN-001-31 | ambigüedad (formato) | LOW | spec.md «Historia 1 (P1)» (L16–L48) vs plantilla oficial «User Story N» | El formato difiere de la plantilla oficial. No hay ambigüedad real. | Sin acción obligatoria. Mantener el formato del proyecto. |
| AN-001-32 | ambigüedad | LOW | spec.md NFR-002 («autorización vigente», L131); NFR-006 («incertidumbre», L264) | «Vigente» y «incertidumbre» no tienen criterio de medición. | Añadir la definición operativa al glosario o al NFR. |

### Resultado por pasada

- **A. Duplicación:** 2 hallazgos (AN-001-12, AN-001-13). Hay además solapamiento entre división por ítem de FR-004 y FR-015, aceptado como alias.
- **B. Ambigüedad:** 13 hallazgos (AN-001-04, 05, 06, 07, 14, 17, 18, 19, 20, 28, 30, 31, 32). Los más relevantes son 04, 06 y 07, por atributos de seguridad (QR, criterio de insumos críticos y umbral antifraude) sin criterio medible.
- **C. Subespecificación:** 5 hallazgos (AN-001-11, 15, 16, 25, 27).
- **D. Alineación constitución:** 5 hallazgos (AN-001-01, 03, 08, 09, 10). Principios revisados sin hallazgo adicional: I (core compartido, FR-014 correcto), V (datos autorizados y denominadores en acceptance.md; el «medido» no se declara), VI (idempotencia y compensación en NFR-003 y ADV-002). Principio III: el límite de 0 CLP y la denegación por defecto no aparecen en el spec; se cubren en AN-001-03.
- **E. Cobertura:** 7 hallazgos (AN-001-02, 21, 22, 23, 24, 26, 29).
- **F. Inconsistencia** (registrada como ambigüedad): AN-001-05, 14, 17, 18, 19, 20, 28 y 30. Son las contradicciones entre artefactos y la deriva terminológica. Ya constan en la pasada B, por lo que no se cuentan dos veces.

---

## Cobertura FR y SC → tareas

Criterio: **explícita** = el ID aparece en tasks.md; **indirecta** = cubierto por acceptance.md, que tasks.md referencia en T006 (o por T004/T103 en NFR); **sin tarea** = ninguna tarea lo referencia.

| Requisito | ¿Tiene tarea? | Tareas (IDs) | Notas |
|-----------|---------------|--------------|-------|
| FR-001 | Indirecta | T006 → AT-001 | QR sin criterio de revocación (AN-001-04). |
| FR-002 | Indirecta | T006 → AT-002 | |
| FR-003 | Indirecta | T006 → AT-003 | Muestra sin definir (AN-001-05). |
| FR-004 | Indirecta | T006 → AT-004 | |
| FR-005 | Indirecta | T006 → AT-005 | Estados separados pendientes (AN-001-08). |
| FR-006 | Indirecta | T006 → AT-006, ADV-003 | Ventana offline sin límite (AN-001-15). |
| FR-007 | Indirecta | T006 → AT-007 | |
| FR-008 | Indirecta | T006 → AT-008 | |
| FR-009 | Indirecta | T006 → AT-009 | |
| FR-010 | Indirecta | T006 → AT-010 | Requiere datos autorizados. |
| FR-011 | Indirecta | T006 → AT-011 | Verificación de aprobación incompleta (AN-001-03). |
| FR-012 | Indirecta | T006 → AT-012 | Umbral sin cifra (AN-001-07). |
| FR-013 | Indirecta | T006 → AT-013 | Alcance y campos limitados (AN-001-09). |
| FR-014 | Indirecta | T005, T006 → AT-014 | |
| FR-015 | **Explícita** (validación) | T102, T103 | **Sin tarea de implementación** (AN-001-02). |
| FR-016 | **Explícita** (validación) | T102, T103 | **Sin tarea de implementación** (AN-001-02). |
| NFR-001 | Indirecta | T004, T006 → ADV-001..003 | |
| NFR-002 | Indirecta | T004, T006 → ADV-001..003 | |
| NFR-003 | Indirecta | T006 → ADV-001..003 | |
| NFR-004 | **Sin tarea** | — | RPO/RTO y retención (AN-001-22). |
| NFR-005 | **Sin tarea** | — | Medición desde recepción (AN-001-22). |
| NFR-006 | Indirecta | T103 (AC-US-CAF) | |
| SC-001 | **Sin tarea** | — | Construible; «verificación pendiente» (AN-001-21). |
| SC-002 | Excluido | — | Resultado de negocio (cierre −30 % vs eleventa). Requiere línea base. |
| SC-003 | **Sin tarea** | — | Construible (AN-001-21). |
| SC-004 | **Sin tarea** | — | Construible (AN-001-21). |
| SC-005 | **Sin tarea** | — | Construible (AN-001-21). |
| SC-006 | Excluido | — | Resultado de negocio; «insumos críticos» sin definir (AN-001-06). |
| SC-007 | **Sin tarea** | — | Construible (AN-001-21). |
| SC-008 | **Sin tarea** | — | Construible (AN-001-21). |

## Tareas sin requisito mapeado

- **T001:** inventario de fuentes. Tarea de proceso, ya completada.
- **T003:** resolución de Q-CAF-01/02/03. Gobernanza. Relacionada con clarificaciones, no con un FR.
- **T007:** informe y backlog genérico. Solapa con T105 (AN-001-13).
- **T104:** depende de Q-REA-01/02, definidos en RSalman (AN-001-25 corregido); sigue sin resolverse por requerir aprobación del propietario.
- **T105:** depende de Q-TOOL-01, definido en RSalman (AN-001-25 corregido). Solapa con T007.

## Métricas

- Requisitos considerados: FR 16 + NFR 6 + SC construibles 6 = **28** (SC-002 y SC-006 excluidos).
- Cobertura explícita por ID (≥1 tarea que nombra el ID): **2 / 28** (7 %), solo FR-015 y FR-016, y solo en validación.
- Cobertura indirecta o explícita (≥1 tarea, directa o vía acceptance.md): **20 / 28** (71 %).
- Requisitos sin tarea: **8** (NFR-004, NFR-005, SC-001, SC-003, SC-004, SC-005, SC-007, SC-008).
- Total de tareas: **12** (T001–T007, T101–T105); completadas: 3 (T001, T002, T101).
- Ambigüedades (categoría ambigüedad, incluidas las inconsistencias de la pasada F): **13**.
- Duplicaciones: **2**.
- Problemas de alineación constitucional: **5** (1 CRITICAL, 1 HIGH, 3 MEDIUM).
- Total de hallazgos: **32**. Límite de 50 no alcanzado; no hay overflow.

## Conteo final por severidad

| Severidad | Número | IDs |
|-----------|--------|-----|
| CRITICAL | 1 | AN-001-01 |
| HIGH | 6 | AN-001-02, 03, 04, 05, 06, 07 |
| MEDIUM | 22 | AN-001-08 a AN-001-29 |
| LOW | 3 | AN-001-30, 31, 32 |
| **Total** | **32** | |

## Próximas acciones

- Hay un CRITICAL (AN-001-01). Resolverlo antes de cualquier `/speckit-implement`. Si la feature sigue BLOCKED, esto ya lo cubre, pero el bloqueo debe incluir este punto de forma explícita.
- Los HIGH que afectan a seguridad y aprobación (AN-001-03, 04, 07) se cierran junto con T004. Los de criterio de medición (AN-001-05, 06) se cierran en T006.
- Las dependencias de Q-CAF-01/02/03 no se responden aquí. Se resuelven en T003 con el responsable indicado.
- Los identificadores externos (AN-001-25) están verificados en RSalman; el conflicto de Q-CORE-03 quedó resuelto el 2026-10-27 (rige `aclaraciones.md`; medición a Q-COMP-05). El registro de FR-015/FR-016 (AN-001-02) sigue pendiente.
- El análisis solo registra; no aplica cambios. Si se quiere, se pueden preparar propuestas de remediación concretas para los HIGH y CRITICAL, previa aprobación explícita.
