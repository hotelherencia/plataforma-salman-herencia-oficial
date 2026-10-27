# Datos F09

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## asset
Bien propio o de tercero con historia

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| room_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK room.id; mismo company_id salvo entidad global -> room | INTERNAL |
| owner_party_id | uuid | si | NOT NULL; FK party.id; mismo company_id salvo entidad global -> party | INTERNAL |
| code | varchar(64) | si | NOT NULL | INTERNAL |
| category | varchar(64) | si | NOT NULL | INTERNAL |
| model | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| serial | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| condition | text CHECK enum | si | NOT NULL; enum UNKNOWN,GOOD,REPAIR,REPLACE,UNSAFE,RETIRED; UNKNOWN,GOOD,REPAIR,REPLACE,UNSAFE,RETIRED | INTERNAL |
| acquired_on | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| warranty_end | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| cost_minor | bigint | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## maintenance_order
Trabajo preventivo/correctivo

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| asset_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK asset.id; mismo company_id salvo entidad global -> asset | INTERNAL |
| room_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK room.id; mismo company_id salvo entidad global -> room | INTERNAL |
| kind | text CHECK enum | si | NOT NULL; enum PREVENTIVE,CORRECTIVE; PREVENTIVE,CORRECTIVE | INTERNAL |
| priority | text CHECK enum | si | NOT NULL; enum CRITICAL,HIGH,NORMAL,LOW; CRITICAL,HIGH,NORMAL,LOW | INTERNAL |
| description | text | si | NOT NULL | INTERNAL |
| assignee_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| supplier_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK supplier.id; mismo company_id salvo entidad global -> supplier | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum OPEN,PLANNED,IN_PROGRESS,WAITING_PARTS,VERIFICATION,CLOSED,CANCELLED; OPEN,PLANNED,IN_PROGRESS,WAITING_PARTS,VERIFICATION,CLOSED,CANCELLED | INTERNAL |
| due_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| room_block_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK room_block.id; mismo company_id salvo entidad global -> room_block | INTERNAL |
| cost_minor | bigint | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## asset_inspection
Evaluación de calidad documentada

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| asset_id | uuid | si | NOT NULL; FK asset.id; mismo company_id salvo entidad global -> asset | INTERNAL |
| checked_at | timestamptz | si | NOT NULL | INTERNAL |
| inspector_id | uuid | si | NOT NULL; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| safety | varchar(64) | si | NOT NULL | INTERNAL |
| hygiene | varchar(64) | si | NOT NULL | INTERNAL |
| functionality | varchar(64) | si | NOT NULL | INTERNAL |
| recommendation | text CHECK enum | si | NOT NULL; enum KEEP,REPAIR,REPLACE,RETIRE; KEEP,REPAIR,REPLACE,RETIRE | INTERNAL |
| document_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK document.id; mismo company_id salvo entidad global -> document | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## renewal_item
Inversion justificada

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| asset_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK asset.id; mismo company_id salvo entidad global -> asset | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| description | text | si | NOT NULL | INTERNAL |
| quantity | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| priority | text CHECK enum | si | NOT NULL; enum SAFETY,QUALITY,EFFICIENCY,APPEARANCE; SAFETY,QUALITY,EFFICIENCY,APPEARANCE | INTERNAL |
| budget_line_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK budget_line.id; mismo company_id salvo entidad global -> budget_line | INTERNAL |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |
| purchase_order_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK purchase_order.id; mismo company_id salvo entidad global -> purchase_order | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PROPOSED,QUOTED,APPROVED,ORDERED,RECEIVED,INSTALLED,ACCEPTED,CANCELLED; PROPOSED,QUOTED,APPROVED,ORDERED,RECEIVED,INSTALLED,ACCEPTED,CANCELLED | INTERNAL |
| new_asset_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK asset.id; mismo company_id salvo entidad global -> asset | INTERNAL |
| estimated_downtime_hours | numeric(18,6) | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
