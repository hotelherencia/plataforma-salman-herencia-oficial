# Instrucciones del proyecto

**Fase (desde 2026-10-28): construcción V1 de la plataforma.** Ya no es solo
ingeniería documental: se construyen tres artefactos que se aceptan juntos —
front en Vercel, contrato API y backend en Railway — según
`docs/arquitectura/spec-front-v1.md`, `docs/arquitectura/spec-api-v1.md` y
`docs/arquitectura/spec-backend-v1.md`, que son la especificación gobernante.
Sustituyen al «destino» de `docs/arquitectura/plataforma.md`; ADR-001 y
`specs/*/plan.md` quedan como histórico no ejecutado. El hotel es el primer
módulo; cafetería, inmobiliaria y constructora quedan nombradas y fuera de
esta versión.

## Reglas que se mantienen

- Documentación de negocio en castellano. Toda decisión nueva lleva fuente o
  se marca como propuesta; distinguir HECHO DOCUMENTADO, REQUISITO PROPUESTO,
  DECISIÓN PENDIENTE y SUPUESTO.
- **Sin sistemas externos reales:** Webpay, Mercado Pago, SII, Booking,
  Airbnb y WhatsApp existen solo como puertos; sin adaptador responden «no
  configurado» y la API devuelve 503 con estado pendiente. Nada de pagos,
  facturación, envíos ni cambios en cuentas reales sin autorización
  específica.
- **El repositorio no lleva `.env`.** Secretos y `DATABASE_URL` viven en
  variables del despliegue (Railway/Vercel).
- **La especificación se cumple con hechos, no con prosa:** cada pieza se
  acepta con pruebas que la ejercen (HTTP contra el contrato, persistencia
  tras reinicio, reglas de sesión e idempotencia).
- Los módulos en memoria (`core/incremento1`, `verticales/*/incremento1`)
  son la especificación ejecutable del dominio: el servicio los importa y sus
  pruebas (181) no se rompen.
- El stack es el que el proceso ejecuta (Python + FastAPI + PostgreSQL 17;
  Next.js en el front). No elegir stack en prosa: se fija en código y en las
  tres specs.
- **Backlog reactivado (2026-10-28).** El tablero vive de la construcción V1:
  gobierna `backlog/v1/` (4 épicas: contrato API, backend, front y despliegue
  H7). El corpus documental de ciclos previos quedó cerrado en el tablero;
  no volver a abrir sus ítems salvo orden del propietario. El dictamen de
  plataforma (`docs/arquitectura/evaluacion-bases.md`) sigue siendo la
  escalera de verificación por filas.
- **Git y despliegue.** H1 a H6 corren en local: sin pull request y sin
  despliegue. El propietario ordenó versionar y publicar en GitHub el avance
  (commit/push del 2026-10-28 con H1–H3). La derogación plena queda en H7,
  que es el hito que publica la rama de trabajo y despliega Railway y Vercel.
  H7 no empieza hasta que existan las cuentas; no están verificadas.
