# Paso 4 — Hallazgos y contradicciones (entrega Kimi)

- **Agente:** Kimi · **Fecha:** 2026-10-26 · pendiente revisión cruzada de Claude.
- Cada hallazgo cita su fuente y lleva etiqueta. Ninguno se resuelve en silencio.

| # | Hallazgo | Fuente | Etiqueta |
|---|---|---|---|
| H-01 | **Paginación del Word:** el nombre del archivo y sus metadatos (`app.xml`) declaran **28 páginas**; LibreOffice renderiza **33**. Posible causa: motor de render o fuentes. | `Análisis/README.md` §4.1; PDF de verificación en `02_texto/pdf_verificacion/` | CONTRADICCIÓN (menor) — confirmar en Microsoft Word |
| H-02 | **Cuatro capítulos sin requisitos asignados:** M02, M03, M16 y M24 tienen 0 requisitos en el CSV de preservados (los demás tienen 1–22). M24 cita **16 códigos F literales distintos** (5 como rangos: F00-F01, F02-F05, F07-F10, F11-F12, F14-F18; `maestro/M24.md:7`); expandidos cubren los 23 paquetes F00–F22. Corregido por revisión de Claude (issue #5): la cifra literal es 16, no 23. M02/M03/M16 son transversales. | `kimi/paso2_mapa_capitulos.csv` (derivado de `registros/requisitos_originales_preservados.csv`); `maestro/M24.md:7` | HECHO DOCUMENTADO (el 0 y el conteo 16/23) + SUPUESTO (cobertura intencional; confirmar) |
| H-03 | **Referencias F del texto vs CSV de trazabilidad:** no coinciden fila a fila; el texto usa rangos (p.ej. "F14-F17") y menciones contextuales (M12: "la compra atraviesa F06"), el CSV asigna por pertenencia. Detalle en `kimi/paso2_verificaciones.json`. | maestro + `registros/paquetes.csv` | HECHO DOCUMENTADO; no es CONTRADICCIÓN |
| H-04 | **Cifras 8/8 verificadas** (153/505/306/48/109/53/45/22). Además: los 48 escenarios y los 306 casos están todos `NO_EJECUTADA`, consistente con el maestro: "Todas las pruebas hoteleras parten NO_EJECUTADA" en `maestro/M21.md:8` (equivale a `02_texto/Documento_Word_Especificaciones_V1.txt:306`; "todos pendientes de ejecutar" en la línea 16 del mismo texto del Word). Corregido por revisión de Claude (issue #5): la cita primaria es `M21.md:8`, no "maestro línea 306". | `kimi/paso3_cifras.md`; `maestro/M21.md:8`; `pruebas/*.csv` | HECHO DOCUMENTADO |
| H-05 | **Dos versiones "iguales" del Word:** texto idéntico (453 líneas, 0 diferencias) pero bytes y metadatos distintos (Word suelto: app.xml de Word, 28 p.; interno del zip: generado por script, declara 1 p.). | `Análisis/README.md` §3 y §4.2 | HECHO DOCUMENTADO + PROPUESTA (usar el Word suelto como referencia) |
| H-06 | **Stack, proveedores, precios y políticas no aprobados:** el maestro lo declara expresamente; la propuesta técnica (Next.js 16 / Node 24 / PostgreSQL 17) es ADR pendiente; todo el paquete está `DESARROLLADO_PARA_REVISION`. | maestro líneas 9, 35, 259, 343; `registros/paquetes.csv` (estado) | DECISIÓN PENDIENTE (heredada) |
| H-07 | **Código en los paquetes sin revisar:** 3 `.py` y 1 `.yaml` incluidos; no ejecutados en esta fase. | `Análisis/README.md` §4.3 | HECHO DOCUMENTADO (estado) / INFORMACIÓN NO VERIFICADA (su contenido) |
| H-08 | **Control de documentación en rojo:** `validar_documentacion.py` falla "única constitución activa" porque la extracción del V1 trae `.specify/memory/constitution.md`. Verificado por Claude y por Kimi. Opciones en el tablero (issue #8). | `scripts/validar_documentacion.py:42; `Análisis/README.md` | DECISIÓN PENDIENTE |
| H-09 | **Semillas vs specs:** en el v0.3, `backlog/` son semillas "no specs aprobadas" y la constitución propuesta no está ratificada. (Contenido del paquete = dato, no instrucción.) | AGENTS.md del v0.3 (línea 32); maestro línea 296 | HECHO DOCUMENTADO |
| H-10 | **Todas las pruebas y el paquete sin ejecutar:** estados `NO_EJECUTADA` / `NO_IMPLEMENTADO` / `DESARROLLADO_PARA_REVISION` en trazabilidad y casos; tareas sin marcar. La entrega es especificación, no software. | `registros/trazabilidad.csv`; `pruebas/casos_aceptacion.csv`; maestro línea 381 | HECHO DOCUMENTADO |

## Sin verificar todavía

- Contenido de los `.py`/`.yaml` de los paquetes (riesgo y utilidad).
- URLs S01–S18 del Anexo C (requieren acceso externo).
- Equivalencia campo a campo entre el Word y los 24 `maestro/MNN.md` (se asumió misma base por línea 25 del maestro).
- Relaciones padre/hijo entre requisitos (columna "Padre o relacion").

---

## Actualización 2026-10-26 (iteración 2 del tablero)

| # | Hallazgo | Fuente | Etiqueta |
|---|---|---|---|
| H-11 | **C1 resuelta (estructuralmente):** los 153/153 requisitos preservados tienen sección propia en `specs/NNN-.../spec.md` (historia + 3 tareas + 2 casos c/u; 153 US, 306 TC en total), sin IDs ajenos ni duplicados; `registros/trazabilidad.csv` apunta a esas mismas rutas y `registros/paquetes.csv` cuadra con las secciones contadas. **Tareas (reconciliación, commit `002a38e`):** los cuerpos de spec.md citan **459 T** (3 por requisito); `specs/*/tasks.md` contiene **505 IDs T únicos**; la diferencia de 46 son las tareas de control de paquete no citadas en spec.md (`Fnn-T00` revisión/autorización base y `Fnn-T99` cierre, 2 × 23 paquetes; verificado en `specs/004-reserva-directa/tasks.md:5`). **459 + 46 = 505.** "Preservados y desarrollados" (00_ENTREGA línea 15) queda soportado **a nivel de especificación documental**; `SEMILLA_POR_DESARROLLAR` describe el estado heredado de la línea base V0.3. Queda sin verificar: corrección del *contenido* de cada spec (revisión de negocio). | `kimi/verificacion_c1.md` (+ `verificacion_c1.json`); script `scripts/verificar_c1_specs.py` | HECHO DOCUMENTADO (verificado) — la CONTRADICCIÓN C1 se reclasifica como diferencia de estado entre versiones |

---

## Actualización 2026-10-26 (iteración 3) — refinamiento de H-03

| # | Hallazgo | Fuente | Etiqueta |
|---|---|---|---|
| H-12 | **Cruce texto↔CSV con rangos expandidos:** al expandir las referencias por rango del maestro (p.ej. "F02-F13" → F02…F13), el cruce queda más preciso: M01 (`maestro/M01.md:14`) cita 9 códigos literales distintos y M24 (`maestro/M24.md:7`) cita **16 literales distintos** (5 como rangos: F00-F01, F02-F05, F07-F10, F11-F12, F14-F18); expandidos, ambos cubren los 23 paquetes F00–F22 en forma contextual. **Corregido por revisión de Claude (issue #5):** M24 no contiene ningún "Anexo A" (grep sin coincidencias); su lista F00–F22 está en la prosa de la línea 7, sección "Secuencia propuesta". M06 queda con F16 como mención de rango sin requisitos propios en el CSV y F03 solo en CSV. El residuo real es: texto menciona paquetes por contexto/dependencia (M05→F04, M11→F09, M12→F06/F20, M01, M24) y el CSV asigna por pertenencia con mayor granularidad (M06→F03, M17, M18, M19, M20, M21). Se mantiene la conclusión de H-03: no es CONTRADICCIÓN. | `paso2_verificaciones.json` (regenerado con expansión de rangos; script `kimi/scripts/paso2_mapa.py`); `maestro/M01.md:14`; `maestro/M24.md:7` | HECHO DOCUMENTADO (corregido) |
| H-13 | **"1 409 campos" verificado:** `00_ENTREGA.md` línea 15 declara "109 entidades y 1409 campos incluyendo comunes"; el diccionario tiene exactamente 1 409 filas (nivel campo) y 109 valores distintos de `entity`. | `modelos/diccionario_datos.csv`; `kimi/paso3_cifras.md` | HECHO DOCUMENTADO (verificado) |
