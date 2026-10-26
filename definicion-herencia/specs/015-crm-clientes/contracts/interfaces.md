# Interfaces F14

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| createContact | POST /companies/{company_id}/contacts | ContactInput | ResourceResult | crm.write |
| recordConsent | POST /companies/{company_id}/consents | ConsentInput | ResourceResult | consent.write |
| takeoverConversation | POST /companies/{company_id}/conversations/{id}/takeover | TakeoverInput | ResourceResult | conversation.takeover |
| listConversations | GET /companies/{company_id}/conversations | - | Page | conversation.read |

Eventos emitidos: opportunity.changed, consent.revoked, identity.linked. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
