# Interfaces F18

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| readPortal | GET /guest/portal | - | PortalResult | portal.read |
| guestServiceRequest | POST /guest/service-tickets | ServiceTicket | ResourceResult | portal.request |

Eventos emitidos: guest.requested_service, ticket.resolved, portal.revoked. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
