# Datos F17

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## campaign
Plan comercial con gasto autorizado

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| name | text | si | NOT NULL | INTERNAL |
| channel | varchar(64) | si | NOT NULL | INTERNAL |
| source_code | varchar(64) | si | NOT NULL | INTERNAL |
| medium_code | varchar(64) | si | NOT NULL | INTERNAL |
| starts_at | timestamptz | si | NOT NULL | INTERNAL |
| ends_at | timestamptz | si | NOT NULL | INTERNAL |
| budget_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,APPROVED,SCHEDULED,ACTIVE,PAUSED,CLOSED; DRAFT,APPROVED,SCHEDULED,ACTIVE,PAUSED,CLOSED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## content_piece
Contenido con derechos y aprobación

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| campaign_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK campaign.id; mismo company_id salvo entidad global -> campaign | INTERNAL |
| channel | varchar(64) | si | NOT NULL | INTERNAL |
| format | varchar(64) | si | NOT NULL | INTERNAL |
| body | text | si | NOT NULL | INTERNAL |
| asset_document_ids | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |
| external_post_id | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,REVIEW,APPROVED,SCHEDULED,PUBLISHED,FAILED,MANUAL; DRAFT,REVIEW,APPROVED,SCHEDULED,PUBLISHED,FAILED,MANUAL | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
