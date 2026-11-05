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
- [Hecha, P1] `v1-issue-15` (GitHub `#303`) — la salida no deja disponible la
  unidad si otra estadía sigue en curso (turnover no solapado): resuelta en
  `c4f32dd` (TDD) el 2026-11-04; este índice la había listado bloqueada por
  error — corregido en la sincronización 2026-11-05.
- [Bloqueada] `v1-issue-16` (GitHub `#304`, roles de entrada/salida, depende de 07),
  `v1-issue-17` (GitHub `#305`, tarifa de estadías
  que cruzan periodos), `v1-issue-18` (GitHub `#306`, orden de despliegue y empates de
  tarifas en producción; requiere autorización).
- [Hecha, P3] `v1-issue-19` (GitHub `#307`) — deuda documental (resuelta en
  `7ae13cb`; el estado del tablero se corrigió el 2026-11-05).
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
- [Hecha, P1] `v1-issue-30` (GitHub `#318`) — N0: bandeja `/hotel/agente` y E2E.
- [En curso, P2] `v1-issue-31` (GitHub `#319`) — evaluación de 50 casos hecha
  (AG-V01, SC-003 aprobada con SUT grabado 2026-11-04); falta el adaptador
  real (compuerta N1/N2; bloqueado por D-AGT-02).
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

## Agente de reservas N0 — backend (2026-11-04)

D-AGT-01 ratificada por orden del propietario (2026-11-04: «sigue tu
sugerencia» sobre V1-ISSUE-29 = nivel inicial N0 copiloto, SC-003 como
compuerta). D-AGT-02..06 siguen pendientes: el puerto del modelo responde 503
«modelo no configurado» y las pruebas usan el modelo guionado (NFR-A04).

- [Hecha, P1] `v1-issue-29` (GitHub `#317`) — backend N0 con TDD puro
  (RED→GREEN por capas, specs/005): dominio (`servicio/agente.py`: redactar,
  validar_decision, componer, verificar, NIVELES cerrados por nivel; puerto
  `servicio/modelo_lenguaje.py`: SinAdaptador/ModeloGuionado), migración
  `0011_agente_reservas.sql` (4 tablas + índices; 0010 quedó tomada por el
  canal público), orquestador `procesar` (tope 3 turnos, un reintento ante
  fallo del modelo, verificador determinista, trazas y auditoría con actor
  `agente:<consulta_id>`) y 7 rutas `/hotel/agente/*` en aplicacion.py
  (spec-api-v1 §«Agente de reservas», operaciones 40→47). Identidad de
  servicio `agente` sin clave utilizable ni email (sin sesión por ninguna
  vía). Recotización al aprobar con oferta vencida (409 «la oferta cambió» con
  borrador nuevo); aprobación concurrente con guardia de estado (409 a la
  segunda). Evidencia: AG-U01..U06 (13 tests) y AG-S01..S14 (14 tests) en
  verde; regresión completa servicio 233/233 y dominio 180/180. Las pruebas de
  dominio corren con PYTHONPATH de los incrementos (core+verticales/*).

## Agente de reservas N0 — front y E2E (2026-11-04)

- [Hecha, P1] `v1-issue-30` (GitHub `#318`) — bandeja `/hotel/agente`
  (`front/app/hotel/agente/page.js`): recepción pega la consulta entrante
  (canal + texto), ve el texto redactado ([correo]/[teléfono]/[rut]/[tarjeta]),
  el borrador con las cifras releídas por API, la traza del turno y acciones
  Aprobar (con edición opcional) / Descartar / «Copiar respuesta»; 409 «la
  oferta cambió» se traduce en aviso con el borrador recotizado para aprobar
  el nuevo. Ítem «Agente» en el menú solo para recepción/administrador
  (`front/app/barra.jsx`, escritorio y móvil). E2E `e2e/e2e-agente.mjs` con
  modelo guionado (`AGENTE_GUION_JSON="$(node e2e-agente.mjs --guion)"`, una
  corrida por arranque de la API; AG-E03 quedó cubierto por AG-S07 en
  servicio): AG-E01 flujo feliz con portapapeles y aprobación releída,
  AG-E05 recotización con tarifa cambiada (v2 aprobado, v1 pendiente),
  AG-E02 inyección → escalada sin efectos (0 reservas), AG-E04 caja sin menú
  ni acceso (guardia + 403). APRENDIZAJE de la corrida: (1) `API_BASE_URL` se
  hornea en el build (`next.config.mjs`): toca build + `next start`, no basta
  la variable al arrancar; (2) el ítem 0 de la oferta ordena por id — entre
  corridas es la habitación más vieja de la base, las aserciones se anclan a
  lo que dice el texto del borrador; (3) el polling de Playwright puede ver
  estados transitorios: el aviso se espera con su texto
  (`getByRole('alert').filter({hasText})`), no solo el elemento. Evidencia
  2026-11-04: agente 4/4, base 56/56, operación 20/20, landing 3/3, público
  6/6, servicio 233/233, dominio 180/180.
- Pendiente del paquete (próximo bucle): `#319` — adaptador real del modelo y
  evaluación de 50 casos (compuerta SC-003; bloqueado por D-AGT-02).

## Contrato: unificar «ocupadas» (2026-11-04)

Revisión de contrato pedida por #320 (propuesta de la veracidad 2026-11-03):
dos métricas distintas compartían el nombre `ocupadas` en dos endpoints —
resumen de `GET /hotel/ocupacion` (cupo comprometido `confirmada`+`en_estadia`,
cualquier noche) y serie de `GET /hotel/indicadores` (estadías reales
`en_estadia`+`finalizada`, noches `d ≤ hoy`). El renombre se aprobó con la
orden del propietario de completar el backlog (2026-11-04) y rompió front y
E2E una sola vez, sincronizado en el mismo commit.

- [Hecha, P2] GitHub `#320` — renombre `ocupadas` → `ocupadas_cupo` (resumen
  de `/hotel/ocupacion`) y `ocupadas` → `ocupadas_estadias` (serie de
  `/hotel/indicadores`): contrato antes del código
  (spec-hotel-operacion-v1 §5 y §4.3, spec-api-v1 §«Mantenedor…»), luego
  TDD (tests de reconciliación en rojo → `servicio/panel.py`), front
  (`front/app/hotel/ocupacion/page.js`, `front/app/hotel/panel/page.js`) y
  `e2e/e2e-operacion.mjs` (OCU-03, IND-05). Los KPI `habitaciones_ocupadas` y
  `noches_ocupadas` no cambian (ya eran nombres propios). Evidencia
  2026-11-04: servicio 233/233, operación 20/20, base 56/56, agente 4/4,
  landing 3/3, público 6/6, dominio 180/180.

## Agente N0 — evaluación AG-V01 / SC-003 (2026-11-04)

- [Hecha, P1] `v1-issue-31` (GitHub `#319`, parte de validación y prueba
  ordenada por el propietario) — corpus de 50 casos sintéticos
  (`servicio/evaluaciones/agente/casos.jsonl`: 20 claros, 10 sin cupo,
  10 ambiguos, 5 inyección, 5 datos sensibles; fechas relativas al corte) y
  ejecutor `servicio/evaluacion_agente.py` con métricas de la compuerta
  (tasa sin edición ≥ 90 %, 0 cifras inventadas, 100 % inyecciones escaladas,
  100 % datos redactados; las propuestas adversariales no miden calidad, miden
  defensa). SUT: `ModeloGrabado.desde_archivo` (respuestas grabadas, contract
  test sin red, NFR-A04); con un proveedor real (D-AGT-02) el mismo corpus
  mide sus respuestas. AG-V01 corrida en base aislada `plataforma_eval_agente`
  con autorización del propietario: **SC-003 APROBADA**
  (`AGV-2026-11-04-1e038fb4a9`; informe
  `backlog/v1/evaluacion-agente-agv-2026-11-04.json`): 100 % / 0 / 100 % /
  100 %. La aprobación cubre el pipeline; la compuerta para N1 exige repetir
  la evaluación contra el adaptador real cuando D-AGT-02 lo nombre.
  APRENDIZAJE: el corpus inicial sembró capacidad 2 para consultas de 3–4
  personas y la compuerta lo rechazó (`referencia_inexistente`) — el harness
  funciona como trampa honesta. T050B queda a medias (falta el proveedor);
  T060/T070 (N1/N2) siguen con sus decisiones. Evidencia 2026-11-04: servicio
  244/244, dominio 180/180, agente 4/4, operación 20/20, base 56/56,
  landing 3/3, público 6/6.

## Canal público WhatsApp — evaluación e historias de usuario (2026-11-04)

- [Hecha, P1] `v1-issue-32` (GitHub `#324`, orden del propietario
  2026-11-04: «el canal público puede ser WhatsApp… un agente que reciba la
  petición y responda derivando a 1 agente; crear historias de usuario para
  integrar Meta; lo mínimo es integrar asistencia por IA») — paquete de
  especificación `specs/006-hotel-canal-whatsapp/` (formato spec-kit del
  repo, mismas convenciones que specs/005): HECHO DOCUMENTADO de la
  evaluación (la traza landing es reconcilible vía `solicitudes.origen`;
  las reservas directas no registran canal), fases F0–F2 (F0 manual con
  `canal_origen='whatsapp'` **ya existe** en el agente N0 — ese N0 ya es la
  asistencia por IA mínima, y la bandeja con borrador `escalado` ya es la
  derivación a 1 humano), 4 historias con escenarios de aceptación, FR-W01–
  FR-W07, NFR-W01–W05, SC-W01–W03 y decisiones D-WSP-01/02/03 + D-CANAL-01.
  Sin sistemas externos reales: Meta queda como puerto (sin adaptador →
  503 «no configurado»), la regla de AGENTS.md no cambia. La propuesta del
  issue (`reservas.canal {recepcion, landing}` para «ingresos por canal»)
  queda registrada en §2 del paquete como **D-CANAL-01: propuesta sin
  implementar**, a la espera de decisión explícita del propietario. El issue
  #324 se comenta y queda ABIERTO hasta que el propietario autorice el
  adaptador Meta. Evidencia 2026-11-04: sin cambios de código (solo spec),
  regresión servicio 244/244, dominio 180/180.

## Contacto y leads de la landing — formulario propio (2026-11-04)

- [Hecha, P1] `v1-issue-20` punto 8 (GitHub `#308`, orden del propietario
  2026-11-04: «crear nuestro propio forms desde la landingpage que se integre
  directamente», captar leads para seguimiento; Formspree pierde
  independencia y cuesta) — DECISIÓN tomada y construida: formulario propio
  que postea a la plataforma; **Formspree retirado**. Contrato antes del
  código (spec-api-v1 «Contacto y leads de la landing», 50 operaciones):
  `POST /publico/leads` sin sesión (idempotencia propia, freno por IP,
  CORS solo `/publico/*`, tabla y espacio de claves propios — la clave del
  visitante nunca toca `claves_idempotencia`; los datos de contacto se
  guardan tal cual, son la agenda de seguimiento; la redacción NFR-A03 no
  aplica porque el texto no sale a terceros) y gestión interna
  `GET /hotel/leads` + `POST /hotel/leads/{id}/estado`
  (nuevo→contactado→cerrado con nota, auditoría, idempotencia interna;
  la gestión nunca borra). TDD: 16 pruebas nuevas en
  `servicio/tests/test_leads.py` (CA-LEAD-01..04). Implementación:
  migración `0012_leads.sql`, `servicio/leads.py`, rutas en
  `servicio/aplicacion.py`, bandeja `front/app/hotel/leads` (+ ítem de menú).
  Landing: `js/leads.js` (utilidades puras, mapeo a snake_case) +
  `formulario.js` postea a `{API_URL}/publico/leads` (`API_URL` default el
  front en `/api/*` según `front/vercel.json`; en E2E/local
  `window.LANDING_API_URL`), 3 tests nuevos (`node --test
  'landing/test/*.test.mjs'`, 12/12) y README actualizado. E2E nuevo
  `e2e/e2e-leads.mjs` (5 casos: envío real desde la landing con CORS del
  origen, rechazo sin persistir, bandeja, contactado con nota, cierre sin
  reapertura; el origen de la landing usa puerto fijo LANDING_PORT=4173
  porque el CORS del formulario se valida contra ORIGEN_LANDING).
  APRENDIZAJES: (1) `hasText` de Playwright con string es
  case-insensitive — matcheó el botón «Contactado» como si fuera la celda
  de estado; con regex sin flags es case-sensitive; (2) PUB-03 de
  reserva-publica quedó mal aislado: usaba el mismo rango que PUB-01, cuyo
  cupo consume al convertir — el caso prueba idempotencia, no cupo; ahora
  usa un rango propio libre (+20..+22 días). Evidencia 2026-11-04:
  servicio 260/260, dominio 180/180 (5 raíces), landing unitarios 12/12,
  E2E: base 56/56, operación 20/20, reserva-publica 6/6, landing 3/3,
  leads 5/5, agente 4/4.

## Sincronización de estado — 2026-11-05

Retomo de la construcción sin cambios de código: la revisión del tablero
mostró trabajo completado que el tablero aún registraba abierto.

- Revisión previa: `v1-issue-19` y `v1-issue-27` ya estaban resueltas en
  código (commits `7ae13cb` y `c170656`, con sus pruebas); faltaba solo el
  cierre administrativo.
- Tablero local (`construccion-v1.json`): 19, 21, 22, 23, 24, 27, 29, 30 →
  Hecha; 25 y 31 → En curso (25 falta publicación del CTA en el hosting;
  31 falta el adaptador, bloqueado por D-AGT-02).
- GitHub Issues: cerrados #317, #318 y #325 con comentario de evidencia;
  comentario de estado en #313, #319 y #324. Project n.º 2: #313 y #319
  movidas a «In Progress».
- Regresión servicio: 260/260 en tres corridas consecutivas; la primera
  corrida del día tuvo 1 fallo no capturado por nombre que no reprodujo en
  las tres siguientes — intermitente registrado, sin identidad aún.
- Dominio: 5 raíces OK. No se tocó código de producto.

## Sincronización de estado — 2026-11-05 (segunda pasada)

- Se descubrió trabajo completado sin reflejar: `v1-issue-15` estaba
  resuelta en código desde el 2026-11-04 (`c4f32dd`, TDD del turnover de
  salida; la issue #303 fue cerrada ese día con evidencia) pero el tablero
  local la mantenía «Bloqueada» y el Project n.º 2 en «Decisión humana»;
  el propio índice la listaba bloqueada. Corregidos los tres lugares.
- Épicas e hitos H1–H6 del tablero local (`v1-api`, `v1-back`, `v1-front`
  con sus historias y tareas): «Lista» → «Hecha» según la evidencia de la
  sección «Épicas y hitos» de este índice. Queda solo `v1-desp` (H7) como
  «Lista», coherente con las cuentas aún no verificadas.
- Project n.º 2: #303 y #325 movidas a «Done» (#325 cerrada hoy con
  evidencia de `c385e0f`).
- Landing (#313): verificada la carpeta `landing/` para publicación —
  unitarios 12/12 en verde y `js/config.js` apuntando al front productivo.
  La publicación en el hosting de hotelherencia.cl queda como único paso
  restante; el repo no tiene herramienta de despliegue para ese hosting
  (el runbook de `h7-despliegue.md` declara que no toca DNS ni
  hotelherencia.cl), así que requiere acceso del propietario.
- Caza del intermitente: 3 corridas adicionales, las 3 en verde — acumulado
  del día: 1 fallo no identificado al inicio y 5 corridas 260/260 seguidas.
- Regresión E2E de certificación (sin cambios de código; ambiente local con
  base `plataforma_e2e_landing`, front en build de producción): base 56/56,
  reserva-publica 6/6, leads 5/5, landing 3/3. Informe y capturas en
  `capturas/e2e-2026-11-05/INFORME.md`. Hallazgo: el freno de abuso del
  canal público (6/IP/min en memoria por proceso) 429a al repetir la suite
  de leads contra la misma instancia en la misma ventana — comportamiento
  esperado, corrida única 5/5. `e2e-operacion` y `e2e-agente` no corridas
  hoy (base dedicada/guion; última evidencia en verde 2026-11-04).

## Auditoría de jefatura 2026-11-03 → issues (2026-11-05)

La jefatura auditó el avance (corte 2026-11-03, commit `05b153c`; dictamen:
V1 interna operable, 10,0 % de avance evidenciado sobre 153 requisitos del
alcance completo). Las observaciones llegaron en `audit/` (informe HTML,
zip con matriz y hallazgos CSV). Verifiqué cada hallazgo contra el código
actual antes de crear issues: los de seguridad SEC-A01..A05 y OPS-A02 y
REL-A01 **siguen presentes**; UX-A01 ya estaba resuelto (#276–280, commits
`e49efa5`/`de4c2c9`); FUN-A01 parcialmente (#303 resuelta en `c4f32dd`;
#304/#305 bloqueadas por D-ENT-01); SEC-A00 ya tenía issue (#275).

Traducidos a GitHub Issues (repo + Project n.º 2 con su prioridad):

- **P1:** #326 SEC-A01 (Google ignora baja), #327 SEC-A02 (MFA sin
  reautenticación), #328 SEC-A03 (freno de login reinicia antes del TOTP),
  #329 SEC-A04 (aislamiento de empresa en el límite HTTP), #330 SEC-A05
  (state OAuth sin vincular al navegador), #331 REL-A01 (sin CI ni
  protección de main), #332 OPS-A01 (respaldo sin restauración demostrada —
  acción del propietario).
- **P2:** #333 OPS-A02 (salud sin readiness), #334 ARC-A01 (deuda de
  arquitectura/dependencias), #335 DOC-A01 (documentación y validadores).
- Comentarios cruzados: #275 (SEC-A00, con las dos precisiones técnicas de
  la auditoría) y #296 (FUN-A01, con el estado real de #303/#304/#305).

Tablero local: 10 ítems nuevos `v1-aud-01..10` en `construccion-v1.json`
(estado Lista, con enlace a su issue). La carpeta `audit/` queda sin
versionar (material de entrada de la jefatura; el contenido accionable ya
está en las issues).

## Correcciones de la auditoría — 2026-11-05 (noche)

Orden del propietario: «avanzar con las correcciones». TDD puro (tests en
rojo que reproducían cada vulnerabilidad → arreglo → regresión), contrato
antes que código cuando el contrato cambiaba, y cierre de cada issue con
evidencia. Commits: `18c89f5` (lote 1), `9478190` (SEC-A02), SEC-A05 y
CI en commits propios.

- [Hecha] **SEC-A01 (#326)** — `buscar_usuario_por_email` y
  `obtener_sesion_activa` exigen `activo=true`: Google ya no entra a cuentas
  dadas de baja y las sesiones vivas mueren con la baja.
- [Hecha] **SEC-A02 (#327)** — migración `0013` con `totp_secreto_pendiente`
  separado: el alta/reenrolamiento jamás desprotege la cuenta; reemplazar con
  2FA activo y `DELETE /cuenta/2fa` exigen la clave actual (401); el QR solo
  expone el pendiente. Contrato enmendado (spec-api-v1), front `/cuenta` pide
  la clave, TFA-01 extendida (alta + login con TOTP + baja con
  reautenticación) — E2E base 56/56.
- [Hecha] **SEC-A03 (#328)** — el freno de logins solo se reinicia al
  completar TODA la autenticación: el segundo factor ya no queda sin freno de
  fuerza bruta (5 TOTPs malos → 429).
- [Hecha] **SEC-A04 (#329)** — `_requerir_sesion` deniega 403 a sesión de
  empresa distinta al núcleo en el límite HTTP (2 tests del comportamiento
  viejo de «listas vacías» actualizados al 403).
- [Hecha] **SEC-A05 (#330)** — state OAuth atado a cookie HttpOnly
  `oauth_tx` (10 min, path /auth); `tomar` consume el state en todo intento y
  exige coincidencia: state de otro navegador → 400 y gastado. Cierra el
  login CSRF. Límite: transacciones en memoria (multi-réplica pendiente).
- [Hecha] **OPS-A02 (#333)** — `GET /readiness` con consulta real a la base y
  estado de migraciones (503 si cae); `/salud` sigue siendo liveness pura.
  spec-api-v1 pasa a 51 operaciones.
- [En curso] **REL-A01 (#331)** — CI creado (`.github/workflows/ci.yml`):
  dominio 5 raíces + servicio contra PostgreSQL 17 + unitarios landing +
  build front, en push/PR. Falta solo el paso del propietario: exigir el
  check en la protección de rama (ruleset).
- Tests nuevos: `servicio/tests/test_auditoria_seguridad.py` (17 casos). La
  suite del servicio pasa de 260 a 277 pruebas, dominio 5 raíces OK, landing
  12/12, E2E base 56/56 (tras SEC-A02).

## Segunda pasada de cierre — 2026-11-05 (noche)

- **#275 (rotación de secretos) cerrada** por orden del propietario: rotados
  en los gestores del proveedor; quedan los recordatorios técnicos de la
  auditoría (ADMIN_CLAVE no cambia la clave persistida por sí sola;
  credencial OAuth ≠ clave Gmail; registrar fecha/alcance).
- [Hecha] **DOC-A01 (#335)** — `scripts/validar_estado_v1.py` (13
  comprobaciones: specs gobernantes, operaciones declaradas == filas (51),
  tablero, evidencia citada, landing, `.env`, CI); el validador del corpus
  heredado se archivó con el corpus cerrado. Ficha viva
  `docs/arquitectura/estado-v1.md` con los números vigentes. README
  sincronizado (público, construcción V1, secretos rotados).
- [Hecha] **ARC-A01 (#334)** — dependencias fijadas en los tres
  manifiestos (lock reproducible); entrypoints de Vercel aclarados (vigentes,
  una raíz de build cada uno); spec-backend-v1 sincronizada al flujo real.
  Resta el split de `aplicacion.py` y la revisión de licencias.
- [Hecha] **ARC-A01 — split y licencias (misma noche)** —
  `aplicacion.py` 1.711 → 352 líneas: rutas en `servicio/rutas/`
  (`acceso` 15 rutas, `hotel` 27 incluye solicitudes/leads, `agente` 7) con
  dependencias compartidas en `rutas/comun.py` y modelos en
  `rutas/modelos.py`; comportamiento idéntico verificado por la regresión
  completa del servicio. Licencias revisadas y documentadas en
  spec-backend-v1 (MIT/BSD salvo psycopg LGPL-3.0 con nota de uso).

## Tercera pasada — 2026-11-05 (órdenes del propietario)

- [Hecha] **REL-A01 (#331) redirigida** — el propietario descartó GitHub
  Actions («no me sirve si va a estar bloqueando deploy o deteniendo la
  construcción… no aplicar»): workflow eliminado y la verificación es
  **integral, local y previa al despliegue** — `scripts/verificar_local.py`
  (estado del repo, dominio 5 raíces, suite del servicio contra base dedicada
  creada al vuelo, landing, build de producción del front). Compuerta
  documentada en `h7-despliegue.md`: solo se aprueba un deploy con TODO en
  verde.
- [En curso] **OPS-A01 (#332) — prueba de restauración construida** —
  `scripts/ensayo_restauracion.py` (hechos sobre la base restaurada:
  migraciones, 18 tablas legibles, invariantes de reservas/pagos/auditoría),
  validado con un ciclo local completo (dump → restore → «OPERABLE»), y
  runbook `docs/arquitectura/ensayo-restauracion-pitr.md` con el procedimiento
  desde Railway (fork del PITR → ensayo → medir RPO/RTO → destruir). Resta el
  paso ejecutivo en Railway (dashboard; el CLI local está roto) con registro
  de RPO/RTO medidos en la issue.
