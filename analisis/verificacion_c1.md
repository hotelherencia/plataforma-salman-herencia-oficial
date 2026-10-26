# Verificación C1 — ¿"desarrollados"? specs/*/spec.md vs los 153 preservados

- **Agente:** Kimi · **Fecha:** 2026-10-26 · Iteración 2 del tablero (issue #3).
- **Pregunta:** el CSV marca los 153 requisitos como `SEMILLA_POR_DESARROLLAR`, pero `00_ENTREGA.md` (línea 15) dice "preservados **y desarrollados**". ¿Dónde está el desarrollo?
- **Método:** extraer los `### <ID> -` de las 23 `specs/*/spec.md` y cotejarlos con los 153 IDs preservados y con `registros/trazabilidad.csv`. Solo lectura.

## Resultado

| Chequeo | Resultado | Etiqueta |
|---|---|---|
| IDs preservados con sección propia en alguna `spec.md` | 153 / 153 | HECHO DOCUMENTADO |
| IDs preservados sin sección en specs | 0 | — |
| IDs en specs que no están entre los 153 | 0 | — |
| IDs con sección en más de una spec | 0 | — |
| Rutas de trazabilidad inexistentes | 0 | — |
| Sección en spec distinto al que indica trazabilidad.csv | 0 | — |
| paquetes.csv (#req) vs secciones contadas en spec.md | 0 diferencias | HECHO DOCUMENTADO |
| IDs locales en specs: historias US | 153 · casos TC | 306 | HECHO DOCUMENTADO |
| IDs T citados en los cuerpos de spec.md | 459 (3 por requisito) | HECHO DOCUMENTADO |
| IDs T únicos en `specs/*/tasks.md` | 505 — reconciliación: 459 citados en spec.md + 46 de paquete (`Fnn-T00` base y `Fnn-T99` cierre, 2×23) = 505 | HECHO DOCUMENTADO |


## Conclusión (etiquetada)

**Los 153/153 requisitos preservados tienen su especificación desarrollada** en `specs/NNN-.../spec.md` (sección propia con historia, tareas y casos), y las rutas de `registros/trazabilidad.csv` coinciden. La afirmación "preservados y desarrollados" (00_ENTREGA línea 15) queda **soportada a nivel de especificación documental**. La columna `SEMILLA_POR_DESARROLLAR` describe el estado heredado de la línea base V0.3, no el del V1.0 — la CONTRADICCIÓN C1 se reclasifica como **diferencia de estado entre versiones**, no como desarrollo faltante. Etiqueta: HECHO DOCUMENTADO (verificado) + HIPÓTESIS confirmada. Queda sin verificar: que el *contenido* de cada spec sea correcto (eso es revisión de negocio, fuera de esta verificación estructural).

Fuentes: `fuentes/requisitos_baseline_V0_3.csv` = `registros/requisitos_originales_preservados.csv` (IDs idénticos); `registros/trazabilidad.csv`; `specs/001-.../spec.md … specs/023-.../spec.md`; `registros/paquetes.csv`.