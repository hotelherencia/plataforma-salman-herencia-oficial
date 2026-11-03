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

## Operación del hotel — mantenedor, consulta, ocupación e indicadores (2026-11-03)

Orden del propietario: completar el flujo operativo para entender el negocio
y gestionar habitaciones sin ambigüedad. Spec gobernante nueva:
`docs/arquitectura/spec-hotel-operacion-v1.md` (flujos por rol, métricas con
fórmula/unidad/fuente/limitaciones, criterios CA-*); spec-api-v1 pasa a 32
operaciones. **Cambio de alcance:** el panel operativo entra a V1; los
indicadores financieros de HU-HOT-03 siguen fuera. Evidencia y matriz
requisito → spec → implementación → prueba en
`capturas/e2e-2026-11-03/INFORME-operacion.md`.

- [Hecha] `v1-oper-01` — mantenedor (alta solo-crear, edición auditada,
  tarifa append-only con desempate, baja lógica), detalle de reserva con
  cuenta, búsqueda por periodo, ocupación por noche y panel operativo.
- [Bloqueada, P1] `v1-issue-07` — decisión D-ENT-01: ¿la entrada adopta la
  regla de fecha/hora y documento del dominio? (reencuadrado por `v1-issue-14`).
- [Lista, P2] `v1-issue-08..10` — decisiones pendientes del propietario
  (financieros y rol gerencia; personas/reasignación/tipos; tarifas
  superpuestas, mantenimiento programado, denominador y auditoría).
- No cargados a GitHub Projects (sin acciones externas en esta sesión).


## Revisión de integración y ciclo TDD (2026-11-03, tarde)

Revisión de solo lectura de la operación del hotel (con dos corridas de
Gemini 4 Argon vía `agy` sobre copias aisladas) y primer ciclo TDD.

- [Hecha, P1] `v1-issue-12` — `POST /hotel/reservas` rechaza (409) una
  habitación fuera del cupo, como la oferta y el dominio (spec-hotel-operacion
  §2.7, CA-HAB-07). RED/GREEN en servicio (5) y E2E (`e2e-reserva-vendible.mjs`,
  3); regresión 155/155, 44/44 y 16/16. El código quedó dentro del commit
  local `ca2e40a` de otro trabajo; la E2E y este registro, sin commit.
- [Lista, P2] `v1-issue-13` — renovar la clave de idempotencia tras un 4xx.
- [Hecha, P1] `v1-issue-14` — `v1-issue-07` reencuadrado como decisión
  D-ENT-01 (ahora Bloqueada, a la espera del propietario); spec-api-v1,
  spec-hotel-operacion §7, `docs/funcional/dominio.md` y `flujos.md` describen
  la entrada tal como la fija el contrato vigente (sin cambio de comportamiento).
- [Bloqueada] `v1-issue-15` (salida con otra estadía, depende de 07),
  `v1-issue-16` (roles de entrada/salida), `v1-issue-17` (tarifa de estadías
  que cruzan periodos), `v1-issue-18` (orden de despliegue y empates de
  tarifas en producción; requiere autorización).
- [Lista, P3] `v1-issue-19` — deuda documental.
- No cargados a GitHub Projects (sin acciones externas): falta sincronizar.


## Revisión landing → plataforma (2026-11-03, noche)

Navegación pública de https://hotelherencia.cl/ y del front publicado, sin
enviar formularios ni crear datos. Hoy la landing solo envía una consulta a
Formspree; no existe puente con la plataforma.

- [Bloqueada, P1] `v1-issue-20` — decisión D-PUB-01: qué reserva puede hacer
  un visitante (modalidad, garantía, unidad de venta, precio, datos, límites).
- [Bloqueada, P1] `v1-issue-21` — spec de la superficie pública de la API.
- [Bloqueada, P1] `v1-issue-22` — backend: disponibilidad pública y solicitud.
- [Bloqueada, P1] `v1-issue-23` — front: página pública `/reservar`.
- [Bloqueada, P2] `v1-issue-24` — bandeja de solicitudes en recepción.
- [Bloqueada, P2] `v1-issue-25` — CTA de la landing (código fuera del repo).
- [Bloqueada, P1] `v1-issue-26` — producción opera con la empresa sintética.
- [Lista, P3] `v1-issue-27` — sin sesión se ve el menú interno.
- No cargados a GitHub Projects (sin acciones externas): falta sincronizar.


## Agente de reservas (2026-11-03, noche) — spec-kit `specs/005-hotel-agente-reservas/`

Evaluación de mayor capacidad agéntica traducida a SDD/TDD. El agente nunca
es autoridad: solo llama a herramientas deterministas del servidor y sus
cifras salen de `reservas.oferta`. Antecedente: `specs/002` historia 3.

- [Bloqueada, P1] `v1-issue-28` — decisiones D-AGT-01..06.
- [Bloqueada, P1] `v1-issue-29` — N0 copiloto: dominio, persistencia y API (TDD, modelo guionado).
- [Bloqueada, P1] `v1-issue-30` — N0: bandeja `/hotel/agente` y E2E.
- [Bloqueada, P2] `v1-issue-31` — adaptador real y evaluación de 50 casos (compuerta N1/N2).
- No cargados a GitHub Projects (sin acciones externas): falta sincronizar.
