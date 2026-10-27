# Hoja de decisiones del propietario — plataforma hotel

Estado: **DECISIÓN PENDIENTE** en todas las entradas. Ninguna pregunta está respondida; esta hoja no propone respuestas. Las opciones son las que la fuente deja abiertas. Cada decisión se registra con fecha y evidencia en el T003 de su feature.

Fuentes de definición: `specs/*/spec.md` (idénticas a `F:\Code\RSalman\plataforma-salman\specs`) y el registro `F:\Code\RSalman\plataforma-salman\docs\arquitectura\aclaraciones.md` (definición de Q-CORE, Q-HOT y Q-GOV-01, con responsable propuesto y evidencia de cierre). Los responsables son roles propuestos: según ese registro, los cargos funcionales requieren designación nominal.

Orden: Q-CORE-02, Q-CORE-01, Q-CORE-03, Q-HOT-01, Q-HOT-02, Q-HOT-03, ratificación de la constitución (Q-GOV-01).

Propuestas con evidencia de RSalman para cada pregunta: `hotel/respuestas-propuestas.md` (no ratificadas). Plan de operación y esfuerzo: `hotel/plan-vertical-hotel.md`.

Regla: ninguna tarea de implementación de hotel pasa a Lista mientras `000-core/T003` (Q-CORE-01/02/03) y `002-hotel-reservas-concierge/T003` (Q-HOT-01/02/03) no estén cerradas, y `000-core/T004` no tenga la constitución ratificada.

---

## 1. Q-CORE-02 — Fiscalidad por contribuyente: ¿qué documentos emite el hotel V1 y con qué proveedor DTE?

- **Definición (aclaraciones.md):** «Por contribuyente: comprobantes, anticipos, reservas, IVA aplicable, voucher, factura, proveedor DTE, pasarela y certificados».
- **Responsable propuesto:** responsable tributario + cliente.
- **Evidencia de cierre:** política firmada y ejemplos aprobados.
- **Bloquea:** `000-core/T003`; `000-core/H2/T-DEC`; de forma transitiva, `002-hotel-reservas-concierge/H1/T-IMP` (cobro y documento de la reserva) y los demás T-IMP del hotel.
- **Fuentes adicionales:** `specs/000-core/spec.md` (FR-004, Q-CORE-02); `specs/002-hotel-reservas-concierge/spec.md` (FR-004 y la clarificación «¿Se emite factura a empresas con frecuencia?»); `constitution.md` principio II; hallazgo F-002 de `docs/auditorias/hallazgos.md` (cada pago implica boleta; puede haber anticipos, saldo y voucher; riesgo de doble documentación).
- **Opciones abiertas (sin recomendación):**
  1. El hotel V1 emite solo los documentos de venta que la política fiscal aprobada permita.
  2. El hotel V1 incluye facturación electrónica a empresas; el proveedor DTE queda por nombrar.
  3. El hotel V1 incluye facturación electrónica con proveedor ya elegido; el contrato queda por verificar.
  4. Diferir hasta la revisión del responsable tributario.
- **Nota:** la constitución indica que esta decisión puede cambiar el alcance del núcleo.

## 2. Q-CORE-01 — Empresas, roles y autorización entre empresas

- **Definición (aclaraciones.md):** «Empresas/RUT, locales, jerarquía tenant, roles, soporte y accesos entre empresas».
- **Responsable propuesto:** cliente + seguridad.
- **Evidencia de cierre:** matriz empresa/rol/recurso/acción aprobada.
- **Bloquea:** `000-core/T003`; `000-core/H1/T-DEC`; de forma transitiva, `000-core/T004` (matriz de roles y permisos por empresa) y los T-IMP del hotel.
- **Fuentes adicionales:** `specs/000-core/spec.md` (FR-001, FR-002, NFR-001); `constitution.md` principios I y IV; `docs/arquitectura/vision-general.md` (la jerarquía de tenant debe confirmarla Q-CORE-01).
- **Opciones abiertas (sin recomendación):**
  1. Una sola empresa (tenant) para el hotel V1, sin acceso cruzado.
  2. Varias empresas del grupo en la misma plataforma, con separación estricta de datos y permisos.
  3. Acceso cruzado entre empresas para roles concretos, con autorización explícita y auditada.
  4. Diferir hasta definir la matriz de roles (T004).

## 3. Q-CORE-03 — Responsables de datos, retención, recuperación, presupuesto y autonomía

**Decisión registrada (2026-10-27, confirmada por el propietario):** Q-CORE-03 rige con el significado de `aclaraciones.md` (responsables de datos, retención, recuperación, presupuesto y autonomía). La medición y la priorización se separan en un ID propio, Q-COMP-05, que no forma parte de Q-CORE-03. Esta entrada se mantiene como referencia; la respuesta concreta sigue pendiente.

- **Definición (aclaraciones.md):** «Responsable/encargado, finalidades, base legal, retención, residencia, presupuesto, RPO/RTO y límites agénticos».
- **Responsable propuesto:** cliente + privacidad + operación.
- **Evidencia de cierre:** registro de tratamiento, objetivos y presupuesto.
- **Bloquea:** `000-core/T003`; `000-core/H1/T-DEC`, `000-core/H2/T-DEC`, `000-core/H3/T-DEC`; de forma transitiva, las tareas de retención, restauración y límite del agente del hotel.
- **Fuentes adicionales:** `specs/000-core/spec.md` (NFR-004); `constitution.md` principios III (límite autónomo inicial de 0 CLP como control preventivo, no umbral comercial) y VI (RPO/RTO antes de producción); `docs/auditorias/hallazgos.md` F-017 (NFR sin RPO/RTO, presupuesto ni tratamiento de datos).
- **Preguntas abiertas:** responsable o encargado del tratamiento; finalidades y base legal; plazo de retención; objetivos RPO/RTO; presupuesto; límite monetario autónomo del agente (la constitución fija 0 CLP como control inicial; la cifra comercial no está acordada).

## 4. Q-HOT-01 — PMS actual, datos migrables y fuente de inventario

- **Definición (aclaraciones.md):** «PMS actual, datos migrables, habitaciones/tipos, temporadas y fuente de verdad».
- **Responsable propuesto:** administración del hotel.
- **Evidencia de cierre:** inventario y decisión build/buy/adapt.
- **Bloquea:** `002-hotel-reservas-concierge/T003`; `002-hotel-reservas-concierge/H1/T-DEC` y `…/H2/T-DEC`; de forma transitiva, los T-IMP de H1 y H2 del hotel.
- **Fuentes adicionales:** `specs/002-hotel-reservas-concierge/spec.md` (supuesto «PMS actual y continuidad por confirmar»; clarificación «¿Existe PMS actual con datos a migrar?»); hallazgo F-005 de `docs/auditorias/hallazgos.md` (se presupone un PMS propio antes de evaluar el existente; BLOQUEADO).
- **Opciones abiertas (sin recomendación):**
  1. Continuar con el PMS actual como sistema de registro.
  2. Sustituir el PMS actual por el sistema de registro de la plataforma (con migración).
  3. Mantener el PMS actual para reservas y usar la plataforma para la web y el canal directo.
  4. Diferir hasta confirmar el PMS vigente y sus datos.

## 5. Q-HOT-02 — Canales, volumen y acceso contractual API/channel manager

- **Definición (aclaraciones.md):** «Canales, volumen y acceso contractual API/channel manager».
- **Responsable propuesto:** hotel + proveedor.
- **Evidencia de cierre:** contrato, permisos, sandbox y capacidades.
- **Bloquea:** `002-hotel-reservas-concierge/T003`; `002-hotel-reservas-concierge/H1/T-DEC`; de forma transitiva, los conectores Booking/Airbnb y los T-IMP de H1 y H2.
- **Fuentes adicionales:** `specs/002-hotel-reservas-concierge/spec.md` (dependencias: construir conector o contratar channel manager, «evaluar en research.md»; credenciales de partner de Booking y Airbnb con certificación); hallazgo F-009 de `docs/auditorias/hallazgos.md` (APIs OTA tratadas como accesibles con credenciales; integración inviable sin contrato).
- **Opciones abiertas (sin recomendación):**
  1. Channel manager propio (construir conector).
  2. Channel manager contratado de un tercero con API.
  3. Conexión directa con Booking y Airbnb mediante credenciales de partner, sujeta a certificación.
  4. Sincronización manual mientras se define la vía (no cumple FR-003 en su forma actual; decidir si se acepta).
- **Nota:** `F:\Code\RSalman\plataforma-salman\specs\002-hotel-reservas-concierge\research.md` contiene la comparación que la spec remite. Revisado el 2026-10-27; sus conclusiones y la evidencia de cada alternativa están en `hotel/respuestas-propuestas.md`, sin ratificar.

## 6. Q-HOT-03 — Cancelación, cobro anticipado, factura de empresa, documentación de check-in, housekeeping y límites del agente

- **Definición (aclaraciones.md):** «Cancelación, cobro anticipado, factura empresa, documentación check-in, housekeeping propio/externo y límites del agente».
- **Responsable propuesto:** hotel + legal/tributario.
- **Evidencia de cierre:** políticas y roles aprobados.
- **Bloquea:** `002-hotel-reservas-concierge/T003`; `002-hotel-reservas-concierge/H1/T-DEC`, `…/H2/T-DEC` y `…/H3/T-DEC`; de forma transitiva, las políticas de cambio y cancelación y el límite del agente concierge.
- **Fuentes adicionales:** `specs/002-hotel-reservas-concierge/spec.md` (clarificaciones de cancelación y anticipo, límite monetario del agente, housekeeping, datos de registro); hallazgo de `docs/auditorias/auditoria-hot.md` (datos de identidad, anticipo, factura y cancelación no definidos).
- **Preguntas abiertas:** política de cancelación y de cobro anticipado (total, parcial o garantía); si se emite factura a empresas desde V1; documentación mínima de check-in; límite monetario del agente sin aprobación humana (en la spec, un cambio sin penalidad requiere aprobación humana hasta ratificar Q-HOT-03); housekeeping propio o externo.

## 7. Ratificación de la constitución 1.1.0 (Q-GOV-01)

- **Definición (aclaraciones.md):** «Ratificar ampliaciones de constitución y seis principios».
- **Responsable propuesto:** Cristóbal Herrera (autoridad documental y técnica original, según aclaraciones.md).
- **Evidencia de cierre:** versión, aprobación y nota de migración.
- **Bloquea:** `000-core/T004`; de forma transitiva, `000-core/T005`–`T007` y todas las tareas de implementación que dependen del gate del núcleo.
- **Fuentes adicionales:** `constitution.md` (versión propuesta 1.1.0, 2026-10-16; «Ratificación pendiente»; la gobernanza permite exigir MAJOR al ratificar); `docs/investigacion-competitiva/decisiones-pendientes.md` (la constitución no se modifica ni cambia de versión; Q-GOV-01 permanece pendiente).
- **Opciones abiertas (sin recomendación):**
  1. Ratificar la 1.1.0 como MINOR.
  2. Ratificar exigiendo MAJOR por el alcance del núcleo y la matización de la emisión tributaria.
  3. No ratificar y mantener la base CAF §1 hasta nueva propuesta.
