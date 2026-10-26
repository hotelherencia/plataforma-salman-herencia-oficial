# Datos F03

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## quote
Oferta inmutable con expiración

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| establishment_id | uuid | si | NOT NULL; FK establishment.id; mismo company_id salvo entidad global -> establishment | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| total_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| tax_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| policy_snapshot | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| price_snapshot | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| expires_at | timestamptz | si | NOT NULL | INTERNAL |
| contact_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK contact.id; mismo company_id salvo entidad global -> contact | INTERNAL |
| origin | jsonb | no | NULL permitido; nunca reemplazar faltante por cero; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum OPEN,ACCEPTED,EXPIRED,SUPERSEDED; OPEN,ACCEPTED,EXPIRED,SUPERSEDED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## inventory_hold
Retención temporal, no reserva vendida

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| quote_id | uuid | si | NOT NULL; FK quote.id; mismo company_id salvo entidad global -> quote | INTERNAL |
| hold_items | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| expires_at | timestamptz | si | NOT NULL | INTERNAL |
| session_hash | text | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum ACTIVE,CONSUMED,EXPIRED,RELEASED; ACTIVE,CONSUMED,EXPIRED,RELEASED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## reservation
Compromiso comercial de alojamiento

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| establishment_id | uuid | si | NOT NULL; FK establishment.id; mismo company_id salvo entidad global -> establishment | INTERNAL |
| quote_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK quote.id; mismo company_id salvo entidad global -> quote | INTERNAL |
| contact_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK contact.id; mismo company_id salvo entidad global -> contact | INTERNAL |
| payer_party_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK party.id; mismo company_id salvo entidad global -> party | INTERNAL |
| channel_code | varchar(64) | si | NOT NULL | INTERNAL |
| external_id | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| external_revision | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| total_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PENDING,CONFIRMED,CANCELLED,NO_SHOW,COMPLETED,CONFLICT; PENDING,CONFIRMED,CANCELLED,NO_SHOW,COMPLETED,CONFLICT | INTERNAL |
| policy_snapshot | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| confirmed_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: UNIQUE(company_id,channel_code,external_id) WHERE external_id IS NOT NULL; total = suma de lineas vigentes; estado no prueba cobro.

## reservation_line
Una unidad de alojamiento dentro de reserva

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| reservation_id | uuid | si | NOT NULL; FK reservation.id; mismo company_id salvo entidad global -> reservation | INTERNAL |
| room_type_id | uuid | si | NOT NULL; FK room_type.id; mismo company_id salvo entidad global -> room_type | INTERNAL |
| arrival_date | date | si | NOT NULL | INTERNAL |
| departure_date | date | si | NOT NULL | INTERNAL |
| adults | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| children | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| price_snapshot | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| total_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PENDING,CONFIRMED,CANCELLED,COMPLETED; PENDING,CONFIRMED,CANCELLED,COMPLETED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## reservation_change
Versión y diferencia de modificación

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| reservation_id | uuid | si | NOT NULL; FK reservation.id; mismo company_id salvo entidad global -> reservation | INTERNAL |
| from_version | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| to_version | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| change_kind | varchar(64) | si | NOT NULL | INTERNAL |
| delta_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| accepted_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |
| reason | text | si | NOT NULL | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## corporate_agreement
Convenio y crédito empresarial

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| payer_party_id | uuid | si | NOT NULL; FK party.id; mismo company_id salvo entidad global -> party | INTERNAL |
| rate_plan_id | uuid | si | NOT NULL; FK rate_plan.id; mismo company_id salvo entidad global -> rate_plan | INTERNAL |
| credit_limit_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| payment_days | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| valid_from | date | si | NOT NULL | INTERNAL |
| valid_to | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| approval_id | uuid | si | NOT NULL; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
