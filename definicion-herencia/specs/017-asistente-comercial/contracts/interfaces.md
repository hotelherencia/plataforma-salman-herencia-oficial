# Interfaces F16

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| runAssistant | POST /companies/{company_id}/assistant-runs | AssistantRun | ResourceResult | assistant.run |

Eventos emitidos: assistant.tool_used, assistant.escalated, assistant.stopped. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
