# Datos F02

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## room_type
Categoría comercial validada

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| created_at | timestamptz | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| updated_at | timestamptz | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PUBLIC_AFTER_APPROVAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PUBLIC_AFTER_APPROVAL |
| establishment_id | uuid | si | NOT NULL; FK establishment.id; mismo company_id salvo entidad global -> establishment | PUBLIC_AFTER_APPROVAL |
| code | varchar(64) | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| name | text | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| max_adults | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PUBLIC_AFTER_APPROVAL |
| max_children | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PUBLIC_AFTER_APPROVAL |
| max_total | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PUBLIC_AFTER_APPROVAL |
| attributes | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | PUBLIC_AFTER_APPROVAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## room
Habitación física

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| establishment_id | uuid | si | NOT NULL; FK establishment.id; mismo company_id salvo entidad global -> establishment | INTERNAL |
| room_type_id | uuid | si | NOT NULL; FK room_type.id; mismo company_id salvo entidad global -> room_type | INTERNAL |
| code | varchar(64) | si | NOT NULL | INTERNAL |
| floor | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| private_bath | boolean | si | NOT NULL | INTERNAL |
| operational_status | text CHECK enum | si | NOT NULL; enum ACTIVE,OUT_OF_SERVICE,RETIRED; ACTIVE,OUT_OF_SERVICE,RETIRED | INTERNAL |
| cleaning_status | text CHECK enum | si | NOT NULL; enum CLEAN,DIRTY,IN_PROGRESS,INSPECTION,READY; CLEAN,DIRTY,IN_PROGRESS,INSPECTION,READY | INTERNAL |
| bed_configuration | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| capacity_valid_from | date | si | NOT NULL | INTERNAL |

Restricción: UNIQUE(establishment_id,code); configuración válida capacidad; catálogo real de Hotel Herencia suma 17.

## room_block
Indisponibilidad autorizada con fechas

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| room_id | uuid | si | NOT NULL; FK room.id; mismo company_id salvo entidad global -> room | INTERNAL |
| start_date | date | si | NOT NULL | INTERNAL |
| end_date | date | si | NOT NULL | INTERNAL |
| reason | varchar(64) | si | NOT NULL | INTERNAL |
| work_order_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK maintenance_order.id; mismo company_id salvo entidad global -> maintenance_order | INTERNAL |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PROPOSED,ACTIVE,RELEASED,CANCELLED; PROPOSED,ACTIVE,RELEASED,CANCELLED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## inventory_day
Capacidad serializada por tipo y noche

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| establishment_id | uuid | si | NOT NULL; FK establishment.id; mismo company_id salvo entidad global -> establishment | INTERNAL |
| room_type_id | uuid | si | NOT NULL; FK room_type.id; mismo company_id salvo entidad global -> room_type | INTERNAL |
| night | date | si | NOT NULL | INTERNAL |
| capacity | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| blocked | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| confirmed | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| held | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| revisión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |

Restricción: UNIQUE(establishment_id,room_type_id,night); campos >=0; bloqueo transaccional ordenado; commitments externos en conflicto nunca se ocultan.

## rate_plan
Plan comercial con condiciones

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| created_at | timestamptz | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| updated_at | timestamptz | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PUBLIC_AFTER_APPROVAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PUBLIC_AFTER_APPROVAL |
| code | varchar(64) | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| name | text | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | PUBLIC_AFTER_APPROVAL |
| policy_id | uuid | si | NOT NULL; FK policy.id; mismo company_id salvo entidad global -> policy | PUBLIC_AFTER_APPROVAL |
| breakfast_included | boolean | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,ACTIVE,RETIRED; DRAFT,ACTIVE,RETIRED | PUBLIC_AFTER_APPROVAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## rate_price
Precio por fecha y ocupación

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| rate_plan_id | uuid | si | NOT NULL; FK rate_plan.id; mismo company_id salvo entidad global -> rate_plan | INTERNAL |
| room_type_id | uuid | si | NOT NULL; FK room_type.id; mismo company_id salvo entidad global -> room_type | INTERNAL |
| start_date | date | si | NOT NULL | INTERNAL |
| end_date | date | si | NOT NULL | INTERNAL |
| adults | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| children | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| channel_code | varchar(64) | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| amount_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| tax_included | boolean | si | NOT NULL | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| priority | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## promotion
Descuento al cliente, no comisión

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| code | varchar(64) | si | NOT NULL | INTERNAL |
| rate_plan_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK rate_plan.id; mismo company_id salvo entidad global -> rate_plan | INTERNAL |
| kind | text CHECK enum | si | NOT NULL; enum PERCENT,FIXED; PERCENT,FIXED | INTERNAL |
| value | numeric(20,8) | si | NOT NULL; decimal exacto, límite por regla de negocio | INTERNAL |
| stackable | boolean | si | NOT NULL | INTERNAL |
| priority | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| starts_at | timestamptz | si | NOT NULL | INTERNAL |
| ends_at | timestamptz | si | NOT NULL | INTERNAL |
| approval_id | uuid | si | NOT NULL; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## sale_restriction
Límites de venta de un plan/tipo

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| rate_plan_id | uuid | si | NOT NULL; FK rate_plan.id; mismo company_id salvo entidad global -> rate_plan | INTERNAL |
| room_type_id | uuid | si | NOT NULL; FK room_type.id; mismo company_id salvo entidad global -> room_type | INTERNAL |
| date | date | si | NOT NULL | INTERNAL |
| min_nights | integer | no | NULL permitido; nunca reemplazar faltante por cero; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| max_nights | integer | no | NULL permitido; nunca reemplazar faltante por cero; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| closed_arrival | boolean | si | NOT NULL | INTERNAL |
| closed_departure | boolean | si | NOT NULL | INTERNAL |
| stop_sell | boolean | si | NOT NULL | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
