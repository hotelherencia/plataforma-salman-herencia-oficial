# Datos F01

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## group
Agrupacion gerencial, no fusion jurídica

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| name | text | si | NOT NULL | INTERNAL |
| reporting_currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum ACTIVE,ARCHIVED; ACTIVE,ARCHIVED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## company
Persona jurídica que conserva obligaciones propias

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| group_id | uuid | si | NOT NULL; FK group.id; mismo company_id salvo entidad global -> group | INTERNAL |
| legal_name | text | si | NOT NULL | INTERNAL |
| tax_id | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| country | char(2) | si | NOT NULL; ISO 3166-1 alfa-2 | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,ACTIVE,ARCHIVED; DRAFT,ACTIVE,ARCHIVED | INTERNAL |
| operator_confirmed | boolean | si | NOT NULL | INTERNAL |

Restricción: UNIQUE(country,tax_id) cuando tax_id no es NULL; no activar sin identificación validada.

## party
Persona o entidad con roles societarios o comerciales

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| kind | text CHECK enum | si | NOT NULL; enum PERSON,COMPANY; PERSON,COMPANY | INTERNAL |
| display_name | text | si | NOT NULL | INTERNAL |
| tax_id | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| country | char(2) | si | NOT NULL; ISO 3166-1 alfa-2 | INTERNAL |
| verified_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## ownership
Participación societaria con historia

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| investor_id | uuid | si | NOT NULL; FK party.id; mismo company_id salvo entidad global -> party | INTERNAL |
| percentage | numeric(20,8) | si | NOT NULL; decimal exacto, límite por regla de negocio | INTERNAL |
| share_class | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| valid_from | date | si | NOT NULL | INTERNAL |
| valid_to | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| source_document_id | uuid | si | NOT NULL; FK document.id; mismo company_id salvo entidad global -> document | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum HISTORICAL,PROPOSED,VERIFIED; HISTORICAL,PROPOSED,VERIFIED | INTERNAL |

Restricción: 0 < percentage <= 100; valid_to > valid_from; suma verificada por sociedad/clase/periodo no excede 100; faltante no se completa por inferencia.

## establishment
Lugar operado por una sociedad

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| code | varchar(64) | si | NOT NULL | INTERNAL |
| name | text | si | NOT NULL | INTERNAL |
| timezone | text | si | NOT NULL | INTERNAL |
| address | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,ACTIVE,CLOSED; DRAFT,ACTIVE,CLOSED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## unit
Unidad económica con resultado separado

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| establishment_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK establishment.id; mismo company_id salvo entidad global -> establishment | INTERNAL |
| code | varchar(64) | si | NOT NULL | INTERNAL |
| name | text | si | NOT NULL | INTERNAL |
| kind | text CHECK enum | si | NOT NULL; enum HOTEL,CAFE,PROPERTY,INVESTMENT,HOLDING,CONSTRUCTION; HOTEL,CAFE,PROPERTY,INVESTMENT,HOLDING,CONSTRUCTION | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## cost_center
Destino de asignación gerencial

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| code | varchar(64) | si | NOT NULL | INTERNAL |
| name | text | si | NOT NULL | INTERNAL |
| active | boolean | si | NOT NULL | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## user_account
Cuenta de acceso sin contraseña propia almacenada

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| subject | text | si | NOT NULL | INTERNAL |
| issuer | text | si | NOT NULL | INTERNAL |
| display_name | text | si | NOT NULL | INTERNAL |
| email | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum INVITED,ACTIVE,SUSPENDED,REVOKED; INVITED,ACTIVE,SUSPENDED,REVOKED | INTERNAL |
| mfa_enrolled | boolean | si | NOT NULL | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## role_grant
Alcance efectivo de usuario

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| user_id | uuid | si | NOT NULL; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| role_code | varchar(64) | si | NOT NULL | INTERNAL |
| unit_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| valid_from | timestamptz | si | NOT NULL | INTERNAL |
| valid_to | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| approved_by | uuid | si | NOT NULL; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |

Restricción: Mismo usuario/rol/alcance no se duplica en períodos activos; expiración revoca sesiones pertinentes.

## policy
Regla empresarial versionada

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| unit_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| kind | varchar(64) | si | NOT NULL | INTERNAL |
| policy_version | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| valid_from | timestamptz | si | NOT NULL | INTERNAL |
| valid_to | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| content | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,APPROVED,RETIRED; DRAFT,APPROVED,RETIRED | INTERNAL |
| approved_by | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## approval
Autorización sensible con límite y vigencia

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| requester_id | uuid | si | NOT NULL; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| action | varchar(64) | si | NOT NULL | INTERNAL |
| target_type | varchar(64) | si | NOT NULL | INTERNAL |
| target_id | uuid | si | NOT NULL | INTERNAL |
| payload_hash | text | si | NOT NULL | INTERNAL |
| amount_minor | bigint | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |
| currency | char(3) | no | NULL permitido; nunca reemplazar faltante por cero; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum REQUESTED,APPROVED,REJECTED,EXPIRED,REVOKED; REQUESTED,APPROVED,REJECTED,EXPIRED,REVOKED | INTERNAL |
| approver_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| expires_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| reason | text | si | NOT NULL | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## file_object
Archivo privado con cuarentena y acceso

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| storage_key | text | si | NOT NULL | INTERNAL |
| sha 256 | text | si | NOT NULL | INTERNAL |
| media_type | text | si | NOT NULL | INTERNAL |
| size_bytes | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| scan_status | text CHECK enum | si | NOT NULL; enum QUARANTINE,CLEAN,REJECTED; QUARANTINE,CLEAN,REJECTED | INTERNAL |
| classification | text CHECK enum | si | NOT NULL; enum PUBLIC,INTERNAL,PERSONAL,RESTRICTED; PUBLIC,INTERNAL,PERSONAL,RESTRICTED | INTERNAL |
| retention_class | varchar(64) | si | NOT NULL | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## document
Referencia documental de negocio

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| file_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK file_object.id; mismo company_id salvo entidad global -> file_object | INTERNAL |
| issuer_party_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK party.id; mismo company_id salvo entidad global -> party | INTERNAL |
| document_type | varchar(64) | si | NOT NULL | INTERNAL |
| folio | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| issue_date | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,VALID,REJECTED,CANCELLED; DRAFT,VALID,REJECTED,CANCELLED | INTERNAL |
| related_type | varchar(64) | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| related_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: UNIQUE(company_id,issuer_party_id,document_type,folio) cuando todos definidos; archivo debe CLEAN.

## audit_event
Historia inmutable de acciones relevantes

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| actor_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| agent_execution_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| action | varchar(64) | si | NOT NULL | INTERNAL |
| target_type | varchar(64) | si | NOT NULL | INTERNAL |
| target_id | uuid | si | NOT NULL | INTERNAL |
| occurred_at | timestamptz | si | NOT NULL | INTERNAL |
| correlation_id | uuid | si | NOT NULL | INTERNAL |
| reason | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| change_summary | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| previous_hash | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
