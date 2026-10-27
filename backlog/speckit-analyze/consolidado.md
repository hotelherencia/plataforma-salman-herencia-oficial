# Consolidado del análisis de consistencia — plataforma-salman

Fecha: 2026-10-27. Fuente: los cinco informes de esta carpeta (`000-core.md`, `001-cafeteria-mesas-pos.md`, `002-hotel-reservas-concierge.md`, `003-inmobiliaria-comercial.md`, `004-constructora-obra.md`).

**Naturaleza del análisis:** ejecución manual de la skill `speckit-analyze` (solo lectura), no salida del CLI de Spec Kit. T007 y T105 siguen abiertas: exigen la ejecución oficial con la herramienta instalada. Este consolidado no las cierra.

**Alcance de esta consolidación:** agrupa hallazgos por tema y conserva los IDs originales. No re-verifica cada cita línea a línea; se fía de los informes. No propone respuestas a las preguntas Q-*.

---

## 1. Conteo por feature

| Feature | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---:|---:|---:|---:|---:|
| 000-core | 0 | 8 | 16 | 7 | 31 |
| 001-cafeteria-mesas-pos | 1 | 6 | 22 | 3 | 32 |
| 002-hotel-reservas-concierge | 0 | 5 | 16 | 3 | 24 |
| 003-inmobiliaria-comercial | 2 | 5 | 13 | 3 | 23 |
| 004-constructora-obra | 1 | 2 | 13 | 7 | 23 |
| **Total** | **4** | **26** | **80** | **23** | **133** |

Nota de severidad: AN-000-24 (HIGH) es una condición de salida del bloqueo, no un defecto; el agente la dejó en HIGH y la mantengo. AN-000-07 y AN-002-03/004 quedan como HIGH porque dependen de que la constitución 1.1.0 (sin ratificar) se ratifique como norma; si se ratifica, suben a CRITICAL.

---

## 2. Los 4 CRITICAL

| ID | Feature | Resumen |
|---|---|---|
| AN-001-01 | 001 | La spec no define finalidad, base, responsable, destinatarios, residencia ni retención de los datos personales (comensales, teléfono, pagos, facturas). Constitución §IV. |
| AN-003-02 | 003 | H1 escenario 3 y FR-005 emiten boleta al pagar la reserva, sin la política tributaria revisada que exige la constitución §II. |
| AN-003-03 | 003 | Sin finalidad, base legal ni derechos para datos personales; no cita Ley 19.628 ni 21.719. Constitución §IV. |
| AN-004-01 | 004 | Voz, fotos y ubicación de trabajadores sin registrar finalidad, base, responsable, destinatarios, residencia ni retención. Constitución §IV. |

---

## 3. Temas que se repiten entre features

Cada tema agrupa los hallazgos de varias features. La prioridad refleja cuántas features lo tocan y la gravedad.

### T1. Privacidad y transición a la Ley 21.719 — prioridad máxima
- **Hallazgos:** AN-000-01 (HIGH), AN-001-01 (CRITICAL), AN-002-03 (HIGH), AN-003-03 (CRITICAL), AN-004-01 (CRITICAL).
- **Hecho común:** la constitución §IV exige registrar los campos de tratamiento y planificar la transición al 01-12-2026 (35 días desde el análisis). Ninguna spec tiene FR ni AT que lo cubra.
- **Decisión que lo desbloquea:** Q-CORE-03 (responsables, retención, base legal), con el significado de `aclaraciones.md` (decisión del 2026-10-27; ver T9).

### T2. Fiscalidad: redondeo CLP/UF, política tributaria y estados documentales
- **Hallazgos:** AN-000-06 (HIGH, redondeo UF), AN-000-07 (HIGH, estados separados), AN-001-08 (MEDIUM, estados de FR-005), AN-002-04 (HIGH, redondeo IVA), AN-003-02 (CRITICAL, boleta al pagar), AN-003-05 (HIGH, moneda y redondeo), AN-004-10 (MEDIUM, moneda y UF).
- **Hecho común:** la constitución §II exige CLP en unidades enteras, redondeo ratificado y separar aprobación, emisión, aceptación y entrega documental. Ninguna feature lo define; la dependencia de Q-CORE-02 no aparece en varios requisitos donde hace falta.
- **Decisión que lo desbloquea:** Q-CORE-02 (política por contribuyente), y para moneda y redondeo, una regla ratificada.

### T3. Aprobaciones humanas: caducidad, uso único y vinculación
- **Hallazgos:** AN-000-08 (MEDIUM), AN-001-03 (HIGH, aprobación por WhatsApp), AN-002-06 (MEDIUM), AN-004-02 (HIGH).
- **Hecho común:** la constitución §III exige aprobaciones con caducidad, uso único y vinculación a operación y parámetros. Las specs solo cubren parte de eso.
- **Acción:** un requisito transversal en el core (000-core FR-007) que las verticales referencien, en lugar de cuatro redacciones.

### T4. Umbrales, latencias y métricas sin denominador ni línea base
- **Hallazgos:** AN-000-05 (HIGH, batería de accesos), AN-000-11 (MEDIUM, NFR-005), AN-001-05 (HIGH, 5 s al 100 % frente a 90 %), AN-001-06 (HIGH, «insumos críticos»), AN-001-07 (HIGH, «fuera de patrón»), AN-002-02 (HIGH, 5 min al 100 % frente a 95 %), AN-002-05 (HIGH, «cero sobreventas»), AN-002-08 (MEDIUM, latencia del agente), AN-002-14 (MEDIUM, líneas base), AN-003-04 (HIGH, línea base y ventana), AN-004-11 (MEDIUM, «disponible»), AN-004-12 (MEDIUM, NFR-004 y 005).
- **Hecho común:** la constitución §V exige denominador, muestra, línea base y tolerancia antes de declarar cumplimiento. Ningún SC lo define.
- **Acción:** una plantilla única de métrica (unidad, numerador, denominador, ventana, línea base, tolerancia) aplicada a todos los SC.

### T5. Cobertura y trazabilidad de tareas
- **Hallazgos:** AN-000-10, AN-000-12, AN-000-21 (ninguna tarea cita IDs), AN-000-22, AN-001-02 (FR-015/016 sin implementación, ya conocido), AN-001-21 y AN-001-24 (ninguna tarea cita FR por ID), AN-001-22, AN-001-23, AN-001-29, AN-002-09 (la cabecera de acceptance.md promete facetas que no se cumplen), AN-002-10, AN-002-11, AN-002-12, AN-003-06 (FR-001..009 sin tarea explícita), AN-003-07, AN-004-15.
- **Hecho común:** las tareas no citan IDs de requisito. La cobertura solo se puede inferir, y los SC construibles no tienen tarea de medición.
- **Acción:** citar IDs de FR, SC, NFR y AT en cada tarea al redactar el backlog por historia (T007). Añadir tareas de instrumentación de medición (T4 y T5 se resuelven juntas).

### T6. Duplicación de requisitos y escenarios
- **Hallazgos:** AN-000-18 (FR-012 y RF-CORE-01), AN-000-25, AN-000-26, AN-001-12, AN-002-16 (RF-HOT-01..03 frente a FR-018..020), AN-002-21, AN-003-10 (FR-015/017, 016/019, 006/018), AN-003-11, AN-004-05 (FR-020 y FR-022 casi iguales), AN-004-06, AN-004-07, AN-004-08.
- **Hecho común:** el mismo requisito o escenario aparece con dos IDs o con texto copiado en dos o tres lugares. Un cambio en una copia no se propaga.
- **Acción:** una fuente canónica por requisito y escenario; el resto referencia por ID. Tabla de equivalencia RF-HOT/RF-INM/RF-OBR frente a FR.

### T7. Terminología y glosario
- **Hallazgos:** AN-000-04 (HIGH, «acción crítica» sin definir), AN-000-16, AN-000-17, AN-000-19, AN-001-19, AN-001-20 (empresa frente a tenant), AN-002-17, AN-003-13, AN-003-14, AN-004-09, AN-004-14, AN-001-32, AN-003-15 (urgencia), AN-003-22.
- **Hecho común:** los mismos conceptos se llaman de varias formas; términos clave no tienen criterio.
- **Acción:** un glosario compartido por el core, citado desde las cinco specs. «Acción crítica» es el más urgente (AN-000-04), porque SC-003 y FR-005/007 dependen de él.

### T8. Contradicciones conocidas (sin resolver, a la espera de tu confirmación)
- **SC-008 del hotel frente a RF-HOT-04** (AN-002-01): el 8 % de upsell del proveedor frente a la regla de no usar métricas del proveedor. Recomendación ya registrada: meta propia con línea base.
- **Escrituración en inmobiliaria** (AN-003-01): FR-003 incluye «escriturada», el Problema la deja fuera de V1. Recomendación ya registrada: fuera de V1, «escriturada» a V2.
- **Plan frente a constitución** (AN-000-15, AN-002-19): el plan dice «sin modificaciones»; la constitución es la versión propuesta 1.1.0.

### T9. Definiciones de Q-* y dependencias externas
- **Q-CORE-03: resuelto el 2026-10-27.** Rige `aclaraciones.md`; la medición y priorización pasan a Q-COMP-05. Antes tenía dos definiciones en RSalman: `aclaraciones.md` (responsables, retención, RPO/RTO) y `decisiones-pendientes.md` («Q-COMP-05 / Q-CORE-03», medición y priorización). Hallazgos AN-000-14 y AN-001-25. Hay que resolverlo antes de cerrar NFR-004 y la decisión de core.
- **Preguntas sin Q asignado en hotel:** factura a empresas y housekeeping (AN-002-15).
- **Preguntas que no se pueden hacer sin prerrequisito:** escenarios de H1 de cafetería que dependen de Q-CAF-01 sin marcarlo (AN-001-27); pregunta de proveedores fuera de Q-CAF-03 (AN-001-26).
- **REA y Node:** T104, T105 y T204 dependen de REA y de Node ≥ 22.19 (AN-004-16); el runtime actual es Node 18.19.1 según `aclaraciones.md` L7. Q-REA-01 y Q-REA-03 exigen tu aprobación.
- **Referencias de los informes a Q-* «no verificadas»:** AN-003-21 y AN-001-25 las marcan como no verificables en la carpeta. Están definidas en RSalman (`docs/arquitectura/aclaraciones.md`, `docs/investigacion-competitiva/decisiones-pendientes.md`); el hallazgo de referencia está corregido solo en AN-001-25.

### T10. Duplicación de tareas de Spec Kit
- **Hallazgos:** AN-000-27, AN-001-13, AN-002-13, AN-004-17. Las parejas T007/T105, T104/T204 y T102/T202 se solapan.
- **Acción:** consolidar en una tarea por par con dependencias explícitas. T007 debe depender también de T102–T104 (AN-001-29, AN-004-17).

### T11. Plan: stack, versiones y ADR
- **Hallazgos:** AN-000-30, AN-001-30, AN-002-18, AN-003-18, AN-004-18 (plan frente a Redis: «no fijar versiones» frente a versiones concretas, y Redis contradictorio), AN-002-20 y AN-004-19 (ADR y rutas `../../docs/` que no resuelven dentro de ``), AN-000-23.
- **Nota:** AN-000-23 afirma que los ADR-001..006 están en `RSalman/docs/arquitectura/decisiones/`. No lo comprobé en esta consolidación.

### T12. Formato y namespace
- **Hallazgos:** AN-000-29, AN-001-31, AN-002-22, AN-003-20, AN-003-23, AN-004-21, AN-004-22. AGENTS.md pide namespace de feature para FR, SC y AT; ninguna spec lo aplica. Diferencias con la plantilla oficial («Historia N» frente a «User Story N», sin Edge Cases en 004).
- **Acción:** documentar la convención del namespace por carpeta y no renumerar IDs heredados. El formato no bloquea.

---

## 4. Orden sugerido de decisión

1. **Privacidad (T1):** ratificar la finalidad y la base de tratamiento por categoría de dato, y decidir la lectura de Q-CORE-03. Desbloquea AN-000-01, AN-001-01, AN-002-03, AN-003-03 y AN-004-01.
2. **Q-CORE-03 (T9):** resuelto; rige `aclaraciones.md`. Falta solo que Q-COMP-05 se registre en RSalman.
3. **Q-CORE-02 y política fiscal (T2):** emisión tributaria por contribuyente, redondeo, moneda y estados documentales. Desbloquea el CRITICAL AN-003-02.
4. **Aprobaciones (T3):** caducidad, uso único y vinculación, como requisito único del core.
5. **Métricas (T4):** plantilla de métrica con denominador y línea base para cada SC.
6. **Contradicciones (T8):** confirmar las dos recomendaciones ya registradas.
7. **Trazabilidad y consolidación (T5, T6, T10):** citar IDs en tareas, eliminar duplicados, unir T007 con T105 y añadir la dependencia de T102–T104.

---

## 5. Preguntas abiertas para el propietario

- ¿Se confirma la recomendación sobre SC-008 del hotel? (T8)
- ¿Se confirma la recomendación sobre la escrituración en inmobiliaria? (T8)
- ¿Se ratifica la constitución 1.1.0, y como MINOR o MAJOR? Afecta a la severidad de AN-000-07, AN-002-03 y AN-004-02. (T1 y T3)
- ¿Se autoriza el cambio de Node a v22+ para REA? (T9, Q-REA-01)
- ¿Qué criterio de urgencia se usa en postventa de inmobiliaria? (AN-003-15)

Las respuestas las da el propietario; el análisis no las propone.

---

## 6. Qué no hace este consolidado

- No cierra T007 ni T105. Esas tareas exigen la ejecución oficial con `specify` y las skills instaladas, con su salida adjunta.
- No modifica las specs, el plan, las tareas ni los informes originales.
- No resuelve ninguna pregunta Q-*.
