# Índice del backlog de construcción V1 — 2026-10-28

Backlog vigente de la fase de construcción. Gobiernan las specs
`docs/arquitectura/spec-api-v1.md`, `spec-backend-v1.md` y `spec-front-v1.md`.
Fuente de ítems: `backlog/v1/construccion-v1.json` (42 ítems). Carga en
GitHub Projects (Project n.º 2): `backlog/v1/carga-v1.log.json`.

El corpus documental de ciclos previos queda cerrado en el tablero (ver
«Limpieza del tablero» abajo); su índice histórico sigue en
`backlog/indice.md`.

## Épicas y hitos

- [Hecha 2026-10-28] P1 `v1-api` — Contrato API → **`h1` Hecha**: el OpenAPI 3.1 servido por el backend (`/openapi.json`) cubre las 10 operaciones; prueba de contrato en `test_h5_maduracion.py`.
- [Lista] P1 `v1-back` — Backend Railway → **H1–H5 Hechas 2026-10-28** (arranque, sesión, reserva persistente, cobro por el núcleo, maduración con validación/seguridad/auditoría y prueba de reinicio real; 39 pruebas del servicio + 181 del dominio).
- [Hecha 2026-10-28] P1 `v1-front` — Front Vercel → **H6a–H6c Hechas** (Next.js: login, 7 pantallas, rutas vacías; verificado con navegador: API caída → error y nada confirmable; demo en http://127.0.0.1:3000 contra la API en :8080).
- [Lista] P2 `v1-desp` — Despliegue H7 → verificar cuentas, push (derogación solo H7), Railway, Vercel.

Criterio de aceptación de cada hito: las pruebas citadas en su historia, con
el backend en local (H1–H6 sin push ni despliegue, según AGENTS.md).

## Limpieza del tablero (2026-10-28)

- Cerrados como «not planned» los 118 ítems abiertos del corpus documental
  (gates T00x/T10x/T20x, historias y tareas del ladder DEC→IMP, épica e
  historias de las cinco features) y las 3 historias HU-HOT del manual:
  lo que siga aplicando se reescribe como historia V1.
- Conservados abiertos: los 15 ítems «Decisión humana» (las preguntas Q-*
  de verticales futuras y gobernanza siguen pendientes del propietario) y
  los 77 ítems Done (incrementos y casos de aceptación: evidencia del dominio).
- Detalle de la correspondencia vieja→nueva: habitaciones/tarifas (HU-HOT-01)
  → `v1-back/h3` + `v1-front/h6b/t1`; caja (HU-HOT-02) → `v1-back/h4` +
  `v1-front/h6b/t4`; indicadores (HU-HOT-03) fuera de V1.

## Revisión E2E de aceptación — 2026-11-03

Aceptación del módulo hotel en local (datos sintéticos, base `plataforma_e2e`
desechable, front en build de producción + navegador): **41/41 flujos
APROBADO, 0 fallos** — matriz en `capturas/e2e-2026-11-03/INFORME.md` y suite
reproducible en `e2e/` (`cd e2e && npm install && npm run e2e`). Incluye los
rechazos por rol (administrador/recepción/caja), validaciones, idempotencia y
verificación de efectos; complementada con API caída (criterio front 1) y
persistencia tras reinicio (criterio backend 4). Ampliación del contrato ese
mismo día: `GET /hotel/habitaciones` (inventario operativo; spec-api-v1 pasa a
27 operaciones). Correcciones que la revisión levantó y ya están integradas:
regresión PUT→POST en alta/tarifa de habitaciones, reservas que nacía vacía,
gestión de usuarios sin lista, resumen de confirmación por tipo de operación,
login con «admin» precargado. Desplegado en producción (Vercel + Railway) y
verificado: `/hotel/habitaciones` responde 401 anónimo en Railway.

**Issues abiertos para corregir** (alta en `construccion-v1.json`,
`v1-issue-01..06`): los 20 tests del servicio en rojo heredados de H6/H7
(P1, incluye seguridad de cookies/CORS); cobertura E2E del alta 2FA en
navegador; formularios del front visibles para roles que el contrato rechaza;
hidratación bloqueada en `next dev` con HMR caído; procedimiento de
aprobación de deploys Railway (NEEDS_APPROVAL); `e2e-resultados.json`
versionado que envejece.
