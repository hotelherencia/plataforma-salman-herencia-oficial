# Respuestas propuestas — vertical hotel

Fecha: 2026-10-27. Estado de todas las entradas: **PROPUESTA, NO RATIFICADA**. Ninguna pregunta está respondida por el propietario. Cada propuesta se apoya en la documentación de RSalman y cita su ruta. Donde la documentación no alcanza, se indica y la pregunta queda como DECISIÓN PENDIENTE.

Rutas (`R:` = `F:\Code\RSalman\plataforma-salman\docs\`):
- Documentos de arquitectura, auditorías e investigación: `R:` + ruta relativa, por ejemplo `R:arquitectura/aclaraciones.md`.
- Specs de RSalman: `F:\Code\RSalman\plataforma-salman\specs\`, por ejemplo `...\specs\002-hotel-reservas-concierge\research.md`.
- Constitución del workspace: `.specify/memory/constitution.md`.
- Spec del hotel en el proyecto: `specs/002-hotel-reservas-concierge/spec.md`.

Todas las rutas citadas se comprobaron con `Test-Path` el 2026-10-27.

Lectura general: la documentación no contiene respuestas aprobadas del cliente. Contiene controles propuestos, recomendaciones provisionales y advertencias de bloqueo. Esta hoja distingue esos niveles.

---

## Q-HOT-01 — PMS actual, datos migrables y fuente de inventario

- **Registro:** `R:arquitectura/aclaraciones.md` (línea 13). Responsable: administración del hotel.
- **Evidencia:**
  - `R:auditorias/hallazgos.md`, F-005 (crítica, BLOQUEADO): la spec presupone un PMS propio antes de evaluar el existente. Corrección: sistema de registro por seleccionar.
  - `R:arquitectura/decisiones/ADR-002.md`: no imponer PMS propio; integrar mediante referencias y contratos. La selección de PMS y channel manager está bloqueada.
  - `F:\Code\RSalman\plataforma-salman\specs\002-hotel-reservas-concierge\research.md`: «inventariar operación y evaluar adaptadores antes de reemplazar sistemas». Las alternativas de adaptar frente a construir no se aprueban sin inventario real.
  - `specs/002-hotel-reservas-concierge/spec.md` línea 111: «PMS actual y continuidad por confirmar en Q-HOT-01; no se decide abandonarlo».
- **Propuesta (no ratificada):** inventariar el PMS vigente y sus datos migrables antes de decidir construir. Si el PMS actual expone API o exportación suficiente, adaptarlo. El research también menciona la captura manual controlada como alternativa; no es una opción elegida.
- **Falta para cerrar:** inventario real de habitaciones, tipos, temporadas y fuente de verdad; costo total de cada alternativa; prueba de exportación con muestra minimizada.
- **Bloquea:** `002/T003`, `H1/T-DEC`, `H2/T-DEC`.

## Q-HOT-02 — Canales, volumen y acceso contractual API / channel manager

- **Registro:** `R:arquitectura/aclaraciones.md` (línea 14). Responsable: hotel + proveedor.
- **Evidencia:**
  - `R:auditorias/hallazgos.md`, F-009 (crítica, BLOQUEADO): APIs OTA tratadas como accesibles con credenciales; la integración es inviable sin contrato ni certificación.
  - `F:\Code\RSalman\plataforma-salman\specs\002-hotel-reservas-concierge\research.md`: «preferir evaluar channel manager autorizado antes de conectores directos». Booking exige proceso de acceso; Airbnb publica partners, pero eso no prueba acceso API. No inferir capacidad de escritura a partir de que un proveedor declare usar MCP.
  - `R:arquitectura/decisiones/ADR-006.md`: adaptar el sistema existente con esos contratos si el plan, la API o el permiso lo admiten; captura y revisión humana controlada ante falta de integración.
- **Propuesta (no ratificada):** no asumir acceso directo a Booking ni Airbnb. Preferir un channel manager autorizado con contrato. Mientras el canal no responda, la captura controlada no confirma cupo: el estado de sincronización queda incierto y no se promete disponibilidad (F-006).
- **Tensión a decidir:** FR-003 exige sincronización en ambos sentidos con Booking y Airbnb. Sin contrato, esa forma no se cumple. Mantener FR-003 o reformularlo es decisión del propietario.
- **Falta para cerrar:** contrato o acceso real de partner, sandbox autorizado y capacidades por canal.
- **Bloquea:** `002/T003`, `H1/T-DEC`; transitivamente, los conectores Booking y Airbnb.

## Q-HOT-03 — Cancelación, cobro anticipado, factura a empresa, documentación de check-in, housekeeping y límites del agente

- **Registro:** `R:arquitectura/aclaraciones.md` (línea 15). Responsable: hotel + legal/tributario.
- **Evidencia:**
  - `R:investigacion-competitiva/historias-propuestas.md`, RF-HOT-01 (FR-018): modificar o cancelar con versión, cupo, tarifa, penalidad y saldo; separar devolución de liquidación. Es propuesta, no regla aprobada.
  - `R:arquitectura/decisiones/ADR-004.md`: separar resultado de pago, hecho tributario, entrega documental y decisión comercial; no exponer al modelo herramientas directas de cobro o emisión.
  - `R:auditorias/hallazgos.md`, F-002 (crítica): cada pago implica boleta; riesgo de doble documentación con anticipos y voucher.
  - `R:auditorias/hallazgos.md`, F-006 (crítica): seguir vendiendo con inventario local durante una caída contradice impedir sobreventa.
  - `specs/002-hotel-reservas-concierge/spec.md`, FR-011: reglas de autonomía con montos máximos y escalamiento. La constitución fija 0 CLP como control preventivo inicial, no como umbral comercial.
- **Propuesta por subpregunta (no ratificada):**
  - Límite monetario del agente: 0 CLP sin aprobación humana. Es el valor que la constitución fija como control inicial; la cifra comercial no está acordada.
  - Cancelación y cobro anticipado: la documentación no elige entre cobro total, parcial o garantía. DECISIÓN PENDIENTE.
  - Factura a empresas desde V1: DECISIÓN PENDIENTE. Depende de Q-CORE-02.
  - Documentación de check-in y housekeeping propio o externo: sin evidencia suficiente. DECISIÓN PENDIENTE.
- **Cierre previsto:** RF-HOT-01 (FR-018) se ratifica en `002/T202`.
- **Falta para cerrar:** política de cancelación y anticipo aprobada; decisión de factura a empresas; documentación mínima de check-in; decisión sobre housekeeping.
- **Bloquea:** `002/T003`, `H1/T-DEC`, `H2/T-DEC`, `H3/T-DEC`.

## Q-CORE-01 — Empresas, roles y autorización entre empresas

- **Registro:** `R:arquitectura/aclaraciones.md` (línea 7). Responsable: cliente + seguridad.
- **Evidencia:**
  - `R:arquitectura/vision-general.md`: los tenants representan empresas con permisos y responsabilidades propios.
  - `.specify/memory/constitution.md`, principio IV: «Empresas del mismo grupo permanecen separadas».
  - `R:arquitectura/decisiones/ADR-001.md`: extraer identidad, aislamiento, auditoría y adaptadores compartidos; mantener datos de negocio en las verticales.
- **Propuesta (no ratificada):** una sola empresa para el hotel V1, sin acceso cruzado. Las empresas del grupo permanecen separadas, como exige la constitución.
- **Falta para cerrar:** matriz de roles y recursos aprobada por el cliente.
- **Bloquea:** `000-core/T003`; transitivamente `000-core/T004` y los T-IMP del hotel.

## Q-CORE-02 — Fiscalidad por contribuyente (documentos, anticipos, DTE)

- **Registro:** `R:arquitectura/aclaraciones.md` (línea 8). Responsable: responsable tributario + cliente. Cierre: política firmada y ejemplos aprobados.
- **Evidencia:**
  - `R:auditorias/hallazgos.md`, F-002 (crítica): separar pago, hecho, entrega y documento. Estado: control propuesto, bloqueado por fiscalidad.
  - `R:arquitectura/decisiones/ADR-004.md`: separar resultado de pago, hecho tributario, entrega documental y decisión comercial.
  - `F:\Code\RSalman\plataforma-salman\specs\000-core\spec.md` y `specs/000-core/spec.md`, FR-004: «Determinar y emitir el documento tributario aplicable mediante política aprobada por contribuyente».
- **Propuesta (no ratificada):** política por contribuyente con separación entre pago y documento. No se elige proveedor DTE: la documentación no permite elegirlo.
- **Falta para cerrar:** decisión del responsable tributario; proveedor DTE; ejemplos aprobados de anticipo, saldo y voucher.
- **Factura a empresas:** DECISIÓN PENDIENTE. Su frecuencia y si entra en V1 no están documentadas.
- **Bloquea:** `000-core/T003`; transitivamente, `H1/T-IMP` y los demás T-IMP del hotel.

## Q-CORE-03 — Responsables de datos, retención, recuperación, presupuesto y autonomía

- **Registro:** `R:arquitectura/aclaraciones.md` (línea 9). Significado confirmado por el propietario el 2026-10-27 (ver `backlog/decisiones-hotel.md`, §3).
- **Evidencia:**
  - `R:auditorias/hallazgos.md`, F-017 (alta, bloqueado): NFR sin RPO/RTO, presupuesto, tratamiento de datos ni mediciones base.
  - `specs/000-core/spec.md`, NFR-004: remite a esta pregunta sin valores.
  - `.specify/memory/constitution.md`: Ley 19.628 y transición a Ley 21.719 al 01-12-2026; RPO/RTO antes de producción.
- **Propuesta (no ratificada):** no se propone valor para ninguna subpregunta. No existe en la documentación un registro de tratamiento ni objetivos RPO/RTO.
- **Falta para cerrar:** responsable o encargado; finalidades y base legal; plazo de retención; RPO/RTO; presupuesto; límite autónomo.
- **Bloquea:** `000-core/T003`; transitivamente, las tareas de retención y restauración del hotel.

## Q-CORE-04 — Efectos laterales de herramientas y mensajes o cargos implícitos

- **Registro:** `R:investigacion-competitiva/decisiones-pendientes.md` (tabla de aclaraciones adicionales). Responsable: seguridad + integración + negocio.
- **Evidencia:**
  - `R:arquitectura/decisiones/ADR-006.md`: el core exige perfil y autorización de efectos externos y provee correlación y auditoría.
  - `R:auditorias/hallazgos.md`, F-023 (crítica): confusión entre cancelar y devolver; acuse y cargo confundidos.
- **Propuesta (no ratificada):** ningún efecto externo (mensaje, cobro, emisión) se ejecuta sin autorización explícita del perfil correspondiente. Es el criterio de ADR-006, no una decisión del cliente.
- **Falta para cerrar:** perfil de operación real; prueba negativa de herramientas; quién autoriza mensajes y cargos.
- **Estado:** DECISIÓN PENDIENTE. No tiene ítem propio en el backlog. Afecta a `002/H3/T-IMP`, que lo indica en su cuerpo sin incluirlo en `depende_de`.

## Q-HOT-04 — Cambios de fecha, categoría, tarifa, penalidad, saldo y devolución

- **Registro:** `R:investigacion-competitiva/decisiones-pendientes.md` (aclaraciones adicionales). Responsable: hotel + finanzas/tributario.
- **Evidencia:** RF-HOT-01 en `R:investigacion-competitiva/historias-propuestas.md`; `R:arquitectura/decisiones/ADR-006.md`.
- **Propuesta (no ratificada):** la propuesta de cambio se muestra con su diferencia, y se requiere aceptación explícita sobre la versión concreta. No se confirma ningún cambio sin ella.
- **Cierre previsto:** `002/T202` (FR-018).
- **Falta para cerrar:** reglas de penalidad y devolución; ejemplos aprobados.
- **Bloquea:** `002/H1/T-DEC`, `002/H2/T-DEC`, `002/H3/T-DEC`, `002/H1/T-IMP`, `002/H2/T-IMP`, `002/H3/T-IMP` y `002/T203`. Las tres preguntas Q-HOT-04/05/06 comparten el cierre en T202 y bloquean hoy los mismos siete ids; H2 espera el paquete entero.

## Q-HOT-05 — Extras por persona, noche o estadía; destino del cargo

- **Registro:** `R:investigacion-competitiva/decisiones-pendientes.md`. Responsable: hotel + cafetería + contabilidad.
- **Evidencia:** RF-HOT-02 en `R:investigacion-competitiva/historias-propuestas.md`; `specs/002-hotel-reservas-concierge/spec.md`, FR-019.
- **Propuesta (no ratificada):** FR-019 propone vincular el extra a la estadía. La matriz de cuenta, destino y periodicidad no está definida; no se propone ninguna.
- **Cierre previsto:** `002/T202` (FR-019).
- **Falta para cerrar:** matriz servicio, regla, cuenta, destino y contribuyente.
- **Bloquea:** `002/H1/T-DEC`, `002/H2/T-DEC`, `002/H3/T-DEC`, `002/H1/T-IMP`, `002/H2/T-IMP`, `002/H3/T-IMP` y `002/T203`. Igual que Q-HOT-04 y Q-HOT-06: el paquete entero comparte T202 y bloquea los siete ids.

## Q-HOT-06 — Acuse por canal, mapeos, persistencia y conflictos

- **Registro:** `R:investigacion-competitiva/decisiones-pendientes.md`. Responsable: integración + proveedor.
- **Evidencia:** RF-HOT-03 en `R:investigacion-competitiva/historias-propuestas.md`; `specs/002-hotel-reservas-concierge/spec.md`, FR-020 (distinguir acuse de aplicación, pago y confirmación comercial); `R:auditorias/hallazgos.md`, F-006.
- **Propuesta (no ratificada):** acuse durable separado de la aplicación. Ante un conflicto de canal, no se confirma inventario incierto.
- **Cierre previsto:** `002/T202` (FR-020).
- **Falta para cerrar:** contrato real de operación del canal; casos de prueba en sandbox autorizado.
- **Bloquea:** `002/H1/T-DEC`, `002/H2/T-DEC`, `002/H3/T-DEC`, `002/H1/T-IMP`, `002/H2/T-IMP`, `002/H3/T-IMP` y `002/T203`. Hoy T202 bloquea estos siete ids; las tres preguntas Q-HOT-04/05/06 comparten su cierre, así que H2 espera el paquete entero y no puede cerrar `H2/T-DEC` con una sola de ellas.

## Q-GOV-01 — Ratificación de la constitución 1.1.0

- **Registro:** `R:arquitectura/aclaraciones.md` (línea 24). Responsable: Cristóbal Herrera.
- **Evidencia:**
  - `R:arquitectura/decisiones/ADR-001.md` a `ADR-004.md`: estado «ratificación pendiente».
  - `R:investigacion-competitiva/decisiones-pendientes.md`: «Constitución revisada: no se modifica ni cambia versión». Esto contradice la versión 1.1.0 propuesta; ver `backlog/speckit-analyze/000-core.md`, AN-000-15.
- **Propuesta:** ninguna. Es decisión del propietario, con las tres opciones registradas en `backlog/decisiones-hotel.md`, §7.
- **Falta para cerrar:** decisión de versión y nota de migración.
- **Bloquea:** `000-core/T004`, y transitivamente el gate del núcleo.

---

## Resumen

| Pregunta | Estado de la propuesta | Evidencia principal | Cierre previsto |
|---|---|---|---|
| Q-HOT-01 | Inventariar antes de construir | F-005, ADR-002, research | `002/T003` |
| Q-HOT-02 | No asumir acceso directo; FR-003 en tensión | F-009, F-006, research | `002/T003` |
| Q-HOT-03 | Límite del agente en 0 CLP sin aprobación; el resto, decisión del propietario | RF-HOT-01, ADR-004, F-002, F-006 | `002/T003` |
| Q-CORE-01 | Una sola empresa; grupo separado | constitución IV, vision-general, ADR-001 | `000-core/T003` |
| Q-CORE-02 | Política conservadora; proveedor DTE sin elegir; factura a empresas pendiente | F-002, ADR-004 | `000-core/T003` |
| Q-CORE-03 | Sin propuesta | F-017 | `000-core/T003` |
| Q-CORE-04 | Ningún efecto externo sin autorización; DECISIÓN PENDIENTE | ADR-006, F-023 | Sin ítem propio |
| Q-HOT-04 | Aceptación explícita sobre la versión | RF-HOT-01 | `002/T202` |
| Q-HOT-05 | Vincular a la estadía; matriz pendiente | RF-HOT-02, FR-019 | `002/T202` |
| Q-HOT-06 | Acuse separado de la aplicación | RF-HOT-03, FR-020, F-006 | `002/T202` |
| Q-GOV-01 | Sin propuesta: decisión del propietario | ADR-001..004 | `000-core/T004` |

Ninguna propuesta desbloquea implementación por sí sola. El bloqueo sigue vigente hasta que el propietario las ratifique y se registre fecha y evidencia en `002/T003`, `000-core/T003` y `002/T202`.
