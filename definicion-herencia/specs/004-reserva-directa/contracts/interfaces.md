# Interfaces F03

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| createQuote | POST /public/properties/{property_slug}/quotes | QuoteRequest | QuoteResponse | public.quote |
| createHold | POST /public/properties/{property_slug}/holds | HoldRequest | HoldResponse | public.hold |
| createReservation | POST /public/properties/{property_slug}/reservations | ReservationRequest | ReservationPublic | public.reserve |
| amendReservation | POST /companies/{company_id}/reservations/{id}/amendments | ReservationAmend | ResourceResult | reservation.amend |
| listReservations | GET /companies/{company_id}/reservations | - | Page | reservation.read |

Eventos emitidos: quote.created, reservation.pending, reservation.confirmed, reservation.changed, reservation.cancelled. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
