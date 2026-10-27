# plataforma-salman-herencia

Plataforma **core multi-vertical** del Grupo Salman, desplegada para la
**empresa base Herencia** (Hotel Herencia). Esta base **no es la vertical
hotel**: es la plataforma compartida completa — núcleo transversal más cuatro
verticales de negocio. La vertical hotel es solo una de las cuatro.

## Qué contiene

- `specs/000-core/` — núcleo compartido: identidad, autorización, límites de
  tenant, adaptadores de pagos/documentos/comunicación y auditoría.
- `specs/001-cafeteria-mesas-pos/` — vertical cafetería (mesas, pedidos, POS).
- `specs/002-hotel-reservas-concierge/` — vertical hotel (reservas, operación,
  concierge). Único código existente: `verticales/hotel/incremento0/` (prueba
  local de reserva de última unidad, sin UI ni red).
- `specs/003-inmobiliaria-comercial/` y `specs/004-constructora-obra/` —
  verticales inmobiliaria y constructora.
- `backlog/` — índice y carga de los 150 ítems del backlog, plan vertical del
  hotel, hojas de decisiones, actas (firma del hotel y cierre de la definición
  heredada) y nota de depuración del árbol.
- `core/` — espacio reservado del núcleo. `verticales/` — código por vertical.
  `scripts/` — validadores documentales y carga del backlog a GitHub.
- `docs/` — documentación que no es spec activa: `docs/definicion-herencia/`
  (definición SDD V1.0 heredada, pendiente de firma del propietario; conservada
  por falta de traza), `docs/archivo-no-construccion/` (notas de análisis) y
  `docs/historial-consolidacion.md` (README histórico).

## Estado

Cinco features **BLOCKED** para implementación (decisiones del propietario
pendientes: ver `backlog/hotel/acta-para-firmar.md`). Nada implementado en
producción. El incremento 0 del hotel es una prueba local aislada (10 pruebas
OK, solo biblioteca estándar). GitHub: repositorio privado
`hotelherencia/plataforma-salman-herencia-oficial` y Project n.º 2 «Project
Plataforma Hotel Herencia» con los 150 ítems cargados (18 en «Decisión humana»,
19 en Done; Esfuerzo solo en tareas hoja del hotel).

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
