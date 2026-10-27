# Paso 3 — Recuento de cifras declaradas vs contadas (entrega Kimi)

- **Agente:** Kimi · **Fecha:** 2026-10-26 · pendiente revisión cruzada de Claude.

| Cifra declarada | Contada | Método de conteo | Estado | Etiqueta |
|---|---|---|---|---|
| 153 requisitos | 153 | Filas de `registros/requisitos_originales_preservados.csv` (153); `registros/trazabilidad.csv` (mismos 153 IDs, dif 0); suma de la columna requisitos de `registros/paquetes.csv` (=153); `matrices/01_requisitos_base.csv` del SDD v0.3 (=153) | Coincide | HECHO DOCUMENTADO (verificado) |
| 505 tareas | 505 | Filas de `registros/tareas.csv` | Coincide | HECHO DOCUMENTADO (verificado) |
| 306 casos | 306 | Filas de `pruebas/casos_aceptacion.csv` (153 POSITIVA + 153 NEGATIVA; exactamente 2 por cada uno de los 153 requisitos; min=max=2) | Coincide | HECHO DOCUMENTADO (verificado) |
| 48 escenarios críticos | 48 | Filas de `pruebas/escenarios_criticos.csv` | Coincide | HECHO DOCUMENTADO (verificado) |
| 109 entidades | 109 | Valores distintos de la columna `entity` en `modelos/diccionario_datos.csv` (1 409 filas = campos, no entidades) | Coincide | HECHO DOCUMENTADO (verificado) |
| 53 pantallas | 53 | Filas de `ux/pantallas.csv` | Coincide | HECHO DOCUMENTADO (verificado) |
| 45 decisiones | 45 | Filas de `registros/decisiones.csv`; consistente con el maestro ("se conserva D01-D44 y se agrega D45", línea 88) | Coincide | HECHO DOCUMENTADO (verificado) |
| 22 acoplamientos clasificados | 22 | Filas de `registros/acoplamientos_resueltos.csv` | Coincide | HECHO DOCUMENTADO (verificado) |
| 1 409 campos (00_ENTREGA.md línea 15) | 1 409 | Filas de `modelos/diccionario_datos.csv` (nivel campo; las 109 entidades son valores distintos de su columna `entity`) | Coincide | HECHO DOCUMENTADO (verificado) |

**Resultado: las 8 cifras declaradas en el maestro (líneas 13–18) coinciden con el conteo sobre los CSV extraídos; además, el "1 409 campos" declarado en `00_ENTREGA.md` (línea 15) coincide con las filas del diccionario.**

## Datos complementarios del recuento

- Prioridades: P0=118 · P1=29 · P2=6.
- Niveles de caso: 292 `FUTURA_PRUEBA_DE_ACEPTACION` + 14 `DOCUMENTAL_Y_PIPELINE`.
- Las 8 cifras se verificaron con `tail -n +2` (restar cabecera) y, para entidades, con valores distintos de la columna clave; no se ejecutó código de los paquetes.

## Sin verificar todavía (para iteración)

- Número de tareas por paquete frente a `specs/NNN-.../tasks.md` (si existe).
- Escenarios críticos por funcionalidad vs el maestro.
- `pruebas/gherkin/` (cantidad de features).
- URLs S01–S18 (Anexo C) — requieren acceso externo; no verificadas.
- Paginación 28 vs 33 del Word (CONTRADICCIÓN MENOR viva).
