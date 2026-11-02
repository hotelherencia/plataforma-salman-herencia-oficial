# Cómo funciona la app — documentación funcional (2026-11-02)

HECHO DOCUMENTADO. Describe la plataforma **como opera hoy en producción**,
para lectura de negocio y de onboarding técnico. Las specs que gobiernan la
construcción siguen en `docs/arquitectura/spec-{front,api,backend}-v1.md`;
esto es el mapa funcional del sistema desplegado.

## En una frase

El usuario entra por navegador al **front en Vercel**; el front habla
**mismo-origen** (`/api/*`) con el **servicio FastAPI en Railway**, que decide
todo el negocio y persiste en **PostgreSQL** (misma red privada, backups PITR);
el acceso es con usuario/clave (+ TOTP opcional) o con **Google**; cada push a
`main` reconstruye front y backend automáticamente.

## Piezas

| Pieza | Dónde vive | Rol |
|---|---|---|
| Front (Next.js) | Vercel — `plataforma-salman-herencia-oficial.vercel.app` | 7 pantallas del hotel + login; jamás calcula negocio |
| Puente `/api/*` | rewrite de Vercel → Railway | mismo-origen: sin CORS ni cookies de terceros |
| Servicio (FastAPI) | Railway — `servicio-production-a2d7.up.railway.app` | las 10 operaciones, reglas de dominio, sesiones, auditoría |
| Base de datos | Railway PostgreSQL 16 (imagen Railway, volumen) | persistencia + freno de logins por usuario en memoria de proceso |
| Backups PITR | bucket `Postgres-PITR` (Railway) | recuperación a punto en el tiempo (~4 semanas) |
| Google OAuth | Google Cloud (cliente propio) | login social vinculado por email |
| GitHub | repo `hotelherencia/plataforma-salman-herencia-oficial` | cada push a `main` despliega ambos (regla de autor Hobby) |

## Índice

- [`arquitectura.md`](arquitectura.md) — componentes, despliegue y cómo viaja una llamada.
- [`flujos.md`](flujos.md) — secuencias: acceso, ciclo de reserva completo, housekeeping, usuarios.
- [`dominio.md`](dominio.md) — entidades, estados y reglas de negocio.
