# Interfaces F05

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| checkin | POST /companies/{company_id}/checkins | CheckinInput | ResourceResult | stay.checkin |
| moveRoom | POST /companies/{company_id}/stays/{id}/moves | MoveInput | ResourceResult | stay.move |
| checkout | POST /companies/{company_id}/stays/{id}/checkout | CheckoutInput | ResourceResult | stay.checkout |
| runNightAudit | POST /companies/{company_id}/night-audits | NightAudit | ResourceResult | night.close |
| listStays | GET /companies/{company_id}/stays | - | Page | stay.read |

Eventos emitidos: stay.checked_in, stay.room_changed, stay.checked_out, night.closed. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
