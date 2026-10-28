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
- [Lista] P1 `v1-front` — Front Vercel → `h6a` esqueleto y login · `h6b` siete pantallas · `h6c` reglas duras y error sin API. **Siguiente.**
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
