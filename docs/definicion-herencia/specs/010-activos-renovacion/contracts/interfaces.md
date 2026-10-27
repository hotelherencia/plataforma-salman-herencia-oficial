# Interfaces F09

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| registerAsset | POST /companies/{company_id}/assets | AssetInput | ResourceResult | asset.write |
| createMaintenance | POST /companies/{company_id}/maintenance-orders | MaintenanceInput | ResourceResult | maintenance.create |
| planRenewal | POST /companies/{company_id}/renewals | RenewalInput | ResourceResult | renewal.create |
| acceptInstallation | POST /companies/{company_id}/installations | InstallationInput | ResourceResult | asset.accept |
| listAssets | GET /companies/{company_id}/assets | - | Page | asset.read |

Eventos emitidos: maintenance.opened, maintenance.closed, renewal.approved, asset.installed. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
