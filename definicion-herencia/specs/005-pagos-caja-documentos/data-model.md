# Datos F04

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## folio
Cuenta comercial de estadía o grupo

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| reservation_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK reservation.id; mismo company_id salvo entidad global -> reservation | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| debtor_party_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK party.id; mismo company_id salvo entidad global -> party | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum OPEN,SETTLED,RECEIVABLE,CLOSED; OPEN,SETTLED,RECEIVABLE,CLOSED | INTERNAL |
| due_date | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## charge
Cargo por servicio, no cobro

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| folio_id | uuid | si | NOT NULL; FK folio.id; mismo company_id salvo entidad global -> folio | INTERNAL |
| stay_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK stay.id; mismo company_id salvo entidad global -> stay | INTERNAL |
| concept | varchar(64) | si | NOT NULL | INTERNAL |
| service_date | date | si | NOT NULL | INTERNAL |
| quantity | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| unit_price_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| net_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| tax_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| gross_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PLANNED,POSTED,REVERSED; PLANNED,POSTED,REVERSED | INTERNAL |
| source_key | text | si | NOT NULL | INTERNAL |
| reverses_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK charge.id; mismo company_id salvo entidad global -> charge | INTERNAL |

Restricción: UNIQUE(company_id,source_key); gross=net+tax; reverso conserva monto/moneda y referencia.

## payment_intent
Intento de pago antes de resultado cierto

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | RESTRICTED |
| created_at | timestamptz | si | NOT NULL | RESTRICTED |
| updated_at | timestamptz | si | NOT NULL | RESTRICTED |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | RESTRICTED |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | RESTRICTED |
| quote_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK quote.id; mismo company_id salvo entidad global -> quote | RESTRICTED |
| reservation_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK reservation.id; mismo company_id salvo entidad global -> reservation | RESTRICTED |
| provider | varchar(64) | si | NOT NULL | RESTRICTED |
| external_token_ref | text | no | NULL permitido; nunca reemplazar faltante por cero | RESTRICTED |
| order_ref | text | si | NOT NULL | RESTRICTED |
| amount_minor | bigint | si | NOT NULL; >= 0 | RESTRICTED |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | RESTRICTED |
| status | text CHECK enum | si | NOT NULL; enum CREATED,PENDING,AUTHORIZED,FAILED,UNKNOWN,REFUND_PENDING,CLOSED; CREATED,PENDING,AUTHORIZED,FAILED,UNKNOWN,REFUND_PENDING,CLOSED | RESTRICTED |
| expires_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | RESTRICTED |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## payment
Fondo recibido y comprobado

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| intent_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK payment_intent.id; mismo company_id salvo entidad global -> payment_intent | INTERNAL |
| kind | text CHECK enum | si | NOT NULL; enum ADVANCE,SETTLEMENT,GUARANTEE,LEGACY_CREDIT; ADVANCE,SETTLEMENT,GUARANTEE,LEGACY_CREDIT | INTERNAL |
| method | text CHECK enum | si | NOT NULL; enum CASH,TRANSFER,CARD,OTA,LEGACY; CASH,TRANSFER,CARD,OTA,LEGACY | INTERNAL |
| amount_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| received_at | timestamptz | si | NOT NULL | INTERNAL |
| provider | varchar(64) | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| external_transaction_id | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| holder_party_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK party.id; mismo company_id salvo entidad global -> party | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum VERIFIED,PARTIALLY_REFUNDED,REFUNDED,DISPUTED; VERIFIED,PARTIALLY_REFUNDED,REFUNDED,DISPUTED | INTERNAL |
| source_document_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK document.id; mismo company_id salvo entidad global -> document | INTERNAL |

Restricción: UNIQUE(company_id,provider,external_transaction_id) WHERE external_transaction_id IS NOT NULL; no contabilizar callback no verificado.

## payment_allocation
Aplicación que no puede exceder pago o cuenta

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| payment_id | uuid | si | NOT NULL; FK payment.id; mismo company_id salvo entidad global -> payment | INTERNAL |
| folio_id | uuid | si | NOT NULL; FK folio.id; mismo company_id salvo entidad global -> folio | INTERNAL |
| amount_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum ACTIVE,REVERSED; ACTIVE,REVERSED | INTERNAL |
| applied_at | timestamptz | si | NOT NULL | INTERNAL |

Restricción: Suma de aplicaciones activas <= pago neto disponible; bloqueo de pago/cuenta; moneda identica.

## refund
Devolución autorizada del pago original

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| payment_id | uuid | si | NOT NULL; FK payment.id; mismo company_id salvo entidad global -> payment | INTERNAL |
| amount_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| approval_id | uuid | si | NOT NULL; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |
| reason | text | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum REQUESTED,APPROVED,SUBMITTED,CONFIRMED,FAILED,UNKNOWN; REQUESTED,APPROVED,SUBMITTED,CONFIRMED,FAILED,UNKNOWN | INTERNAL |
| external_id | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| confirmed_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Suma confirmada + reservada para enviar <= saldo reembolsable; no reintentar a ciegas estado UNKNOWN.

## cash_shift
Caja y arqueo por turno

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| cashbox_code | varchar(64) | si | NOT NULL | INTERNAL |
| cashier_id | uuid | si | NOT NULL; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| opening_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| counted_minor | bigint | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |
| difference_minor | bigint | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum OPEN,SUBMITTED,CLOSED,REOPENED; OPEN,SUBMITTED,CLOSED,REOPENED | INTERNAL |
| opened_at | timestamptz | si | NOT NULL | INTERNAL |
| closed_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Una sola caja/moneda/turno abierto; arqueo exacto; cierre/reapertura con auditoría.

## cash_movement
Movimiento de efectivo o traslado

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| cash_shift_id | uuid | si | NOT NULL; FK cash_shift.id; mismo company_id salvo entidad global -> cash_shift | INTERNAL |
| kind | text CHECK enum | si | NOT NULL; enum RECEIPT,REFUND,WITHDRAWAL,DEPOSIT,TRANSFER_IN,TRANSFER_OUT,ADJUSTMENT; RECEIPT,REFUND,WITHDRAWAL,DEPOSIT,TRANSFER_IN,TRANSFER_OUT,ADJUSTMENT | INTERNAL |
| amount_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| payment_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK payment.id; mismo company_id salvo entidad global -> payment | INTERNAL |
| transfer_group_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |
| document_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK document.id; mismo company_id salvo entidad global -> document | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## fiscal_document
Estado tributario del proveedor habilitado

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| folio_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK folio.id; mismo company_id salvo entidad global -> folio | INTERNAL |
| type_code | varchar(64) | si | NOT NULL | INTERNAL |
| official_folio | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| provider_ref | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| net_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| tax_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| total_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,SUBMITTED,ACCEPTED,REJECTED,CORRECTED; DRAFT,SUBMITTED,ACCEPTED,REJECTED,CORRECTED | INTERNAL |
| original_document_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK fiscal_document.id; mismo company_id salvo entidad global -> fiscal_document | INTERNAL |
| issue_date | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
