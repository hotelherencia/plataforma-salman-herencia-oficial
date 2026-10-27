# Datos F12

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## cost_entry
Costo con fuente y grado de certeza

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| stay_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK stay.id; mismo company_id salvo entidad global -> stay | INTERNAL |
| room_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK room.id; mismo company_id salvo entidad global -> room | INTERNAL |
| concept | varchar(64) | si | NOT NULL | INTERNAL |
| service_date | date | si | NOT NULL | INTERNAL |
| amount_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| certainty | text CHECK enum | si | NOT NULL; enum MEASURED,ESTIMATED,PENDING; MEASURED,ESTIMATED,PENDING | INTERNAL |
| source_type | varchar(64) | si | NOT NULL | INTERNAL |
| source_id | uuid | si | NOT NULL | INTERNAL |
| source_key | text | si | NOT NULL | INTERNAL |
| allocation_rule_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK policy.id; mismo company_id salvo entidad global -> policy | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## cost_pool
Bolsa comun neta de costos ya directos

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| concept | varchar(64) | si | NOT NULL | INTERNAL |
| period_start | date | si | NOT NULL | INTERNAL |
| period_end | date | si | NOT NULL | INTERNAL |
| total_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| already_direct_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| basis | text CHECK enum | si | NOT NULL; enum ROOM_NIGHTS,AREA,TIME,OTHER_APPROVED; ROOM_NIGHTS,AREA,TIME,OTHER_APPROVED | INTERNAL |
| policy_id | uuid | si | NOT NULL; FK policy.id; mismo company_id salvo entidad global -> policy | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,APPROVED,ALLOCATED,CLOSED; DRAFT,APPROVED,ALLOCATED,CLOSED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## budget_line
Presupuesto separado por naturaleza

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| period_start | date | si | NOT NULL | INTERNAL |
| period_end | date | si | NOT NULL | INTERNAL |
| category | text CHECK enum | si | NOT NULL; enum OPERATING,CAPEX,TECHNOLOGY,ADVERTISING; OPERATING,CAPEX,TECHNOLOGY,ADVERTISING | INTERNAL |
| concept | varchar(64) | si | NOT NULL | INTERNAL |
| approved_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## conversion_event
Hecho comercial sin duplicación

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| reservation_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK reservation.id; mismo company_id salvo entidad global -> reservation | INTERNAL |
| campaign_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK campaign.id; mismo company_id salvo entidad global -> campaign | INTERNAL |
| event_name | varchar(64) | si | NOT NULL | INTERNAL |
| business_event_id | uuid | si | NOT NULL | INTERNAL |
| amount_minor | bigint | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |
| currency | char(3) | no | NULL permitido; nunca reemplazar faltante por cero; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| consent_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK consent.id; mismo company_id salvo entidad global -> consent | INTERNAL |
| occurred_at | timestamptz | si | NOT NULL | INTERNAL |
| export_status | text CHECK enum | si | NOT NULL; enum INTERNAL,QUEUED,SENT,BLOCKED,FAILED; INTERNAL,QUEUED,SENT,BLOCKED,FAILED | INTERNAL |

Restricción: UNIQUE(company_id,business_event_id,event_name); valor no suma anticipo y venta.
