# Interfaces F07

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| createTask | POST /companies/{company_id}/tasks | TaskInput | ResourceResult | task.assign |
| executeTask | POST /companies/{company_id}/tasks/{id}/executions | TaskExecute | ResourceResult | task.execute |
| inspectTask | POST /companies/{company_id}/task-executions/{id}/inspect | InspectTask | ResourceResult | task.inspect |
| sendLaundry | POST /companies/{company_id}/laundry-dispatches | LaundrySend | ResourceResult | laundry.operate |
| receiveLaundry | POST /companies/{company_id}/laundry-receipts | LaundryReceive | ResourceResult | laundry.operate |
| listTasks | GET /companies/{company_id}/tasks | - | Page | task.read |
| listLaundry | GET /companies/{company_id}/laundry | - | Page | laundry.read |

Eventos emitidos: task.completed, task.accepted, task.rework, laundry.sent, laundry.received, room.ready. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
