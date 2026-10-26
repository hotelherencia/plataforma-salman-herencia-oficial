# Datos F07

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## task
Trabajo operativo identificable

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| room_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK room.id; mismo company_id salvo entidad global -> room | INTERNAL |
| area_code | varchar(64) | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| stay_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK stay.id; mismo company_id salvo entidad global -> stay | INTERNAL |
| kind | varchar(64) | si | NOT NULL | INTERNAL |
| assignee_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK worker.id; mismo company_id salvo entidad global -> worker | INTERNAL |
| due_at | timestamptz | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PENDING,ASSIGNED,IN_PROGRESS,DONE,INSPECTION,REWORK,ACCEPTED,CANCELLED; PENDING,ASSIGNED,IN_PROGRESS,DONE,INSPECTION,REWORK,ACCEPTED,CANCELLED | INTERNAL |
| source_key | text | si | NOT NULL | INTERNAL |
| checklist_version | text | si | NOT NULL | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## task_execution
Trabajo efectivo sin duplicados

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| task_id | uuid | si | NOT NULL; FK task.id; mismo company_id salvo entidad global -> task | INTERNAL |
| worker_id | uuid | si | NOT NULL; FK worker.id; mismo company_id salvo entidad global -> worker | INTERNAL |
| started_at | timestamptz | si | NOT NULL | INTERNAL |
| ended_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| paused_seconds | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| checklist_result | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| device_event_id | uuid | si | NOT NULL | INTERNAL |
| participation | numeric(20,8) | si | NOT NULL; decimal exacto, límite por regla de negocio | INTERNAL |
| quality_status | text CHECK enum | si | NOT NULL; enum PENDING,PASS,FAIL; PENDING,PASS,FAIL | INTERNAL |

Restricción: UNIQUE(company_id,device_event_id); participaciones elegibles de tarea suman 1; ended_at>=started_at.

## inspection
Control de calidad

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| task_id | uuid | si | NOT NULL; FK task.id; mismo company_id salvo entidad global -> task | INTERNAL |
| inspector_id | uuid | si | NOT NULL; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| checked_at | timestamptz | si | NOT NULL | INTERNAL |
| result | text CHECK enum | si | NOT NULL; enum PASS,FAIL; PASS,FAIL | INTERNAL |
| findings | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| release_room | boolean | si | NOT NULL | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## textile_movement
Pieza reutilizable y su estado

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| product_id | uuid | si | NOT NULL; FK product.id; mismo company_id salvo entidad global -> product | INTERNAL |
| quantity | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| from_state | varchar(64) | si | NOT NULL | INTERNAL |
| to_state | varchar(64) | si | NOT NULL | INTERNAL |
| from_warehouse_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK warehouse.id; mismo company_id salvo entidad global -> warehouse | INTERNAL |
| to_warehouse_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK warehouse.id; mismo company_id salvo entidad global -> warehouse | INTERNAL |
| room_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK room.id; mismo company_id salvo entidad global -> room | INTERNAL |
| stay_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK stay.id; mismo company_id salvo entidad global -> stay | INTERNAL |
| task_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK task.id; mismo company_id salvo entidad global -> task | INTERNAL |
| laundry_lot_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK laundry_lot.id; mismo company_id salvo entidad global -> laundry_lot | INTERNAL |
| source_key | text | si | NOT NULL | INTERNAL |

Restricción: UNIQUE(company_id,source_key); quantity entero; balance por estado/ubicacion no negativo.

## laundry_lot
Envio y retorno de piezas o kilos

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| supplier_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK supplier.id; mismo company_id salvo entidad global -> supplier | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| sent_at | timestamptz | si | NOT NULL | INTERNAL |
| received_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum OPEN,SENT,PARTIAL,RECEIVED,DISPUTED,CLOSED; OPEN,SENT,PARTIAL,RECEIVED,DISPUTED,CLOSED | INTERNAL |
| weight_kg | numeric(18,6) | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |
| cost_minor | bigint | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| allocation_basis | text CHECK enum | si | NOT NULL; enum PIECE,WEIGHT,ESTIMATED_WEIGHT; PIECE,WEIGHT,ESTIMATED_WEIGHT | INTERNAL |
| document_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK document.id; mismo company_id salvo entidad global -> document | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## laundry_line
Balance por textil del lote

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| laundry_lot_id | uuid | si | NOT NULL; FK laundry_lot.id; mismo company_id salvo entidad global -> laundry_lot | INTERNAL |
| product_id | uuid | si | NOT NULL; FK product.id; mismo company_id salvo entidad global -> product | INTERNAL |
| sent_qty | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| good_qty | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| rejected_qty | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| lost_qty | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| unit_weight_kg | numeric(18,6) | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |
| approved_loss_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |

Restricción: sent_qty = good_qty+rejected_qty+lost_qty+pending_qty; pending derivado; pérdida exige aprobación.
