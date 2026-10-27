# Datos F10

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## worker
Persona trabajadora y rol vigente

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | RESTRICTED |
| created_at | timestamptz | si | NOT NULL | RESTRICTED |
| updated_at | timestamptz | si | NOT NULL | RESTRICTED |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | RESTRICTED |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | RESTRICTED |
| user_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | RESTRICTED |
| name | text | si | NOT NULL | RESTRICTED |
| employer_party_id | uuid | si | NOT NULL; FK party.id; mismo company_id salvo entidad global -> party | RESTRICTED |
| role | varchar(64) | si | NOT NULL | RESTRICTED |
| status | text CHECK enum | si | NOT NULL; enum PENDING,ACTIVE,LEAVE,INACTIVE; PENDING,ACTIVE,LEAVE,INACTIVE | RESTRICTED |
| contract_document_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK document.id; mismo company_id salvo entidad global -> document | RESTRICTED |
| regime_policy_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK policy.id; mismo company_id salvo entidad global -> policy | RESTRICTED |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## shift
Cobertura programada

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| worker_id | uuid | si | NOT NULL; FK worker.id; mismo company_id salvo entidad global -> worker | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| position | varchar(64) | si | NOT NULL | INTERNAL |
| starts_at | timestamptz | si | NOT NULL | INTERNAL |
| ends_at | timestamptz | si | NOT NULL | INTERNAL |
| break_minutes | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,PUBLISHED,REPLACED,CANCELLED; DRAFT,PUBLISHED,REPLACED,CANCELLED | INTERNAL |
| replacement_of | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK shift.id; mismo company_id salvo entidad global -> shift | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## attendance
Tiempo real separado de tareas

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | RESTRICTED |
| created_at | timestamptz | si | NOT NULL | RESTRICTED |
| updated_at | timestamptz | si | NOT NULL | RESTRICTED |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | RESTRICTED |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | RESTRICTED |
| worker_id | uuid | si | NOT NULL; FK worker.id; mismo company_id salvo entidad global -> worker | RESTRICTED |
| shift_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK shift.id; mismo company_id salvo entidad global -> shift | RESTRICTED |
| clock_in | timestamptz | si | NOT NULL | RESTRICTED |
| clock_out | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | RESTRICTED |
| source | varchar(64) | si | NOT NULL | RESTRICTED |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | RESTRICTED |
| status | text CHECK enum | si | NOT NULL; enum RECORDED,REVIEW,APPROVED,EXPORTED; RECORDED,REVIEW,APPROVED,EXPORTED | RESTRICTED |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## incentive_rule
Regla de incentivo versionada

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| policy_id | uuid | si | NOT NULL; FK policy.id; mismo company_id salvo entidad global -> policy | INTERNAL |
| effective_from | date | si | NOT NULL | INTERNAL |
| effective_to | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| weights | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| value_per_point | numeric(20,8) | si | NOT NULL; decimal exacto, límite por regla de negocio | INTERNAL |
| cap_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| quality_required | boolean | si | NOT NULL | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## incentive_award
Preliquidación auditable

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | RESTRICTED |
| created_at | timestamptz | si | NOT NULL | RESTRICTED |
| updated_at | timestamptz | si | NOT NULL | RESTRICTED |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | RESTRICTED |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | RESTRICTED |
| worker_id | uuid | si | NOT NULL; FK worker.id; mismo company_id salvo entidad global -> worker | RESTRICTED |
| rule_id | uuid | si | NOT NULL; FK incentive_rule.id; mismo company_id salvo entidad global -> incentive_rule | RESTRICTED |
| period_start | date | si | NOT NULL | RESTRICTED |
| period_end | date | si | NOT NULL | RESTRICTED |
| points | numeric(20,8) | si | NOT NULL; decimal exacto, límite por regla de negocio | RESTRICTED |
| amount_minor | bigint | si | NOT NULL; >= 0 | RESTRICTED |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | RESTRICTED |
| source_task_ids | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | RESTRICTED |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,REVIEW,APPROVED,EXPORTED,PAID,REVERSED; DRAFT,REVIEW,APPROVED,EXPORTED,PAID,REVERSED | RESTRICTED |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | RESTRICTED |

Restricción: UNIQUE(worker_id,rule_id,period_start,period_end); no duplicar tarea ni períodos; regla congelada al aprobar.
