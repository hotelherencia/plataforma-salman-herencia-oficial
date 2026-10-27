# Interfaces F06

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| createProduct | POST /companies/{company_id}/products | ProductInput | ResourceResult | stock.configure |
| createPurchase | POST /companies/{company_id}/purchases | PurchaseInput | ResourceResult | purchase.create |
| approvePurchase | POST /companies/{company_id}/purchases/{id}/approve | ApprovalDecision | ResourceResult | purchase.approve |
| receivePurchase | POST /companies/{company_id}/receipts | ReceiveInput | ResourceResult | purchase.receive |
| adjustStock | POST /companies/{company_id}/stock-adjustments | StockAdjustment | ResourceResult | stock.adjust |
| transferStock | POST /companies/{company_id}/stock-transfers | StockTransfer | ResourceResult | stock.transfer |
| readStock | GET /companies/{company_id}/stock | - | Page | stock.read |
| listPurchases | GET /companies/{company_id}/purchases | - | Page | purchase.read |

Eventos emitidos: purchase.approved, goods.received, stock.moved, stock.adjusted. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
