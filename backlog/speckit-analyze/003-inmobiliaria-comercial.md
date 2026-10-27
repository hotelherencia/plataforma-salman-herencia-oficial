# Análisis de consistencia Spec Kit — 003-inmobiliaria-comercial

- **Fecha:** 2026-10-27
- **Feature:** `003-inmobiliaria-comercial` · **Estado:** BLOCKED para implementación
- **Modo:** solo lectura. No se modificó ningún archivo del proyecto ni de RSalman.
- **Nota de ejecución:** análisis ejecutado manualmente siguiendo la skill oficial `speckit-analyze` (pasos 2–5: carga, modelos semánticos, pasadas A–E y límite de 50 hallazgos) en esta sesión. No es salida del CLI.
- **Paso 1:** `check-prerequisites.ps1` no existe en el proyecto; se usaron las rutas directas a spec.md, plan.md, tasks.md y la constitución. `.specify/extensions.yml` no existe, por lo que no hay hooks pre ni post análisis.
- **Fuentes leídas:** `specs/003-inmobiliaria-comercial/spec.md`, `plan.md`, `tasks.md`, `acceptance.md`, `.specify/memory/constitution.md`. Para verificar referencias cruzadas se buscó en `data-model.md`, `contracts/README.md` y `checklists/requirements.md`. No se abrieron los documentos de RSalman; las referencias Q-* se registran tal como aparecen en la carpeta y no se responden aquí.
- **Límite:** 23 hallazgos, por debajo del tope de 50. No hubo desbordamiento.

## Tabla de hallazgos

| ID | Categoría | Severidad | Ubicación | Resumen | Recomendación |
|----|-----------|-----------|-----------|---------|---------------|
| AN-003-01 | Inconsistencia (contradicción conocida) | HIGH | spec.md L8 y L96 (fuera de V1) vs. spec.md L55 (FR-003), L68 (entidad Unidad) y plan.md L28 (máquina de estados) | La escrituración queda fuera de V1 según el Problema y los Supuestos, pero FR-003 incluye el estado «escriturada» y la entidad Unidad incluye «escritura». Plan.md también la incluye en la máquina de estados. | Mantener ambas redacciones. Recomendación pendiente de confirmación del propietario; no se resuelve en este informe. |
| AN-003-02 | Constitución (principio II) | CRITICAL | spec.md L25 (H1, escenario 3) y L57 (FR-005) vs. constitution.md principio II y plan.md L16 | La constitución exige que anticipos y reservas tengan política revisada por responsable tributario, y separar emisión de aceptación. El escenario 3 y FR-005 prescriben emisión de boleta o comprobante al pagar la reserva sin esa precondición en la spec. El plan la deja como gate pendiente (Q-CORE-02). | Condicionar FR-005 y el escenario 3 a la política tributaria revisada. No diluir el principio. Si el propietario considera que no hay conflicto, reclasificar a HIGH. |
| AN-003-03 | Constitución (principio IV) | CRITICAL | spec.md (ausente); plan.md L18 (solo «Retención, roles y revisión legal pendientes»); data-model.md L23 (minimización y retención) | La constitución exige registrar finalidad, base de tratamiento, responsable o encargado, destinatarios, residencia, retención y derechos, y planificar Ley 19.628 y la transición a Ley 21.719 (01-12-2026). En toda la carpeta no aparece «21.719» ni «19.628», y no hay finalidad ni base legal para datos de leads, clientes ni portal. | Añadir a spec.md una sección de tratamiento de datos personales con los campos exigidos, marcada como pendiente de validación jurídica. Revisar la severidad con el propietario. |
| AN-003-04 | Constitución (principio V) | HIGH | spec.md L80–87 (SC-001 a SC-009); acceptance.md L26–33 | La constitución exige definir denominadores, muestras, línea base y tolerancias. Los SC no los fijan: SC-004 compara «frente al proceso actual» sin línea base y SC-002 dice «24/7» sin ventana. Acceptance.md lo deja como «verificación pendiente». | Definir denominador, ventana, línea base y tolerancia para cada SC antes de T006. Mantener el estado «no medido» hasta entonces. |
| AN-003-05 | Constitución (principio II) | HIGH | spec.md L56–59 (FR-004, FR-007), L288 («precio UF»); checklists/requirements.md L23 | La constitución exige CLP en unidades enteras y reglas de redondeo ratificadas para conversiones desde UF. La spec no declara moneda ni redondeo para precio, pie, cuotas o financiamiento. Solo aparece «precio UF» en RF-INM-02. El checklist lo tiene pendiente. | Declarar moneda y redondeo como requisito pendiente explícito en FR-003, FR-004 y FR-007, y en el precio UF de RF-INM-02. |
| AN-003-06 | Cobertura (E) | HIGH | tasks.md L5–13 y L17–29; spec.md L53–63 | FR-001 a FR-009, FR-013 y FR-014 no tienen tarea explícita. Su única conexión es indirecta, vía T006 y acceptance.md (AT-001 a AT-011). Tasks.md difiere la creación de tareas de implementación hasta resolver T003–T007 (L13). Es un gate documentado, no una omisión, pero no existe mapa FR→tarea. | Registrar en tasks.md la trazabilidad FR→AT→tarea futura, marcando cada FR como pendiente de T006 y del gate T003–T007. La heurística podría dar CRITICAL; se fija en HIGH porque el bloqueo es explícito. |
| AN-003-07 | Cobertura (E) | MEDIUM | spec.md L80–87; tasks.md (sin tarea) | SC-001 a SC-007 y SC-009 no tienen tarea de medición ni instrumentación (dedup en 5 minutos, primera respuesta 24/7, auditoría trimestral y mensual del ledger). T005 y T205 tratan costos y latencias de forma genérica. | Añadir a T205 o T006 la instrumentación de medición por SC, con fuente, ventana y denominador. |
| AN-003-08 | Trazabilidad | MEDIUM | spec.md L80–87 | El hueco SC-008 no está explicado. La lista pasa de SC-007 a SC-009 sin ninguna nota, a diferencia de H3 y FR-010 a FR-012, que sí están explicados en spec.md L8 y L103. | Añadir una nota que indique si SC-008 fue retirado, trasladado o nunca existió. No renumerar. |
| AN-003-09 | Trazabilidad | MEDIUM | spec.md L125 | Se menciona un «SC de emisión en 30/60 segundos» que no existe en la tabla de SC (SC-001 a SC-009). Es una métrica huérfana: no es trazable ni medible. | Decidir si entra como SC con ID propio o si se retira la referencia. Hasta entonces no se considera requisito. |
| AN-003-10 | Duplicación (A) | HIGH | spec.md L212 (FR-015) vs. L397 (FR-017); L213 (FR-016) vs. L399 (FR-019); L58 (FR-006) vs. L398 (FR-018) | Pares de requisitos solapados con redacción distinta y sin precedencia explícita. FR-015 y FR-017 distinguen visita propuesta y confirmada. FR-016 y FR-019 tratan el permiso de contacto. FR-006 y FR-018 tratan la promesa y su firma. La única regla de precedencia es genérica (spec.md L132). | Consolidar en un solo FR por concepto, o declarar precedencia para cada par. |
| AN-003-11 | Duplicación (A) | LOW | acceptance.md L86, L87 y L89 frente a L62, L68 y L74 | AT-014, AT-015 y AT-017 repiten textualmente AC-US-INM-001-03, 001-06 y 002-03. | Referenciar el AC en lugar de copiar el texto, o eliminar los AT redundantes. |
| AN-003-12 | Inconsistencia (casos borde) | MEDIUM | spec.md L42 frente a acceptance.md L9 y L18 (AT-003, ADV-001) | Dos ejecutivos cotizan la misma unidad. El caso borde dice que la otra cotización se invalida y se avisa. AT-003 y ADV-001 dicen que el segundo pago queda en conciliación o gestión humana. No hay precedencia entre ambos. | Unificar en spec.md el tratamiento de la cotización invalidada y del segundo pago. El reembolso sigue dependiendo de Q-INM-02. |
| AN-003-13 | Inconsistencia (actores) | MEDIUM | spec.md L10 frente a L23, L311, L354 y L372 | La lista de actores tiene cuatro roles. El texto usa además cliente, agente, administrador autorizado, técnico asignado, coordinador de postventa y receptor técnico, sin definirlos. | Completar la lista de actores o añadir un glosario. |
| AN-003-14 | Inconsistencia (terminología) | MEDIUM | spec.md L54 y L67 (visita) frente a L247 (cita); spec.md L60 y L73 (solicitud de postventa) frente a L172 y L190 (CasoPostventa), y plan.md L48 (AtenciónPostventa); spec.md L69 (Lead y Cliente) frente a L154 y L331 (Contacto y Persona); spec.md L62 (registro de auditoría) frente a L87 (ledger) | El mismo concepto se nombra de varias formas en los tres archivos y en la propia spec. | Crear un glosario único en data-model.md y usar un solo término por concepto. |
| AN-003-15 | Ambigüedad (B) | MEDIUM | spec.md L37, L60 y L186 («urgente», «garantía», «no cubierta») | «Urgente» es categoría de clasificación de postventa, pero no tiene criterio operativo. AT-008 depende de ese criterio. | Definir el criterio de urgencia dentro del catálogo previsto en RF-INM-04 (precondición en L362). No inventarlo en esta fase. |
| AN-003-16 | Inconsistencia (dependencias) | MEDIUM | spec.md L57 (FR-005: Webpay o Mercado Pago), L102 (dependencia solo Webpay Plus) y L109 (clarificación abierta sobre pago en línea) | FR-005 prescribe dos pasarelas, pero la dependencia solo lista Webpay Plus. La clarificación abierta cuestiona si el pago en línea es obligatorio. | Alinear FR-005, la dependencia y la clarificación según decisión del propietario. |
| AN-003-17 | Ambigüedad (B) | MEDIUM | spec.md L58 (FR-006: firma electrónica, Ley 19.799) frente a L101 (proveedor de firma electrónica avanzada) | No está especificado el nivel de firma exigido. La dependencia pide firma avanzada y el FR solo dice firma electrónica. | Especificar en FR-006 el nivel de firma exigido, o declararlo pendiente en research.md. |
| AN-003-18 | Inconsistencia (plan) | MEDIUM | plan.md L9 frente a L42 | El Resumen lista Python 3.12, PostgreSQL 16 y Redis con versiones, y dice «no fijar versiones». Complexity Tracking indica que no se justifica Redis. | Elegir una sola posición: stack como candidato sin versión, coherente con ADR-003 pendiente, y retirar Redis si no se justifica. |
| AN-003-19 | Referencia no verificada | MEDIUM | contracts/README.md L37 («endpoint Tokko placeholder») | El proveedor Tokko no aparece en spec.md ni en plan.md. La spec solo nombra Portalinmobiliario, TOCTOC y Yapo. | Confirmar en research.md si Tokko es un proveedor evaluado. Si no, eliminar la mención. |
| AN-003-20 | Gobernanza del proyecto | MEDIUM | spec.md (FR-001 a FR-020, SC-*); acceptance.md (AT-001 a AT-017) | AGENTS.md pide namespace de feature para FR, SC y AT. Los IDs usados no llevan namespace (solo el nombre de la carpeta). | Documentar la convención (carpeta 003 o prefijo INM) en spec.md o acceptance.md. No renumerar IDs heredados. |
| AN-003-21 | Referencia no verificada | MEDIUM | tasks.md L19–21, L28 (Q-REA-01/02/03, Q-TOOL-01, T105); spec.md L120 y L335 (Q-CORE-01/03); spec.md L405 (Q-INM-05/06/07, no referenciados en plan ni tasks) | Se referencian Q-CORE, Q-REA, Q-TOOL y Q-INM-05 a 07, cuyas definiciones no están en la carpeta. T104, T105 y T204 quedan condicionados a ellos. | Verificar en el repositorio de decisiones que existen y cuál es su estado. No responder aquí. |
| AN-003-22 | Terminología (heredada) | LOW | spec.md L113 («compras») y L125 («OTA») | Términos de otra vertical, como «compras» (obra) y «OTA» (hotelería), sin definir en una spec comercial. | Retirar o contextualizar los términos. |
| AN-003-23 | Formato | LOW | spec.md L14 («brecha e del estado»), L32 (espacio antes de «;») y estructura general | Erratas menores y diferencias de formato frente a la plantilla oficial de Spec Kit. | Corregir erratas. Adaptar la estructura a la plantilla solo si se quiere uniformidad. No bloquea. |

## Cobertura FR y SC → tareas

Leyenda: «Tarea explícita» es la que nombra el requisito en tasks.md. «Cobertura indirecta» es el criterio de aceptación de acceptance.md.

| Requisito | Tarea explícita | Cobertura indirecta (acceptance.md) | Notas |
|-----------|-----------------|--------------------------------------|-------|
| FR-001 | No | AT-001 | AN-003-06 |
| FR-002 | No | AT-002 | AN-003-06 |
| FR-003 | No | AT-003 | AN-003-01, AN-003-06 |
| FR-004 | No | AT-004 | AN-003-05, AN-003-06 |
| FR-005 | No | AT-005 | AN-003-02, AN-003-06, AN-003-16 |
| FR-006 | No | AT-006 | AN-003-06, AN-003-17 |
| FR-007 | No | AT-007 | AN-003-06 |
| FR-008 | No | AT-008 | AN-003-06, AN-003-15 |
| FR-009 | No | AT-009 | AN-003-06 |
| FR-010 a FR-012 | Fuera de alcance | — | Trasladados a 004 (spec.md L8). Hueco explicado. |
| FR-013 | No | AT-010 | AN-003-03, AN-003-06 |
| FR-014 | No | AT-011 | AN-003-06 |
| FR-015 | T102 | AT-012 | Sin hallazgo propio |
| FR-016 | T102 | AT-013 | Sin hallazgo propio |
| FR-017 | T202 y T203 (AC nuevos) | AT-014 | AN-003-10 |
| FR-018 | T202 y T203 (AC nuevos) | AT-015 | AN-003-10 |
| FR-019 | T202 y T203 (AC nuevos) | AT-016 | AN-003-10 |
| FR-020 | T202 y T203 (AC nuevos) | AT-017 | AN-003-10, AN-003-11 |
| SC-001 | No | Fila «verificación pendiente» | AN-003-07 |
| SC-002 | No | Fila «verificación pendiente» | AN-003-04, AN-003-07 |
| SC-003 | No | Fila «verificación pendiente» | AN-003-07 |
| SC-004 | No | Fila «verificación pendiente» | AN-003-04, AN-003-07 |
| SC-005 | No | Fila «verificación pendiente» | AN-003-07 |
| SC-006 | No | Fila «verificación pendiente» | AN-003-07 |
| SC-007 | No | Fila «verificación pendiente» | AN-003-07 |
| SC-008 | No existe | — | Hueco sin explicar (AN-003-08) |
| SC-009 | No | Fila «verificación pendiente» | AN-003-07 |
| SC de emisión 30/60 s | No existe como SC | — | Referencia huérfana (AN-003-09) |

**Huecos de numeración:** FR-010 a FR-012 y H3 están explicados (spec.md L8 y L103). SC-008 no está explicado (AN-003-08). FR-013 y FR-014 existen y están cubiertos en acceptance.md.

## Tareas sin requisito mapeado

- T001: inventario de fuente y preservación de IDs. Proceso, sin requisito.
- T002: modelo conceptual y amenazas. Cubre el modelo en general, sin FR explícito.
- T003: resolver Q-INM-01 a 04. Vinculada a decisiones, no a FR.
- T004: ratificar alternativas, constitución, ADR y permisos. Vinculada a gobernanza, no a FR.
- T005: contratos técnicos. Sin FR explícito; contracts/README.md los relaciona con FR-005, FR-013 y otros.
- T006: casos de prueba. Cubre indirectamente FR-001 a FR-020 vía acceptance.md, pero no lo nombra.
- T007: reejecutar controles y análisis de Spec Kit. Proceso.
- T104, T204: observaciones de runtime, condicionadas a Q-REA. Sin requisito explícito.
- T105: análisis oficial y backlog. Condicionada a Q-TOOL-01.
- T205: costos y latencias. Vinculada a NFR-005 de forma genérica, sin SC explícito.

Las tareas T007 y T105 piden la ejecución oficial del análisis cuando haya Spec Kit disponible. Este informe no las cierra.

## Resultados por pasada

- **A. Duplicación:** hallazgos AN-003-10 y AN-003-11.
- **B. Ambigüedad:** no se encontraron placeholders (TODO, TKTK, ???, `<placeholder>`). No se encontraron adjetivos vagos sin criterio medible en las cuatro fuentes. La única ambigüedad relevante es «urgente» (AN-003-15). Se registran además AN-003-17 y AN-003-16.
- **C. Subespecificación:** hallazgos AN-003-05, AN-003-06, AN-003-15 y AN-003-16. Los archivos referenciados por tasks.md y plan.md existen en la carpeta: data-model.md, research.md, quickstart.md, contracts/README.md y checklists/requirements.md. Los ADR-001 a ADR-006 y los documentos de docs/ no se verificaron.
- **D. Alineación con la constitución:** hallazgos AN-003-02, AN-003-03, AN-003-04 y AN-003-05. Los principios I, III y VI no tienen hallazgos. Principio III: denegación por defecto, límite de 0 CLP y escritura MCP deshabilitada (NFR-002) están alineados. La caducidad y el uso único de las aprobaciones aparecen en contracts/README.md L9, no en la spec, y no se consideran hallazgo.
- **E. Cobertura:** hallazgos AN-003-06, AN-003-07, AN-003-08 y AN-003-09. Ver tabla anterior.
- **F. Inconsistencia:** hallazgos AN-003-01, AN-003-12, AN-003-13, AN-003-14, AN-003-18 y AN-003-19.

## Métricas

- Requisitos (FR + SC): 25 (17 FR y 8 SC). Los NFR-001 a NFR-006 se usan como referencia y no se cuentan en el inventario.
- Tareas: 17 (T001 a T007, T101 a T105, T201 a T205).
- Cobertura con tarea explícita: 6 de 25 (24 %). Solo FR-015 a FR-020.
- Cobertura con criterio de aceptación: 25 de 25 (100 %). Los 17 FR tienen AT y los 8 SC tienen fila en acceptance.md, en estado «verificación pendiente».
- Ambigüedades: 3 (AN-003-15, AN-003-16, AN-003-17).
- Duplicaciones: 2 (AN-003-10, AN-003-11).
- Problemas críticos: 2 (AN-003-02, AN-003-03).

## Conteo final por severidad

| Severidad | Cantidad | IDs |
|-----------|----------|-----|
| CRITICAL | 2 | AN-003-02, AN-003-03 |
| HIGH | 5 | AN-003-01, AN-003-04, AN-003-05, AN-003-06, AN-003-10 |
| MEDIUM | 13 | AN-003-07, 08, 09, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21 |
| LOW | 3 | AN-003-11, AN-003-22, AN-003-23 |
| **Total** | **23** | |

## Próximos pasos sugeridos

- Antes de `/speckit-implement` no hay nada que ejecutar: la feature sigue BLOCKED por el gate T003–T007.
- Resolver primero los CRITICAL (AN-003-02 y AN-003-03), que son de constitución, y después los HIGH.
- Esta ejecución manual no cierra T007 ni T105. Esas tareas requieren la ejecución oficial de speckit-analyze cuando haya Spec Kit disponible.
- No se aplicó ninguna remediación. Si el propietario lo pide, se pueden preparar propuestas de cambio para los 5 primeros hallazgos, sin aplicarlas automáticamente.
