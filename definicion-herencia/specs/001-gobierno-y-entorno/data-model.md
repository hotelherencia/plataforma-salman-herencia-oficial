# Datos F00

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## outbox_event
Evento persistido con transacción de dominio

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| event_type | varchar(64) | si | NOT NULL | INTERNAL |
| aggregate_id | uuid | si | NOT NULL | INTERNAL |
| aggregate_version | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| payload | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| correlation_id | uuid | si | NOT NULL | INTERNAL |
| occurred_at | timestamptz | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum PENDING,PROCESSING,SENT,FAILED,DEAD_LETTER; PENDING,PROCESSING,SENT,FAILED,DEAD_LETTER | INTERNAL |
| attempts | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| next_attempt_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Unicidad por event_id (id); transacción junto a dominio; reintentos acotados.
