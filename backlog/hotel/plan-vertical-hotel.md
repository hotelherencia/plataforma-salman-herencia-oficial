# Plan de operación — vertical hotel (002-hotel-reservas-concierge)

Fecha: 2026-10-27. Estado: **BLOQUEADO** por decisiones del propietario. Este plan ordena el trabajo y pesa el esfuerzo; no inicia ninguna tarea de implementación.

Archivos relacionados:
- `respuestas-propuestas.md`: propuestas con evidencia para las preguntas Q. No ratificadas.
- `github-projects-hotel.json`: 33 ítems del hotel. El esfuerzo va solo en tareas hoja.
- `../decisiones-hotel.md`: hoja de decisiones del propietario.

---

## 1. Escala de esfuerzo

- Puntos en la escala 0, 1, 2, 3, 5, 8, 13. Solo en tareas hoja: épica e historias no llevan campo `esfuerzo`; su total es la suma de sus hojas.
- Las tareas de decisión y de gate miden análisis y coordinación, no código. Sus puntos cuentan como estimación de esfuerzo. El tiempo de espera del propietario no se mide como duración.
- Las tareas hechas valen 0.
- Una tarea de más de 8 puntos debe desglosarse antes de pasar a **Lista**. Aplica a `H1/T-IMP` y `H3/T-IMP` (13 cada una). **No se desglosan todavía**: no hay autorización para partir el alcance.
- Los puntos son un juicio de orden de magnitud, no una medición ni un compromiso de entrega.

---

## 2. Árbol: épica, historias y tareas

Total de la épica: **116 puntos** = 54 de gates abiertos + 28 de preparación de historias + 34 de implementación bloqueada. Las tareas hechas suman 0 y están incluidas en los 54 sin aportar puntos.

```
Épica 002 — Hotel: reservas y concierge                         BLOQUEADA
│
├── Gates de la épica (54 pts)
│   ├── T001  Inventariar fuente y separar alcance               0  HECHA
│   ├── T002  Modelo conceptual, amenazas y catálogo             0  HECHA
│   ├── T003  Resolver Q-HOT-01, Q-HOT-02, Q-HOT-03              3  BACKLOG
│   ├── T004  Ratificar alternativas, constitución y permisos    3  BLOQUEADA
│   ├── T005  Contratos técnicos (ejemplos, errores, idempot.)   5  BLOQUEADA
│   ├── T006  Casos de prueba concretos (ADV-001..003, carga)    5  BLOQUEADA
│   ├── T007  Controles documentales y análisis Spec Kit         2  BLOQUEADA
│   ├── T101  Comparar historias heredadas y fuentes             0  HECHA
│   ├── T102  Validar reglas FR-016/017 con usuarios             3  BLOQUEADA
│   ├── T103  Precisar casos AC-US-HOT con muestras              5  BLOQUEADA
│   ├── T104  Demo autorizada (REA, Q-REA-01/02)                 5  BLOQUEADA
│   ├── T105  Análisis Spec Kit oficial (Q-TOOL-01)              2  BLOQUEADA
│   ├── T201  Reconstruir RF-HOT-01..04                          0  HECHA
│   ├── T202  Ratificar estados y permisos FR-018..020           5  BLOQUEADA
│   ├── T203  Invariantes y contratos (timeout, repetición)      8  BLOQUEADA
│   ├── T204  Conducta en demo/entorno propio (REA)              5  BLOQUEADA
│   └── T205  Costos y latencias por etapa                       3  BLOQUEADA
│
├── Historia H1 — Reservar y pagar desde la web del hotel        P1  BLOQUEADA
│   ├── T-DEC  Decidir Q-HOT-01/02/03 para H1 (y Q-HOT-04 vía T202)   2
│   ├── T-DIS  Diseñar contrato y estados de H1                        5
│   ├── T-ACC  Casos de aceptación de US-HOT-001                       3
│   └── T-IMP  Implementar H1 (desglosar antes de Lista: 13 pts)      13
│
├── Historia H2 — Operar la estadía (check-in, pedido, housekeeping)  P2  BLOQUEADA
│   ├── T-DEC  Decidir Q-HOT-01, Q-HOT-03 para H2 (y Q-HOT-05 vía T202)  2
│   ├── T-DIS  Diseñar contrato y estados de H2                        3
│   ├── T-ACC  Casos de aceptación de US-HOT-002                       3
│   └── T-IMP  Implementar H2                                          8
│
└── Historia H3 — Concierge agéntico por WhatsApp                     P3  BLOQUEADA
    ├── T-DEC  Decidir Q-HOT-03, Q-HOT-04 para H3 (Q-HOT-04 vía T202)  2
    ├── T-DIS  Diseñar contrato y estados de H3                        5
    ├── T-ACC  Casos de aceptación de US-HOT-003                       3
    └── T-IMP  Implementar H3 (desglosar antes de Lista: 13 pts)      13
```

Suma por historia (derivada de las hojas): H1 = 23, H2 = 16, H3 = 23.

---

## 3. Dependencias de la vertical

Cada `T-IMP` depende de su `T-ACC`, de `002/T007` y de `000-core/T007`. Además, `H1/T-IMP`, `H2/T-IMP` y `H3/T-IMP` dependen de `002/T103`, `002/T202` y `002/T203`: son las tareas que `tasks.md` marca como previas a implementar. Cada issue lista exactamente estas dependencias en su cuerpo.

T202 no está cerrada. Cuando se cierre, su salida ratifica solo Q-HOT-04 (FR-018), Q-HOT-05 (FR-019) y Q-HOT-06 (FR-020). Q-HOT-01, Q-HOT-02 y Q-HOT-03 las cierra `002/T003`. Q-CORE-01, Q-CORE-02 y Q-CORE-03 las cierra `000-core/T003`. Q-GOV-01 la cierra `000-core/T004`. Q-CORE-04, Q-REA-01, Q-REA-02, Q-REA-03 y Q-TOOL-01 no tienen ítem.

| Pregunta | Cierra en | Bloquea |
|---|---|---|
| Q-HOT-04 (cambios, penalidad, devolución) | `002/T202` (FR-018) | `H1/T-DEC`, `H2/T-DEC`, `H3/T-DEC`, `H1/T-IMP`, `H2/T-IMP`, `H3/T-IMP`, `T203` |
| Q-HOT-05 (extras, cuenta, destino) | `002/T202` (FR-019) | `H1/T-DEC`, `H2/T-DEC`, `H3/T-DEC`, `H1/T-IMP`, `H2/T-IMP`, `H3/T-IMP`, `T203` |
| Q-HOT-06 (acuse por canal, conflictos) | `002/T202` (FR-020) | `H1/T-DEC`, `H2/T-DEC`, `H3/T-DEC`, `H1/T-IMP`, `H2/T-IMP`, `H3/T-IMP`, `T203` |
| Q-CORE-04 (efectos externos, mensajes y cargos) | **Sin ítem propio: DECISIÓN PENDIENTE** | Afecta a `H3/T-IMP` (indicado en su cuerpo; no está en `depende_de`) |

Q-CORE-01, Q-CORE-02 y Q-CORE-03 viven en `000-core/T003`, no en el `T003` del hotel. El `T003` del hotel resuelve solo Q-HOT-01, Q-HOT-02 y Q-HOT-03.

La columna «Bloquea» de Q-HOT-04, Q-HOT-05 y Q-HOT-06 lista los siete ids que T202 bloquea hoy. H2 espera el paquete entero porque las tres preguntas comparten T202: no puede cerrar H2/T-DEC con una sola de ellas.

---

## 4. Camino crítico (medido sobre el grafo de dependencias)

Duraciones en puntos, con las dependencias internas del hotel. Las externas no suman tiempo y se excluyen.

| Nodo | Termina en (puntos acumulados) |
|---|---:|
| `002/T004` | 6 |
| `002/T102` | 9 |
| `002/T005` | 11 |
| `002/T006` | 16 |
| `002/T103` | 16 |
| `002/H1/T-DEC` | 16 |
| `002/T007` | 18 |
| `002/T202` | 14 |
| `002/T203` | 22 |
| `002/H1/T-DIS` | 21 |
| `002/H1/T-ACC` | 24 |

**Resultados:**

- **Inicio de `H1/T-IMP`: 24 puntos** (nodo limitante `H1/T-ACC`, EF 24). Es el máximo de sus prerrequisitos. El cuello de botella medido es la rama de Q-HOT-04: `T003 → T004 → T102 → T202 → H1/T-DEC → H1/T-DIS → H1/T-ACC`.
- **Inicio de `H2/T-IMP`: 22 puntos** (nodo limitante `H2/T-ACC`, EF 22): `T003 → T004 → T102 → T202 → H2/T-DEC → H2/T-DIS → H2/T-ACC`.
- **Inicio de `H3/T-IMP`: 24 puntos** (nodo limitante `H3/T-ACC`, EF 24): `T003 → T004 → T102 → T202 → H3/T-DEC → H3/T-DIS → H3/T-ACC`.
- La cadena de refinamiento `T003 → T004 → T102 → T202 → T203` suma **22**. Es más corta que la rama de Q-HOT-04 (24), así que no es el cuello de botella, aunque sí sea el camino más largo de refinamiento.
- La rama de gobierno hasta `T007` suma **18**. Sola, no determina el inicio: `H1/T-IMP` espera a la rama de Q-HOT-04.
- **Suma serial de los prerrequisitos internos** (si nada corre en paralelo): `H1/T-IMP` 49 puntos (14 nodos), `H2/T-IMP` 47 (14), `H3/T-IMP` 49 (14).
- Los puntos de cada `T-IMP` (13, 8 y 13) no están incluidos en estos valores.

Se excluyen del número `000-core/T007` (y, transitivamente, `000-core/T003` a `T006`) y el tiempo de espera de las decisiones del propietario. Los puntos de `T003` y de los `T-DEC` sí cuentan como esfuerzo estimado.

**Nota sobre cifras anteriores:** versiones previas de este plan decían 18, 22, 28 y 31. Quedan superadas por el grafo actual: 18 era la rama de gobierno sola, 22 era la cadena de refinamiento sola, y 31 sumaba un tramo que no es el camino crítico.

---

## 5. Olas de ejecución

| Ola | Contenido | Puntos | Quién actúa |
|---|---|---:|---|
| 0. Decisiones | `002/T003` (Q-HOT-01/02/03). En `000-core`: `T003` (Q-CORE-01/02/03) y `T004` (constitución y Q-GOV-01) | 3 + gates externos | Propietario y responsables de negocio |
| 1. Gobierno y contratos | `T004` → `T005` → `T006` → `T007` | 3 + 5 + 5 + 2 = 15 | Equipo técnico, con el propietario para permisos |
| 2. Refinamiento | `T102`, `T103`, `T104`, `T105`, `T202`, `T203`, `T204`, `T205` | 36 | Equipo técnico; `T104` y `T204` dependen de REA |
| 3. Historias | H1, H2, H3: cada una `T-DEC` → `T-DIS` → `T-ACC` → `T-IMP` | H1 23, H2 16, H3 23 | Equipo técnico, por historia |

**Las olas agrupan; no se suman en serie.** El inicio de cada tarea lo da el grafo de dependencias de la sección 4. `H1/T-DEC` puede empezar cuando termina `T202`, sin esperar a `T104`, `T204` ni `T205`.

Notas sobre pares de tareas con trabajo parecido, sin fusionarlas:
- `T104` (demo REA, Q-REA-01/02) y `T204` (conducta en demo, Q-REA-01/02/03): mismo tipo de prueba.
- `T007` y `T105`: análisis de consistencia de Spec Kit. El análisis manual de `speckit-analyze/consolidado.md` no cierra ninguno de los dos.

Orden recomendado dentro de la ola 3: H1 primero, porque es P1 y cubre FR-001..005. H2 comparte con H1 el cobro y la cuenta (FR-004 y FR-009). H3 comparte FR-016..020 con H1 y H2 y depende de Q-CORE-04 y Q-HOT-03.

---

## 6. Tensión de alcance: cafetería en H2

**CONTRADICCIÓN, sin resolver aquí.** La spec dice que el hotel básico no necesita la cafetería en producción (`specs/002-hotel-reservas-concierge/spec.md` línea 8). Pero el escenario de aceptación de H2 (línea 36) y la historia (línea 30) usan el módulo de pedidos de la cafetería para el servicio a la habitación, y FR-007 lo exige.

Por eso, `H2/T-IMP` (8 puntos) se lee en dos partes, sin crear IDs nuevos:
- **Operación del hotel:** check-in digital, housekeeping y cuenta de estadía. No depende de la cafetería.
- **Pedido a habitación (FR-007):** depende de `001-cafeteria-mesas-pos`, y no entra en el camino crítico del hotel básico.

La decisión de si el pedido a habitación va en V1 queda como DECISIÓN PENDIENTE del propietario.

---

## 7. Qué debe ocurrir antes de pasar a Lista

Para cada tarea de hotel, Lista exige:

1. Dependencias cerradas, incluidas las de `000-core`.
2. Decisiones registradas con fecha y evidencia en su `T003` o en `000-core/T003`.
3. Esfuerzo de 8 puntos o menos, o desglose registrado. Aplica a `H1/T-IMP` y `H3/T-IMP`.
4. Salida verificable definida en `tasks.md`.

Adicionalmente:
- `H1/T-IMP`, `H2/T-IMP` y `H3/T-IMP`: no antes de `T103`, `T202`, `T203`, su `T-ACC`, `002/T007` y `000-core/T007`.
- `H3/T-IMP`: además, Q-CORE-04 cerrada (DECISIÓN PENDIENTE) y la política de autonomía (Q-HOT-03).

---

## 8. Integración con GitHub Projects

Mapeo propuesto por ítem (reflejado en `github-projects-hotel.json`):

| Campo | Valor |
|---|---|
| Título | `[Épica] <id> — <título>`, `[Historia] <id> — <título>` o `[Tarea] <id> — <título>` |
| Tipo | Épica, Historia o Tarea |
| Estado | Backlog, Bloqueada, Lista, En curso, En revisión, Hecha |
| Prioridad | P1, P2, P3 |
| Vertical | hotel |
| Esfuerzo | Número en {0, 1, 2, 3, 5, 8, 13}, solo en tareas. **Campo nuevo: hay que crearlo en el Project.** |
| Padre | Épica o Historia |
| Depende de | Lista de ids del backlog |

**Estado de la integración:** no se han creado issues ni se ha tocado el Project. Requiere autorización explícita, porque es visible para terceros. Revisión con `gh` el 2026-10-27: `hotelherencia` es una cuenta de usuario **sin repositorios** —`hotelherencia/plataforma-salman-herencia-oficial` no existe aún— y el propietario confirmó el 2026-10-27 como destino el Project **n.º 2 «Project Plataforma Hotel Herencia»** (`https://github.com/users/hotelherencia/projects/2`), público, 0 ítems, Status por defecto (Todo / In Progress / Done). Antes de ejecutar la carga falta crear el repositorio (o confirmar su nombre definitivo) y crear en el Project el campo numérico `Esfuerzo`; los demás campos del mapeo de esta tabla (Tipo, Prioridad, Vertical, Padre, Depende de) tampoco existen aún. El archivo de carga definido es `backlog/github-projects.json` (150 ítems, esfuerzo solo en tareas hoja, estado tal como está).

---

## 9. Lo que este plan no hace

- No responde ninguna pregunta Q-*. Las propuestas están en `respuestas-propuestas.md` y no están ratificadas.
- No cambia el estado de ningún ítem a Lista ni inicia implementación.
- No modifica la spec, `tasks.md`, la constitución ni los ADR.
- No desglosa `H1/T-IMP` ni `H3/T-IMP`.
- No crea issues ni toca el Project.
