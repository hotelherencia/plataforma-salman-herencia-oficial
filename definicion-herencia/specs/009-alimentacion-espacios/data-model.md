# Datos F08

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## recipe
Receta y rendimiento con versión

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| name | text | si | NOT NULL | INTERNAL |
| recipe_version | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| yield_portions | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,APPROVED,RETIRED; DRAFT,APPROVED,RETIRED | INTERNAL |
| allergen_notes | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## recipe_line
Consumo base de ingrediente

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| recipe_id | uuid | si | NOT NULL; FK recipe.id; mismo company_id salvo entidad global -> recipe | INTERNAL |
| product_id | uuid | si | NOT NULL; FK product.id; mismo company_id salvo entidad global -> product | INTERNAL |
| quantity | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| unit | varchar(64) | si | NOT NULL | INTERNAL |
| allowed_substitutions | jsonb | no | NULL permitido; nunca reemplazar faltante por cero; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## food_batch
Producción que consume ingredientes una vez

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| recipe_id | uuid | si | NOT NULL; FK recipe.id; mismo company_id salvo entidad global -> recipe | INTERNAL |
| business_date | date | si | NOT NULL | INTERNAL |
| portions | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| expires_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PLANNED,PRODUCED,CLOSED; PLANNED,PRODUCED,CLOSED | INTERNAL |
| source_key | text | si | NOT NULL | INTERNAL |
| actual_ingredients | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## breakfast_service
Derecho y servicio por pasajero/dia

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| stay_guest_id | uuid | si | NOT NULL; FK stay_guest.id; mismo company_id salvo entidad global -> stay_guest | INTERNAL |
| service_date | date | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum ELIGIBLE,SERVED,NOT_CONSUMED,SUBSTITUTED,CANCELLED; ELIGIBLE,SERVED,NOT_CONSUMED,SUBSTITUTED,CANCELLED | INTERNAL |
| batch_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK food_batch.id; mismo company_id salvo entidad global -> food_batch | INTERNAL |
| served_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| quantity | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |

Restricción: UNIQUE(stay_guest_id,service_date); servicio no consume nuevamente ingredientes ya consumidos por lote.

## meal_order
Cena subcontratada

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| stay_id | uuid | si | NOT NULL; FK stay.id; mismo company_id salvo entidad global -> stay | INTERNAL |
| supplier_id | uuid | si | NOT NULL; FK supplier.id; mismo company_id salvo entidad global -> supplier | INTERNAL |
| service_date | date | si | NOT NULL | INTERNAL |
| quantity | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| price_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| cost_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum REQUESTED,CONFIRMED,DELIVERED,CANCELLED,INCIDENT; REQUESTED,CONFIRMED,DELIVERED,CANCELLED,INCIDENT | INTERNAL |
| charge_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK charge.id; mismo company_id salvo entidad global -> charge | INTERNAL |
| payable_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK payable.id; mismo company_id salvo entidad global -> payable | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## space
Recurso reservable distinto de habitación

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| created_at | timestamptz | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| updated_at | timestamptz | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PUBLIC_AFTER_APPROVAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PUBLIC_AFTER_APPROVAL |
| establishment_id | uuid | si | NOT NULL; FK establishment.id; mismo company_id salvo entidad global -> establishment | PUBLIC_AFTER_APPROVAL |
| code | varchar(64) | si | NOT NULL | PUBLIC_AFTER_APPROVAL |
| capacity | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PUBLIC_AFTER_APPROVAL |
| policy_id | uuid | si | NOT NULL; FK policy.id; mismo company_id salvo entidad global -> policy | PUBLIC_AFTER_APPROVAL |
| equipment | jsonb | no | NULL permitido; nunca reemplazar faltante por cero; esquema validado; no SQL, secretos o campos arbitrarios | PUBLIC_AFTER_APPROVAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## space_booking
Uso y buffers de montaje/limpieza

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| space_id | uuid | si | NOT NULL; FK space.id; mismo company_id salvo entidad global -> space | INTERNAL |
| contact_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK contact.id; mismo company_id salvo entidad global -> contact | INTERNAL |
| starts_at | timestamptz | si | NOT NULL | INTERNAL |
| ends_at | timestamptz | si | NOT NULL | INTERNAL |
| setup_minutes | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| cleanup_minutes | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| attendees | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum HELD,CONFIRMED,COMPLETED,CANCELLED; HELD,CONFIRMED,COMPLETED,CANCELLED | INTERNAL |
| charge_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK charge.id; mismo company_id salvo entidad global -> charge | INTERNAL |

Restricción: EXCLUDE overlap para intervalo ampliado con buffers y espacio en HELD/CONFIRMED; aforo validado.
