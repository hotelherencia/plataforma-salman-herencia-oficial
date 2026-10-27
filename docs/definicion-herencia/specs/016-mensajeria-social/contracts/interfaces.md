# Interfaces F15

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| sendMessage | POST /companies/{company_id}/messages | MessageInput | ResourceResult | message.send |
| ingestVerifiedEvent | POST /integrations/{integration_id}/inbound | ExternalEnvelope | ResourceResult | integration.signature |

Eventos emitidos: message.received, message.delivered, conversation.taken_over, message.rejected. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
