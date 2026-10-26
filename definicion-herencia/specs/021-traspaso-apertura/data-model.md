# Datos F20

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## migration_batch
Carga de apertura autorizada

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| source_name | text | si | NOT NULL | INTERNAL |
| file_hash | text | si | NOT NULL | INTERNAL |
| cutoff_at | timestamptz | si | NOT NULL | INTERNAL |
| schema_version | text | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum UPLOADED,VALIDATED,PREVIEW,APPROVED,IMPORTED,REJECTED,REVERSED; UPLOADED,VALIDATED,PREVIEW,APPROVED,IMPORTED,REJECTED,REVERSED | INTERNAL |
| approved_by | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| control_totals | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| rejected_rows | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |

Restricción: UNIQUE(company_id,file_hash,cutoff_at,schema_version); staging no altera producción.

## handover_item
Obligación o bien recibido con excepción

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| batch_id | uuid | si | NOT NULL; FK migration_batch.id; mismo company_id salvo entidad global -> migration_batch | INTERNAL |
| kind | text CHECK enum | si | NOT NULL; enum RESERVATION,FUNDS,ASSET,STOCK,STAFF,CONTRACT,ACCESS,CLAIM; RESERVATION,FUNDS,ASSET,STOCK,STAFF,CONTRACT,ACCESS,CLAIM | INTERNAL |
| source_ref | text | si | NOT NULL | INTERNAL |
| target_type | varchar(64) | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| target_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum EXPECTED,RECEIVED,OBSERVED,PENDING,DISPUTED,RESOLVED; EXPECTED,RECEIVED,OBSERVED,PENDING,DISPUTED,RESOLVED | INTERNAL |
| responsible_party_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK party.id; mismo company_id salvo entidad global -> party | INTERNAL |
| amount_minor | bigint | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |
| currency | char(3) | no | NULL permitido; nunca reemplazar faltante por cero; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| due_on | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
