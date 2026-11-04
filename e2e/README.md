# Suite E2E de la plataforma V1

Revisión ejecutable de los flujos declarados e integrados en V1 (módulo
hotel + rutas de acceso/cuenta), en local, con navegador real (Chromium) y
datos 100 % sintéticos. Lee `capturas/e2e-AAAA-MM-DD/INFORME.md` para la
matriz de aceptación y su evidencia.

## Requisitos

- Backend en `127.0.0.1:8080`: base **sintética y desechable** (p. ej.
  `plataforma_e2e`), `ADMIN_USUARIO`/`ADMIN_CLAVE` en el entorno,
  `ORIGEN_FRONT=http://127.0.0.1:3000`, migraciones aplicadas al arrancar.
- Front en `127.0.0.1:3000`: `npm run build && npm run start` en `front/`
  con `API_BASE_URL=http://127.0.0.1:8080` (siempre el build de producción;
  en `next dev` un proxy que corte el WebSocket HMR deja la app sin
  hidratar, ver «Operación continua» en `docs/arquitectura/h7-despliegue.md`).

## Correr la suite

```bash
cd e2e
npm install     # solo la primera vez
npm run e2e
```

Salida: un `✓/✗` por flujo, el resumen `N/N APROBADOS, 0 FALLIDOS` y
`e2e-resultados.json` (misma carpeta).

## Re-ejecución y datos

La suite es **re-ejecutable sin resetear la base**: siembra usuarios y
habitaciones con identificadores únicos por corrida (`RUN`) y todas las
mutaciones llevan claves de idempotencia únicas por corrida. Las corridas
anteriores dejan filas en la base sintética; no interfieren.

## Artefactos

- `e2e-resultados.json`: se **regenera en cada corrida**. Es la evidencia
  machine-readable de la aceptación: se versiona **junto con** el INFORME.md
  de la misma fecha tras cada revisión formal, y fuera de eso puede ignorarse
  el diff. Si un diff aparece en un commit de otro tema, es ruido: regenerar
  con una corrida completa o restaurarlo.
- `capturas/e2e-AAAA-MM-DD/*.png`: evidencia visual numerada en el orden de
  los casos; la ruta queda registrada en cada corrida que llama a `evidencia`.

## Suite de operación (2026-11-03)

`e2e-operacion.mjs` cubre mantenedor de habitaciones, consulta de reservas,
ocupación e indicadores (`docs/arquitectura/spec-hotel-operacion-v1.md` §6).
No toca `e2e.mjs`; mismos requisitos. Resultados en
`e2e-operacion-resultados.json`, capturas `op-NN-*.png`.

```bash
FRONT_URL=http://127.0.0.1:3000 API_URL=http://127.0.0.1:8080 node e2e-operacion.mjs
```

**Base de pruebas:** la corrida formal debe usar una base dedicada
(p. ej. `DATABASE_URL_TEST=.../plataforma_test_operacion`) o una desechable
recién creada: con otra sesión escribiendo en la base compartida, los tests
fallan por interferencia (deadlocks, sesiones borradas). Ver V1-ISSUE-08.

## Suite de la landing (2026-11-04)

`e2e-landing.mjs` (V1-ISSUE-25, CA-PUB-12) sirve `landing/` en un puerto
efímero y verifica con navegador real que el CTA «Consultar reserva» abre
`/reservar` del front con inicio/fin/personas (PUB-07) y que rangos
inválidos o fechas vacías se rechazan en la landing sin navegar (PUB-08/09;
la validación espeja la de `/reservar`). Solo requiere el front en
FRONT_URL; la base del front se inyecta con `window.LANDING_PLATAFORMA_URL`
(addInitScript), sin tocar los estáticos.

```bash
FRONT_URL=http://127.0.0.1:3000 node e2e-landing.mjs
```

## Suite del agente de reservas (2026-11-04)

`e2e-agente.mjs` (V1-ISSUE-30) cubre la bandeja `/hotel/agente` con el modelo
guionado (NFR-A04): flujo feliz con redacción de datos personales, portapapeles
y aprobación releída; recotización al aprobar con oferta vencida («la oferta
cambió» → borrador nuevo); escalada por decisión inválida sin efectos; y rol
caja sin menú ni acceso. Requiere la API con el guion en el entorno (una
corrida por arranque de la API) y psql + `E2E_DB_URL` (AG-E05 envejece la
vigencia de la oferta directo en la base de pruebas):

```bash
export AGENTE_GUION_JSON="$(node e2e-agente.mjs --guion)"
# arrancar la API con ese entorno y el front (build con API_BASE_URL horneado)
FRONT_URL=http://127.0.0.1:3000 API_URL=http://127.0.0.1:8080 \
  E2E_DB_URL=postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_e2e_agente \
  node e2e-agente.mjs
```

Resultados en `e2e-agente-resultados.json`, capturas `ag-NN-*.png`. AG-E03
(503 sin adaptador) se cubre en servicio (AG-S07) y el guion es obligatorio
aquí. Las aserciones se anclan al ítem 0 de la oferta tal como lo compone el
servidor (la oferta ordena por id): la suite es re-ejecutable en la misma base
sin reset, como las demás.

**Bases recién creadas en `e2e-reserva-publica.mjs`:** PUB-01 auto-selecciona
la primera opción de la oferta (orden `ORDER BY id` de `reservas.oferta`) y
la convierte; PUB-03 pide las mismas fechas y exige la habitación de la
corrida. Si la base está vacía salvo esa habitación, PUB-02 y PUB-03 fallan
siempre (oferta vacía u ocupada). Sembrar antes una habitación vendible
ajena con tarifa que ordene antes, p. ej. `HAB-PUB-000000DECOY` con tarifa
2026–2027 — es el estado habitual de la base compartida `plataforma_e2e`.
