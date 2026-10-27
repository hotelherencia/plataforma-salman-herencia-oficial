# Interfaces F01

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| createOwnership | POST /companies/{company_id}/ownership | OwnershipInput | ResourceResult | ownership.write |
| grantRole | POST /companies/{company_id}/role-grants | RoleGrant | ResourceResult | access.approve |
| requestApproval | POST /companies/{company_id}/approvals | ApprovalRequest | ResourceResult | approval.request |
| decideApproval | POST /companies/{company_id}/approvals/{id}/decision | ApprovalDecision | ResourceResult | approval.decide |
| listCompanies | GET /companies/{company_id}/companies | - | Page | company.read |

Eventos emitidos: company.activated, access.revoked, approval.decided. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
