# Decisiones pendientes del propietario

- **Fecha de corte:** 2026-11-20
- **Alcance:** los 7 issues abiertos de decisión humana (`#30`, `#100`, `#115`, `#119`, `#128`, `#143`, `#147`).
- **Regla de gobernanza (`AGENTS.md`):** ninguna de estas decisiones se implementa ni se cierra por cuenta del equipo. Toda recomendación aquí marcada lleva la etiqueta **REQUISITO PROPUESTO**; solo la confirmación explícita del propietario con fecha y evidencia convierte una opción en **HECHO DOCUMENTADO** y habilita el cierre de la tarjeta en el tablero.

---

## Resumen ejecutivo

| Issue | Vertical / Módulo | Preguntas bloqueantes | Estado actual | ¿Bloquea V1 Hotel? |
|---|---|---|---|---|
| [#30](https://github.com/hotelherencia/plataforma-salman-herencia-oficial/issues/30) | `000-core/H3/T-DEC` | `Q-CORE-03` (resuelta), **`Q-CORE-04`** (pendiente) | **DECISIÓN PENDIENTE** (solo `Q-CORE-04`) | Parcial (solo si se activa autonomía > N0 o herramientas con efectos laterales) |
| [#100](https://github.com/hotelherencia/plataforma-salman-herencia-oficial/issues/100) | `003-inmobiliaria-comercial/T003` | `Q-INM-01`, `Q-INM-02`, `Q-INM-03`, `Q-INM-04` | **DECISIÓN PENDIENTE** (gate de vertical) | No (inmobiliaria fuera de V1) |
| [#115](https://github.com/hotelherencia/plataforma-salman-herencia-oficial/issues/115) | `003-inmobiliaria-comercial/H1/T-DEC` | `Q-INM-01`, `Q-INM-02`, `Q-INM-03` | **DECISIÓN PENDIENTE** (hereda de `#100`) | No |
| [#119](https://github.com/hotelherencia/plataforma-salman-herencia-oficial/issues/119) | `003-inmobiliaria-comercial/H2/T-DEC` | `Q-INM-01`, `Q-INM-04` | **DECISIÓN PENDIENTE** (hereda de `#100`) | No |
| [#128](https://github.com/hotelherencia/plataforma-salman-herencia-oficial/issues/128) | `004-constructora-obra/T003` | `Q-OBR-01`, `Q-OBR-02`, `Q-OBR-03` | **DECISIÓN PENDIENTE** (gate de vertical) | No (constructora fuera de V1) |
| [#143](https://github.com/hotelherencia/plataforma-salman-herencia-oficial/issues/143) | `004-constructora-obra/H3/T-DEC` | `Q-OBR-01`, `Q-OBR-02`, `Q-OBR-03` | **DECISIÓN PENDIENTE** (hereda de `#128`) | No |
| [#147](https://github.com/hotelherencia/plataforma-salman-herencia-oficial/issues/147) | `004-constructora-obra/H4/T-DEC` | `Q-OBR-03`, `Q-OBR-04` (texto no migrado) | **DECISIÓN PENDIENTE** (hereda de `#128` + recuperar texto `Q-OBR-04`) | No |

> **HECHO DOCUMENTADO** (`docs/investigacion-competitiva/decisiones-pendientes.md`): las referencias a `Q-INM-05/06/07` y `Q-OBR-04` apuntan a un archivo del repositorio origen que no fue migrado. Si se retoman esas verticales, primero debe recuperarse o reescribirse el enunciado exacto con el propietario.

---

## 1. Issue #30 — `000-core/H3/T-DEC`: `Q-CORE-03` y `Q-CORE-04`

- **HECHO DOCUMENTADO:** `Q-CORE-03` ya fue resuelta el 2026-10-27 (`backlog/hotel/resolucion-dudas-2026-10-27.md`: retención 6 años, RPO 1 h, RTO 4 h, responsable = administrador de la empresa; validación jurídica Ley 21.719 pendiente antes de ampliar uso).
- **DECISIÓN PENDIENTE (`Q-CORE-04`):** efectos laterales por herramienta/parámetro; quién autoriza mensajes externos o cargos y cómo se deduplican (fuente: `backlog/hotel/respuestas-propuestas.md` §Q-CORE-04, ADR-006, F-023).

### Opciones
- **Opción A (conservadora — bloqueo por defecto):** toda herramienta del núcleo/agente con efecto lateral (enviar WhatsApp/correo al cliente, asentar cargo, emitir DTE, reembolsar) exige aprobación humana explícita (`nivel N0/N1`, tope autónomo `0 CLP`) y clave de idempotencia obligatoria (`Idempotency-Key` / `efecto_nucleo_id`) ligada al actor que autoriza.
- **Opción B (semiatónoma por umbral):** permitir que el agente envíe respuestas informativas sin aprobación humana (N1/N2) manteniendo `0 CLP` y aprobación humana obligatoria para cualquier cargo, reserva firme, cancelación o devolución.
- **Opción C (autónoma con tope monetario):** delegar reservas y cargos hasta un tope CLP mensual definido por el propietario.

### Recomendación (**REQUISITO PROPUESTO**)
- **Opción A** mientras no exista evaluación periódica de regresión en producción y contrato de mensajería activo; eventualmente transitar a **Opción B** solo para respuestas informativas ya verificadas por el verificador determinista (`SC-003` 50/50 aprobado en `cac3750`).

### Consecuencias
- **Con Opción A:** riesgo mínimo de cobros o mensajes indebidos; recepción aprueba cada borrador antes de enviarlo; cumple estrictamente F-023 y ADR-006.
- **Con Opción B:** reduce carga operativa en recepción para preguntas frecuentes, pero exige monitoreo de alertas y pruebas negativas de herramientas antes de encender canales externos.
- **Con Opción C:** introduce riesgo financiero y legal directo ante errores de interpretación; requiere seguros/topes contractuales no vigentes.

---

## 2. Issues #100, #115 y #119 — Vertical `003-inmobiliaria-comercial`

> **HECHO DOCUMENTADO:** `#100` (`T003`) es el gate de la vertical; `#115` (`H1`: lead a promesa) depende de `Q-INM-01/02/03` y `#119` (`H2`: cobranza y postventa) depende de `Q-INM-01/04`. Al responder `#100`, se destraban `#115` y `#119` en bloque. La vertical está marcada **BLOCKED** y fuera del alcance de V1 (hotel).

### `Q-INM-01` — Proyectos, CRM actual y captura autorizada de leads (`#100`, `#115`, `#119`)
- **DECISIÓN PENDIENTE:** cuántos proyectos y unidades activas existen, qué CRM/planillas se usan hoy (y si se migran) y qué portales/canales tienen autorización formal de captura (Portalinmobiliario, TOCTOC, Yapo, WhatsApp).
- **Opciones:**
  - **A:** Partir con 1 proyecto piloto en la plataforma sin migrar histórico viejo; captura por formulario web propio + importación por correo oficial del portal (sin scraping).
  - **B:** Migrar planillas/CRM histórico completo e integrar APIs de portales desde día 1.
  - **C:** Postergar la vertical inmobiliaria hasta completar la estabilización de Hotel + Cafetería.
- **Recomendación (**REQUISITO PROPUESTO**):** **Opción C** en el corto plazo (foco en Hotel V1), y al activar la vertical comenzar con **Opción A**.
- **Consecuencias:** A evita deuda de migración y riesgos legales de scraping; B exige contratos API con portales y limpieza previa de planillas; C evita dispersar capacidad operativa hoy.

### `Q-INM-02` — Reserva inmobiliaria, vigencia y reembolsos (`#100`, `#115`)
- **DECISIÓN PENDIENTE:** si la reserva de unidad exige pago en línea (Webpay/Mercado Pago) o admite transferencia validada manualmente, plazo de vigencia de la cotización/reserva y política de devolución si no se firma la promesa.
- **Opciones:**
  - **A:** Bloqueo de unidad solo tras comprobante validado por administración (transferencia o pasarela cuando se contrate); cotización vigente 48–72 h; toda devolución requiere aprobación humana y respaldo contable (nunca reembolso automático).
  - **B:** Pago en línea obligatorio por Webpay con bloqueo instantáneo y devolución automática al vencer.
- **Recomendación (**REQUISITO PROPUESTO**):** **Opción A** (coherente con la política actual de sin pasarelas activas sin autorización y contabilidad append-only).
- **Consecuencias:** A reduce riesgo de doble venta y disputas de contracargo, a cambio de validación manual; B requiere contrato Webpay Plus y validación jurídica de reembolsos.

### `Q-INM-03` — Revisión legal de promesa de compraventa y firma electrónica (`#100`, `#115`)
- **DECISIÓN PENDIENTE:** quién redacta/aprueba la promesa (abogado interno o estudio externo), plazo máximo entre reserva y promesa, y si se exige Firma Electrónica Avanzada (Ley 19.799) con proveedor API o firma presencial/notarial con archivo digital.
- **Opciones:**
  - **A:** Plantilla revisada por abogado del propietario; en V1 inmobiliaria el sistema gestiona estado y archivo del PDF firmado (notaría o proveedor externo), sin integrar firma electrónica API inicialmente.
  - **B:** Integración directa con proveedor de firma electrónica avanzada (Ley 19.799) desde el primer hito.
- **Recomendación (**REQUISITO PROPUESTO**):** **Opción A** para V1 de la vertical.
- **Consecuencias:** A acorta el tiempo de salida y evita costos fijos de proveedor FEA antes de validar volumen; B exige evaluación contractual, sandbox y revisión legal previa.

### `Q-INM-04` — Garantías de postventa y responsables (`#100`, `#119`)
- **DECISIÓN PENDIENTE:** plazos de garantía por tipo de falla (terminaciones, instalaciones, estructura conforme LGUC Art. 18), quién clasifica/aprueba si está cubierta y SLA de escalamiento (la spec propone 72 h como **SUPUESTO**).
- **Opciones:**
  - **A:** Adoptar plazos legales chilenos (LGUC Art. 18: 3 años terminaciones, 5 instalaciones, 10 estructura) como matriz base, con jefe de postventa como único aprobador de cobertura y SLA de 72 h hábiles.
  - **B:** Definir matriz personalizada más estricta con contratistas externos asignables en plataforma.
- **Recomendación (**REQUISITO PROPUESTO**):** **Opción A** ratificada por el responsable legal/postventa.
- **Consecuencias:** A alinea la plataforma con la normativa chilena y evita que el agente rechace casos fuera de política; B agrega gestión de terceros y permisos adicionales.

---

## 3. Issues #128, #143 y #147 — Vertical `004-constructora-obra`

> **HECHO DOCUMENTADO:** `#128` (`T003`) es el gate de la vertical; `#143` (`H3`: avance y compras) depende de `Q-OBR-01/02/03` y `#147` (`H4`: presupuesto, inspección y materiales) depende de `Q-OBR-03` y `Q-OBR-04`. La vertical está marcada **BLOCKED** y fuera de V1.

### `Q-OBR-01` — Obras propias o de terceros, presupuesto y módulo previo (`#128`, `#143`)
- **DECISIÓN PENDIENTE:** si la constructora ejecuta solo obras propias del grupo o también contratos para terceros, formato del presupuesto base por partida y confirmación de que no existe módulo previo entregable.
- **Opciones:**
  - **A:** Alcance inicial solo para obras propias del grupo con presupuesto versionado cargado desde planilla estándar (sin depender de módulo heredado).
  - **B:** Incluir obras para terceros con estados de pago, retenciones y facturación de avance desde el primer hito.
- **Recomendación (**REQUISITO PROPUESTO**):** **Opción A** (cuando se decida abrir la vertical).
- **Consecuencias:** A evita modelar contratos con mandantes externos y estados de pago complejos antes de validar control interno; B multiplica el alcance contable y tributario.

### `Q-OBR-02` — Unidad de avance, calendario y umbral de desvío (`#128`, `#143`)
- **DECISIÓN PENDIENTE:** cómo se mide el avance físico (porcentaje por partida vs. cubicación/cantidad ejecutada), frecuencia de corte (diario/semanal) y umbral de desvío que dispara alerta.
- **Opciones:**
  - **A:** Avance medido en unidad física de partida (m², m³, un, ml) con conversión automática a % ponderado, corte semanal y alerta por desvío > 5 % o retroceso registrado (conservando versión anterior).
  - **B:** Avance solo en % libre reportado por jefe de obra, corte mensual.
- **Recomendación (**REQUISITO PROPUESTO**):** **Opción A**.
- **Consecuencias:** A impide confundir avance físico con costo ejecutado (`FR-015`) y da trazabilidad real; B es más rápido de llenar pero propenso a estimaciones subjetivas.

### `Q-OBR-03` — Aprobadores, compras, seguridad e inspecciones (`#128`, `#143`, `#147`)
- **DECISIÓN PENDIENTE:** quién aprueba solicitudes de compra y con qué tope (el límite del asistente parte en `0 CLP`), qué inspecciones de calidad/seguridad son obligatorias y qué evidencia exige el cierre de observaciones.
- **Opciones:**
  - **A:** El jefe de obra o asistente solo genera borradores de compra (`0 CLP` autónomo); el administrador aprueba toda orden antes de emitir; inspecciones exigen foto + responsable + fecha de cierre validada por humano.
  - **B:** Aprobación escalonada por monto (jefe de obra hasta un tope CLP definido, administración sobre ese tope).
- **Recomendación (**REQUISITO PROPUESTO**):** **Opción A** inicialmente, revisable a **Opción B** una vez auditado el primer trimestre de obra.
- **Consecuencias:** A garantiza `SC-010` (cero compras no autorizadas) desde el inicio; B agiliza compras menores de obra si se define un tope formal y auditoría mensual.

### `Q-OBR-04` — Alcance de subcontratos y consultas técnicas / RFI (`#147`)
- **HECHO DOCUMENTADO:** el texto completo de `Q-OBR-04` no existe en este repositorio (no migrado desde el repo origen).
- **Opciones:**
  - **A:** Dejar gestión integral de subcontratos y RFI explícitamente fuera de la primera fase de `004-constructora-obra` (registrar solo referencias documentales en observaciones de inspección).
  - **B:** Recuperar/redactar el alcance completo de subcontratos y RFI con el propietario antes de diseñar `H4`.
- **Recomendación (**REQUISITO PROPUESTO**):** **Opción A** para no bloquear `H4` cuando se active la vertical, o confirmar con el propietario si desea redactar el alcance en **Opción B**.
- **Consecuencias:** A acota `H4` a presupuesto, inspecciones y bodega de materiales (donde ya puede reutilizarse el core de stock); B amplía la vertical a gestión contractual de subcontratistas.

---

## Cómo registrar la decisión y cerrar estas tarjetas

Para cerrar cualquiera de los 7 issues:
1. El propietario elige la opción (o redacta su variante) y la registra con **fecha** en un documento bajo `docs/decisiones/` (mismo formato que `docs/decisiones/decisiones-2026-11-20.md`).
2. Se marca la tarea `T003` / `T-DEC` en el `specs/*/tasks.md` correspondiente.
3. Se comenta el issue con el enlace al registro de decisión, se cierra y se mueve la tarjeta del Project a **Done**.
