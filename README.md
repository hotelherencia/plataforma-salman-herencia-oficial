# plataforma-salman-herencia

Plataforma **core multi-vertical** del Grupo Salman, **en definición** para
la **empresa base Herencia** (Hotel Herencia). Esta base **no es la vertical
hotel**: es la plataforma compartida completa — núcleo transversal más cuatro
verticales de negocio. La vertical hotel es solo una de las cuatro.

## Qué contiene

- `specs/000-core/` — núcleo compartido: identidad, autorización, límites de
  tenant, adaptadores de pagos/documentos/comunicación y auditoría.
- `specs/001-cafeteria-mesas-pos/` — vertical cafetería (mesas, pedidos, POS).
- `specs/002-hotel-reservas-concierge/` — vertical hotel (reservas, operación,
  concierge).
- `specs/003-inmobiliaria-comercial/` y `specs/004-constructora-obra/` —
  verticales inmobiliaria y constructora.
- `servicio/` — proceso real de la plataforma (spec-backend-v1): FastAPI +
  PostgreSQL 17. Arranque: `.venv/bin/python -m servicio` (configuración solo
  por variables de entorno; dependencias en `servicio/requirements.txt`).
  Su prueba de arranque: `servicio/tests/test_h1.py`. El prototipo
  `plataforma/` queda obsoleto con este servicio.
- `backlog/` — índice y carga de los 150 ítems del backlog, plan vertical del
  hotel, hojas de decisiones, actas (firma del hotel y cierre de la definición
  heredada) y nota de depuración del árbol.
- `core/` — espacio del núcleo. `verticales/` — código por vertical. En ambos
  hay módulos en memoria y sin red (incremento 0 del hotel; incremento 1 del
  núcleo y de las cuatro verticales): la especificación ejecutable del dominio,
  **PROPUESTA TÉCNICA no ratificada** (marco en `docs/arquitectura/plataforma.md`).
  `scripts/` — validadores documentales y carga del backlog a GitHub.
- `docs/` — documentación que no es spec activa: `docs/definicion-herencia/`
  (definición SDD V1.0 heredada, pendiente de firma del propietario; conservada
  por falta de traza), `docs/arquitectura/` (propuesta técnica de la plataforma
  y sus flujos Mermaid, no ratificada), `docs/investigacion-competitiva/`
  (dudas de base Q-* contrastadas con práctica de mercado; no cierran decisiones),
  `docs/archivo-no-construccion/` (notas de análisis) y
  `docs/historial-consolidacion.md` (README histórico).

## Cómo correr en local (desarrollo)

Dirección local por defecto: **http://127.0.0.1:8080** (cámbiala con
`SERVICIO_PUERTO`/`SERVICIO_HOST`). Todo es configuración por variables de
entorno; el repositorio no lleva `.env`.

```bash
# 1) Base de datos local (una sola vez)
sudo -u postgres createuser -P plataforma     # clave sintética de desarrollo
sudo -u postgres createdb -O plataforma plataforma

# 2) Dependencias del servicio (una sola vez)
python3 -m venv .venv
.venv/bin/pip install -r servicio/requirements.txt

# 3) Arrancar el servicio
export DATABASE_URL="postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma"
export ADMIN_USUARIO=admin
export ADMIN_CLAVE="clave-admin-sintetica"
.venv/bin/python -m servicio
```

Probar: `curl http://127.0.0.1:8080/salud`; `POST /sesion` con
`{"usuario","clave"}` abre sesión (cookie `sid`); las demás operaciones en
[docs/arquitectura/spec-api-v1.md](docs/arquitectura/spec-api-v1.md). Pruebas:
`.venv/bin/python -m unittest discover -s servicio/tests -t .`

**Front (Next.js)** en `front/` — la única variable es `API_BASE_URL`:

```bash
cd front
npm install
API_BASE_URL="http://127.0.0.1:8080" npm run build   # la URL se inlaza al compilar
# API con ORIGEN_FRONT=http://127.0.0.1:3000 y COOKIE_SEGURA=1
npm run start                                        # http://127.0.0.1:3000
```

## Estado

Decisión del propietario, 2026-10-28: se construye el mínimo de tres artefactos
(front en Vercel, API y backend en Railway; hotel como primer módulo). Specs
que gobiernan: `docs/arquitectura/spec-front-v1.md`,
`docs/arquitectura/spec-api-v1.md` y `docs/arquitectura/spec-backend-v1.md`
(las versiones sin `-v1` quedaron sustituidas). Cafetería, inmobiliaria y
constructora siguen fuera de esta versión. En producción desde el 2026-10-30
(H7, ver «Desplegado en producción» más abajo). El estado BLOCKED del
2026-10-16 no gobierna ese mínimo. `plataforma/servidor.py`
no es la API ni el servicio de Railway.

**Desplegado en producción (2026-10-30, H7; actualizado 2026-11-02):** dos
servicios en Vercel, equipo `dev-2ddb`, conectados a este repo — cada push a
`main` reconstruye ambos (requiere autor del commit
`hotelherenciacl@gmail.com`, regla Hobby):

| Servicio | Proyecto | URL pública |
|---|---|---|
| Front (Next.js, root `front/`) | `plataforma-salman-herencia-oficial` | https://plataforma-salman-herencia-oficial.vercel.app |
| API/backend (FastAPI, root repo, `api.index:app`) | `plataforma-salman-herencia-oficial-ag24` | (eliminado del equipo el 2026-11-02) |

El proyecto API de Vercel (`-ag24`) fue eliminado del equipo el 2026-11-02;
**el front consume el backend Railway mismo-origen** (2026-11-02 noche:
rewrite `/api/(.*)` del front en Vercel hacia `servicio-production-a2d7.up.railway.app`;
`API_BASE_URL=/api`). Adiós CORS y cookies cross-site (Chrome venía
rechazando la cookie `sid` de terceros): la cookie queda first-party en
`plataforma-salman-herencia-oficial.vercel.app`. Verificado en producción:
`/api/salud` → 200 por el proxy, `/api/auth/google/estado` →
`configurado:true` y `POST /api/sesion` mismo-origen → 200. El plan original
de backend en Railway, sustituido el 2026-10-30 por API en Vercel, quedó
**restablecido el 2026-11-02** (orden del propietario). Runbook con las
lecciones en `docs/arquitectura/h7-despliegue.md`.

**Pendiente de producción:** registrar la URI de redirección de Google
**mismo-origen** (`https://plataforma-salman-herencia-oficial.vercel.app/api/auth/google/callback`)
en Cloud Console — el backend ya la envía (2026-11-02 noche, tras el rewrite
`/api`); sin ella el login con Google vuelve a dar 400; activar
PITR en el servicio `postgres` (Backups → Enable PITR); rotar secretos
(`VERCEL_TOKEN`, clave de aplicación Gmail, `ADMIN_CLAVE` productiva — expuesta
en chat 2026-11-02). **Backend Railway (2026-11-02, orden del propietario,
EN VIVO):** proyecto `plataforma-salman-herencia` creado por API con
PostgreSQL 16, repo GitHub conectado (auto-deploy en cada push) y secretos
`ADMIN_*` fijados (detalle en
`docs/arquitectura/h7-despliegue.md`). **PITR activado el 2026-11-02**
(Backups → Enable PITR por el propietario): bucket `Postgres-PITR` (US West),
`WAL_ARCHIVE_*` fijadas y pgBackRest archivando — full semanal + diferencial
diaria, retención ~4 semanas.

**Construcción (2026-10-28):** backend real en `servicio/` (H1–H5 +
maduración: validación, seguridad, contrato OpenAPI servido, auditoría;
39 pruebas + 181 del dominio) y **front en `front/`** (H6: Next.js con login,
las siete pantallas del hotel, rutas vacías de las otras verticales y la regla
«API caída → error y nada confirmable», verificado con navegador contra el
servicio real). Demo local: API en http://127.0.0.1:8080 y front en
http://127.0.0.1:3000. H7 resuelto el 2026-10-30 (ver «Desplegado en
producción» más arriba). El código local es en memoria y sin red: incremento 0 del hotel
(17 pruebas OK) e incremento 1 del núcleo y de las cuatro verticales
(9 + 102 hotel + 19 cafetería + 20 inmobiliaria + 14 constructora, todas OK,
solo biblioteca estándar; propuesta técnica no ratificada). El 2026-10-28 se
reparó el import de `datetime` en `verticales/hotel/incremento1` que impedía
ejecutar sus 102 pruebas; las 6 baterías se reejecutaron OK (181 pruebas).
GitHub: repositorio privado
`hotelherencia/plataforma-salman-herencia-oficial` y Project n.º 2 «Project
Plataforma Hotel Herencia» con 255 ítems (2026-10-28): corpus documental
cerrado, 16 decisiones del propietario abiertas y el backlog de construcción
V1 en `backlog/v1/` — 211 Done, 28 Todo, 16 Decisión humana.

## Reglas y validación

Ver `AGENTS.md` (documentación de negocio en castellano; construcción autorizada
del mínimo front / API / backend, sin datos productivos ni pasarelas). Control documental:
`python3 scripts/validar_documentacion.py` (hoy no arranca por falta heredada de
`docs/auditorias/originales-sha256.json`; condición conocida, no introducida por
esta estructura).

## Procedencia

La definición V1.0 de `docs/definicion-herencia/` fue importada verificada por
SHA-256 (MANIFEST 371/371) desde `Herencia_Especificaciones_V1.zip`. Las cinco
specs activas provienen de la base documental RSalman consolidada el 15-10-2026.
