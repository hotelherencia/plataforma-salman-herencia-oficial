# Índice del backlog de construcción V1 — 2026-10-28

Backlog vigente de la fase de construcción. Gobiernan las specs
`docs/arquitectura/spec-api-v1.md`, `spec-backend-v1.md` y `spec-front-v1.md`.
Fuente de ítems: `backlog/v1/construccion-v1.json` (81 ítems). Carga en
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

- [Hecha] `v1-oper-01` (GitHub `#295`) — mantenedor (alta solo-crear, edición auditada,
  tarifa append-only con desempate, baja lógica), detalle de reserva con
  cuenta, búsqueda por periodo, ocupación por noche y panel operativo.
- [Bloqueada, P1] `v1-issue-07` (GitHub `#296`) — decisión D-ENT-01: ¿la entrada adopta la
  regla de fecha/hora y documento del dominio? (reencuadrado por `v1-issue-14`).
- [Lista, P2] `v1-issue-08..10` (GitHub `#297..#299`) — decisiones pendientes del propietario
  (financieros y rol gerencia; personas/reasignación/tipos; tarifas
  superpuestas, mantenimiento programado, denominador y auditoría).
- Sincronizados en GitHub Issues y `hotelherencia/projects/2` (`#289..#294` para `v1-issue-01..06`, `#295..#299` para `v1-oper-01` y `v1-issue-07..10`, `#300..#301` para `v1-issue-11..12`).


## Revisión de integración y ciclo TDD (2026-11-03, tarde)

Revisión de solo lectura de la operación del hotel (con dos corridas de
Gemini 4 Argon vía `agy` sobre copias aisladas) y primer ciclo TDD.

- [Hecha, P1] `v1-issue-12` (GitHub `#301`) — `POST /hotel/reservas` rechaza (409) una
  habitación fuera del cupo, como la oferta y el dominio (spec-hotel-operacion
  §2.7, CA-HAB-07). RED/GREEN en servicio (5) y E2E (`e2e-reserva-vendible.mjs`,
  3); regresión 155/155, 44/44 y 16/16. El código quedó dentro del commit
  local `ca2e40a` de otro trabajo; la E2E y este registro, sin commit.
- [Hecha, P1] `v1-issue-13` (GitHub `#281`) — renovar la clave de idempotencia tras un 4xx.
- [Hecha, P1] `v1-issue-14` (GitHub `#302`) — `v1-issue-07` reencuadrado como decisión
  D-ENT-01 (ahora Bloqueada, a la espera del propietario); spec-api-v1,
  spec-hotel-operacion §7, `docs/funcional/dominio.md` y `flujos.md` describen
  la entrada tal como la fija el contrato vigente (sin cambio de comportamiento).
- [Bloqueada] `v1-issue-15` (GitHub `#303`, salida con otra estadía, depende de 07),
  `v1-issue-16` (GitHub `#304`, roles de entrada/salida), `v1-issue-17` (GitHub `#305`, tarifa de estadías
  que cruzan periodos), `v1-issue-18` (GitHub `#306`, orden de despliegue y empates de
  tarifas en producción; requiere autorización).
- [Lista, P3] `v1-issue-19` (GitHub `#307`) — deuda documental.
- Sincronizados en GitHub Issues y `hotelherencia/projects/2` (`#281`, `#301..#307`).


## Revisión landing → plataforma (2026-11-03, noche)

Navegación pública de https://hotelherencia.cl/ y del front publicado, sin
enviar formularios ni crear datos. Hoy la landing solo envía una consulta a
Formspree; no existe puente con la plataforma.

- [Bloqueada, P1] `v1-issue-20` (GitHub `#308`) — decisión D-PUB-01: qué reserva puede hacer
  un visitante (modalidad, garantía, unidad de venta, precio, datos, límites).
- [Bloqueada, P1] `v1-issue-21` (GitHub `#309`) — spec de la superficie pública de la API.
- [Bloqueada, P1] `v1-issue-22` (GitHub `#310`) — backend: disponibilidad pública y solicitud.
- [Bloqueada, P1] `v1-issue-23` (GitHub `#311`) — front: página pública `/reservar`.
- [Bloqueada, P2] `v1-issue-24` (GitHub `#312`) — bandeja de solicitudes en recepción.
- [Bloqueada, P2] `v1-issue-25` (GitHub `#313`) — CTA de la landing (código fuera del repo).
- [Bloqueada, P1] `v1-issue-26` (GitHub `#314`) — producción opera con la empresa sintética.
- [Lista, P3] `v1-issue-27` (GitHub `#315`) — sin sesión se ve el menú interno.
- Sincronizados en GitHub Issues y `hotelherencia/projects/2` (`#308..#315`).


## Agente de reservas (2026-11-03, noche) — spec-kit `specs/005-hotel-agente-reservas/`

Evaluación de mayor capacidad agéntica traducida a SDD/TDD. El agente nunca
 es autoridad: solo llama a herramientas deterministas del servidor y sus
cifras salen de `reservas.oferta`. Antecedente: `specs/002` historia 3.

- [Bloqueada, P1] `v1-issue-28` (GitHub `#316`) — decisiones D-AGT-01..06.
- [Bloqueada, P1] `v1-issue-29` (GitHub `#317`) — N0 copiloto: dominio, persistencia y API (TDD, modelo guionado).
- [Bloqueada, P1] `v1-issue-30` (GitHub `#318`) — N0: bandeja `/hotel/agente` y E2E.
- [Bloqueada, P2] `v1-issue-31` (GitHub `#319`) — adaptador real y evaluación de 50 casos (compuerta N1/N2).
- Sincronizados en GitHub Issues y `hotelherencia/projects/2` (`#316..#319`).


## Auditoría técnica integral UI/UX, responsive, accesibilidad, rendimiento e integración (2026-11-03)

Auditoría sobre instancias locales aisladas (`:8097` y `:3017`) en 7 viewports
(`320px` a `1440px`) y 4 roles (`anonimo`, `administrador`, `recepcion`, `caja`).
Cargados en GitHub Issues y en `hotelherencia/projects/2`:

- [Hecha, P1] `v1-issue-13` (GitHub `#281`, enriquecido) — renovar clave de
  idempotencia tras 4xx o exponer «Nueva operación» en todas las pantallas con mutación (resuelto en `e49efa5`).
- [Hecha, P1] `v1-issue-32` (GitHub `#282`) — cobro parcial en `/hotel/pago`
  con `clave: 'cobro-web-1'` por defecto devuelve `201` (`reintento: true`) sin
  registrar el segundo abono (resuelto en `e49efa5`).
- [Hecha, P1] `v1-issue-33` (GitHub `#283`) — cambio de clave propia para
  roles `recepcion` y `caja` en `/cuenta` e inclusión de `id` en `GET /sesion` (resuelto en `e49efa5`).
- [Hecha, P2] `v1-issue-34` (GitHub `#284`) — desbordamiento horizontal móvil
  (`320px–430px`) en `/hotel/habitaciones/[id]`, `/hotel/reservas/[id]` y `/hotel/oferta` (resuelto en `de4c2c9`).
- [Hecha, P2] `v1-issue-35` (GitHub `#285`) — precarga de `reserva_id` y
  `habitacion_id`/fechas entre pantallas operativas y eliminación de defaults
  inválidos en `/hotel/reserva` (resuelto en `de4c2c9`).
- [Hecha, P2] `v1-issue-36` (GitHub `#286`) — accesibilidad y táctil: blancos
  `>= 44×44 px`, semántica de tabla en listados, foco visible, `prefers-reduced-motion`
  y confirmación en acciones destructivas (resuelto en `de4c2c9`).
- [Hecha, P2] `v1-issue-37` (GitHub `#287`) — rendimiento: compartir estado de
  `useSesion()` para evitar 2 a 3 llamadas `GET /sesion` por montaje (resuelto en `e49efa5`).
- [Hecha, P3] `v1-issue-38` (GitHub `#288`) — guardia de sesión y `.pagina` en
  `/cafeteria`, `/inmobiliaria` y `/constructora`, y formato `clp()` en `/hotel/caja` (resuelto en `de4c2c9`).
- [Hecha, P1] `v1-issue-39` (GitHub `#321`) — blindaje de cancelación y operaciones de estadía
  ante concurrencia (`SELECT ... FOR UPDATE` en `servicio/cobro.py` y
  `pg_advisory_xact_lock` en `servicio/idempotencia.py`), guardia síncrona de
  doble envío, corrección de bloqueo tras `window.confirm` y contexto operativo
  de la reserva en `/hotel/estadia` (`servicio/tests/test_cancelacion_estadia.py`).

## Bucle landing → plataforma (2026-11-04)

Construcción del pedazo de V1-ISSUE-25 que vive en este repositorio. La
landing de hotelherencia.cl está fuera del repo (Apache estático), así que
se versiona en `landing/` una réplica fiel del sitio actual, lista para
publicar en ese hosting, con el CTA ya cableado al front público. Ciclo
TDD: RED (tests + E2E nuevos en rojo) → GREEN (implementación) → regresión.

- [Hecha, P1] `v1-issue-25` (GitHub `#313`) — landing estática en `landing/`
  (hero con widget de reserva, ubicación, servicios, habitaciones, galería,
  FAQ y contacto con el contenido del sitio vigente). El CTA «Consultar
  reserva» valida el rango con la misma regla que `front/app/reservar/page.js`
  (`landing/js/reserva.js`, funciones puras también corridas en Node) y abre
  `/reservar?inicio=…&fin=…&personas=…` (CA-PUB-12), sin datos personales en
  la URL. E2E nueva `e2e/e2e-landing.mjs` (PUB-07/08/09), navegador real
  contra esta carpeta servida estáticamente y el front en build de
  producción: 3/3. Contacto: con `FORMSPREE_URL` sin configurar orienta a
  tel/WhatsApp (D-PUB-01 sigue pendiente del propietario). Regresión del
  canal público completa (PUB-01..05 + BAN-01): 6/6 contra base
  `plataforma_e2e_landing`. El issue se mantiene abierto hasta que el CTA
  esté publicado y verificado en el hosting real.
- APRENDIZAJE de la corrida: `e2e-reserva-publica.mjs` asume una base con al
  menos una habitación vendible ajena a la corrida: PUB-01 auto-selecciona
  la primera opción de la oferta (`buscar()` de `/reservar`) y la convierte,
  y PUB-03 reutiliza las mismas fechas exigiendo la habitación de la
  corrida. Con una base recién creada PUB-02/03 fallan siempre; hay que
  sembrar una habitación «decoy» con tarifa que ordene antes (documentado en
  `e2e/README.md`).
