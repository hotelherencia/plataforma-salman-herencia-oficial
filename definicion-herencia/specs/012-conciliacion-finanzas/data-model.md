# Datos F11

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## bank_account
Cuenta cuyo titular y moneda se verifican

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | RESTRICTED |
| created_at | timestamptz | si | NOT NULL | RESTRICTED |
| updated_at | timestamptz | si | NOT NULL | RESTRICTED |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | RESTRICTED |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | RESTRICTED |
| bank_name | text | si | NOT NULL | RESTRICTED |
| account_masked | text | si | NOT NULL | RESTRICTED |
| account_secret_ref | text | si | NOT NULL | RESTRICTED |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | RESTRICTED |
| unit_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK unit.id; mismo company_id salvo entidad global -> unit | RESTRICTED |
| status | text CHECK enum | si | NOT NULL; enum PENDING,ACTIVE,REVOKED; PENDING,ACTIVE,REVOKED | RESTRICTED |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## payable
Obligación con proveedor

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| supplier_id | uuid | si | NOT NULL; FK supplier.id; mismo company_id salvo entidad global -> supplier | INTERNAL |
| document_id | uuid | si | NOT NULL; FK document.id; mismo company_id salvo entidad global -> document | INTERNAL |
| order_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK purchase_order.id; mismo company_id salvo entidad global -> purchase_order | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| total_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| paid_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| due_date | date | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PENDING,APPROVED,PART_PAID,PAID,DISPUTED; PENDING,APPROVED,PART_PAID,PAID,DISPUTED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## payable_payment
Pago a proveedor aprobado, no automatizado libremente

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| payable_id | uuid | si | NOT NULL; FK payable.id; mismo company_id salvo entidad global -> payable | INTERNAL |
| amount_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| bank_movement_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK bank_movement.id; mismo company_id salvo entidad global -> bank_movement | INTERNAL |
| approval_id | uuid | si | NOT NULL; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |
| paid_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PROPOSED,APPROVED,RECORDED,REVERSED; PROPOSED,APPROVED,RECORDED,REVERSED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## bank_import
Lote importado sin duplicación

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| bank_account_id | uuid | si | NOT NULL; FK bank_account.id; mismo company_id salvo entidad global -> bank_account | INTERNAL |
| file_id | uuid | si | NOT NULL; FK file_object.id; mismo company_id salvo entidad global -> file_object | INTERNAL |
| file_hash | text | si | NOT NULL | INTERNAL |
| period_start | date | si | NOT NULL | INTERNAL |
| period_end | date | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum UPLOADED,PARSED,PREVIEW,APPROVED,IMPORTED,REJECTED; UPLOADED,PARSED,PREVIEW,APPROVED,IMPORTED,REJECTED | INTERNAL |
| opening_balance_minor | bigint | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| closing_balance_minor | bigint | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## bank_movement
Hecho bancario inmutable

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| bank_account_id | uuid | si | NOT NULL; FK bank_account.id; mismo company_id salvo entidad global -> bank_account | INTERNAL |
| import_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK bank_import.id; mismo company_id salvo entidad global -> bank_import | INTERNAL |
| external_id | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| booked_on | date | si | NOT NULL | INTERNAL |
| amount_minor | bigint | si | NOT NULL | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| description | text | si | NOT NULL | INTERNAL |
| fingerprint | text | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum UNMATCHED,PARTIAL,MATCHED,DISPUTED; UNMATCHED,PARTIAL,MATCHED,DISPUTED | INTERNAL |

Restricción: UNIQUE(bank_account_id,external_id) sólo cuando ID estable; fingerprint candidato no causa fusion automática.

## settlement
Liquidación de procesador o canal

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| provider | varchar(64) | si | NOT NULL | INTERNAL |
| external_id | text | si | NOT NULL | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| gross_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| fee_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| refund_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| net_minor | bigint | si | NOT NULL | INTERNAL |
| expected_on | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| document_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK document.id; mismo company_id salvo entidad global -> document | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum EXPECTED,RECEIVED,PARTIAL,RECONCILED,DISPUTED; EXPECTED,RECEIVED,PARTIAL,RECONCILED,DISPUTED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## settlement_line
Desglose de cobros de liquidación

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| settlement_id | uuid | si | NOT NULL; FK settlement.id; mismo company_id salvo entidad global -> settlement | INTERNAL |
| payment_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK payment.id; mismo company_id salvo entidad global -> payment | INTERNAL |
| reservation_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK reservation.id; mismo company_id salvo entidad global -> reservation | INTERNAL |
| gross_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| fee_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| refund_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## reconciliation_group
Conciliación many-to-many con control

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PROPOSED,APPROVED,POSTED,REVERSED; PROPOSED,APPROVED,POSTED,REVERSED | INTERNAL |
| difference_minor | bigint | si | NOT NULL | INTERNAL |
| reason | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| approved_by | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## reconciliation_allocation
Asignación a hecho financiero

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| group_id | uuid | si | NOT NULL; FK reconciliation_group.id; mismo company_id salvo entidad global -> reconciliation_group | INTERNAL |
| source_type | text CHECK enum | si | NOT NULL; enum PAYMENT,SETTLEMENT,BANK,FEE,REFUND,ADJUSTMENT; PAYMENT,SETTLEMENT,BANK,FEE,REFUND,ADJUSTMENT | INTERNAL |
| source_id | uuid | si | NOT NULL | INTERNAL |
| amount_minor | bigint | si | NOT NULL | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| side | text CHECK enum | si | NOT NULL; enum BUSINESS,BANK; BUSINESS,BANK | INTERNAL |

Restricción: Suma aplicada a fuente no excede disponible; por grupo suma lado BUSINESS = lado BANK para POSTED, o diferencia aprobada explícita.

## accounting_export
Intercambio contable controlado

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| period_start | date | si | NOT NULL | INTERNAL |
| period_end | date | si | NOT NULL | INTERNAL |
| mapping_version | text | si | NOT NULL | INTERNAL |
| batch_key | text | si | NOT NULL | INTERNAL |
| control_totals | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| file_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK file_object.id; mismo company_id salvo entidad global -> file_object | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,VALIDATED,SENT,ACCEPTED,REJECTED,REVERSED; DRAFT,VALIDATED,SENT,ACCEPTED,REJECTED,REVERSED | INTERNAL |
| external_ack | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
