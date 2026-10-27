# Interfaces F04

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| startPayment | POST /public/properties/{property_slug}/payment-attempts | PaymentStart | PaymentStartResult | public.pay |
| readPaymentStatus | GET /public/properties/{property_slug}/payment-attempts/{id} | - | PaymentResult | public.pay_status |
| createCharge | POST /companies/{company_id}/charges | ChargeInput | ResourceResult | folio.charge |
| recordManualPayment | POST /companies/{company_id}/payments | ManualPayment | ResourceResult | payment.record |
| allocatePayment | POST /companies/{company_id}/payment-allocations | AllocationInput | ResourceResult | payment.allocate |
| requestRefund | POST /companies/{company_id}/refunds | RefundInput | ResourceResult | refund.request |
| openCash | POST /companies/{company_id}/cash-shifts | CashOpen | ResourceResult | cash.operate |
| closeCash | POST /companies/{company_id}/cash-shifts/{id}/close | CashClose | ResourceResult | cash.close |
| issueFiscal | POST /companies/{company_id}/fiscal-documents | FiscalIssue | ResourceResult | fiscal.issue |
| listFolios | GET /companies/{company_id}/folios | - | Page | folio.read |

Eventos emitidos: payment.authorized, payment.failed, payment.unknown, payment.allocated, refund.completed, cash.closed, fiscal.updated. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
