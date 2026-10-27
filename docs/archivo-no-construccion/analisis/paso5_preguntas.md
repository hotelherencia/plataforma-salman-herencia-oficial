# Paso 5 — Preguntas para el propietario (Ricardo Salman)

- **Agente:** Kimi · **Fecha:** 2026-10-26.
- Solo DECISIONES PENDIENTES que bloquean avance, redactadas para responder sí/no o elegir.

| # | Pregunta | Por qué bloquea | Contexto |
|---|---|---|---|
| Q1 | **Control de documentación:** ¿elegimos la opción **1** (excluir `Análisis/` del control de constitución en `scripts/validar_documentacion.py:42`), la 2 (sacar la extracción fuera del repo) o la 3 (dejar el fallo documentado)? | El control sigue rojo hasta decidir; condiciona cualquier commit futuro de `Análisis/`. | Kimi y Claude recomiendan la opción 1. Tablero issue #8. |
| Q2 | **Capítulos M02, M03, M16 y M24 tienen 0 requisitos asignados** en el CSV de preservados. ¿Confirmas que es cobertura intencional (capítulos transversales) o exiges trazabilidad mínima por capítulo? | Define si el mapa 24↔153 está completo o hay brecha a corregir con el equipo. | `kimi/paso2_mapa_capitulos.csv` (H-02). |
| Q3 | **Paginación del Word:** ¿puedes abrir el documento en Microsoft Word y confirmar si son **28 o 33 páginas**? | Bloquea citar "28 p." en cualquier documentación derivada. | H-01; PDF de verificación en `02_texto/pdf_verificacion/`. |
| Q4 | **Versión de referencia del Word:** ¿apruebas usar el Word suelto como versión de referencia y el interno del zip como respaldo (PROPUESTA del Paso 1)? sí/no | Fija cuál de las dos versiones "iguales" manda ante cualquier divergencia futura. | H-05. |
| Q5 | **Reparto de roles:** por tu instrucción ("continuar, colaborar, iterar") Kimi entregó los Pasos 2–4. ¿Confirmas que **Claude haga la revisión cruzada** de 2–4 y siga con el 5, o volvemos al reparto original? | Evita duplicar trabajo y deja claro quién revisa qué. | Tablero issues #3, #7. |
| Q6 | **Stack propuesto** (Next.js 16 / Node.js 24 LTS / PostgreSQL 17, monolito modular): ¿se mantiene **PRELIMINAR pendiente de D45** o lo ratificas ahora? | No bloquea el análisis documental; bloquea cualquier construcción y el F00. | H-06; maestro línea 259. |

## Notas

- Q1, Q3 y Q4 desbloquean controles y citas; Q2 y Q5 desbloquean el trabajo de los agentes; Q6 es de negocio/construcción.
- Respuestas válidas: "Q1: 1", "Q4: sí", etc. Las registramos en el tablero con fecha.
