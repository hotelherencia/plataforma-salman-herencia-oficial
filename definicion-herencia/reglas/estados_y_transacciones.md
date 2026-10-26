# Estados y transacciones

La tabla de transiciones específica el comportamiento de los procesos sensibles. Los nombres de estado se normalizaron contra los enums del diccionario. La tabla define transiciones sensibles; cualquier transición no autorizada por este contrato y la regla de su comando se rechaza. Conversation usa owner_mode, no el estado comercial del hilo. La validación es documental, no ejecuta cambios de base.

## Reserva e inventario
BEGIN; bloquear inventory_day por establecimiento,tipo,fecha ordenados; validar capacidad-bloqueado-confirmado-held; purgar/expirar retenciones bajo lock; insertar hold/reserva/lineas; modificar contadores; crear outbox; COMMIT. UNIQUE de reserva externa y ejecución idempotente. Confirmacion de un hold mueve held a confirmed en la misma transacción, nunca resta capacidad dos veces.

La asignación física usa rango timestamp semiabierto y constraint de no solapamiento para el mismo cuarto. Una mudanza cierra segmento y abre otro; service_night preserva una noche por linea/fecha. Capacidad comercial y asignación física no pueden contradecir bloqueos. Una sobreventa externa se registra CONFLICT y se resuelve, no se oculta sobrescribiendo una reserva.

## Pago
Intento antes de salir a proveedor; registrar referencia y monto; callback/consulta verificados crean payment único, no una venta adicional. Bloquear payment/folio al aplicar. Cobro confirmado después de expiración vuelve a validar cupo; si falta, mantener dinero y caso pendiente de alternativa/reembolso. UNKNOWN no es FAILED. Una devolución confirmada libera/revierte aplicaciones segun su naturaleza, referencia pago original y conserva saldo restante.

## Compras y consumo
Orden aprobada compromete presupuesto; receipt actualiza stock y outbox. Factura crea obligación al verificarse su recepcion/servicio; pago extingue deuda, no recibe bienes. Consumo cocina ocurre al producir; servicio consume porción producida. Textil cambia de estado sin baja patrimonial por uso. Cada movimiento tiene causa única.

## Cierre y reversos
POSTED/CLOSED impide edicion destructiva. Reabrir necesita motivo/autorizacion y nueva versión; reverso produce contrapartida enlazada. Nunca deshacer hechos externos por rollback de código. Perder la respuesta de una acción no justifica crear otra referencia externa.
