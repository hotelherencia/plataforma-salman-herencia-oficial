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

## Estado

Cinco features **BLOCKED** para implementación (decisiones del propietario
pendientes: ver `backlog/hotel/acta-para-firmar.md`). Nada implementado en
producción. El código local es en memoria y sin red: incremento 0 del hotel
(17 pruebas OK) e incremento 1 del núcleo y de las cuatro verticales
(9 + 102 hotel + 19 cafetería + 20 inmobiliaria + 14 constructora, todas OK,
solo biblioteca estándar; propuesta técnica no ratificada). GitHub: repositorio
privado
`hotelherencia/plataforma-salman-herencia-oficial` y Project n.º 2 «Project
Plataforma Hotel Herencia» con los 155 ítems cargados (estado fechado del
tablero en `backlog/indice.md`, actualizado el 2026-10-27: 133 Bloqueada,
22 Hecha; Esfuerzo solo en tareas hoja del hotel).

## Reglas y validación

Ver `AGENTS.md` (documentación de negocio en castellano; no implementar ni
desplegar sin orden aprobada). Control documental:
`python3 scripts/validar_documentacion.py` (hoy no arranca por falta heredada de
`docs/auditorias/originales-sha256.json`; condición conocida, no introducida por
esta estructura).

## Procedencia

La definición V1.0 de `docs/definicion-herencia/` fue importada verificada por
SHA-256 (MANIFEST 371/371) desde `Herencia_Especificaciones_V1.zip`. Las cinco
specs activas provienen de la base documental RSalman consolidada el 15-10-2026.
