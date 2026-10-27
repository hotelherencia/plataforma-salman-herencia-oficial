# Interfaces F11

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| previewBankImport | POST /companies/{company_id}/bank-imports | BankImport | ResourceResult | bank.import |
| commitBankImport | POST /companies/{company_id}/bank-imports/{id}/commit | Reason | ResourceResult | bank.import |
| createReconciliation | POST /companies/{company_id}/reconciliations | ReconcileInput | ResourceResult | reconciliation.create |
| postReconciliation | POST /companies/{company_id}/reconciliations/{id}/post | ApprovalDecision | ResourceResult | reconciliation.approve |
| exportAccounting | POST /companies/{company_id}/accounting-exports | AccountingExport | ResourceResult | accounting.export |
| listUnmatched | GET /companies/{company_id}/reconciliation-items | - | Page | bank.read |

Eventos emitidos: bank.imported, reconciliation.posted, reconciliation.reversed, accounting.exported. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
