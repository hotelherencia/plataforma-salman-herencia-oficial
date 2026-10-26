# Interfaces F17

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| createCampaign | POST /companies/{company_id}/campaigns | CampaignInput | ResourceResult | campaign.create |
| activateCampaign | POST /companies/{company_id}/campaigns/{id}/activate | ApprovalDecision | ResourceResult | campaign.activate |
| createContent | POST /companies/{company_id}/content | ContentInput | ResourceResult | content.write |
| publishContent | POST /companies/{company_id}/content/{id}/publish | ApprovalDecision | ResourceResult | content.publish |
| listCampaigns | GET /companies/{company_id}/campaigns | - | Page | campaign.read |

Eventos emitidos: content.published, campaign.activated, campaign.paused. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
