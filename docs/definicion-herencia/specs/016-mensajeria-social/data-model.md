# Datos F15

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## conversation
Hilo y toma humana exclusiva

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PERSONAL |
| created_at | timestamptz | si | NOT NULL | PERSONAL |
| updated_at | timestamptz | si | NOT NULL | PERSONAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PERSONAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PERSONAL |
| identity_id | uuid | si | NOT NULL; FK channel_identity.id; mismo company_id salvo entidad global -> channel_identity | PERSONAL |
| status | text CHECK enum | si | NOT NULL; enum OPEN,WAITING_CUSTOMER,WAITING_AGENT,RESOLVED,CLOSED; OPEN,WAITING_CUSTOMER,WAITING_AGENT,RESOLVED,CLOSED | PERSONAL |
| owner_mode | text CHECK enum | si | NOT NULL; enum HUMAN,BOT,UNASSIGNED; HUMAN,BOT,UNASSIGNED | PERSONAL |
| owner_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | PERSONAL |
| priority | varchar(64) | si | NOT NULL | PERSONAL |
| last_inbound_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| service_window_until | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| handoff_version | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PERSONAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## message
Mensaje único con estado de envio

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PERSONAL |
| created_at | timestamptz | si | NOT NULL | PERSONAL |
| updated_at | timestamptz | si | NOT NULL | PERSONAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PERSONAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PERSONAL |
| conversation_id | uuid | si | NOT NULL; FK conversation.id; mismo company_id salvo entidad global -> conversation | PERSONAL |
| external_id | text | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| direction | text CHECK enum | si | NOT NULL; enum INBOUND,OUTBOUND; INBOUND,OUTBOUND | PERSONAL |
| body_secret_ref | text | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| template_id | text | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| purpose | varchar(64) | si | NOT NULL | PERSONAL |
| status | text CHECK enum | si | NOT NULL; enum QUEUED,SENT,DELIVERED,READ,FAILED,BLOCKED; QUEUED,SENT,DELIVERED,READ,FAILED,BLOCKED | PERSONAL |
| sent_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| dedup_key | text | si | NOT NULL | PERSONAL |
| correlation_id | uuid | si | NOT NULL | PERSONAL |

Restricción: UNIQUE(company_id,dedup_key); unicidad external_id por cuenta; ventana/permiso se revisa al enviar.
