# Datos F06

Propuesta de persistencia, no migración ejecutada. Tipos/retencion/origen/historia completos en `modelos/diccionario_datos.csv`; no duplicar entidades consumidas de otros paquetes. Los campos JSON se validan por `modelos/esquemas_json.json`.

## supplier
Relación comercial local con un tercero

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| party_id | uuid | si | NOT NULL; FK party.id; mismo company_id salvo entidad global -> party | INTERNAL |
| contact | jsonb | no | NULL permitido; nunca reemplazar faltante por cero; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| payment_terms_days | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,ACTIVE,BLOCKED; DRAFT,ACTIVE,BLOCKED | INTERNAL |
| bank_details_ref | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| bank_verified_at | timestamptz | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## product
Articulo normalizado para compra y consumo

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| code | varchar(64) | si | NOT NULL | INTERNAL |
| name | text | si | NOT NULL | INTERNAL |
| kind | text CHECK enum | si | NOT NULL; enum FOOD,CONSUMABLE,RESALE,TEXTILE,SPARE,ASSET; FOOD,CONSUMABLE,RESALE,TEXTILE,SPARE,ASSET | INTERNAL |
| base_unit | varchar(64) | si | NOT NULL | INTERNAL |
| purchase_unit | varchar(64) | si | NOT NULL | INTERNAL |
| conversion | numeric(20,8) | si | NOT NULL; decimal exacto, límite por regla de negocio | INTERNAL |
| lot_tracking | boolean | si | NOT NULL | INTERNAL |
| expiry_required | boolean | si | NOT NULL | INTERNAL |
| minimum_stock | numeric(18,6) | no | NULL permitido; nunca reemplazar faltante por cero; >= 0 | INTERNAL |
| quality_spec | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## warehouse
Ubicacion de existencias

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
| kind | text CHECK enum | si | NOT NULL; enum STORAGE,FLOOR,KITCHEN,LAUNDRY,QUARANTINE; STORAGE,FLOOR,KITCHEN,LAUNDRY,QUARANTINE | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## stock_lot
Lote utilizable o restringido

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| product_id | uuid | si | NOT NULL; FK product.id; mismo company_id salvo entidad global -> product | INTERNAL |
| warehouse_id | uuid | si | NOT NULL; FK warehouse.id; mismo company_id salvo entidad global -> warehouse | INTERNAL |
| lot_code | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| expires_on | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum AVAILABLE,QUARANTINE,EXPIRED,CLOSED; AVAILABLE,QUARANTINE,EXPIRED,CLOSED | INTERNAL |
| unit_cost_minor | numeric(20,8) | no | NULL permitido; nunca reemplazar faltante por cero; decimal exacto, límite por regla de negocio | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## stock_movement
Libro de cantidades inmutable

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| product_id | uuid | si | NOT NULL; FK product.id; mismo company_id salvo entidad global -> product | INTERNAL |
| lot_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK stock_lot.id; mismo company_id salvo entidad global -> stock_lot | INTERNAL |
| warehouse_id | uuid | si | NOT NULL; FK warehouse.id; mismo company_id salvo entidad global -> warehouse | INTERNAL |
| quantity_delta | numeric(18,6) | si | NOT NULL | INTERNAL |
| kind | varchar(64) | si | NOT NULL | INTERNAL |
| source_type | varchar(64) | si | NOT NULL | INTERNAL |
| source_id | uuid | si | NOT NULL | INTERNAL |
| source_key | text | si | NOT NULL | INTERNAL |
| unit_cost_minor | numeric(20,8) | no | NULL permitido; nunca reemplazar faltante por cero; decimal exacto, límite por regla de negocio | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| transfer_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |

Restricción: UNIQUE(company_id,source_key); no borrar; transferencias son pares con suma cantidad cero; stock disponible no negativo.

## supplier_price
Precio comparable con vigencia

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| supplier_id | uuid | si | NOT NULL; FK supplier.id; mismo company_id salvo entidad global -> supplier | INTERNAL |
| product_id | uuid | si | NOT NULL; FK product.id; mismo company_id salvo entidad global -> product | INTERNAL |
| pack_quantity | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| unit | varchar(64) | si | NOT NULL | INTERNAL |
| net_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| tax_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| freight_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| valid_from | date | si | NOT NULL | INTERNAL |
| valid_to | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| source_type | text CHECK enum | si | NOT NULL; enum QUOTE,INVOICE,LAST_PURCHASE; QUOTE,INVOICE,LAST_PURCHASE | INTERNAL |
| document_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK document.id; mismo company_id salvo entidad global -> document | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## purchase_order
Compromiso autorizado

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| supplier_id | uuid | si | NOT NULL; FK supplier.id; mismo company_id salvo entidad global -> supplier | INTERNAL |
| unit_id | uuid | si | NOT NULL; FK unit.id; mismo company_id salvo entidad global -> unit | INTERNAL |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |
| total_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,REQUESTED,APPROVED,ORDERED,PARTIAL,RECEIVED,CANCELLED; DRAFT,REQUESTED,APPROVED,ORDERED,PARTIAL,RECEIVED,CANCELLED | INTERNAL |
| expected_on | date | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |
| budget_line_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK budget_line.id; mismo company_id salvo entidad global -> budget_line | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## purchase_line
Articulo o servicio pedido

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| order_id | uuid | si | NOT NULL; FK purchase_order.id; mismo company_id salvo entidad global -> purchase_order | INTERNAL |
| product_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK product.id; mismo company_id salvo entidad global -> product | INTERNAL |
| description | text | si | NOT NULL | INTERNAL |
| quantity | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| unit | varchar(64) | si | NOT NULL | INTERNAL |
| unit_price_minor | numeric(20,8) | si | NOT NULL; decimal exacto, límite por regla de negocio | INTERNAL |
| tax_code | varchar(64) | si | NOT NULL | INTERNAL |
| total_minor | bigint | si | NOT NULL; >= 0 | INTERNAL |
| currency | char(3) | si | NOT NULL; ISO 4217; CLP escala 0 en fixture, otras segun catálogo | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## receipt
Entrega física independiente del pago

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| order_id | uuid | si | NOT NULL; FK purchase_order.id; mismo company_id salvo entidad global -> purchase_order | INTERNAL |
| supplier_document_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK document.id; mismo company_id salvo entidad global -> document | INTERNAL |
| received_at | timestamptz | si | NOT NULL | INTERNAL |
| receiver_id | uuid | si | NOT NULL; FK user_account.id; mismo company_id salvo entidad global -> user_account | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum DRAFT,ACCEPTED,DISPUTED,REVERSED; DRAFT,ACCEPTED,DISPUTED,REVERSED | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.

## receipt_line
Cantidad aceptada/rechazada por linea

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| receipt_id | uuid | si | NOT NULL; FK receipt.id; mismo company_id salvo entidad global -> receipt | INTERNAL |
| order_line_id | uuid | si | NOT NULL; FK purchase_line.id; mismo company_id salvo entidad global -> purchase_line | INTERNAL |
| accepted_quantity | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| rejected_quantity | numeric(18,6) | si | NOT NULL; >= 0 | INTERNAL |
| lot_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK stock_lot.id; mismo company_id salvo entidad global -> stock_lot | INTERNAL |
| reason | text | no | NULL permitido; nunca reemplazar faltante por cero | INTERNAL |

Restricción: Aceptado/rechazado >=0; acumulado no excede pedido+tolerancia aprobada; una reversion no ignora consumo posterior.

## stock_count
Conteo con corte y ajuste autorizado

| Campo | Tipo | Obligatorio | Regla/FK | Privacidad |
| --- | --- | --- | --- | --- |
| id | uuid | si | NOT NULL | INTERNAL |
| created_at | timestamptz | si | NOT NULL | INTERNAL |
| updated_at | timestamptz | si | NOT NULL | INTERNAL |
| versión | integer | si | NOT NULL; entero; versión >= 1 y contadores >= 0 | INTERNAL |
| company_id | uuid | si | NOT NULL; FK company.id; mismo company_id salvo entidad global -> company | INTERNAL |
| warehouse_id | uuid | si | NOT NULL; FK warehouse.id; mismo company_id salvo entidad global -> warehouse | INTERNAL |
| snapshot_at | timestamptz | si | NOT NULL | INTERNAL |
| status | text CHECK enum | si | NOT NULL; enum OPEN,COUNTED,RECOUNT,APPROVED,POSTED; OPEN,COUNTED,RECOUNT,APPROVED,POSTED | INTERNAL |
| count_lines | jsonb | si | NOT NULL; esquema validado; no SQL, secretos o campos arbitrarios | INTERNAL |
| approval_id | uuid | no | NULL permitido; nunca reemplazar faltante por cero; FK approval.id; mismo company_id salvo entidad global -> approval | INTERNAL |

Restricción: Integridad de alcance, revisión, estados y evidencia segun spec.
