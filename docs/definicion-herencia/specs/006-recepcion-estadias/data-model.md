# Datos F05

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## guest
Pasajero con datos mínimos protegidos

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PERSONAL |
| created_at | timestamptz | si | NOT NULL | PERSONAL |
| updated_at | timestamptz | si | NOT NULL | PERSONAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PERSONAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PERSONAL |
| display_name | text | si | NOT NULL | PERSONAL |
| document_type | varchar(64) | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| document_secret_ref | text | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| country_of_residence | char(2) | no | NULL permitido; nunca reemplazar faltante por cero; ISO 3166-1 alfa-2 | PERSONAL |
| contact_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK contact.id; mismo company_id salvo entidad global -> contact | PERSONAL |
| is_minor | boolean | si | NOT NULL | PERSONAL |
| guardian_guest_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK guest.id; mismo company_id salvo entidad global -> guest | PERSONAL |
| retention_class | varchar(64) | si | NOT NULL | PERSONAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## stay
Servicio real independiente de reserva y pago

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| reservation_line_id | uuid | si | NOT NULL; FK reservation_line.id; mismo company_id salvo entidad global -> reservation_line | INTERNAL |
| arrival_actual | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| departure_actual | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum EXPECTED,IN_HOUSE,DEPARTED,CANCELLED; EXPECTED,IN_HOUSE,DEPARTED,CANCELLED | INTERNAL |
| business_date | date | si | NOT NULL | INTERNAL |
| folio_id | uuid | si | NOT NULL; FK folio.id; mismo company_id salvo entidad global -> folio | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## stay_guest
Presencia efectiva de cada pasajero

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| stay_id | uuid | si | NOT NULL; FK stay.id; mismo company_id salvo entidad global -> stay | INTERNAL |
| guest_id | uuid | si | NOT NULL; FK guest.id; mismo company_id salvo entidad global -> guest | INTERNAL |
| arrived_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| departed_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| breakfast_eligible | boolean | si | NOT NULL | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## room_assignment
Segmento físico sin solapes

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| stay_id | uuid | si | NOT NULL; FK stay.id; mismo company_id salvo entidad global -> stay | INTERNAL |
| room_id | uuid | si | NOT NULL; FK room.id; mismo company_id salvo entidad global -> room | INTERNAL |
| from_at | timestamptz | si | NOT NULL | INTERNAL |
| to_at | timestamptz | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PLANNED,ACTIVE,CLOSED,CANCELLED; PLANNED,ACTIVE,CLOSED,CANCELLED | INTERNAL |
| reason | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: EXCLUDE solape room_id con tstzrange(from_at,to_at,[)) en estados activos; to_at > from_at; tenant consistente.

## service_night
Unidad canónica de servicio e ingreso por noche

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| stay_id | uuid | si | NOT NULL; FK stay.id; mismo company_id salvo entidad global -> stay | INTERNAL |
| night | date | si | NOT NULL | INTERNAL |
| room_id | uuid | si | NOT NULL; FK room.id; mismo company_id salvo entidad global -> room | INTERNAL |
| occupied | boolean | si | NOT NULL | INTERNAL |
| persons | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| charge_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK charge.id; mismo company_id salvo entidad global -> charge | INTERNAL |
| cost_assignment | jsonb | no | NULL permitido; nunca reemplazar faltante por cero; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |

Restricción: UNIQUE(stay_id,night); traslado no duplica noche, cargo ni ADR.

## shift_log
Entrega operacional entre turnos

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| establishment_id | uuid | si | NOT NULL; FK establishment.id; mismo company_id salvo entidad global -> establishment | INTERNAL |
| business_date | date | si | NOT NULL | INTERNAL |
| from_user_id | uuid | si | NOT NULL; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| to_user_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| summary | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| accepted_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum OPEN,HANDED_OVER,ACCEPTED,DISPUTED; OPEN,HANDED_OVER,ACCEPTED,DISPUTED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## custody_item
Llave u objeto bajo custodia

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PERSONAL |
| created_at | timestamptz | si | NOT NULL | PERSONAL |
| updated_at | timestamptz | si | NOT NULL | PERSONAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PERSONAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PERSONAL |
| kind | text CHECK enum | si | NOT NULL; enum KEY,LOST_ITEM; KEY,LOST_ITEM | PERSONAL |
| room_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK room.id; mismo company_id salvo entidad global -> room | PERSONAL |
| stay_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK stay.id; mismo company_id salvo entidad global -> stay | PERSONAL |
| description | text | si | NOT NULL | PERSONAL |
| location | text | si | NOT NULL | PERSONAL |
| status | text CHECK enum | si | NOT NULL; enum HELD,ISSUED,RETURNED,DISPOSED; HELD,ISSUED,RETURNED,DISPOSED | PERSONAL |
| recipient_ref | text | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| delivered_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## night_audit
Revisión de fecha operacional

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| establishment_id | uuid | si | NOT NULL; FK establishment.id; mismo company_id salvo entidad global -> establishment | INTERNAL |
| business_date | date | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum OPEN,CHECKING,CLOSED,REOPENED; OPEN,CHECKING,CLOSED,REOPENED | INTERNAL |
| exceptions | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| closed_by | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| closed_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
