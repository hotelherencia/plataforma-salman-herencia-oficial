# Interfaces F13

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| registerIntegration | POST /companies/{company_id}/integrations | IntegrationInput | ResourceResult | integration.configure |
| reconcileChannel | POST /companies/{company_id}/integrations/{id}/reconcile | Reason | ResourceResult | integration.reconcile |
| integrationHealth | GET /companies/{company_id}/integrations/{id}/health | - | StatusResult | integration.read |

Eventos emitidos: channel.event_applied, channel.conflict, integration.degraded, inventory.sync_requested. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
