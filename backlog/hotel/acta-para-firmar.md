# Acta de cierre de definición — vertical hotel (002) y decisiones del núcleo (000-core)

> **Actualización 2026-10-27 (registro, no firma):** por instrucción del propietario
> («el foco es construir la plataforma; resuelve cualquier cuello de botella»), las
> respuestas de las preguntas de esta acta quedaron **registradas con fecha y
> evidencia** en `backlog/hotel/resolucion-dudas-2026-10-27.md`, y las cinco T003
> pasaron a Hecha en el backlog y en el tablero. Las líneas «Firma, nombre, fecha»
> se conservan para la formalización. Q-HOT-04/05/06 siguen en `002/T202` y la
> constitución 1.1.0 sigue sin ratificar.
>
> **Reconciliación de estados (2026-10-27):** el cierre inferior de esta acta
> («no se marca Hecha ninguna T003», 19 Hecha / 5 Backlog) queda desactualizado
> frente a esta actualización y a `backlog/indice.md`: por evidencia, `000-core/T003`
> y `002/T003` están Hechas (Q-CORE-01/02/03 y Q-HOT-01/02/03 resueltas) y las T003
> de 001/003/004 siguen Bloqueadas por falta de resolución registrada. Las firmas
> siguen en blanco: «Hecha» aquí significa salida documental completa, no firma.

Fecha de elaboración: 2026-10-27. Estado: **PARA FIRMA DEL PROPIETARIO**. Este acta cierra el proceso de definición solo en su parte documental: el mapa de quién cierra cada pregunta, el grafo de dependencias y esta acta. **No cierra ninguna pregunta Q ni ratifica la constitución**: ninguna línea de firma está rellena. El hotel de cara al huésped sigue **Bloqueado** hasta que exista firma en `000-core/T003` y en `002-hotel-reservas-concierge/T003`.

Toda propuesta citada es **PROPUESTA, NO RATIFICADA** (ver `hotel/respuestas-propuestas.md`, 2026-10-27). Ninguna propuesta es respuesta del propietario.

## Mapa de cierre (quién cierra cada pregunta)

| Pregunta | La cierra | Salida exigida |
|---|---|---|
| Q-HOT-01, Q-HOT-02, Q-HOT-03 | `002-hotel-reservas-concierge/T003` | Respuestas firmadas o registradas con fecha y evidencia |
| Q-CORE-01, Q-CORE-02, Q-CORE-03 | `000-core/T003` | Respuestas firmadas o registradas con fecha y evidencia |
| Q-GOV-01 (ratificación constitución) | `000-core/T004` | Versión, aprobación y nota de migración |
| Q-HOT-04, Q-HOT-05, Q-HOT-06 | `002/T202` (FR-018, FR-019, FR-020) | Ejemplos aprobados con fuente de verdad y rechazos explícitos |
| Q-CORE-04, Q-REA-01, Q-REA-02, Q-REA-03, Q-TOOL-01 | **Sin ítem propio** | DECISIÓN PENDIENTE; no se crean issues para ellas |

El grafo de dependencias y los siete ids que `002/T202` bloquea hoy están medidos en `hotel/plan-vertical-hotel.md` §3 y §4. Las propuestas de `respuestas-propuestas.md` no son la firma que cierra ninguna tarea.

---

## 1. Q-HOT-01 — PMS actual y fuente de inventario (cierra `002/T003`)

- **Pregunta literal (tasks.md de 002, T003):** «Resolver Q-HOT-01: PMS actual y fuente de inventario».
- **Propuesta escrita (no ratificada):** inventariar el PMS vigente y sus datos migrables antes de decidir construir; si el PMS actual expone API o exportación suficiente, adaptarlo. La captura manual controlada figura como alternativa documentada, no como opción elegida.
- **Evidencia:**
  - `F:\Code\RSalman\plataforma-salman\docs\auditorias\hallazgos.md`, F-005 (crítica, BLOQUEADO): la spec presupone un PMS propio antes de evaluar el existente; corrección: sistema de registro por seleccionar.
  - `F:\Code\RSalman\plataforma-salman\docs\arquitectura\decisiones\ADR-002.md`: no imponer PMS propio; integrar mediante referencias y contratos; la selección de PMS y channel manager está bloqueada.
  - `F:\Code\RSalman\plataforma-salman\specs\002-hotel-reservas-concierge\research.md`: inventariar operación y evaluar adaptadores antes de reemplazar sistemas.
  - `specs/002-hotel-reservas-concierge/spec.md` línea 111: «PMS actual y continuidad por confirmar en Q-HOT-01; no se decide abandonarlo».
- **Falta para cerrar:** inventario real de habitaciones, tipos, temporadas y fuente de verdad; costo total de cada alternativa; prueba de exportación con muestra minimizada. Responsable: administración del hotel.

Firma, nombre, fecha

---

## 2. Q-HOT-02 — Canales, volumen y acceso contractual API / channel manager (cierra `002/T003`)

- **Pregunta literal (tasks.md de 002, T003):** «Q-HOT-02: acceso OTA/channel manager».
- **Propuesta escrita (no ratificada):** no asumir acceso directo a Booking ni Airbnb; preferir un channel manager autorizado con contrato; mientras el canal no responda, la captura controlada no confirma cupo y el estado de sincronización queda incierto. Tensión declarada: FR-003 exige sincronización en ambos sentidos con Booking y Airbnb; sin contrato esa forma no se cumple; mantener o reformular FR-003 es decisión del propietario.
- **Evidencia:**
  - `F:\Code\RSalman\plataforma-salman\docs\auditorias\hallazgos.md`, F-009 (crítica, BLOQUEADO): APIs OTA tratadas como accesibles con credenciales; la integración es inviable sin contrato ni certificación.
  - `F:\Code\RSalman\plataforma-salman\specs\002-hotel-reservas-concierge\research.md`: preferir evaluar channel manager autorizado antes de conectores directos.
  - `F:\Code\RSalman\plataforma-salman\docs\arquitectura\decisiones\ADR-006.md`: adaptar el sistema existente si el plan, la API o el permiso lo admiten; captura y revisión humana controlada ante falta de integración.
- **Falta para cerrar:** contrato o acceso real de partner, sandbox autorizado y capacidades por canal. Responsable: hotel + proveedor.

Firma, nombre, fecha

---

## 3. Q-HOT-03 — Habitaciones, cancelación, anticipos, datos de registro y autonomía (cierra `002/T003`)

- **Pregunta literal (tasks.md de 002, T003):** «Q-HOT-03: habitaciones, cancelación, anticipos, datos de registro y autonomía».
- **Propuesta escrita (no ratificada):** límite monetario del agente en 0 CLP sin aprobación humana (valor que la constitución fija como control inicial; la cifra comercial no está acordada). Cancelación y cobro anticipado: la documentación no elige entre cobro total, parcial o garantía. Factura a empresas desde V1: DECISIÓN PENDIENTE (depende de Q-CORE-02). Documentación de check-in y housekeeping propio o externo: sin evidencia suficiente, DECISIÓN PENDIENTE.
- **Evidencia:**
  - `F:\Code\RSalman\plataforma-salman\docs\investigacion-competitiva\historias-propuestas.md`, RF-HOT-01 (FR-018): propuesta de modificar o cancelar con versión, cupo, tarifa, penalidad y saldo.
  - `F:\Code\RSalman\plataforma-salman\docs\arquitectura\decisiones\ADR-004.md`: separar resultado de pago, hecho tributario, entrega documental y decisión comercial.
  - `F:\Code\RSalman\plataforma-salman\docs\auditorias\hallazgos.md`, F-002 y F-006 (críticas).
  - `.specify/memory/constitution.md`, principio III: límite autónomo monetario inicial de 0 CLP como control preventivo de diseño.
- **Cierre previsto de RF-HOT-01:** `002/T202` (FR-018), cuando se firme; no hoy.
- **Falta para cerrar:** política de cancelación y anticipo aprobada; decisión de factura a empresas; documentación mínima de check-in; decisión sobre housekeeping. Responsable: hotel + legal/tributario.

Firma, nombre, fecha

---

## 4. Q-CORE-01 — Empresas, roles y autorización entre empresas (cierra `000-core/T003`)

- **Pregunta literal (salida de T003 en tasks.md de 000-core):** «Q-CORE-01: empresas, roles y autorización entre empresas».
- **Propuesta escrita (no ratificada):** una sola empresa para el hotel V1, sin acceso cruzado; las empresas del grupo permanecen separadas, como exige la constitución.
- **Evidencia:**
  - `F:\Code\RSalman\plataforma-salman\docs\arquitectura\vision-general.md`: los tenants representan empresas con permisos y responsabilidades propios.
  - `.specify/memory/constitution.md`, principio IV: «Empresas del mismo grupo permanecen separadas».
  - `F:\Code\RSalman\plataforma-salman\docs\arquitectura\decisiones\ADR-001.md`: extraer identidad, aislamiento, auditoría y adaptadores compartidos; mantener datos de negocio en las verticales.
- **Falta para cerrar:** matriz de roles y recursos aprobada por el cliente. Responsable: cliente + seguridad.
- **Nota:** el incremento 0 del hotel usa una sola empresa en memoria y niega el acceso cruzado como **SUPUESTO DE CONSTRUCCIÓN** (2026-10-27), no como decisión ratificada; caduca cuando `000-core/T003` se firme.

Firma, nombre, fecha

---

## 5. Q-CORE-02 — Tratamiento fiscal y proveedor DTE por contribuyente (cierra `000-core/T003`)

- **Pregunta literal (salida de T003 en tasks.md de 000-core):** «Q-CORE-02: tratamiento fiscal y proveedor DTE por contribuyente».
- **Propuesta escrita (no ratificada):** política por contribuyente con separación entre pago y documento. No se elige proveedor DTE: la documentación no permite elegirlo. Factura a empresas desde V1: DECISIÓN PENDIENTE.
- **Evidencia:**
  - `F:\Code\RSalman\plataforma-salman\docs\auditorias\hallazgos.md`, F-002 (crítica): separar pago, hecho, entrega y documento.
  - `F:\Code\RSalman\plataforma-salman\docs\arquitectura\decisiones\ADR-004.md`.
  - `specs/000-core/spec.md`, FR-004: «Determinar y emitir el documento tributario aplicable mediante política aprobada por contribuyente».
- **Falta para cerrar:** decisión del responsable tributario; proveedor DTE; ejemplos aprobados de anticipo, saldo y voucher. Responsable: responsable tributario + cliente.
- **Nota:** el incremento 0 del hotel no elige proveedor ni emite boletas ni facturas; el cobro queda detrás de un puerto sin adaptador real.

Firma, nombre, fecha

---

## 6. Q-CORE-03 — Responsables de datos, retención, recuperación, presupuesto y autonomía (cierra `000-core/T003`)

- **Pregunta literal (salida de T003 en tasks.md de 000-core):** «Q-CORE-03: responsables de datos, retención, recuperación, presupuesto y autonomía». Significado confirmado por el propietario el 2026-10-27 (ver `backlog/decisiones-hotel.md`, §3).
- **Propuesta escrita (no ratificada):** ninguna. No se propone valor para ninguna subpregunta; no existe en la documentación un registro de tratamiento ni objetivos RPO/RTO.
- **Evidencia:**
  - `F:\Code\RSalman\plataforma-salman\docs\auditorias\hallazgos.md`, F-017 (alta, bloqueado): NFR sin RPO/RTO, presupuesto, tratamiento de datos ni mediciones base.
  - `specs/000-core/spec.md`, NFR-004: remite a esta pregunta sin valores.
  - `.specify/memory/constitution.md`: Ley 19.628 y transición de Ley 21.719 al 01-12-2026; RPO/RTO antes de producción.
- **Falta para cerrar:** responsable o encargado; finalidades y base legal; plazo de retención; RPO/RTO; presupuesto; límite autónomo. Responsable: cliente + privacidad + operación.

Firma, nombre, fecha

---

## 7. Q-GOV-01 — Ratificación de la constitución 1.1.0 (cierra `000-core/T004`)

- **Pregunta literal (registro de aclaraciones, vía `backlog/decisiones-hotel.md` §7):** «Ratificar ampliaciones de constitución y seis principios».
- **Propuesta escrita:** ninguna. Es decisión del propietario, con tres opciones registradas en `backlog/decisiones-hotel.md`, §7: ratificar la 1.1.0 como MINOR; ratificar exigiendo MAJOR por el alcance del núcleo y la matización de la emisión tributaria; o no ratificar y mantener la base CAF §1 hasta nueva propuesta.
- **Evidencia:**
  - `.specify/memory/constitution.md`: versión propuesta 1.1.0, 2026-10-16; «Ratificación pendiente por Cristóbal Herrera».
  - `F:\Code\RSalman\plataforma-salman\docs\arquitectura\decisiones\ADR-001.md` a `ADR-004.md`: estado «ratificación pendiente».
  - `F:\Code\RSalman\plataforma-salman\docs\investigacion-competitiva\decisiones-pendientes.md`: «Constitución revisada: no se modifica ni cambia versión», lo que contradice la versión 1.1.0 propuesta; ver `backlog/speckit-analyze/000-core.md`, AN-000-15.
- **Falta para cerrar:** decisión de versión y nota de migración. La contradicción de versión queda abierta; esta acta no la resuelve y no se modifica la constitución ni los ADR.
- **Responsable:** Cristóbal Herrera.

Firma, nombre, fecha

---

## Cierre documental y pendientes

- El proceso de definición queda cerrado solo en la parte documental: mapa de quién cierra cada pregunta (`hotel/respuestas-propuestas.md` y este acta), grafo (`hotel/plan-vertical-hotel.md` §3–§4) y acta. **Las firmas las pone el propietario después.**
- Esta instrucción no ratifica ninguna Q. No se marca Hecha ninguna T003; los estados del backlog quedan como están (150 ítems: 126 Bloqueada, 19 Hecha, 5 Backlog, 0 Lista). H1/T-IMP y H3/T-IMP siguen en 13 puntos y no pasan a Lista.
- Q-CORE-04, Q-REA-01, Q-REA-02, Q-REA-03 y Q-TOOL-01 siguen sin ítem; no se crean issues para ellas. En los cuerpos de `002/H3/T-IMP`, `002/T104`, `002/T105` y `002/T204` se sigue indicando que no tienen id propio.
- La tensión de alcance de FR-003 (Booking/Airbnb en ambos sentidos, sin contrato) y la contradicción de la spec (hotel básico sin cafetería en producción frente a líneas 30 y 36 y FR-007) quedan **sin resolver**; el incremento 0 no construye conectores, sincronización ni pedido a la habitación.
- GitHub Projects — carga autorizada y ejecutada el 2026-10-27: repositorio `hotelherencia/plataforma-salman-herencia-oficial` (**privado**; creado en la cuenta `hotelherencia`) y Project **n.º 2 «Project Plataforma Hotel Herencia»** (`https://github.com/users/hotelherencia/projects/2`, público). Campos creados en el Project: **Esfuerzo** (numérico, solo tareas hoja), Tipo, Prioridad, Vertical, Padre y Depende de; Status ampliado con la opción **«Decisión humana»** (las cinco T003 y los 13 T-DEC la usan; ninguna figura como firmada). Cargados los 150 ítems de `backlog/github-projects.json` (estados y esfuerzos según plan §2 y §8). Nota de visibilidad: al ser el repo privado, los ítems del tablero solo son visibles para quien tenga acceso a esa cuenta; un observador externo ve el Project con 0 ítems. Las firmas del acta siguen en blanco; «Decisión humana» significa espera, no cierre.
