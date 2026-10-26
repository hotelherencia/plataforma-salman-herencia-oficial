# Interfaces F12

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| distributeCost | POST /companies/{company_id}/cost-distributions | CostDistribution | ResourceResult | cost.distribute |
| calculateReport | POST /companies/{company_id}/reports | ReportRequest | ReportResult | report.read |

Eventos emitidos: cost.distributed, report.generated, conversion.recorded. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
