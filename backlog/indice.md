# Índice de backlog (cargado en GitHub Projects el 2026-10-27: Project n.º 2 de hotelherencia; reconciliado con el tablero el 2026-10-28)

> **Cierre de ciclo (2026-10-28):** este corpus documental quedó cerrado en el
> tablero (ítems abiertos cerrados como «not planned», salvo las 15 decisiones
> pendientes; todo lo Done se conserva). El backlog vigente de construcción es
> **[v1/](v1/indice.md)** (42 ítems: 4 épicas, 9 historias, 29 tareas).

Reconciliación con el tablero (2026-10-28), por evidencia y con fecha:
- Se crean los 5 issues que faltaban del corpus (`001-cafeteria-mesas-pos/T201`–`T205`, issues #206–#210): el log de carga inicial solo llegó a 150. T201 → Done (Hecha documentada); T202–T205 → Todo.
- Se corrigen 47 estados del tablero que carecían de fuente documental: 44 tareas marcadas Done vuelven a Todo y las T003 de `001`, `003` y `004` vuelven a «Decisión humana». Fuente de verdad: `specs/*/tasks.md` las tiene abiertas (`[ ]`) y la reconciliación del 2026-10-27 (abajo) fijó las T003 por evidencia. Regla aplicada: el tablero se corrige a la evidencia documental; quien avance una tarea registra su fuente.
- Se registran localmente los 55 ítems creados en el repo tras la carga inicial (issues #151–#205: incrementos y casos AT-*/ADV-*/AC-US-*, todos Done) en `backlog/github-projects-extras.json`. Evidencia de su Done: 181 pruebas locales de los incrementos en memoria, OK el 2026-10-28 (6 baterías: hotel incr.0 = 17, núcleo incr.1 = 9, hotel incr.1 = 102, cafetería = 19, inmobiliaria = 20, constructora = 14). Reparación previa necesaria: import de `datetime` en `verticales/hotel/incremento1/hotel_inventario/dominio.py`.
- Se cargan las 3 historias nuevas derivadas del Manual Maestro (`HU-HOT-01`, `HU-HOT-02`, `HU-HOT-03`, issues #211–#213, propuestas) desde `backlog/github-projects-hu-manual.json`; fuente: `backlog/hotel/historias-manual-maestro.md`.

Nota de reconciliación (2026-10-27): los estados de las cinco T003 se fijan por evidencia, no por el estado previo de este índice:
- `000-core/T003` y `002-hotel-reservas-concierge/T003` → **Hecha**. Fuente: `backlog/hotel/resolucion-dudas-2026-10-27.md` (instrucción del propietario, 2026-10-27, «resuelve cualquier cuello de botella»): Q-CORE-01/02/03 y Q-HOT-01/02/03 resueltas con valores por defecto de mercado, fecha y evidencia — la salida que `specs/*/tasks.md` exige para T003.
- `001-cafeteria-mesas-pos/T003`, `003-inmobiliaria-comercial/T003` y `004-constructora-obra/T003` → **Bloqueada**. No existe resolución registrada de Q-CAF-01/02/03, Q-INM-01…04 ni Q-OBR-01/02/03; el «Hecha» previo carecía de fuente y se corrige.
- Contradicción documental del mismo día resuelta: `backlog/hotel/acta-para-firmar.md` (cierre), `cierre-dudas-decision-humana.md` y `correccion-datos-backend.md` sostienen que las T003 siguen abiertas; se resuelve a favor de la fuente con respuestas fechadas y con evidencia. La constitución 1.1.0 **no** se ratifica (Q-GOV-01 sigue en `000-core/T004`) y las firmas manuscritas del acta siguen en blanco.

Brecha corregida (2026-10-27): `001-cafeteria-mesas-pos` ya tiene T201–T205 en `specs/001-cafeteria-mesas-pos/tasks.md` y en este backlog; T201 figura como Hecha (FR-015 y FR-016 registrados en spec.md). Cierra la brecha registrada el 2026-10-27.

Total corpus: 155 issues — Épica: 5, Historia: 13, Tarea: 137
Estados del corpus: Bloqueada: 133, Hecha: 22 (fuente: este índice y `specs/*/tasks.md`)
Tablero GitHub (2026-10-28): 213 ítems = corpus 155 + extras 55 + manual 3. Estados: Todo: 120, Done: 77, Decisión humana: 16

Orden: épica → historias P1 y P2/P3 → tareas de gate → tareas por historia (DEC → DIS → ACC → IMP).

- [Bloqueada] P1 `000-core` — 000-core — Core transversal
  - [Bloqueada] P1 `000-core/H1` — 000-core/H1 — Administrar acceso por empresa (US-CORE-001)
  - [Bloqueada] P1 `000-core/H2` — 000-core/H2 — Confirmar pagos y documentos sin duplicaciones (US-CORE-002)
  - [Bloqueada] P2 `000-core/H3` — 000-core/H3 — Gobernar acciones y contratos (US-CORE-003)
  - [Hecha] P1 `000-core/T001` — 000-core/T001 — Inventariar fuente, separar alcance y preservar IDs
  - [Hecha] P1 `000-core/T002` — 000-core/T002 — Derivar modelo conceptual, amenazas y catálogo de aceptación
  - [Hecha] P1 `000-core/T003` — 000-core/T003 — Resolver decisiones Q-* de la feature
  - [Bloqueada] P1 `000-core/T004` — 000-core/T004 — Ratificar alternativas, constitución y permisos por empresa
  - [Bloqueada] P1 `000-core/T005` — 000-core/T005 — Completar contratos técnicos
  - [Bloqueada] P1 `000-core/T006` — 000-core/T006 — Convertir acceptance.md en casos de prueba concretos
  - [Bloqueada] P1 `000-core/T007` — 000-core/T007 — Reejecutar controles documentales y cerrar hallazgos
  - [Hecha] P1 `000-core/T101` — 000-core/T101 — Comparar historias heredadas y fuentes; alias US-*
  - [Bloqueada] P1 `000-core/T102` — 000-core/T102 — Validar con usuarios reglas nuevas de FR-010/FR-011
  - [Bloqueada] P1 `000-core/T103` — 000-core/T103 — Precisar casos AC-US con muestras, permisos y errores
  - [Bloqueada] P1 `000-core/T104` — 000-core/T104 — Evaluar en demo autorizada las observaciones que faltan (REA)
  - [Bloqueada] P1 `000-core/T105` — 000-core/T105 — Análisis de consistencia oficial de Spec Kit y backlog ratificado
  - [Hecha] P1 `000-core/T201` — 000-core/T201 — Investigar y reconstruir RF derivados
  - [Bloqueada] P1 `000-core/T202` — 000-core/T202 — Ratificar estados, cantidades, permisos y excepciones de FR-012
  - [Bloqueada] P1 `000-core/T203` — 000-core/T203 — Revisar invariantes y contratos lógicos (timeout, repetición, parcialidad)
  - [Bloqueada] P1 `000-core/T204` — 000-core/T204 — Comprobar conducta en demo/entorno propio autorizado (REA)
  - [Bloqueada] P1 `000-core/T205` — 000-core/T205 — Revisar costos y latencias por etapa
    - [Bloqueada] P1 `000-core/H1/T-DEC` — 000-core/H1/T-DEC — Decidir Q-CORE-01, Q-CORE-03 para H1
    - [Bloqueada] P1 `000-core/H1/T-DIS` — 000-core/H1/T-DIS — Diseñar contrato y estados de H1
    - [Bloqueada] P1 `000-core/H1/T-ACC` — 000-core/H1/T-ACC — Casos de aceptación de US-CORE-001
    - [Bloqueada] P1 `000-core/H1/T-IMP` — 000-core/H1/T-IMP — Implementar H1 (NO INICIAR: bloqueada)
    - [Bloqueada] P1 `000-core/H2/T-DEC` — 000-core/H2/T-DEC — Decidir Q-CORE-02, Q-CORE-03 para H2
    - [Bloqueada] P1 `000-core/H2/T-DIS` — 000-core/H2/T-DIS — Diseñar contrato y estados de H2
    - [Bloqueada] P1 `000-core/H2/T-ACC` — 000-core/H2/T-ACC — Casos de aceptación de US-CORE-002
    - [Bloqueada] P1 `000-core/H2/T-IMP` — 000-core/H2/T-IMP — Implementar H2 (NO INICIAR: bloqueada)
    - [Bloqueada] P2 `000-core/H3/T-DEC` — 000-core/H3/T-DEC — Decidir Q-CORE-03, Q-CORE-04 para H3
    - [Bloqueada] P2 `000-core/H3/T-DIS` — 000-core/H3/T-DIS — Diseñar contrato y estados de H3
    - [Bloqueada] P2 `000-core/H3/T-ACC` — 000-core/H3/T-ACC — Casos de aceptación de US-CORE-003
    - [Bloqueada] P2 `000-core/H3/T-IMP` — 000-core/H3/T-IMP — Implementar H3 (NO INICIAR: bloqueada)
- [Bloqueada] P1 `001-cafeteria-mesas-pos` — 001-cafeteria-mesas-pos — Cafetería: mesas, pedidos y POS
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/H1` — 001-cafeteria-mesas-pos/H1 — Pedir y pagar desde la mesa (US-CAF-001)
  - [Bloqueada] P2 `001-cafeteria-mesas-pos/H2` — 001-cafeteria-mesas-pos/H2 — Control de gastos e inventario con margen por producto (US-CAF-002)
  - [Bloqueada] P3 `001-cafeteria-mesas-pos/H3` — 001-cafeteria-mesas-pos/H3 — Propuestas y alertas del agente (US-CAF-003)
  - [Hecha] P1 `001-cafeteria-mesas-pos/T001` — 001-cafeteria-mesas-pos/T001 — Inventariar fuente, separar alcance y preservar IDs
  - [Hecha] P1 `001-cafeteria-mesas-pos/T002` — 001-cafeteria-mesas-pos/T002 — Derivar modelo conceptual, amenazas y catálogo de aceptación
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T003` — 001-cafeteria-mesas-pos/T003 — Resolver decisiones Q-* de la feature
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T004` — 001-cafeteria-mesas-pos/T004 — Ratificar alternativas, constitución y permisos por empresa
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T005` — 001-cafeteria-mesas-pos/T005 — Completar contratos técnicos
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T006` — 001-cafeteria-mesas-pos/T006 — Convertir acceptance.md en casos de prueba concretos
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T007` — 001-cafeteria-mesas-pos/T007 — Reejecutar controles documentales y cerrar hallazgos
  - [Hecha] P1 `001-cafeteria-mesas-pos/T101` — 001-cafeteria-mesas-pos/T101 — Comparar historias heredadas y fuentes; alias US-*
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T102` — 001-cafeteria-mesas-pos/T102 — Validar con usuarios reglas nuevas de FR-015/FR-016
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T103` — 001-cafeteria-mesas-pos/T103 — Precisar casos AC-US con muestras, permisos y errores
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T104` — 001-cafeteria-mesas-pos/T104 — Evaluar en demo autorizada las observaciones que faltan (REA)
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T105` — 001-cafeteria-mesas-pos/T105 — Análisis de consistencia oficial de Spec Kit y backlog ratificado
  - [Hecha] P1 `001-cafeteria-mesas-pos/T201` — 001-cafeteria-mesas-pos/T201 — Investigar y reconstruir RF derivados
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T202` — 001-cafeteria-mesas-pos/T202 — Ratificar estados, cantidades, permisos y excepciones de FR-015, FR-016
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T203` — 001-cafeteria-mesas-pos/T203 — Revisar invariantes y contratos lógicos (timeout, repetición, parcialidad)
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T204` — 001-cafeteria-mesas-pos/T204 — Comprobar conducta en demo/entorno propio autorizado (REA)
  - [Bloqueada] P1 `001-cafeteria-mesas-pos/T205` — 001-cafeteria-mesas-pos/T205 — Revisar costos y latencias por etapa
    - [Bloqueada] P1 `001-cafeteria-mesas-pos/H1/T-DEC` — 001-cafeteria-mesas-pos/H1/T-DEC — Decidir Q-CAF-01, Q-CAF-02 para H1
    - [Bloqueada] P1 `001-cafeteria-mesas-pos/H1/T-DIS` — 001-cafeteria-mesas-pos/H1/T-DIS — Diseñar contrato y estados de H1
    - [Bloqueada] P1 `001-cafeteria-mesas-pos/H1/T-ACC` — 001-cafeteria-mesas-pos/H1/T-ACC — Casos de aceptación de US-CAF-001
    - [Bloqueada] P1 `001-cafeteria-mesas-pos/H1/T-IMP` — 001-cafeteria-mesas-pos/H1/T-IMP — Implementar H1 (NO INICIAR: bloqueada)
    - [Bloqueada] P2 `001-cafeteria-mesas-pos/H2/T-DEC` — 001-cafeteria-mesas-pos/H2/T-DEC — Decidir Q-CAF-02, Q-CAF-03 para H2
    - [Bloqueada] P2 `001-cafeteria-mesas-pos/H2/T-DIS` — 001-cafeteria-mesas-pos/H2/T-DIS — Diseñar contrato y estados de H2
    - [Bloqueada] P2 `001-cafeteria-mesas-pos/H2/T-ACC` — 001-cafeteria-mesas-pos/H2/T-ACC — Casos de aceptación de US-CAF-002
    - [Bloqueada] P2 `001-cafeteria-mesas-pos/H2/T-IMP` — 001-cafeteria-mesas-pos/H2/T-IMP — Implementar H2 (NO INICIAR: bloqueada)
    - [Bloqueada] P3 `001-cafeteria-mesas-pos/H3/T-DEC` — 001-cafeteria-mesas-pos/H3/T-DEC — Decidir Q-CAF-03 para H3
    - [Bloqueada] P3 `001-cafeteria-mesas-pos/H3/T-DIS` — 001-cafeteria-mesas-pos/H3/T-DIS — Diseñar contrato y estados de H3
    - [Bloqueada] P3 `001-cafeteria-mesas-pos/H3/T-ACC` — 001-cafeteria-mesas-pos/H3/T-ACC — Casos de aceptación de US-CAF-003
    - [Bloqueada] P3 `001-cafeteria-mesas-pos/H3/T-IMP` — 001-cafeteria-mesas-pos/H3/T-IMP — Implementar H3 (NO INICIAR: bloqueada)
- [Bloqueada] P1 `002-hotel-reservas-concierge` — 002-hotel-reservas-concierge — Hotel: reservas y concierge
  - [Bloqueada] P1 `002-hotel-reservas-concierge/H1` — 002-hotel-reservas-concierge/H1 — Reservar y pagar desde la web del hotel (US-HOT-001)
  - [Bloqueada] P2 `002-hotel-reservas-concierge/H2` — 002-hotel-reservas-concierge/H2 — Operar la estadía: check-in digital, pedidos y housekeeping (US-HOT-002)
  - [Bloqueada] P3 `002-hotel-reservas-concierge/H3` — 002-hotel-reservas-concierge/H3 — Concierge agéntico por WhatsApp con reglas de autonomía (US-HOT-003)
  - [Propuesta] P1 `002-hotel-reservas-concierge/HU-HOT-01` — 002-hotel-reservas-concierge/HU-HOT-01 — Configurar habitación y tarifa (HU-HOT-01)
  - [Propuesta] P1 `002-hotel-reservas-concierge/HU-HOT-02` — 002-hotel-reservas-concierge/HU-HOT-02 — Conciliación y cierre financiero diario (HU-HOT-02)
  - [Propuesta] P1 `002-hotel-reservas-concierge/HU-HOT-03` — 002-hotel-reservas-concierge/HU-HOT-03 — Indicador mínimo de gerencia (HU-HOT-03)
  - [Hecha] P1 `002-hotel-reservas-concierge/T001` — 002-hotel-reservas-concierge/T001 — Inventariar fuente, separar alcance y preservar IDs
  - [Hecha] P1 `002-hotel-reservas-concierge/T002` — 002-hotel-reservas-concierge/T002 — Derivar modelo conceptual, amenazas y catálogo de aceptación
  - [Hecha] P1 `002-hotel-reservas-concierge/T003` — 002-hotel-reservas-concierge/T003 — Resolver decisiones Q-* de la feature
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T004` — 002-hotel-reservas-concierge/T004 — Ratificar alternativas, constitución y permisos por empresa
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T005` — 002-hotel-reservas-concierge/T005 — Completar contratos técnicos
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T006` — 002-hotel-reservas-concierge/T006 — Convertir acceptance.md en casos de prueba concretos
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T007` — 002-hotel-reservas-concierge/T007 — Reejecutar controles documentales y cerrar hallazgos
  - [Hecha] P1 `002-hotel-reservas-concierge/T101` — 002-hotel-reservas-concierge/T101 — Comparar historias heredadas y fuentes; alias US-*
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T102` — 002-hotel-reservas-concierge/T102 — Validar con usuarios reglas nuevas de FR-016/FR-017
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T103` — 002-hotel-reservas-concierge/T103 — Precisar casos AC-US con muestras, permisos y errores
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T104` — 002-hotel-reservas-concierge/T104 — Evaluar en demo autorizada las observaciones que faltan (REA)
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T105` — 002-hotel-reservas-concierge/T105 — Análisis de consistencia oficial de Spec Kit y backlog ratificado
  - [Hecha] P1 `002-hotel-reservas-concierge/T201` — 002-hotel-reservas-concierge/T201 — Investigar y reconstruir RF derivados
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T202` — 002-hotel-reservas-concierge/T202 — Ratificar estados, cantidades, permisos y excepciones de FR-018, FR-019, FR-020
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T203` — 002-hotel-reservas-concierge/T203 — Revisar invariantes y contratos lógicos (timeout, repetición, parcialidad)
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T204` — 002-hotel-reservas-concierge/T204 — Comprobar conducta en demo/entorno propio autorizado (REA)
  - [Bloqueada] P1 `002-hotel-reservas-concierge/T205` — 002-hotel-reservas-concierge/T205 — Revisar costos y latencias por etapa
    - [Bloqueada] P1 `002-hotel-reservas-concierge/H1/T-DEC` — 002-hotel-reservas-concierge/H1/T-DEC — Decidir Q-HOT-01, Q-HOT-02, Q-HOT-03 para H1
    - [Bloqueada] P1 `002-hotel-reservas-concierge/H1/T-DIS` — 002-hotel-reservas-concierge/H1/T-DIS — Diseñar contrato y estados de H1
    - [Bloqueada] P1 `002-hotel-reservas-concierge/H1/T-ACC` — 002-hotel-reservas-concierge/H1/T-ACC — Casos de aceptación de US-HOT-001
    - [Bloqueada] P1 `002-hotel-reservas-concierge/H1/T-IMP` — 002-hotel-reservas-concierge/H1/T-IMP — Implementar H1 (NO INICIAR: bloqueada)
    - [Bloqueada] P2 `002-hotel-reservas-concierge/H2/T-DEC` — 002-hotel-reservas-concierge/H2/T-DEC — Decidir Q-HOT-01, Q-HOT-03 para H2
    - [Bloqueada] P2 `002-hotel-reservas-concierge/H2/T-DIS` — 002-hotel-reservas-concierge/H2/T-DIS — Diseñar contrato y estados de H2
    - [Bloqueada] P2 `002-hotel-reservas-concierge/H2/T-ACC` — 002-hotel-reservas-concierge/H2/T-ACC — Casos de aceptación de US-HOT-002
    - [Bloqueada] P2 `002-hotel-reservas-concierge/H2/T-IMP` — 002-hotel-reservas-concierge/H2/T-IMP — Implementar H2 (NO INICIAR: bloqueada)
    - [Bloqueada] P3 `002-hotel-reservas-concierge/H3/T-DEC` — 002-hotel-reservas-concierge/H3/T-DEC — Decidir Q-HOT-03, Q-HOT-04 para H3
    - [Bloqueada] P3 `002-hotel-reservas-concierge/H3/T-DIS` — 002-hotel-reservas-concierge/H3/T-DIS — Diseñar contrato y estados de H3
    - [Bloqueada] P3 `002-hotel-reservas-concierge/H3/T-ACC` — 002-hotel-reservas-concierge/H3/T-ACC — Casos de aceptación de US-HOT-003
    - [Bloqueada] P3 `002-hotel-reservas-concierge/H3/T-IMP` — 002-hotel-reservas-concierge/H3/T-IMP — Implementar H3 (NO INICIAR: bloqueada)
- [Bloqueada] P1 `003-inmobiliaria-comercial` — 003-inmobiliaria-comercial — Inmobiliaria comercial
  - [Bloqueada] P1 `003-inmobiliaria-comercial/H1` — 003-inmobiliaria-comercial/H1 — De lead a promesa en un solo flujo (US-INM-001)
  - [Bloqueada] P2 `003-inmobiliaria-comercial/H2` — 003-inmobiliaria-comercial/H2 — Cobranza y postventa con agente (US-INM-002)
  - [Hecha] P1 `003-inmobiliaria-comercial/T001` — 003-inmobiliaria-comercial/T001 — Inventariar fuente, separar alcance y preservar IDs
  - [Hecha] P1 `003-inmobiliaria-comercial/T002` — 003-inmobiliaria-comercial/T002 — Derivar modelo conceptual, amenazas y catálogo de aceptación
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T003` — 003-inmobiliaria-comercial/T003 — Resolver decisiones Q-* de la feature
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T004` — 003-inmobiliaria-comercial/T004 — Ratificar alternativas, constitución y permisos por empresa
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T005` — 003-inmobiliaria-comercial/T005 — Completar contratos técnicos
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T006` — 003-inmobiliaria-comercial/T006 — Convertir acceptance.md en casos de prueba concretos
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T007` — 003-inmobiliaria-comercial/T007 — Reejecutar controles documentales y cerrar hallazgos
  - [Hecha] P1 `003-inmobiliaria-comercial/T101` — 003-inmobiliaria-comercial/T101 — Comparar historias heredadas y fuentes; alias US-*
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T102` — 003-inmobiliaria-comercial/T102 — Validar con usuarios reglas nuevas de FR-015/FR-016
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T103` — 003-inmobiliaria-comercial/T103 — Precisar casos AC-US con muestras, permisos y errores
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T104` — 003-inmobiliaria-comercial/T104 — Evaluar en demo autorizada las observaciones que faltan (REA)
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T105` — 003-inmobiliaria-comercial/T105 — Análisis de consistencia oficial de Spec Kit y backlog ratificado
  - [Hecha] P1 `003-inmobiliaria-comercial/T201` — 003-inmobiliaria-comercial/T201 — Investigar y reconstruir RF derivados
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T202` — 003-inmobiliaria-comercial/T202 — Ratificar estados, cantidades, permisos y excepciones de FR-017, FR-018, FR-019, FR-020
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T203` — 003-inmobiliaria-comercial/T203 — Revisar invariantes y contratos lógicos (timeout, repetición, parcialidad)
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T204` — 003-inmobiliaria-comercial/T204 — Comprobar conducta en demo/entorno propio autorizado (REA)
  - [Bloqueada] P1 `003-inmobiliaria-comercial/T205` — 003-inmobiliaria-comercial/T205 — Revisar costos y latencias por etapa
    - [Bloqueada] P1 `003-inmobiliaria-comercial/H1/T-DEC` — 003-inmobiliaria-comercial/H1/T-DEC — Decidir Q-INM-01, Q-INM-02, Q-INM-03 para H1
    - [Bloqueada] P1 `003-inmobiliaria-comercial/H1/T-DIS` — 003-inmobiliaria-comercial/H1/T-DIS — Diseñar contrato y estados de H1
    - [Bloqueada] P1 `003-inmobiliaria-comercial/H1/T-ACC` — 003-inmobiliaria-comercial/H1/T-ACC — Casos de aceptación de US-INM-001
    - [Bloqueada] P1 `003-inmobiliaria-comercial/H1/T-IMP` — 003-inmobiliaria-comercial/H1/T-IMP — Implementar H1 (NO INICIAR: bloqueada)
    - [Bloqueada] P2 `003-inmobiliaria-comercial/H2/T-DEC` — 003-inmobiliaria-comercial/H2/T-DEC — Decidir Q-INM-01, Q-INM-04 para H2
    - [Bloqueada] P2 `003-inmobiliaria-comercial/H2/T-DIS` — 003-inmobiliaria-comercial/H2/T-DIS — Diseñar contrato y estados de H2
    - [Bloqueada] P2 `003-inmobiliaria-comercial/H2/T-ACC` — 003-inmobiliaria-comercial/H2/T-ACC — Casos de aceptación de US-INM-002
    - [Bloqueada] P2 `003-inmobiliaria-comercial/H2/T-IMP` — 003-inmobiliaria-comercial/H2/T-IMP — Implementar H2 (NO INICIAR: bloqueada)
- [Bloqueada] P1 `004-constructora-obra` — 004-constructora-obra — Constructora y control de obra
  - [Bloqueada] P1 `004-constructora-obra/H3` — 004-constructora-obra/H3 — Reportar avance y preparar compras (US-OBR-003)
  - [Bloqueada] P2 `004-constructora-obra/H4` — 004-constructora-obra/H4 — Controlar presupuesto, inspección y materiales (US-OBR-004)
  - [Hecha] P1 `004-constructora-obra/T001` — 004-constructora-obra/T001 — Inventariar fuente, separar alcance y preservar IDs
  - [Hecha] P1 `004-constructora-obra/T002` — 004-constructora-obra/T002 — Derivar modelo conceptual, amenazas y catálogo de aceptación
  - [Bloqueada] P1 `004-constructora-obra/T003` — 004-constructora-obra/T003 — Resolver decisiones Q-* de la feature
  - [Bloqueada] P1 `004-constructora-obra/T004` — 004-constructora-obra/T004 — Ratificar alternativas, constitución y permisos por empresa
  - [Bloqueada] P1 `004-constructora-obra/T005` — 004-constructora-obra/T005 — Completar contratos técnicos
  - [Bloqueada] P1 `004-constructora-obra/T006` — 004-constructora-obra/T006 — Convertir acceptance.md en casos de prueba concretos
  - [Bloqueada] P1 `004-constructora-obra/T007` — 004-constructora-obra/T007 — Reejecutar controles documentales y cerrar hallazgos
  - [Hecha] P1 `004-constructora-obra/T101` — 004-constructora-obra/T101 — Comparar historias heredadas y fuentes; alias US-*
  - [Bloqueada] P1 `004-constructora-obra/T102` — 004-constructora-obra/T102 — Validar con usuarios reglas nuevas de FR-019/FR-020
  - [Bloqueada] P1 `004-constructora-obra/T103` — 004-constructora-obra/T103 — Precisar casos AC-US con muestras, permisos y errores
  - [Bloqueada] P1 `004-constructora-obra/T104` — 004-constructora-obra/T104 — Evaluar en demo autorizada las observaciones que faltan (REA)
  - [Bloqueada] P1 `004-constructora-obra/T105` — 004-constructora-obra/T105 — Análisis de consistencia oficial de Spec Kit y backlog ratificado
  - [Hecha] P1 `004-constructora-obra/T201` — 004-constructora-obra/T201 — Investigar y reconstruir RF derivados
  - [Bloqueada] P1 `004-constructora-obra/T202` — 004-constructora-obra/T202 — Ratificar estados, cantidades, permisos y excepciones de FR-021, FR-022, FR-023
  - [Bloqueada] P1 `004-constructora-obra/T203` — 004-constructora-obra/T203 — Revisar invariantes y contratos lógicos (timeout, repetición, parcialidad)
  - [Bloqueada] P1 `004-constructora-obra/T204` — 004-constructora-obra/T204 — Comprobar conducta en demo/entorno propio autorizado (REA)
  - [Bloqueada] P1 `004-constructora-obra/T205` — 004-constructora-obra/T205 — Revisar costos y latencias por etapa
    - [Bloqueada] P1 `004-constructora-obra/H3/T-DEC` — 004-constructora-obra/H3/T-DEC — Decidir Q-OBR-01, Q-OBR-02, Q-OBR-03 para H3
    - [Bloqueada] P1 `004-constructora-obra/H3/T-DIS` — 004-constructora-obra/H3/T-DIS — Diseñar contrato y estados de H3
    - [Bloqueada] P1 `004-constructora-obra/H3/T-ACC` — 004-constructora-obra/H3/T-ACC — Casos de aceptación de US-OBR-003
    - [Bloqueada] P1 `004-constructora-obra/H3/T-IMP` — 004-constructora-obra/H3/T-IMP — Implementar H3 (NO INICIAR: bloqueada)
    - [Bloqueada] P2 `004-constructora-obra/H4/T-DEC` — 004-constructora-obra/H4/T-DEC — Decidir Q-OBR-03, Q-OBR-04 para H4
    - [Bloqueada] P2 `004-constructora-obra/H4/T-DIS` — 004-constructora-obra/H4/T-DIS — Diseñar contrato y estados de H4
    - [Bloqueada] P2 `004-constructora-obra/H4/T-ACC` — 004-constructora-obra/H4/T-ACC — Casos de aceptación de US-OBR-004
    - [Bloqueada] P2 `004-constructora-obra/H4/T-IMP` — 004-constructora-obra/H4/T-IMP — Implementar H4 (NO INICIAR: bloqueada)

## Ítems del tablero fuera del corpus (55, registrados el 2026-10-28)

Issues #151–#205 creados en el repo tras la carga inicial; todos Done en el tablero.
Detalle completo (título, número, URL y grupo) en `backlog/github-projects-extras.json`.
Evidencia del Done: pruebas locales de los incrementos en memoria, 181 OK el 2026-10-28.

- Grupo `hotel-incremento` (3): Incremento 1 — inventario local, estados de unidad y cuenta; Incremento 2 — estadía local: entrada, noche y salida; Bucle 3 — housekeeping: limpieza y preparación para check-in.
- Grupo `hotel-aceptacion` (31): casos AT-*/ADV-*/AC-US-HOT-* del hotel (issues #154–#185).
- Grupo `vertical-cafeteria` (18): casos AT-*/ADV-*/AC-US-CAF-* de cafetería (issues #186–#202).
- Grupo `vertical-incremento` (3): incremento 1 del núcleo (#203), inmobiliaria (#204) y constructora (#205).
