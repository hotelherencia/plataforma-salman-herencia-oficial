# Datos F14

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## contact
Identidad comercial mínima

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PERSONAL |
| created_at | timestamptz | si | NOT NULL | PERSONAL |
| updated_at | timestamptz | si | NOT NULL | PERSONAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PERSONAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PERSONAL |
| display_name | text | si | NOT NULL | PERSONAL |
| email | text | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| phone | text | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| preferred_language | varchar(64) | si | NOT NULL | PERSONAL |
| status | text CHECK enum | si | NOT NULL; enum ACTIVE,MERGED,RESTRICTED,ANONYMIZED; ACTIVE,MERGED,RESTRICTED,ANONYMIZED | PERSONAL |
| merged_into | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK contact.id; mismo company_id salvo entidad global -> contact | PERSONAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## channel_identity
Identidad acotada a cuenta/canal

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PERSONAL |
| created_at | timestamptz | si | NOT NULL | PERSONAL |
| updated_at | timestamptz | si | NOT NULL | PERSONAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PERSONAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PERSONAL |
| contact_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK contact.id; mismo company_id salvo entidad global -> contact | PERSONAL |
| integration_id | uuid | si | NOT NULL; FK integration_account.id; mismo company_id salvo entidad global -> integration_account | PERSONAL |
| channel | varchar(64) | si | NOT NULL | PERSONAL |
| external_user_id | text | si | NOT NULL | PERSONAL |
| verified_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |

Restricción: UNIQUE(integration_id,channel,external_user_id); no fusion por nombre.

## consent
Permiso por finalidad y canal

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PERSONAL |
| created_at | timestamptz | si | NOT NULL | PERSONAL |
| updated_at | timestamptz | si | NOT NULL | PERSONAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PERSONAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PERSONAL |
| contact_id | uuid | si | NOT NULL; FK contact.id; mismo company_id salvo entidad global -> contact | PERSONAL |
| purpose | text CHECK enum | si | NOT NULL; enum SERVICE,MARKETING,MEASUREMENT,WHATSAPP_CONTACT; SERVICE,MARKETING,MEASUREMENT,WHATSAPP_CONTACT | PERSONAL |
| channel | varchar(64) | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| status | text CHECK enum | si | NOT NULL; enum GRANTED,REVOKED,EXPIRED; GRANTED,REVOKED,EXPIRED | PERSONAL |
| obtained_at | timestamptz | si | NOT NULL | PERSONAL |
| proof_document_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK document.id; mismo company_id salvo entidad global -> document | PERSONAL |
| notice_version | text | si | NOT NULL | PERSONAL |
| revoked_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## opportunity
Consulta convertida en proceso comercial

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| contact_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK contact.id; mismo company_id salvo entidad global -> contact | INTERNAL |
| conversation_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK conversation.id; mismo company_id salvo entidad global -> conversation | INTERNAL |
| owner_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum NEW,ACTIVE,QUOTED,FOLLOW_UP,WON,LOST; NEW,ACTIVE,QUOTED,FOLLOW_UP,WON,LOST | INTERNAL |
| quote_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK quote.id; mismo company_id salvo entidad global -> quote | INTERNAL |
| reservation_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK reservation.id; mismo company_id salvo entidad global -> reservation | INTERNAL |
| next_action_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| lost_reason | varchar(64) | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
