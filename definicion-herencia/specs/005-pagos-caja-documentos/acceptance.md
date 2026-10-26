# Aceptacion F04

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-PAY-001-P | PAY-001 | 100000 recibidos en diciembre para enero figuran como anticipo y obligación futura. | Anticipo diciembre para enero no se suma a venta enero dos veces |
| TC-PAY-001-N | PAY-001 | Clasificar garantía por daños como venta del día automáticamente. | Rechazo de regla contable y registro pendiente de clasificación. |
| TC-PAY-002-P | PAY-002 | Cuenta 140000 se cubre con 70000 transferencia y 70000 tarjeta. | Dos medios cancelan una cuenta sin duplicar ingresos |
| TC-PAY-002-N | PAY-002 | Dos operadores aplican simultaneamente el mismo saldo de pago. | Sólo aplicaciones permitidas; segundo recibe conflicto, nunca saldo negativo. |
| TC-PAY-003-P | PAY-003 | Respuesta autorizada de proveedor coincide con orden y monto esperado. | Retorno del navegador sin autorización no marca pagado |
| TC-PAY-003-N | PAY-003 | Cliente envia success=true o token de otra orden. | No se marca pagado; evento de fraude y error sin revelar otra cuenta. |
| TC-PAY-004-P | PAY-004 | Diez repeticiones identicas generan un pago y una aplicación. | Repetir callback diez veces registra un cobro |
| TC-PAY-004-N | PAY-004 | Reintentar tras timeout sin conocer si proveedor cargo. | Consultar estado por orden antes de otro intento; estado UNKNOWN visible. |
| TC-PAY-005-P | PAY-005 | Devolución parcial de 20000 sobre 70000 deja 50000 netos y evidencia. | Devolución parcial deja saldo y trazabilidad correctos |
| TC-PAY-005-N | PAY-005 | Dos devoluciones concurrentes que superan saldo disponible. | 409 REFUND_LIMIT; ninguna doble salida, escalamiento de incertidumbre. |
| TC-PAY-006-P | PAY-006 | 10000 inicial +50000 cobros -20000 retiro =40000 esperado. | Arqueo concilia efectivo esperado y contado; diferencia no se borra |
| TC-PAY-006-N | PAY-006 | Conteo 39000 y operador intenta cambiar una venta para cuadrar. | Diferencia -1000 permanece; requerir motivo y revisión. |
| TC-PAY-007-P | PAY-007 | Retiro 20000 y abono 20000 cancelan transito sin afectar resultado. | Retiro para depositar no reduce resultado como gasto |
| TC-PAY-007-N | PAY-007 | Depósito por 19000 para retiro de 20000. | 1000 pendiente y alerta; no ajuste automático de ingresos. |
| TC-PAY-008-P | PAY-008 | Supervisor reabre con motivo y deja auditoría antes/despues. | Recepcionista no reabre un cierre aprobado |
| TC-PAY-008-N | PAY-008 | Recepcionista intenta reabrir turno ya aprobado. | 403; original inmutable y solicitud de revisión opcional. |
| TC-TAX-001-P | TAX-001 | Proveedor acepta emisión y se registra folio/respuesta verificables. | Rechazo de emisión queda pendiente, no como documento aceptado |
| TC-TAX-001-N | TAX-001 | Proveedor rechaza documento por dato tributario inválido. | Estado REJECTED y tarea de corrección, no mostrarlo como emitido aceptado. |
| TC-TAX-002-P | TAX-002 | Caso ficticio cumple política aprobada y conserva respaldo de tratamiento. | Extranjero sin requisitos no obtiene exención automática |
| TC-TAX-002-N | TAX-002 | Huésped extranjero sin evidencia suficiente pide tarifa exenta. | Derivar validación y aplicar regla aprobada correspondiente, no exención automática. |
| TC-TAX-003-P | TAX-003 | Nota parcial enlazada ajusta referencia sin borrar factura original. | Anulación preserva documento original y saldo correcto |
| TC-TAX-003-N | TAX-003 | Eliminar factura para ocultar error o emitir dos notas iguales por reintento. | Operación bloqueada/deduplicada, historial integro. |
| TC-SEC-008-P | SEC-008 | Enlace de una reserva cobra sólo monto calculado por servidor. | Probar enlace de otra reserva no revela cuenta; un enlace a pago no autoriza devolución. |
| TC-SEC-008-N | SEC-008 | Manipular ID o amount en URL para pagar menos o leer otra cuenta. | 403/422, sin cambiar oferta ni estado financiero. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
