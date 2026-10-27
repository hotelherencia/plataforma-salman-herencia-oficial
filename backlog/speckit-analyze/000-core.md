# Análisis de consistencia Spec Kit — 000-core

**Fecha:** 2026-10-27
**Feature:** `000-core` (Core transversal) · **Estado:** BLOCKED para implementación

> Nota de procedencia: este análisis se ejecutó **manualmente en esta sesión**, siguiendo los pasos 2–5 de la skill oficial `speckit-analyze` (`C:/Users/herre/AppData/Local/Temp/speckit_probe/probe/.claude/skills/speckit-analyze/SKILL.md`). **No es salida del CLI de Spec Kit.**
>
> - Paso 1 omitido por indicación: `check-prerequisites.ps1` no existe en el proyecto; se usaron las rutas directas a `spec.md`, `plan.md`, `tasks.md` y la constitución.
> - Hooks: `.specify/extensions.yml` no existe; no hay hooks `before_analyze` / `after_analyze` que ejecutar.
> - Solo lectura: no se modificó ningún archivo del proyecto ni de RSalman. El único archivo escrito es este informe.
> - Artefactos leídos: `specs/000-core/spec.md`, `plan.md`, `tasks.md`, `acceptance.md`; `.specify/memory/constitution.md`. Verificados por búsqueda: `data-model.md`, `contracts/README.md`, `checklists/requirements.md`. De RSalman solo las definiciones de Q-* (`docs/arquitectura/aclaraciones.md`, `docs/investigacion-competitiva/decisiones-pendientes.md`).
> - Categorías: las cinco pedidas más **inconsistencia** (pasada F de la skill), que se usa cuando dos artefactos o fuentes no coinciden y ninguna de las otras cinco describe el caso.
> - Formato de historias («Historia N» en lugar de «User Story N») marcado como LOW de formato, según lo acordado; no se trata como defecto.
> - Las marcas «propuesta, no ejecutada» se tratan como intencionales.

---

## 1. Hallazgos

Ninguna pasada (A–F) quedó vacía. Total: **31 hallazgos** (límite de la skill: 50). Severidad: **0 CRITICAL, 8 HIGH, 16 MEDIUM, 7 LOW**.

| ID | Categoría | Severidad | Ubicación(es) | Resumen | Recomendación |
|----|-----------|-----------|---------------|---------|---------------|
| AN-000-01 | Alineación constitución | HIGH | `constitution.md` §IV (L19); `spec.md` (sin mención); `tasks.md` (sin tarea) | La constitución exige planificar el régimen vigente Ley 19.628 y la transición a Ley 21.719 al 01-12-2026. La spec no menciona ninguna de las dos leyes, ni finalidad, base de tratamiento, encargado, residencia ni retención como requisito. Q-CORE-03 lo difiere sin tarea propia. La fecha de transición está a ~5 semanas de la fecha de este análisis. | Añadir requisito de cumplimiento de privacidad (registro de tratamiento) o una tarea previa a T003 con validación jurídica del régimen aplicable. |
| AN-000-02 | Inconsistencia | HIGH | `decisiones-pendientes.md` (Q-CORE-04, RSalman); `spec.md` L227 y L251; `plan.md` L36 (Fase 0); `tasks.md` T003, T202 | Q-CORE-04 (efectos laterales de herramientas y cargos/mensajes implícitos) bloquea FR-012 y RF-CORE-01, pero no aparece en la Fase 0 del plan, en T003 ni en las dependencias de RF-CORE-01 («Q-CORE-01/03»). FR-012 queda sin su bloqueo explícito en el plan. | Incluir Q-CORE-04 en Fase 0 y en T003, o crear una tarea propia previa a T202. Añadirlo a las dependencias de RF-CORE-01. |
| AN-000-03 | Inconsistencia | HIGH | `plan.md` L26 (IntentoPago en core) vs L48 («Mantener estos registros en el dominio»: Intento, EventoExterno, CasoConciliación) | El plan coloca el intento de pago en el diseño del core, pero después mueve Intento, EventoExterno y CasoConciliación al dominio. Sin embargo, FR-003, FR-008 y FR-011 (requisitos del core) exigen registrar intentos y conciliar eventos externos. Dueño de la conciliación: indefinido. | Decidir y registrar en ADR-005 qué parte de Intento/EventoExterno/Conciliación es core. Ajustar FR-003/008/011 o el plan para que coincidan. |
| AN-000-04 | Ambigüedad | HIGH | `spec.md` SC-003 (L52), FR-005 (L40), FR-007 (L42), NFR-002 (L61) | «Acción crítica» se usa como término central pero no está definida ni enumerada. SC-003 («Toda acción crítica tiene actor, tenant, evidencia y resultado») no es verificable: no se sabe qué acciones entran. | Definir glosario o lista cerrada (p. ej., pago, emisión documental, compromiso contractual, envío externo, cambio de permisos) y referenciarla desde `acceptance.md`. |
| AN-000-05 | Subespecificación | HIGH | `spec.md` SC-001 (L50); `acceptance.md` ADV-001..003 (L16–18) | SC-001 exige «cero accesos entre tenants en la batería adversarial aprobada», pero no define quién aprueba la batería, su tamaño ni su cobertura. Solo hay tres escenarios ADV. | Definir denominador, casos mínimos, aprobador y muestra de la batería. Registrarlos en `acceptance.md` junto a SC-001. |
| AN-000-06 | Alineación constitución | HIGH | `constitution.md` §II (L11); `spec.md` FR-003 (L38), FR-004 (L39); `plan.md` (sin mención); `tasks.md` (sin tarea) | La constitución exige que CLP se cobre en unidades enteras y que las conversiones desde UF tengan precisión y redondeo ratificados. La spec habla de «monto» sin unidad ni redondeo, y ni el plan ni las tareas lo recogen. | Añadir requisito de unidades CLP enteras y reglas de redondeo UF. Incluir el punto como gate antes de T005. |
| AN-000-07 | Alineación constitución | HIGH | `constitution.md` §II (L11) vs `plan.md` L28 (Documento: «pendiente → emitido/observado → regularizado»); `spec.md` FR-004 (L39) | La constitución exige separar aprobación bancaria, emisión, aceptación y entrega documental. El modelo de estados del plan no separa esas fases, y FR-004 tampoco. No hay AT que lo pruebe. Nota: la constitución es la versión propuesta 1.1.0, aún sin ratificar; si la separación se ratifica como MUST, este caso pasa a CRITICAL. | Enmendar el modelo de estados documental y añadir un AT que verifique la separación de fases. Confirmar con el responsable si la regla es MUST. |
| AN-000-08 | Alineación constitución | MEDIUM | `constitution.md` §III (L15); `spec.md` H3 (L169, «vigencia») y FR-007 (L42); `acceptance.md` AT-007 (L13) | La constitución exige aprobaciones con caducidad y uso único. La spec solo menciona vigencia. AT-007 prueba el cambio de monto, pero no el reuso de una aprobación ya consumida. (`contracts/README.md` sí menciona uso único, pero no es requisito ni prueba.) | Añadir uso único a FR-007 y un AT que rechace reutilizar una aprobación consumida o expirada. |
| AN-000-09 | Alineación constitución | MEDIUM | `constitution.md` §VI (L27); `spec.md` FR-005 (L40); `acceptance.md` AT-005 (L11) | La constitución exige auditoría con correlación, parámetros minimizados, política, aprobación, evidencia y resultado. FR-005 omite correlación y minimización de parámetros. (`contracts/README.md` sí menciona correlation-id.) | Añadir correlación y minimización de parámetros a FR-005 y a AT-005. |
| AN-000-10 | Cobertura | MEDIUM | `constitution.md` §IV y §VI (L19, L27); `plan.md` L30 («pérdida de evidencia»); `spec.md` NFR-004 (L63); `tasks.md` | RPO/RTO, restauración y fallos parciales no tienen tarea propia ni AT. NFR-004 depende solo de T003. La amenaza «pérdida de evidencia» del plan no tiene control verificable. | Añadir tarea posterior a T003 para definir RPO/RTO y probar restauración y fallos parciales. Añadir un AT para NFR-004. |
| AN-000-11 | Cobertura | MEDIUM | `spec.md` NFR-005 (L64); `acceptance.md` (sin AT); `tasks.md` T205 | NFR-005 (medir latencia de recepción a resultado confirmado, incluidos errores y desconexión) no tiene escenario de aceptación. T205 menciona latencias, pero sin criterio de denominador ni muestra. | Añadir AT o caso de medición para NFR-005 con denominador, muestra y tratamiento de errores. |
| AN-000-12 | Cobertura | MEDIUM | `plan.md` L30 («privilegios de soporte»); `aclaraciones.md` Q-CORE-01 («soporte»); `acceptance.md` ADV-001 (L16) | La amenaza «privilegios de soporte» no tiene FR, AT ni tarea. ADV-001 cubre solo usuario, worker y agente, no soporte. | Añadir requisito de acceso de soporte (mínimo privilegio, aprobación y auditoría) y un ADV correspondiente. |
| AN-000-13 | Inconsistencia | MEDIUM | `spec.md` L10 (actor «responsable de privacidad»); `aclaraciones.md` Q-CORE-01 (cliente + seguridad), Q-CORE-03 (cliente + privacidad + operación); `tasks.md` T003 (L7) | T003 asigna como responsables «cliente y responsables de operación, con revisor tributario/legal». No incluye privacidad ni seguridad, que sí figuran como responsables de Q-CORE-01 y Q-CORE-03 y como actor en la spec. | Alinear el campo «Responsable» de T003 con las definiciones de `aclaraciones.md`. |
| AN-000-14 | Inconsistencia | MEDIUM | `aclaraciones.md` L9 (Q-CORE-03 = responsables de datos, retención, recuperación, presupuesto, autonomía) vs `decisiones-pendientes.md` L14 (Q-COMP-05 / Q-CORE-03 = medición y priorización) | Q-CORE-03 tiene dos definiciones en RSalman. **Resuelto 2026-10-27:** rige el significado de `aclaraciones.md`; la medición y priorización pasan a Q-COMP-05. La spec adopta la de `aclaraciones.md`, pero el registro competitivo la usa para medición y priorización. | Separar en dos IDs o corregir el registro competitivo antes de T003, para que la pregunta no quede ambigua. |
| AN-000-15 | Inconsistencia | MEDIUM | `plan.md` L50 («no se modifica constitución») y L58 («Constitución revisada sin modificaciones») vs `constitution.md` L3 (versión propuesta 1.1.0 con registro de ampliaciones) | El plan dice que la constitución no cambia, pero el archivo es una propuesta de MINOR 1.1.0 con ampliaciones. | Declarar en el plan la versión propuesta 1.1.0 y su estado de ratificación pendiente. |
| AN-000-16 | Inconsistencia | MEDIUM | `spec.md` RF-CORE-01 L225 («IntencionEnvio», estados propuesto/autorizado/intentado/confirmado/desconocido) vs `plan.md` L54 («IntencionEfecto», solicitud/permiso/ejecución/resultado) y L28 (pago: iniciado → pendiente → autorizado/rechazado/desconocido) | Dos nombres de entidad y tres conjuntos de estados para conceptos relacionados (intención de efecto, intento de pago y resultado externo). | Crear un glosario de entidades y estados canónicos, citado desde spec y plan. |
| AN-000-17 | Ambigüedad | MEDIUM | `spec.md` L8 («CRM ... no son core») vs AC-US-CORE-001-02 (L108, «captura» de leads), RF-CORE-01 (L204, «guardar un contacto»); `constitution.md` §I (CRM pertenece al dominio) | Los escenarios de core prueban captura de leads y contactos, que es comportamiento CRM. No queda claro si el core es dueño de esa captura o solo de la capacidad del conector. | Reformular como «capacidad de conector habilitada/denegada» sin nombrar CRM, o aclarar el límite en la spec. |
| AN-000-18 | Duplicación | MEDIUM | `spec.md` FR-012 (L246) y RF-CORE-01 (L200); AC-US-CORE-003-03..05 (L235–237); `acceptance.md` L60–62 y AT-012 (L66) | FR-012 y RF-CORE-01 son el mismo requisito con dos IDs. Los AC-US-CORE-003-03..05 aparecen tres veces con el mismo texto. Un cambio en una copia no se propaga a las otras. | Dejar una sola fuente canónica (FR-012) y referenciarla desde RF-CORE-01 y `acceptance.md`. |
| AN-000-19 | Ambigüedad | MEDIUM | `spec.md` NFR-006 («evidencia suficiente», L194); FR-008 («alertas», L43); H3 («vigencia», L169) | Términos sin criterio ni destinatario: «evidencia suficiente», «alertas» (¿a quién y con qué umbral?) y «vigencia» (¿cuánto dura?). | Definir umbral o criterio para cada término en la spec o en el modelo de datos. |
| AN-000-20 | Subespecificación | MEDIUM | `acceptance.md` AT-001..AT-009 (L7–15) | Todas las precondiciones son genéricas («Dadas precondiciones del requisito y actor/tenant autorizados»). El Given no concreta datos, membresías ni roles, así que el caso no es ejecutable sin releer el requisito. | Escribir cada AT con datos concretos (empresas, roles, montos, estados). |
| AN-000-21 | Cobertura (trazabilidad) | MEDIUM | `tasks.md` (todas); T006 (L10) | Ninguna tarea cita FR, NFR, SC o AT por ID. T006 menciona solo ADV-001..003 y deja fuera AT-010..AT-012 sin nombrarlos. T103 cubre AC-US-CORE, pero no los AT. La trazabilidad depende de inferencia. | Citar IDs de requisito y AT en cada tarea, incluidos AT-010..AT-012. |
| AN-000-22 | Cobertura | MEDIUM | `spec.md` FR-002 («procesos asíncronos», L37) y NFR-001 («trabajo en cola», L60); `plan.md` L58 (colas pendientes) | La autorización de procesos asíncronos y colas no tiene tarea ni AT específico. ADV-001 menciona worker, pero no cola ni reintento asíncrono. El plan deja las colas pendientes, lo que es coherente, pero nada lo registra como gate. | Añadir un AT de autorización en procesos asíncronos y un gate explícito en T004 para la decisión de colas. |
| AN-000-23 | Trazabilidad | MEDIUM | `spec.md` L70, L99 y otras (`../../docs/...`); `plan.md` L32 y L58 (ADR-001..006 sin ruta) | Los enlaces relativos `../../docs/` desde `specs/000-core` apuntan a `docs/`, que no existe; los documentos están en RSalman. Los ADR-001..006 existen en `RSalman/docs/arquitectura/decisiones/` y no en el proyecto, y el plan los cita sin ruta. | Corregir los enlaces o documentar la ruta base de RSalman. Citar los ADR con ruta relativa completa. |
| AN-000-24 | Cobertura | HIGH | `tasks.md` (T001–T205); `spec.md` FR-001..012, SC-001..003 | Ningún FR ni SC tiene tarea de implementación ni de prueba ejecutable. Es intencional: T008 está excluida y el backlog se genera en T007 tras T003–T006. Se marca HIGH en lugar de CRITICAL porque el bloqueo está declarado y no es un defecto de consistencia; es una condición de salida. | Mantener el bloqueo. Generar tareas de implementación solo cuando T003–T007 estén cerradas, como indica `tasks.md`. |
| AN-000-25 | Duplicación | LOW | `spec.md` FR-003 (L38), NFR-003 (L62), SC-002 (L51); `acceptance.md` AT-003, ADV-002, AC-US-CORE-002-01 | La idempotencia de pagos se expresa en seis lugares con formulaciones casi iguales. | Consolidar en FR-003 y referenciar desde NFR-003, SC-002 y los AT. |
| AN-000-26 | Duplicación | LOW | `spec.md` L56 y L66 | El bloque «Q-CORE-01: ...; Q-CORE-02: ...; Q-CORE-03: ...» aparece dos veces con el mismo texto. | Eliminar una de las dos copias. |
| AN-000-27 | Duplicación | LOW | `tasks.md`: T007 (L11) vs T105 (L21); T104 (L20) vs T204 (L28); T102 (L18) vs T202 (L26) | Pares de tareas solapadas: dos análisis de consistencia, dos evaluaciones de demo REA y dos validaciones de reglas con negocio/legal. | Consolidar cada par en una tarea con dependencias explícitas. |
| AN-000-28 | Inconsistencia | LOW | `tasks.md` L13 («No se incluye implementar T008») | Se menciona T008, que no existe en la lista. | Reformular como «fuera de alcance» sin numerar. |
| AN-000-29 | Formato | LOW | `spec.md`: secciones «Historia N» (L14, L26), alias H1–H3 y US-CORE-001..003 | Formato no estándar frente a la plantilla oficial («User Story N») y doble numeración de historias. LOW de formato, no defecto, salvo que cree ambigüedad. Aquí no la crea, porque el alias está declarado en la spec (L81, L117, L153). | Ninguna acción obligatoria. Si la plantilla oficial se adopta, mantener el alias como tabla de equivalencia. |
| AN-000-30 | Inconsistencia | LOW | `plan.md` L9 («No fijar versiones») vs L9 (Python 3.12, PostgreSQL 16); L38 («contracts ... presentes») | El plan menciona versiones aunque indica que no las fija; y lista `contracts/` como artefacto presente, cuando solo contiene `README.md` (lógico, sin OpenAPI). | Marcar las versiones como «propuesta de CAF/HOT/INM, no fijada». Precisar en L38 que contracts contiene un README lógico. |
| AN-000-31 | Alineación constitución | LOW | `constitution.md` §IV (rotación de secretos) y §VI (logs estructurados y métricas); `spec.md` FR-006 (L41) | La rotación de secretos y la observabilidad (logs estructurados y métricas) no aparecen en la spec. Son principios declarados sin requisito. | Añadir un requisito de observabilidad y de rotación de secretos, o registrar la exclusión. |

---

## 2. Preguntas Q-*

- **Faltantes:** ninguna. Q-CORE-01, Q-CORE-02, Q-CORE-03 y Q-CORE-04 están definidas en RSalman (`aclaraciones.md` y `decisiones-pendientes.md`). Q-REA-01/02/03 (en `decisiones-pendientes.md`) y Q-TOOL-01 (en `aclaraciones.md`), referenciadas por T104, T204 y T105, también están definidas.
- **Contradicciones:**
  - Q-CORE-03 tenía dos definiciones (AN-000-14), resuelto: rige `aclaraciones.md`; medición a Q-COMP-05.
  - Q-CORE-04 bloquea FR-012 y RF-CORE-01, pero no figura en Fase 0 ni en T003 (AN-000-02).

No se propone ninguna respuesta a las preguntas Q-*.

---

## 3. Cobertura de FR, NFR y SC → tareas

Ningún requisito tiene una tarea que lo cite por ID (AN-000-21). La cobertura es indirecta, por nombre de artefacto o por derivación.

| Requisito | Tareas que lo cubren (indirecto) | Escenario de aceptación | Estado |
|-----------|----------------------------------|-------------------------|--------|
| FR-001 | T004, T006 | AT-001 | Cubierto (indirecto) |
| FR-002 | T004, T006 | AT-002, ADV-001 | Parcial: procesos asíncronos sin tarea (AN-000-22) |
| FR-003 | T005, T006 | AT-003, ADV-002 | Cubierto (indirecto) |
| FR-004 | T003, T006 | AT-004 | Depende de Q-CORE-02; sin tarea de política fiscal propia |
| FR-005 | T005, T006 | AT-005 | Parcial: sin correlación ni minimización (AN-000-09) |
| FR-006 | T003, T006 | AT-006 | Parcial: secretos y rotación sin tarea (AN-000-31) |
| FR-007 | T004, T006 | AT-007 | Parcial: sin uso único (AN-000-08) |
| FR-008 | T006, T203 | AT-008 | Cubierto (indirecto) |
| FR-009 | T005, T006 | AT-009 | Cubierto (indirecto) |
| FR-010 | T102, T103, T104 | AT-010, AC-US-CORE-001-* | Solo validación y demo; sin tarea de implementación |
| FR-011 | T102, T103, T203 | AT-011, AC-US-CORE-002-* | Solo validación; sin tarea de implementación |
| FR-012 (= RF-CORE-01) | T202, T203, T204 | AT-012, AC-US-CORE-003-03..05 | Dependencia de Q-CORE-04 no declarada (AN-000-02) |
| SC-001 | T006 (ADV-001..003) | ADV-001..003 | Parcial: batería no definida (AN-000-05) |
| SC-002 | T006 (AT-003, ADV-002), T203 | AT-003, ADV-002 | Cubierto (indirecto) |
| SC-003 | T006 (AT-005) | AT-005 | Parcial: «acción crítica» no definida (AN-000-04); sin tarea de medición |
| NFR-001 | T004, T006 | ADV-001 | Cubierto (indirecto) |
| NFR-002 | T004, T006 | ADV-003 | Cubierto (indirecto) |
| NFR-003 | T006, T203 | ADV-002 | Cubierto (indirecto) |
| NFR-004 | T003 | Ninguno | **Sin escenario ni tarea** de RPO/RTO ni restauración (AN-000-10) |
| NFR-005 | T205 | Ninguno | **Sin escenario de aceptación** (AN-000-11) |
| NFR-006 | T102, T103 | Remite a AC-US-CORE-* | Cubierto por remisión |

**Resumen de cobertura:**

- Cobertura indirecta por tarea: 21 de 21 (100 %). Requisitos contados: 12 FR, 6 NFR, 3 SC.
- Cobertura explícita (ID citado en la tarea): 0 de 21 (0 %).
- Cobertura por escenario de aceptación (AT, ADV o AC): 18 de 21 (86 %). Sin escenario: NFR-004 y NFR-005.
- Escenarios de aceptación sin tarea que los cite por ID: AT-010, AT-011 y AT-012 (AN-000-21).

---

## 4. Tareas sin requisito mapeado

| Tarea | Motivo |
|-------|--------|
| T001 | Inventario de fuente y alcance; tarea de proceso. Evidencia documental, sin requisito. |
| T002 | Derivación de modelo y catálogo de aceptación; tarea de proceso que cubre todo `acceptance.md`. |
| T007 | Reejecución de controles y análisis; proceso. Solapada con T105 (AN-000-27). |
| T101 | Comparación de historias heredadas; proceso (ya completada). |
| T105 | Análisis de consistencia oficial y backlog; proceso. Solapada con T007 (AN-000-27). |
| T008 (mencionada en L13) | No existe como tarea (AN-000-28). |

Las tareas T003–T006, T102–T104, T201–T205 sí tienen requisito asociado, aunque sea por inferencia.

---

## 5. Constitución

- **CRITICAL:** ninguno. No se detecta un elemento del plan o de la spec que contradiga de forma explícita un principio MUST. Los casos más cercanos son AN-000-07 (separación documental), que tiene el atenuante de que la constitución 1.1.0 aún no está ratificada, y AN-000-01 (privacidad), que es una omisión.
- **HIGH:** AN-000-01 (privacidad y transición Ley 21.719), AN-000-06 (CLP enteros y redondeo UF), AN-000-07 (separación documental).
- **MEDIUM:** AN-000-08 (uso único de aprobaciones), AN-000-09 (campos de auditoría), AN-000-10 (restauración y RPO/RTO), AN-000-15 (versión de la constitución).
- **LOW:** AN-000-31 (observabilidad y rotación de secretos).

---

## 6. Métricas y conteo final

| Métrica | Valor |
|---------|-------|
| Requisitos totales (FR, NFR, SC) | 21 (12 FR, 6 NFR, 3 SC). RF-CORE-01 cuenta como alias de FR-012. |
| Historias | 6 (H1–H3 y US-CORE-001..003) |
| Tareas totales | 17 (T001–T007, T101–T105, T201–T205) |
| Cobertura indirecta de requisitos por tarea | 100 % (21/21) |
| Cobertura explícita por ID en tareas | 0 % (0/21) |
| Cobertura con escenario de aceptación | 86 % (18/21) |
| Ambigüedades (categoría ambigüedad) | 4 (AN-000-04, -17, -19, -20) |
| Duplicaciones (categoría duplicación) | 4 (AN-000-18, -25, -26, -27) |
| Problemas críticos (CRITICAL) | 0 |

**Conteo por severidad:**

| Severidad | Cantidad | IDs |
|-----------|----------|-----|
| CRITICAL | 0 | — |
| HIGH | 8 | AN-000-01, -02, -03, -04, -05, -06, -07, -24 |
| MEDIUM | 16 | AN-000-08 a -23 |
| LOW | 7 | AN-000-25 a -31 |
| **Total** | **31** | |

---

## 7. Próximas acciones

- **No ejecutar `/speckit-implement`.** La feature sigue BLOCKED. Hay 8 HIGH abiertos; ninguno es CRITICAL, pero los HIGH de privacidad (AN-000-01) y de CLP (AN-000-06) afectan a gates de implementación.
- **Antes de T003:** la definición duplicada de Q-CORE-03 quedó resuelta (AN-000-14); pendiente: incluir Q-CORE-04 en T003 y en la Fase 0 (AN-000-02), y alinear responsables (AN-000-13).
- **Antes de T005:** resolver la dependencia Intento/EventoExterno/Conciliación entre core y dominio (AN-000-03) y el modelo de estados documental (AN-000-07).
- **Antes de T006:** definir «acción crítica» (AN-000-04), la batería adversarial de SC-001 (AN-000-05) y escribir los AT con datos concretos (AN-000-20).
- **Sin urgencia:** LOW y MEDIUM de formato y trazabilidad (AN-000-21, -23, -25 a -31).
- **Remediación:** no se aplicó ninguna edición. Si lo deseas, puedo proponer ediciones concretas para los 8 HIGH, sin aplicarlas.
