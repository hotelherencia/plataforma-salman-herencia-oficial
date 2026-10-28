# Especificación — API

**Sustituida el 2026-10-28 por [spec-api-v1.md](spec-api-v1.md).** Este archivo no gobierna. El contrato vigente es el V1.

**DECISIÓN del propietario, 2026-10-28.** Es el contrato entre el front de Vercel y el backend de Railway. No es `docs/definicion-herencia/contratos/openapi.yaml` (catálogo heredado, servidor ficticio, rutas propuestas no implementadas) ni `plataforma/servidor.py` (proceso de biblioteca estándar, fuera de este contrato).

El contrato ejecutable de esta versión es un OpenAPI 3.1 que publica el backend. Una operación que no está en la tabla de abajo no se publica.

## Reglas de todo request

- La empresa sale de la sesión. Un `company_id` enviado por el cliente no autoriza.
- Sin sesión: 401.
- Otra empresa: 403, sin revelar si el recurso existe.
- Toda mutación lleva clave de idempotencia. La misma clave y el mismo cuerpo devuelven el mismo resultado. La misma clave y otro cuerpo: 409.
- Puerto externo sin adaptador: 503, y el estado queda pendiente. Un 503 no se presenta como cobro ni como confirmación.

## Operaciones de esta versión

| Operación | Efecto |
|---|---|
| `POST /sesion` | Abre la sesión de la empresa y fija la cookie. |
| `DELETE /sesion` | Cierra la sesión. |
| `PUT /hotel/habitaciones/{id}` | Alta o cambio de habitación: tipo y capacidad. Solo administrador. |
| `PUT /hotel/tarifas` | Tarifa por fecha. No cambia el precio de una reserva ya aceptada. |
| `GET /hotel/oferta` | Fechas y personas. Devuelve solo lo disponible, con tarifa vigente y vencimiento de la oferta. |
| `POST /hotel/reservas` | Confirma una sola vez. La última unidad en carrera queda en una sola reserva. |
| `POST /hotel/reservas/{id}/pagos` | El núcleo registra el efecto. Si el núcleo rechaza, no hay pago. Sin pasarela, 503 y nada marcado como cobrado. |
| `POST /hotel/reservas/{id}/entrada` | Check-in si la habitación está lista. |
| `POST /hotel/reservas/{id}/salida` | Liquida la cuenta. |
| `GET /hotel/caja?fecha` | Pagos del día ligados a su reserva. Sin movimiento bancario en esta versión. |

## Criterio verificable

El front de Vercel puede implementarse leyendo solo este archivo y el OpenAPI que el backend publica con estas diez operaciones.
