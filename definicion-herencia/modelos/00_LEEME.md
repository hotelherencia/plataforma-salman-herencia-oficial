# Diccionario y modelo de datos

109 entidades propuestas; 1409 campos, incluidos campos comunes. No es una migración ejecutada. Cada FK debe validar identidad y sociedad; los contratos financieros no admiten referencias arbitrarias a objetos de otra sociedad.

## Convenciones
IDs UUID; dinero entero en unidad menor mas moneda; cantidades decimales exactas serializadas como cadenas; UTC para instantes y fechas locales para noches. Nulo es desconocido/no aplicable, nunca cero. jsonb se válida segun esquema de funcion antes de persistir. Las credenciales viven en gestor de secretos.

## Restricciones adicionales
### company
UNIQUE(country,tax_id) cuando tax_id no es NULL; no activar sin identificación validada.

### ownership
0 < percentage <= 100; valid_to > valid_from; suma verificada por sociedad/clase/periodo no excede 100; faltante no se completa por inferencia.

### role_grant
Mismo usuario/rol/alcance no se duplica en períodos activos; expiración revoca sesiones pertinentes.

### room
UNIQUE(establishment_id,code); configuración válida capacidad; catálogo real de Hotel Herencia suma 17.

### inventory_day
UNIQUE(establishment_id,room_type_id,night); campos >=0; bloqueo transaccional ordenado; commitments externos en conflicto nunca se ocultan.

### reservation
UNIQUE(company_id,channel_code,external_id) WHERE external_id IS NOT NULL; total = suma de lineas vigentes; estado no prueba cobro.

### room_assignment
EXCLUDE solape room_id con tstzrange(from_at,to_at,[)) en estados activos; to_at > from_at; tenant consistente.

### service_night
UNIQUE(stay_id,night); traslado no duplica noche, cargo ni ADR.

### charge
UNIQUE(company_id,source_key); gross=net+tax; reverso conserva monto/moneda y referencia.

### payment
UNIQUE(company_id,provider,external_transaction_id) WHERE external_transaction_id IS NOT NULL; no contabilizar callback no verificado.

### payment_allocation
Suma de aplicaciones activas <= pago neto disponible; bloqueo de pago/cuenta; moneda identica.

### refund
Suma confirmada + reservada para enviar <= saldo reembolsable; no reintentar a ciegas estado UNKNOWN.

### cash_shift
Una sola caja/moneda/turno abierto; arqueo exacto; cierre/reapertura con auditoría.

### document
UNIQUE(company_id,issuer_party_id,document_type,folio) cuando todos definidos; archivo debe CLEAN.

### stock_movement
UNIQUE(company_id,source_key); no borrar; transferencias son pares con suma cantidad cero; stock disponible no negativo.

### receipt_line
Aceptado/rechazado >=0; acumulado no excede pedido+tolerancia aprobada; una reversion no ignora consumo posterior.

### task_execution
UNIQUE(company_id,device_event_id); participaciones elegibles de tarea suman 1; ended_at>=started_at.

### textile_movement
UNIQUE(company_id,source_key); quantity entero; balance por estado/ubicacion no negativo.

### laundry_line
sent_qty = good_qty+rejected_qty+lost_qty+pending_qty; pending derivado; pérdida exige aprobación.

### breakfast_service
UNIQUE(stay_guest_id,service_date); servicio no consume nuevamente ingredientes ya consumidos por lote.

### space_booking
EXCLUDE overlap para intervalo ampliado con buffers y espacio en HELD/CONFIRMED; aforo validado.

### incentive_award
UNIQUE(worker_id,rule_id,period_start,period_end); no duplicar tarea ni períodos; regla congelada al aprobar.

### bank_movement
UNIQUE(bank_account_id,external_id) sólo cuando ID estable; fingerprint candidato no causa fusion automática.

### reconciliation_allocation
Suma aplicada a fuente no excede disponible; por grupo suma lado BUSINESS = lado BANK para POSTED, o diferencia aprobada explícita.

### outbox_event
Unicidad por event_id (id); transacción junto a dominio; reintentos acotados.

### inbox_event
UNIQUE(integration_id,external_event_id); payload distinto con mismo ID exige investigacion.

### channel_identity
UNIQUE(integration_id,channel,external_user_id); no fusion por nombre.

### message
UNIQUE(company_id,dedup_key); unicidad external_id por cuenta; ventana/permiso se revisa al enviar.

### conversion_event
UNIQUE(company_id,business_event_id,event_name); valor no suma anticipo y venta.

### portal_grant
UNIQUE(token_hash); nunca almacenar token plano; scope no incluye devolución.

### migration_batch
UNIQUE(company_id,file_hash,cutoff_at,schema_version); staging no altera producción.

## Migraciones
Crear tablas en dos pasadas: primero tablas/claves, luego FK en ciclos conceptuales como reserva-cuenta-estadía. La dependencia referencial circular no es un orden circular de tareas. Nuevas columnas se agregan compatibles, se migran datos y se endurecen restricciones después de verificar. No crear columnas de tasa legal sin version/alcance aprobado.

## Datos personales
Los plazos D16 son bloqueo antes de cargar datos reales. Los historiales técnicos minimizan payload; no clonar documentos ni mensajes en audit_event. La eliminación conserva claves anonimas necesarias para importes sujetos a retención legal.
