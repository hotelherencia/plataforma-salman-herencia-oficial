# docs/ — documentación del proyecto

Documentación que no es spec activa ni código. El árbol de construcción vigente
(spec driven) está en `specs/`, `backlog/`, `core/`,
`verticales/` y `scripts/`.

## Contenido

- `definicion-herencia/` — especificación SDD V1.0 de Hotel Herencia (Documento
  Maestro M01–M24, 23 paquetes F00–F22, 153 requisitos, 45 decisiones, 306
  casos, 109 entidades). Se conserva porque sus IDs no tienen trazabilidad en
  `specs` ni en el backlog y su cierre está pendiente de la firma del
  propietario (ver `../backlog/acta_cierre_definicion.md`). No es la spec activa
  de construcción.
- `archivo-no-construccion/` — notas de la fase de análisis documental
  (2026-10-26) y archivos sueltos ajenos a spec y código. Sin aporte a la
  construcción; se mantiene como respaldo sin borrado definitivo.
- `arquitectura/` — propuesta técnica no ratificada (2026-10-27) de la
  plataforma completa: tres capas (front único, API única, un solo servicio
  con módulos de dominio), stack por artefacto (Vercel/Railway) y cuatro
  flujos Mermaid de integración. No despliega nada.
- `investigacion-competitiva/` — dudas de base (Q-HOT-01/02/03, Q-CORE-01/02/03)
  contrastadas con práctica de mercado y fuentes públicas (2026-10-27). No
  cierra ninguna Q ni tarea de decisión; ninguna propuesta queda ratificada.

La decisión de depuración y sus reglas están en `../backlog/depuracion-carpetas.md`.
