# Depuración de carpetas base — 2026-10-27

> **Reubicación del mismo día (estructura final):** `definicion-herencia/` y
> `archivo-no-construccion/` pasaron de la raíz a `docs/`, con una sola
> carpeta de documentación dentro del proyecto. Después, la carpeta `proyecto/`
> se eliminó como nivel intermedio: su contenido subió a la raíz, que hoy es el
> proyecto **plataforma-salman-herencia**. Las rutas internas citadas en esta
> nota y en el acta se entienden hoy bajo `docs/`, y las referencias vivas ya no
> llevan prefijo `proyecto/` (corregidas el 2026-10-27). El README histórico de
> la antigua carpeta `proyecto/` se preserva en `docs/historial-consolidacion.md`.

Decisión aplicada sobre el árbol de trabajo de la raíz
(`F:\Code\plataforma-salman-herencia-oficial-main\plataforma-salman-herencia-oficial-main`):
queda como árbol de construcción **spec driven** el contenido de la raíz
(`specs/`, `backlog/`, `core/`, `verticales/`, `scripts/`, `.specify/`) más
`docs/definicion-herencia/` (conservada por falta de traza, ver tabla). Las notas de la
fase de análisis documental pasaron a `archivo-no-construccion/`. No se usó borrado
definitivo: todo movimiento conserva la ruta interna bajo `archivo-no-construccion/`.

No se movió ningún archivo citado por hash en el README de la raíz (la referencia
SHA-256 cubre el `MANIFEST.json` de `definicion-herencia/`, que no se movió), por lo
que no se regenera ningún manifiesto.

## Tabla de decisión

Clases: **QUEDA** (sigue en el árbol de trabajo) · **ARCHIVA** (pasa a
`archivo-no-construccion/`) · **CONSERVAR PORQUE FALTA TRAZA** (no se archiva: un ID
que aporta no tiene destino en `specs` ni en `backlog`).

| Ruta | Para qué sirvió | Qué la reemplaza en  | Decisión |
|---|---|---|---|
| `analisis/paso2_mapa_capitulos.csv`, `paso2_mapa_contenido.md`, `paso2_mapa_fichas_sdd.csv`, `paso2_verificaciones.json` | Mapa del contenido del Word y verificaciones del paso 2 del análisis Claude–Kimi (2026-10-26) | Nada; cifras ya consolidadas en el acta y en `definicion-herencia/registros/paquetes.csv`. Fase cerrada según README de raíz | **ARCHIVA** |
| `analisis/paso3_cifras.md`, `verificacion_c1.json`, `verificacion_c1.md` | Recuentos 8/8 verificados y comprobación C1 del paquete | El acta (ahora en `backlog/acta_cierre_definicion.md`) y `definicion-herencia/` (se conserva) | **ARCHIVA** |
| `analisis/paso4_hallazgos.md` (H-01…H-13) | Hallazgos y contradicciones del análisis documental | Decisiones abiertas registradas en `definicion-herencia/registros/decisiones.csv` (D01–D45, Pendiente) y en el acta; el acta no es borrada, se traslada | **ARCHIVA** |
| `analisis/paso5_preguntas.md` | Preguntas sí/no para el propietario | `definicion-herencia/registros/decisiones.csv` es el registro canónico de las 45 decisiones; acta en `backlog/` | **ARCHIVA** |
| `analisis/acta_cierre_definicion.md` | Acta de cierre de la fase de definición (cierre pendiente de firma del propietario) | Ninguna; el README de raíz la cita como cierre pendiente → se conserva dentro de `backlog/` | **CONSERVA (movida a `backlog/acta_cierre_definicion.md`)** |
| `Untitled` (raíz) | Archivo suelto en la raíz; no es spec ni código | Nada | **ARCHIVA** (`archivo-no-construccion/Untitled`, sin citar contenido) |
| `definicion-herencia/` raíz (`00_ENTREGA.md`, `01_GUIA_ENTREGA_EQUIPO.md`, `AGENTS.md`, `MANIFEST.json`) | Entrega SDD V1.0 de Hotel Herencia: guías, manifiesto y reglas de la entrega | Sin destino: los IDs de la entrega (153 requisitos CORE-*/HOT-*/RES-*…, D01–D45, tareas Fnn-Tnn) no existen en `specs` ni en `backlog` (verificado por búsqueda) | **CONSERVAR PORQUE FALTA TRAZA** — IDs: 153 requisitos y 45 decisiones pendientes de Ricardo Salman; acta §3 |
| `definicion-herencia/.specify/` | Memoria Spec Kit de la V1.0 (constitución 1.0, distinta de la de ``) | No es duplicado de `.specify/memory/constitution.md` (1.1.0 propuesta); pertenece a la V1.0 pendiente de ratificación (acta §3.1) | **CONSERVAR PORQUE FALTA TRAZA** — ID: constitución 1.0 |
| `definicion-herencia/sdd/` | Constitución 1.0, ADR-001 stack, dependencias, gates de ejecución | Sin destino; la constitución 1.0 está pendiente de ratificar (acta §3.1) | **CONSERVAR PORQUE FALTA TRAZA** — IDs: constitución 1.0, ADR-001 |
| `definicion-herencia/maestro/` (M01–M24) | Documento Maestro V1.0 (vista md del Word) | Sin destino en `specs` | **CONSERVAR PORQUE FALTA TRAZA** — IDs: M01–M24 |
| `definicion-herencia/specs/` (001–023, F00–F22) | 153 historias de usuario, una por requisito | Sin destino: `specs/000–004` usan otra nomenclatura (FR/SC de fuentes RSalman); sin traslape de IDs (verificado) | **CONSERVAR PORQUE FALTA TRAZA** — IDs: F00–F22 / 153 US |
| `definicion-herencia/registros/` | requisitos preservados, decisiones D01–D45, trazabilidad, 505 tareas, acoplamientos | Sin destino | **CONSERVAR PORQUE FALTA TRAZA** — IDs: requisitos 153, D01–D45, 505 tareas |
| `definicion-herencia/modelos/` | 109 entidades / 1 409 campos | Sin destino | **CONSERVAR PORQUE FALTA TRAZA** — IDs: entidades del diccionario |
| `definicion-herencia/pruebas/` | 306 casos (153+153) y gherkin F00–F22 | Sin destino | **CONSERVAR PORQUE FALTA TRAZA** — IDs: 306 casos |
| `definicion-herencia/contratos/`, `reglas/`, `seguridad/` | Contratos (openapi, eventos), reglas de negocio, amenazas y permisos | Sin destino | **CONSERVAR PORQUE FALTA TRAZA** — IDs de operaciones, eventos e indicadores |
| `definicion-herencia/fuentes/` | Procedencia V0.3 y baseline original de requisitos | Sin destino | **CONSERVAR PORQUE FALTA TRAZA** — IDs: baseline V0.3 de los 153 requisitos |
| `definicion-herencia/carga_inicial/`, `datos_sinteticos/`, `evidencias_documentales/`, `operacion/`, `ux/` | Datos operativos de apertura, fixtures, validación documental, runbooks, 53 pantallas | Sin destino | **CONSERVAR PORQUE FALTA TRAZA** — ligadas a los IDs de la V1.0 (p. ej. 53 pantallas de ux) |

## Movimientos realizados

1. `analisis/acta_cierre_definicion.md` → `backlog/acta_cierre_definicion.md` (conservada; cierre pendiente de firma).
2. `analisis/` (9 archivos restantes) → `archivo-no-construccion/analisis/`.
3. `Untitled` → `archivo-no-construccion/Untitled` (sin leer ni citar contenido).

## Lo que no se tocó

- `` completo: constitución (`.specify/memory/constitution.md`), `AGENTS.md`,
  `README.md`, `specs/000-core`…`004-constructora`, `backlog/` (índice,
  `github-projects.json`, `decisiones-hotel.md`, `acta-para-firmar.md`,
  `acta_cierre_definicion.md`, `hotel/`, `speckit-analyze/`), `core/`,
  `verticales/` (incluido `hotel/incremento0` y sus pruebas) y `scripts/`.
- `definicion-herencia/` completa (conservada por falta de traza).
- `docs/originales` y fuentes externas al repositorio; `.env` (no leído ni copiado).
- No se editaron `spec.md`, `tasks.md`, la constitución ni los ADR. No se marcó
  Hecha ninguna T003.

## Nota sobre GitHub

La carga del backlog al GitHub Project n.º 2 («Project Plataforma Hotel Herencia»)
quedó a un paso de completarse fuera de esta instrucción: creados los 150 issues y
agregados los 150 ítems al tablero; pendiente solo fijar los valores de campos
(corrección en `scripts/cargar_github_projects.py`: la mutación correcta es
`updateProjectV2ItemFieldValue`). Esta depuración no tocó GitHub.
