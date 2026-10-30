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

## Aceptación de H7

Las tres piezas juntas: front de Vercel leyendo solo `API_BASE_URL`, contrato
servido por el backend de Railway, persistencia real en su PostgreSQL;
login usuario/clave+TOTP y login con Google funcionando en producción.
