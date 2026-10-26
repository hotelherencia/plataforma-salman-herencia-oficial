# Datos F18

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## portal_grant
Acceso limitado al huésped

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PERSONAL |
| created_at | timestamptz | si | NOT NULL | PERSONAL |
| updated_at | timestamptz | si | NOT NULL | PERSONAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PERSONAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PERSONAL |
| reservation_id | uuid | si | NOT NULL; FK reservation.id; mismo company_id salvo entidad global -> reservation | PERSONAL |
| contact_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK contact.id; mismo company_id salvo entidad global -> contact | PERSONAL |
| token_hash | text | si | NOT NULL | PERSONAL |
| expires_at | timestamptz | si | NOT NULL | PERSONAL |
| revoked_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| scopes | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | PERSONAL |
| verified_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |

Restricción: UNIQUE(token_hash); nunca almacenar token plano; scope no incluye devolución.

## service_ticket
Solicitud o reclamo con responsable

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | PERSONAL |
| created_at | timestamptz | si | NOT NULL | PERSONAL |
| updated_at | timestamptz | si | NOT NULL | PERSONAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | PERSONAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | PERSONAL |
| stay_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK stay.id; mismo company_id salvo entidad global -> stay | PERSONAL |
| room_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK room.id; mismo company_id salvo entidad global -> room | PERSONAL |
| category | varchar(64) | si | NOT NULL | PERSONAL |
| description | text | si | NOT NULL | PERSONAL |
| priority | varchar(64) | si | NOT NULL | PERSONAL |
| owner_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | PERSONAL |
| due_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |
| status | text CHECK enum | si | NOT NULL; enum OPEN,ASSIGNED,IN_PROGRESS,RESOLVED,CLOSED,REOPENED; OPEN,ASSIGNED,IN_PROGRESS,RESOLVED,CLOSED,REOPENED | PERSONAL |
| maintenance_order_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK maintenance_order.id; mismo company_id salvo entidad global -> maintenance_order | PERSONAL |
| resolution | text | no | NULL permitido; nunca reemplazar faltante por cero | PERSONAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
