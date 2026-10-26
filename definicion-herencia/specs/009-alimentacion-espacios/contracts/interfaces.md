# Interfaces F08

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| produceFood | POST /companies/{company_id}/food-batches | FoodProduce | ResourceResult | food.produce |
| serveBreakfast | POST /companies/{company_id}/breakfast-services | BreakfastServe | ResourceResult | food.serve |
| orderDinner | POST /companies/{company_id}/dinner-orders | DinnerOrder | ResourceResult | dinner.order |
| reserveSpace | POST /companies/{company_id}/space-bookings | SpaceBooking | ResourceResult | space.reserve |
| listBreakfast | GET /companies/{company_id}/breakfast-entitlements | - | Page | food.read |

Eventos emitidos: food.produced, breakfast.served, dinner.delivered, space.reserved. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
