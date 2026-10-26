# Datos F16

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## agent_run
Ejecución limitada y evaluable

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| conversation_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK conversation.id; mismo company_id salvo entidad global -> conversation | INTERNAL |
| agent_role | varchar(64) | si | NOT NULL | INTERNAL |
| model_ref | text | si | NOT NULL | INTERNAL |
| prompt_version | text | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum STARTED,COMPLETED,ESCALATED,FAILED,STOPPED; STARTED,COMPLETED,ESCALATED,FAILED,STOPPED | INTERNAL |
| cost_minor | bigint | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |
| currency | char(3) | no | NULL permitido; nunca reemplazar faltante por cero; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| tools_used | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| started_at | timestamptz | si | NOT NULL | INTERNAL |
| ended_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
