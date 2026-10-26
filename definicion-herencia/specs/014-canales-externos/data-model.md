# Datos F13

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## integration_account
Cuenta y capacidades verificadas

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| provider | varchar(64) | si | NOT NULL | INTERNAL |
| external_account_id | text | si | NOT NULL | INTERNAL |
| unit_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| secret_ref | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DOCUMENTED,ACCOUNT_VERIFIED,PERMISSION_VALIDATED,CONTROLLED_TEST,PRODUCTION_VERIFIED,BLOCKED,UNAVAILABLE; DOCUMENTED,ACCOUNT_VERIFIED,PERMISSION_VALIDATED,CONTROLLED_TEST,PRODUCTION_VERIFIED,BLOCKED,UNAVAILABLE | INTERNAL |
| capabilities | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| last_success_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| token_expires_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## channel_mapping
Equivalencias de canal

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| integration_id | uuid | si | NOT NULL; FK integration_account.id; mismo company_id salvo entidad global -> integration_account | INTERNAL |
| room_type_id | uuid | si | NOT NULL; FK room_type.id; mismo company_id salvo entidad global -> room_type | INTERNAL |
| rate_plan_id | uuid | si | NOT NULL; FK rate_plan.id; mismo company_id salvo entidad global -> rate_plan | INTERNAL |
| external_room_type_id | text | si | NOT NULL | INTERNAL |
| external_rate_plan_id | text | si | NOT NULL | INTERNAL |
| authority | text CHECK enum | si | NOT NULL; enum LOCAL,PROVIDER; LOCAL,PROVIDER | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,VERIFIED,ACTIVE,DISABLED; DRAFT,VERIFIED,ACTIVE,DISABLED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## inbox_event
Entrada externa autenticada y deduplicada

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| integration_id | uuid | si | NOT NULL; FK integration_account.id; mismo company_id salvo entidad global -> integration_account | INTERNAL |
| external_event_id | text | si | NOT NULL | INTERNAL |
| payload_hash | text | si | NOT NULL | INTERNAL |
| event_type | varchar(64) | si | NOT NULL | INTERNAL |
| received_at | timestamptz | si | NOT NULL | INTERNAL |
| signature_verified | boolean | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum RECEIVED,PROCESSING,APPLIED,IGNORED,FAILED,DEAD_LETTER; RECEIVED,PROCESSING,APPLIED,IGNORED,FAILED,DEAD_LETTER | INTERNAL |
| correlation_id | uuid | si | NOT NULL | INTERNAL |

Restricción: UNIQUE(integration_id,external_event_id); payload distinto con mismo ID exige investigacion.
