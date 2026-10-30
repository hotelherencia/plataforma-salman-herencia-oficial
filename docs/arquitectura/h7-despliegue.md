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
`entrypoint: api/index.py`). El rewrite `/api/(.*)` expone la API
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

**Primer build en Vercel (2026-10-30, commit `4905942`): falló con
`FASTAPI_ENTRYPOINT_NOT_FOUND`.** El build de Vercel no toma el
`entrypoint` declarado dentro de `services` del `vercel.json`: exige el
`app` en una ruta convencional (`api/index.py`, `main.py`, `app.py`, …) o
en `tool.vercel.entrypoint` de `pyproject.toml`, en formato `modulo:variable`
(lo indica el propio mensaje del build: `entrypoint = "api_vercel:app"`).
Corrección aplicada el mismo día: `api/index.py` en la raíz reexporta
`servicio.api_vercel.app` y `pyproject.toml` fija `[tool.vercel].entrypoint =
"api.index:app"`. Para builds cuya raíz es `servicio/` (proyecto `-ag24`)
existe `servicio/pyproject.toml` con `entrypoint = "api_vercel:app"`;
`api_vercel.py` se auto-inserta la raíz del repo en `sys.path`. Los dos
`pyproject.toml` solo traen la tabla `[tool.vercel]`: no afectan a pip ni a
Railway (sigue instalando desde `requirements.txt` de la raíz).

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
  `api/index.py` + `pyproject.toml` gobiernan; entonces `API_BASE_URL=/api` y
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

## Aceptación de H7

Las tres piezas juntas: front de Vercel leyendo solo `API_BASE_URL`, contrato
servido por el backend de Railway, persistencia real en su PostgreSQL;
login usuario/clave+TOTP y login con Google funcionando en producción.
