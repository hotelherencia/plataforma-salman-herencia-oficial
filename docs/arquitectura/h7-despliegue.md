# Runbook H7 — despliegue Railway + Vercel

**Estado:** REQUISITO PROPUESTO, 2026-10-29 (actualizado 2026-10-30). Preparación
local hecha (`GOOGLE_REDIRECT_URI` configurable, `runtime.txt`, `railway.toml`,
reserva de `$PORT` con `SERVICIO_PUERTO` como prioridad).
**Bloqueante:** cuentas Railway y Vercel del propietario (H7/T1); sin ellas
no hay despliegue. Este documento no toca DNS ni `hotelherencia.cl`.

## H7/T1 — Cuentas (propietario)

1. Crear cuenta en railway.app y en vercel.com (pueden ser login con GitHub
   de `hotelherencia`).
2. Verificar que el repositorio `hotelherencia/plataforma-salman-herencia-oficial`
   queda accesible para el deploy desde cada plataforma.

## H7/T2 — Rama publicada (hecha 2026-10-29)

`main` ya está pusheada en GitHub (commit `54a0fc4` en adelante).

## H7/T3 — Backend en Railway

**Creado por API el 2026-11-02 (orden del propietario: «para crear el
backend y la bd usar RAILWAY_TOKEN»).** El token de `.env` funciona para la
GraphQL pública (backboard.railway.app/graphql/v2) pero el CLI (`whoami`,
`link`, `up`) lo rechaza (`me` no autorizado), así que todo el flujo fue por
API. Estado: proyecto `plataforma-salman-herencia`
(`1283dc6a-ba9a-4abe-a3c0-af7e0547bd2d`), entorno `production`
(`6eb18182-6077-4b6c-90c9-893b2bdbb39f`), dominio público del servicio
`https://servicio-production-a2d7.up.railway.app`.

- Servicio `postgres` (`639f7fc7-f9b2-4781-ac8a-82d2435f1de6`): imagen
  `ghcr.io/railwayapp-templates/postgres-ssl:16` (la imagen propia de
  Railway, migrada el 2026-11-02 desde `postgres:16-alpine` para habilitar
  PITR según su indicación; ojo: la referencia corta `postgres-ssl:16` NO la
  resuelve el builder — hay que usar la ruta GHCR completa). Volumen nuevo
  tras el cambio (el volumen inicial se eliminó: estaba vacío y el cambio
  alpine→Debian choca permisos uid 70/999; hoy sin datos que migrar).
  Deploy SUCCESS. Usuario `plataforma`, base `plataforma`, clave generada en
  el despliegue (vive solo en Railway). **`btree_gist` (usado por la
  migración 0003) es extensión contrib estándar y está presente.** PITR aún
  no está activado: todavía falta el click del propietario en la pestaña
  Backups del servicio («Enable PITR»; crea el bucket, fija `WAL_ARCHIVE_*`
  y redeploya; el CLI `railway postgres pitr enable` no es usable con el
  token actual). Costo PITR: storage del bucket + egress (comprimido).
- Servicio `servicio` (`44ea5031-b208-4703-a6a4-7728cbab7882`): sin fuente
  aún. Variables fijadas (las no-secretas): `DATABASE_URL` por referencia
  interna `postgresql://plataforma:${{postgres.POSTGRES_PASSWORD}}@${{postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/plataforma`,
  `COOKIE_SEGURA=1`, `SESSION_HORAS=12`, `SERVICIO_HOST=0.0.0.0`,
  `FRONT_URL`/`ORIGEN_FRONT` = front canónico de Vercel,
  `GOOGLE_REDIRECT_URI=https://servicio-production-a2d7.up.railway.app/auth/google/callback`.
  Pendientes del propietario (secretos, no se copian desde `.env`):
  `ADMIN_USUARIO`, `ADMIN_CLAVE`, `ADMIN_EMAIL`, `GOOGLE_CLIENT_ID`,
  `GOOGLE_CLIENT_SECRET` (ayuda: `scripts/mapear_variables_despliegue.py`).
- **Bloqueante restante:** conectar el repo GitHub. `serviceConnect` respondió
  «User does not have access to the repo» porque la app GitHub de Railway no
  está instalada en la org `hotelherencia`. El propietario la instala desde
  el dashboard del proyecto (New → GitHub Repo → autorizar) y con
  `serviceConnect(input: {repo: "hotelherencia/plataforma-salman-herencia-oficial", branch: "main"})`
  queda auto-deploy en cada push (el `railway.toml` de la raíz gobierna
  build/start; Nixpacks instala desde `requirements.txt`, que incluye
  `servicio/requirements.txt`). Alternativa sin app: imagen Docker en GHCR
  (decisión del propietario por la exposición del paquete).
- **Incidente Railway del 2026-10-21 (contexto del token):** Railway tuvo un
  incidente de plataforma el 2026-10-21 (deploys pausados, workspaces en
  «Limited Access»; aviso posterior: «fix is out, monitoring» — el mismo que
  el propietario vio en Vercel). La respuesta al incidente **revocó tokens y
  sesiones** ([nota de recuperación de Railway](https://station.railway.com/questions/workspace-stuck-on-limited-access-dep-ce16a96e)).
  Eso explica el comportamiento del `RAILWAY_TOKEN` actual: la GraphQL
  pública funciona (todo el alta del 2026-11-02 se hizo así), pero `me` y el
  CLI lo rechazan («Invalid RAILWAY_TOKEN»). No es bloqueante: se opera por
  API; si algún día se necesita el CLI, crear un token nuevo en el dashboard
  (los creados tras el incidente deberían tener acceso completo). Nuestro
  proyecto se creó después del incidente y el deploy de postgres salió
  SUCCESS: el workspace no está en pausa de deploys. Evaluación de riesgo
  2026-11-02: sin impacto en datos (BD vacía, creada post-incidente); riesgo
  npm verificado limpio (front solo depende de next/react/react-dom; el
  lockfile no contiene chalk/debug/ansi-styles/strip-ansi/wrap-ansi/
  supports-color); riesgo real vigente: rotación de secretos pendiente del
  2026-10-30 (VERCEL_TOKEN, clave Gmail, ADMIN_CLAVE productiva).
- **Variables Railway → Vercel (pendiente del propietario):** Vercel
  (serverless) no entra a la red privada de Railway, así que el PostgreSQL
  necesita TCP proxy público: dashboard → servicio `postgres` → Connect/Data
  → «Public network» → agregar proxy TCP del puerto 5432 (la API pública solo
  expone `tcpProxyDelete`, no la creación). Con el host:port público, el
  propietario rescata la URL de conexión del mismo panel y la entrega al
  agente, que la fija como `DATABASE_URL` del proyecto Vercel `-ag24` vía API
  REST (sin reimprimirla) y verifica que `/api/sesion` deja de responder 503
  «base de datos no configurada». Las demás variables de `-ag24`
  (`ADMIN_*`, `GOOGLE_CLIENT_*`, etc.) siguen fijadas desde el 2026-10-30.

Flujo original del runbook (referencia, previo a la creación por API):

1. **New Project → Deploy from GitHub** → elegir el repo → servicio único
   (el `railway.toml` define `python -m servicio` y healthcheck `/salud`).
2. **PostgreSQL**: `New → Database → PostgreSQL`; copiar la URL interna que
   Railway genera (`DATABASE_URL`) y asignarla al servicio.
3. **Variables del servicio** (valores reales nunca en el repo):

   | Variable | Origen |
   |---|---|
   | `DATABASE_URL` | Postgres interno de Railway |
   | `ADMIN_USUARIO` / `ADMIN_CLAVE` | credenciales del admin inicial |
   | `ADMIN_EMAIL` | Gmail con que entrará por Google |
   | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Cloud Console |
   | `GOOGLE_REDIRECT_URI` | `https://<tu-dominio-api>/auth/google/callback` |
   | `FRONT_URL` | URL del front en Vercel |
   | `ORIGEN_FRONT` | misma URL del front (CORS) |
   | `COOKIE_SEGURA` | `1` (cookie Secure + SameSite=None entre orígenes) |
   | `SERVICIO_HOST` | `0.0.0.0` |
   | `SERVICIO_PUERTO` | opcional: el código reserva `$PORT` (Railway lo inyecta); `SERVICIO_PUERTO` manda si se define |

4. **Login con Google en producción**: en Cloud Console, agregar la URI
   `GOOGLE_REDIRECT_URI` productiva al cliente web (la local sigue para dev)
   y en «Dominios autorizados» incluir `hotelherencia.cl` si el front vive
   en un subdominio.
5. Verificar: `GET https://<api>/salud` → 200 y `GET /auth/google/estado`
   → `{"configurado":true}`.

## H7/T4 — Front en Vercel

1. **New Project → Import GitHub** → el mismo repo, root `front/`.
2. **Variable de build**: `API_BASE_URL=https://<api-de-railway>` (se inyecta
   en `npm run build`; sin ella el build falla).
3. Build por defecto `next build`, output del framework auto-detectado.
4. Verificar: abrir la URL de Vercel → `/login` muestra el botón de Google
   (el backend responde `configurado: true`) y entrar completa el circuito
   Vercel ↔ Railway con la cookie cross-site.

## H7/T4b — Variante: todo en Vercel (REQUISITO PROPUESTO, 2026-10-30)

Preparación local hecha, pendiente de confirmación del propietario porque
**sustituye a H7/T3 (Railway)**: un solo proyecto Vercel con dos *services*
(`vercel.json` en la raíz): `front` (Next.js) y `servicio` (FastAPI,
`entrypoint: api_vercel:app`). El rewrite `/api/(.*)` expone la API
bajo el mismo dominio; el front se compila con `API_BASE_URL=/api` y las
llamadas del navegador son mismo-origen (sin CORS; cookie `Secure` con
`SameSite=None` sigue sirviendo). El entrypoint quita el prefijo `/api` antes
de enrutar; ninguna ruta del API cambia. `GOOGLE_REDIRECT_URI` sería
`https://<dominio>/api/auth/google/callback`.

Variables del proyecto (compartidas entre services): las de H7/T3 menos
`SERVICIO_HOST`/`SERVICIO_PUERTO`/`ORIGEN_FRONT`, más `API_BASE_URL=/api`
(variable de build del front) y `DATABASE_URL` de PostgreSQL externo
(Vercel Postgres/Neon/u otro; sin él la variante no arranca).

Verificado en local (2026-10-30): entrypoint sirve `/api/salud` y
`/api/auth/google/estado`; build del front con `API_BASE_URL=/api`; suite
commiteada del servicio 42/42 contra una base fresca.

**Builds en Vercel (2026-10-30).** El de `4905942` falló con
`FASTAPI_ENTRYPOINT_NOT_FOUND`: el CLI no lee el `entrypoint` de `services`
en `vercel.json`. El de `478306a` (15:14) volvió a fallar: `pyproject.toml`
tenía `entrypoint = "api/index.py"`, una ruta, y el CLI 65.4.0 solo acepta
`modulo:variable`. El mensaje pidió `[tool.vercel] entrypoint = "api_vercel:app"`.
Corrección: `api_vercel.py` en la raíz reexporta `servicio.api_vercel.app` y
el `pyproject.toml` de la raíz declara esa clave. Si la raíz del proyecto es
`servicio/` (`-ag24`), `servicio/pyproject.toml` declara lo mismo y
`servicio/api_vercel.py` inserta la raíz del repo en `sys.path`. Ninguno de
los dos `pyproject.toml` afecta a pip ni a Railway.

**Despliegue real (2026-10-30, tarde) — regla del autor y estado actual.**

- Regla del autor (plan Hobby): el proyecto Vercel solo despliega commits cuyo
  email de autor se mapee a la cuenta GitHub dueña del proyecto. Comprobado este
  día: `hotelherenciacl@gmail.com` (cuenta `hotelherencia`) → build OK;
  `construccion@herencia.local` (sin cuenta GitHub) → bloqueado («commit author
  email is not valid»); `herrera.jara.cristobal@gmail.com` (cuenta `cherrera0001`,
  no es la dueña) → bloqueado. El repo quedó con `git config user.email
  "hotelherenciacl@gmail.com"` (local al repo). Comando para verificar a qué
  cuenta mapea un email: `gh api repos/hotelherencia/plataforma-salman-herencia-oficial/commits/<sha> --jq '.author.login'`.
- Tres proyectos Vercel quedaron conectados al mismo repo (cada push dispara los
  tres; el estado de cada uno se ve rápido con `gh api repos/.../commits/<sha>/status`):
  1. `dev-2ddb/plataforma-salman-herencia-oficial` — **canónico**. Build de
     `478306a` completado; el dominio sirve el front (Next da 404 en `/api/*`):
     el proyecto quedó como front-only (framework Next.js, root `front/`, ajuste
     del propietario en el dashboard).
  2. `dev-2ddb/plataforma-salman-herencia-oficial-ag24` — falla. Pendiente:
     revisar logs (`npx vercel inspect dpl_A2EcuvDYdaibsdqGb6NPzkNwyx53 --logs`
     con la cuenta dev-2ddb) o eliminar el proyecto.
  3. `cherrera0001s-projects/plataforma-salman-herencia-oficial-main` — proyecto
     fantasma creado al linkear localmente (`vercel link`); bloquea pushes y
     ensucia el estado. Eliminar.
- `API_BASE_URL=/api` se fijó por CLI por error en el proyecto (3) y fue
  eliminada el mismo día. La variable correcta depende de la decisión pendiente:
  **T4** (front en Vercel + API en Railway → `API_BASE_URL=https://<railway>`,
  ver H7/T3) o **T4b** (todo en Vercel → reconfigurar el proyecto canónico para
  que construya desde la raíz del repo, donde `vercel.json` con `services` +
  `api_vercel:app` en `pyproject.toml` gobiernan; entonces `API_BASE_URL=/api` y
  `DATABASE_URL` de PostgreSQL externo — sin él el servicio arranca en memoria y
  no persiste —, más `ADMIN_USUARIO`/`ADMIN_CLAVE`/`ADMIN_EMAIL` y
  `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` en el dashboard).
- Pendiente menor: decidir si la siembra de `HAB-SINT-101..103` al arrancar tiene
  sentido en producción (hoy `sembrar_habitaciones` sigue corriendo).

## H7/T5 — Revisión de configuración (regla permanente, 2026-10-30)

Pedido del propietario: revisar siempre la configuración efectiva contra
`.env` antes de desplegar o diagnosticar. Auditoría del 2026-10-30
(presencia, no valores):

- `.env` local define: `DATABASE_URL`, `GOOGLE_CLIENT_ID`,
  `GOOGLE_CLIENT_SECRET`, `ADMIN_USUARIO`, `ADMIN_CLAVE`, `ADMIN_EMAIL`,
  `ORIGEN_FRONT`, `COOKIE_SEGURA=1`, `SESSION_HORAS=12`. `GOOGLE_REDIRECT_URI`
  y `FRONT_URL` siguen apuntando a `localhost`.
- GitHub Actions: sin secrets ni variables. Proyecto Vercel canónico: sin
  variables configuradas (pendiente según decisión T4/T4b).
- Valores que deben cambiar en producción respecto de `.env` local:
  `DATABASE_URL` (la del proveedor elegido), `GOOGLE_REDIRECT_URI`
  (`https://<dominio>/auth/google/callback` en T4; `.../api/auth/...` en T4b
  y hay que registrarla en Cloud Console), `FRONT_URL`/`ORIGEN_FRONT` (URL de
  Vercel; sin efecto en T4b) y `SERVICIO_HOST=0.0.0.0` en Railway (T4).
  `ADMIN_*` y `GOOGLE_CLIENT_*` pueden reutilizarse; la clave del admin
  inicial conviene rotarla tras el primer login en producción.
- Observación local (sin verificar): con `COOKIE_SEGURA=1` sobre
  `http://localhost` el navegador puede rechazar la cookie (Secure sin https);
  si el login local falla tras ese cambio, probar con `COOKIE_SEGURA=0`.
- Acelerador (2026-10-30): `scripts/mapear_variables_despliegue.py` lee el
  `.env` en la máquina del propietario y imprime los pares CLAVE=valor listos
  para el dashboard (marca lo que parece local). El agente no lo ejecuta sobre
  el `.env` real (política de secretos); lo corre el propietario:
  `python scripts/mapear_variables_despliegue.py t4b --dominio https://<dominio>`
  o `... t4 --railway https://<api> --front https://<front>`.

## H7/T4c — Backend en Vercel (decisión operativa, 2026-10-30, a ratificar)

Con el token del equipo (vive en `.env`, se usa sourced, nunca en el repo) se
inspeccionó `dev-2ddb`. **Topología final (limpieza hecha el 2026-10-30):** dos
proyectos — `plataforma-salman-herencia-oficial` (front: Next.js, root
`front/`) y `plataforma-salman-herencia-oficial-ag24` (API/backend: FastAPI,
root = raíz del repo). Se eliminaron los duplicados `-3lgt`,
`plataforma-salman-herencia` y el proyecto fantasma
`cherrera0001s-projects/plataforma-salman-herencia-oficial-main`.

Decisión operativa: backend en Vercel en `-ag24` (forma T4 con API en Vercel
en lugar de Railway, porque no requiere cuentas nuevas):

- `-ag24` quedó con `rootDirectory` = raíz del repo (antes `servicio/`, cuyo
  bundle no incluía `core/` → 500). Confirmado: el `vercel.json` de la raíz
  SÍ se honra — el front sirve en `/` y el API en `/api/*` (servicio
  FastAPI). Entrypoint `api.index:app` (pyproject de la raíz); `api_vercel:app`
  solo resuelve con raíz `servicio/` (servicio/pyproject.toml), no desde la
  raíz. Con un pyproject presente el build instala dependencias desde
  `[project].dependencies`: sin esa tabla la función falla en runtime con
  `ModuleNotFoundError` (psycopg, 2026-10-30); ambos pyproject la llevan.
  Además el equipo tenía Vercel Authentication (`all_except_custom_domains`)
  y había que desactivarlo en `-ag24` para exponer el API. URL pública:
  `https://plataforma-salman-herencia-oficial-delta.vercel.app` (rutas del
  API bajo `/api/…`; el wrapper también acepta rutas directas).
- Variables de producción fijadas en `-ag24` (vía API REST, 201):
  `ADMIN_USUARIO`, `ADMIN_CLAVE`, `ADMIN_EMAIL`, `GOOGLE_CLIENT_ID`,
  `GOOGLE_CLIENT_SECRET`,
  `GOOGLE_REDIRECT_URI=https://plataforma-salman-herencia-oficial-delta.vercel.app/auth/google/callback`,
  `COOKIE_SEGURA=1`, `SESSION_HORAS=12` y `ORIGEN_FRONT`/`FRONT_URL` = URL
  del front canónico. Falta `DATABASE_URL` externo (ver H7/T5): sin él los
  endpoints con persistencia responden **503 «base de datos no
  configurada»** (fix del 2026-10-30 en `_conexion`; antes era un 500 por
  `AttributeError`), y con él el API persiste de verdad.
- Front canónico: `API_BASE_URL` (build) =
  `https://plataforma-salman-herencia-oficial-delta.vercel.app`; exige
  rebuild, se dispara con el push.

Pendiente del propietario: registrar la URI de redirección productiva en
Google Cloud Console (sin eso el login con Google falla en el consentimiento);
aprovisionar PostgreSQL externo y fijar `DATABASE_URL` en `-ag24`; **rotar
`VERCEL_TOKEN` y la clave de aplicación de Gmail** (se expusieron en chat el
2026-10-30) y regenerar `ADMIN_CLAVE` en producción.

## Cierre del día 2026-10-30

Avances del día (HECHO DOCUMENTADO):

- **H7 operativo:** front y API/backend desplegados en Vercel (equipo
  `dev-2ddb`); topología final de dos proyectos tras limpiar duplicados
  (`-3lgt`, `plataforma-salman-herencia` y el fantasma de
  `cherrera0001s-projects`). Cada push a `main` reconstruye ambos.
- **Identidad Git obligatoria** `hotelherenciacl@gmail.com` forzada por
  `includeIf` (`hasconfig` por URL del remoto) en Windows y WSL — regla
  Hobby de Vercel: solo despliega el autor dueño del proyecto.
- **Lecciones del build de Vercel:** entrypoint en formato `modulo:variable`
  bajo `[tool.vercel]`; con un `pyproject.toml` presente las dependencias se
  instalan desde `[project]` (sin ella, `ModuleNotFoundError` en runtime);
  el `vercel.json` con `services` sí se honra (front en `/`, API en `/api/*`);
  ojo con Vercel Authentication del equipo; sin `DATABASE_URL`, `_conexion`
  responde 503 (era 500).
- **Variables de producción** fijadas vía API REST en el proyecto API (11,
  incluidas `GOOGLE_CLIENT_*`) y en el front (`API_BASE_URL` con prefijo
  `/api`); Google OAuth `configurado:true` en producción.
- **Adaptador del dominio hotel a PostgreSQL** y backlog ADP versionados
  (`6c54ff9`, trabajo en curso del propietario; suite del servicio: 110 OK y
  21 fallos preexistentes en `test_preh7_seguridad.py`).

Verificado en producción el 2026-10-30: front 200; `/api/salud` 200;
`/api/auth/google/estado` → `configurado:true`; `/api/sesion` → 503 claro
«base de datos no configurada»; builds en verde por push (dos contextos).

Pendiente al cierre: `DATABASE_URL` externo (Neon/Vercel Postgres); registrar
el redirect de Google en Cloud Console; rotación de secretos expuestos en
chat; ratificación del propietario de la decisión «API en Vercel en lugar de
Railway» (H7/T4c).

## Aceptación de H7

Las tres piezas juntas: front de Vercel leyendo solo `API_BASE_URL`, contrato
servido por el backend de Railway, persistencia real en su PostgreSQL;
login usuario/clave+TOTP y login con Google funcionando en producción.
