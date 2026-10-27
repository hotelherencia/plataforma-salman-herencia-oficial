# Interfaces F02

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| searchAvailability | POST /public/properties/{property_slug}/availability | StaySearch | AvailabilityResult | public.availability |
| createRoom | POST /companies/{company_id}/rooms | RoomInput | ResourceResult | room.configure |
| blockRoom | POST /companies/{company_id}/room-blocks | RoomBlock | ResourceResult | room.block |
| publishRate | POST /companies/{company_id}/rates | RateInput | ResourceResult | rate.publish |
| listRooms | GET /companies/{company_id}/rooms | - | Page | room.read |

Eventos emitidos: inventory.changed, rate.published, room.blocked. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
