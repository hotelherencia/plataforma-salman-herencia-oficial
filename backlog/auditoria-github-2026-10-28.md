# Auditoría de issues y tablero en GitHub — 2026-10-28

Fuente: lectura de `hotelherencia/plataforma-salman-herencia-oficial` (213 issues,
124 cerrados y 89 abiertos) y del Project n.º 2 (213 ítems). Solo lectura: no se
cerró, reabrió, renombró ni borró nada. Cada acción de la sección 4 requiere
aprobación del propietario antes de ejecutarse.

Clase de evidencia de este informe: HECHO DE GITHUB (conteos y estados) y
HECHO DE REPOSITORIO (rutas existentes). Las propuestas están marcadas como tales.

## 1. Estado real frente al tablero

| Situación | Issues | Problema |
|---|---|---|
| Cerrado en GitHub, columna «Todo» en el tablero | 44 | Contradicción: cerrado sin entregable documentado |
| Cerrado en GitHub, columna «Decisión humana» | 3 | Contradicción: `T003` de 001, 003 y 004 sin resolución registrada |
| Abierto, columna «Todo» | 76 | Coherente, pero sin propietario ni criterio de salida claro |
| Abierto, columna «Decisión humana» | 13 | Coherente; son las decisiones reales del propietario |
| Cerrado, columna «Done» | 77 | 22 tareas de documentación (M) y 55 extras de código (K) |

- El tablero es **público** (`public: true`). Contiene borradores de decisiones y
  datos de negocio. Hacerlo privado es una decisión del propietario.
- El Project n.º 1 («untitled») está vacío (0 ítems). Candidato a eliminar.
- Ningún issue tiene etiquetas. Los 55 extras no tienen tipo, prioridad ni vertical en el tablero.

## 2. Rutas antiguas y referencias rotas

- **155 de 213 issues** citan `proyecto/specs/...`. La estructura plana actual
  (commit `f958709`) usa `specs/...`; los archivos existen sin el prefijo. Corrección mecánica.
- **27 issues** citan `tests/...` sin ruta completa. Los archivos existen en
  `verticales/hotel/incremento1/tests/` y en otras verticales; hay que asignar la ruta por caso.
- **`docs/investigacion-competitiva/decisiones-pendientes.md` y
  `docs/arquitectura/decisiones-pendientes.md` no existen.** Los citan 12 archivos del
  repositorio (specs de 000, 002, 003 y 004, y el plan del hotel) y varios issues.
  Es el único documento que reunía las preguntas Q-* en un solo lugar.
- Las respuestas Q-HOT-01..03 y Q-CORE-01..03 sí existen en
  `backlog/hotel/resolucion-dudas-2026-10-27.md`. Los issues `T-DEC` y `T003` de 000 y 002
  siguen abiertos aunque esas respuestas ya estén escritas.
- `docs/arquitectura/seguridad.md` y `docs/arquitectura/dependencias.md` tampoco existen,
  y las citan 12 archivos de `specs/` y `backlog/`. Mismo tratamiento que el punto anterior.

## 3. Clasificación de los 213 issues

Cada grupo indica sus números y la acción propuesta. Ningún grupo se ha ejecutado.

| Grupo | Nº | Issues | Qué son | Acción propuesta |
|---|---|---|---|---|
| A. Decisión humana (`T-DEC`) | 13 | 22, 26, 30, 50, 54, 58, 83, 87, 91, 115, 119, 143, 147 | Preguntas Q-* sin respuesta de negocio | **Decidir.** Consolidar en 5 issues, uno por feature, con la lista de preguntas. Para 000 y 002 proponer cerrar con la respuesta ya registrada en `resolucion-dudas`, si el propietario la ratifica |
| B. Validación humana | 16 | 13, 15, 20, 46, 48, 74, 76, 81, 106, 108, 113, 134, 136, 141, 209, 210 | `T102` (usuarios), `T104`/`T204` (demo REA), `T205` (costos y latencias) | **Decidir si hay usuarios o demo disponibles.** Si no, consolidar en un issue «validación pendiente» o cerrar como fuera de esta fase |
| C. Ratificación | 11 | 8, 18, 41, 69, 79, 101, 111, 129, 139, 207, 208 | `T004` (constitución, Q-GOV-01), `T202`/`T203` (reglas FR-*) | **Decidir.** Consolidar en un issue de ratificación de constitución y otro de reglas. Q-GOV-01 no tiene propuesta: decisión del propietario |
| D. Implementación bloqueada (`T-IMP`) | 13 | 25, 29, 33, 53, 57, 61, 86, 90, 94, 118, 122, 146, 150 | «NO INICIAR: bloqueada», sin contenido propio | **Cerrar como duplicados** de la historia correspondiente, con motivo «bloqueada por T-DEC» |
| E. Pruebas y controles | 10 | 10, 11, 43, 44, 71, 72, 103, 104, 131, 132 | `T006` (acceptance → pruebas), `T007` (controles documentales) | `T006`: **completar** en 000 o 002 si el propietario lo pide (el código ya cubre parte). `T007`: **cerrar**, porque el validador no arranca por un archivo que no debe inventarse (`docs/auditorias/originales-sha256.json`) |
| F. No aplica | 5 | 16, 49, 77, 109, 137 | `T105`: análisis oficial de Spec Kit | **Cerrar como no aplicable.** `AGENTS.md` prohíbe llamar a ese control análisis oficial |
| G. Historias del Manual | 3 | 211, 212, 213 | HU-HOT-01..03 | **Mantener.** Ya tienen implementación en memoria (`backlog/hotel/evidencia-hu-hot-01-03.md`). Pedir ratificación; sin marcar Hecha |
| H. Historias de spec | 13 | 2, 3, 4, 35, 36, 37, 63, 64, 65, 96, 97, 124, 125 | H1–H4 de 000, 001, 002, 003, 004 | **Mantener** como hijas de la épica; corregir rutas |
| I. Épicas | 5 | 1, 34, 62, 95, 123 | Una por feature | **Mantener**; corregir rutas |
| J. Cerrado, tablero «Todo» | 44 | 9, 14, 19, 21, 23, 24, 27, 28, 31, 32, 42, 47, 51, 52, 55, 56, 59, 60, 70, 75, 80, 82, 84, 85, 88, 89, 92, 93, 102, 107, 112, 114, 116, 117, 120, 121, 130, 135, 140, 142, 144, 145, 148, 149 | `T-ACC`, `T-DIS`, `T003`…`T205` | **Decidir el estado.** 8 de ellos (52, 56, 60, 85, 89, 93, 117, 145) están cubiertos por los extras de código (K). 36 no tienen trabajo: **reabrir** o **cerrar como no hecho** |
| K. Extras de código cerrados | 55 | 151–205 | Incrementos locales con pruebas; cuerpo con «PROPUESTA TÉCNICA» | **Mantener cerrados** como evidencia. Renombrar al formato común; completar tipo, prioridad y vertical en el tablero |
| L. Cerrado, tablero «Decisión humana» | 3 | 40, 100, 128 | `T003` de 001, 003 y 004 | **Reabrir.** No hay resolución registrada (`resolucion-dudas` las marca como bloqueadas) |
| M. Hecha documentada | 22 | 5, 6, 7, 12, 17, 38, 39, 45, 66, 67, 68, 73, 78, 98, 99, 105, 110, 126, 127, 133, 138, 206 | Tareas de documentación con evidencia | **Mantener cerrados.** Sin cambios |

Total: 13 + 16 + 11 + 13 + 10 + 5 + 3 + 13 + 5 + 44 + 55 + 3 + 22 = **213**.

## 4. Preguntas que solo puede responder el propietario

1. **Resoluciones de base (Q-HOT-01..03, Q-CORE-01..03):** ¿se ratifican tal como están en
   `backlog/hotel/resolucion-dudas-2026-10-27.md`? Si se ratifican, se cierran los `T003` de 000 y 002.
2. **Preguntas de 001, 003 y 004 (Q-CAF-01..03, Q-INM-01..04, Q-OBR-01..03):** ¿se responden
   una a una o se delegan con valores por defecto propuestos?
3. **Q-HOT-04, Q-HOT-05, Q-HOT-06 (`002/T202`):** cambios, penalidad, devolución, extras y
   acuse por canal. Son decisiones de negocio; no hay propuesta.
4. **Q-GOV-01 (ratificar constitución 1.1.0):** sigue sin propuesta. ¿Se ratifica, se corrige o se deja pendiente?
5. **Q-CORE-04 y Q-REA-01..03, Q-TOOL-01:** no tienen issue propio. ¿Se crean issues o quedan fuera?
6. **Validaciones con usuarios y demos REA (grupo B):** ¿hay personas o entornos disponibles
   en el plazo? Si no, ¿se cierran o se agrupan?
7. **Implementaciones `T-IMP` bloqueadas (grupo D):** ¿se cierran como duplicados de la historia?
8. **Tareas 36 cerradas sin trabajo (grupo J):** ¿reabrir o cerrar como no hecho?
9. **Las 8 cubiertas por extras (grupo J):** ¿se marcan Done con el enlace al extra como evidencia?
10. **Visibilidad del tablero:** ¿privado o público?
11. **Project n.º 1 vacío:** ¿eliminar?
12. **HU-HOT-01..03 (grupo G):** ¿se ratifican como propuestas del Manual?

## 5. Acciones propuestas que no se han ejecutado

Esperan tu aprobación. Son escrituras en GitHub o borrados.

- Corregir `proyecto/specs/` a `specs/` en 155 cuerpos (mecánico, sin cambiar estado).
- Asignar la ruta completa a las 27 referencias `tests/` (requiere revisar caso por caso).
- Reemplazar la referencia a `decisiones-pendientes.md` por la ubicación real o por
  «DECISIÓN PENDIENTE: documento no existe».
- Crear etiquetas: `decision-propietario`, `validacion-humana`, `bloqueada`,
  `evidencia`, `no-aplica`, `ruta-corregida`.
- Ejecutar los cierres y reaperturas de los grupos D, F, J, L y E (`T007`).
- Consolidar los grupos A, B y C en 5 + 2 + 2 issues nuevos y cerrar los originales
  con referencia al consolidado.
- Cambiar la visibilidad del tablero y eliminar el Project n.º 1, si lo apruebas.

Los borrados de issues no tienen vuelta atrás en GitHub. Por eso no se proponen
borrados de issues; solo cierres con motivo.

## 6. Corrección aplicada en GitHub (2026-10-28, después de la auditoría)

Solo se corrigió lo que no depende de una decisión del propietario:

- **Rutas:** 161 cuerpos corregidos. `proyecto/specs/` pasó a `specs/`; las 27 referencias
  `tests/` tienen ruta completa; las menciones a documentos inexistentes quedan anotadas
  con «documento inexistente en el repo». Ningún cuerpo conserva `proyecto/`.
- **Etiquetas creadas y asignadas:** `decision-propietario` (13), `validacion-humana` (16),
  `bloqueada` (13), `no-aplica` (5), `evidencia` (55) y `ruta-corregida` (161).
- **Reabiertos:** 40, 100 y 128 (`T003` de 001, 003 y 004). El tablero los marca como
  decisión humana y no hay resolución registrada.
- **No se cerró, borró ni consolidó ningún issue.** Tampoco se tocó la visibilidad del tablero.

### Cambios que no hizo esta sesión

- **76 issues pasaron de abiertos a cerrados** entre las 13:53 y las 13:56 del 2026-10-28,
  con actor `hotelherencia`. No los cerró ningún comando de esta sesión; no puedo atribuirlos.
  Afectan a los grupos B (16), D (13), H (13), C (11), E (10), F (5), I (5) y G (3).
  Pendiente: confirmar si el propietario los cerró a propósito. No se han revertido.
- **42 issues nuevos (214 a 255)** creados después de la auditoría, todos abiertos. Son un
  plan «V1» con despliegue en Railway y Vercel (T-DESP, incluido un «Push de la rama de
  trabajo»), FastAPI, Next.js y PostgreSQL. Contradice `AGENTS.md`, que prohíbe desplegar y
  elegir stack sin orden aprobada. No se han tocado.
- Un servidor `plataforma.servidor --puerto 8787`, iniciado a las 10:56 desde este repositorio,
  sigue en ejecución. No lo inicié en esta sesión; el mío (8765) se detuvo.
