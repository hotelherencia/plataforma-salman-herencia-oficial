# Aceptacion F06

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-INV-001-P | INV-001 | Bebida del archivo mal titulado se carga como producto de reventa con unidad correcta. | Producto de bebidas no se clasifica por título erroneo del libro |
| TC-INV-001-N | INV-001 | Producto duplicado por variacion ortografica genera dos stocks no revisados. | Importación propone correspondencia y solicita validación antes de activar duplicado. |
| TC-INV-002-P | INV-002 | Mover cinco unidades de bodega a piso conserva total y cambia ubicacion. | Mover bodega a piso no modifica stock total del establecimiento |
| TC-INV-002-N | INV-002 | Falla una pata de traslado o salida supera stock. | Rollback completo/409 INSUFFICIENT_STOCK; sin unidades desaparecidas. |
| TC-INV-003-P | INV-003 | Salida de leche usa lote vigente mas próximo a vencer. | Producto vencido no se propone para servicio sin excepción permitida |
| TC-INV-003-N | INV-003 | Lote vencido propuesto para desayuno. | 422 LOT_NOT_USABLE y retiro/merma supervisada, no servicio. |
| TC-INV-004-P | INV-004 | Conteo 20 al corte mas entrada posterior 5 termina 25 tras conciliación. | Diferencia genera ajuste trazable y no altera original |
| TC-INV-004-N | INV-004 | Aplicar conteo antiguo como saldo 20 perdiendo las cinco recibidas. | Bloqueo por corte/version y recalculo con movimientos posteriores. |
| TC-INV-005-P | INV-005 | Stock 3, mínimo 10 y pedido en transito 4 propone revisar tres unidades adicionales. | Alerta identifica cantidad propuesta y bases, no compra sola |
| TC-INV-005-N | INV-005 | Ejecutar compra automáticamente sin aprobación de presupuesto. | Sólo alerta/borrador; ninguna orden enviada ni gasto. |
| TC-PUR-001-P | PUR-001 | Compra aprobada por responsable distinto pasa a ORDERED con evidencia. | Compra fuera de umbral no se autoriza por el solicitante |
| TC-PUR-001-N | PUR-001 | Solicitante se autoaprueba compra superior a su límite. | 403; estado REQUESTED sin orden externa. |
| TC-PUR-002-P | PUR-002 | Recibir ocho de diez incorpora ocho y deja dos abiertas. | Recibir 8 de 10 aumenta stock en 8 y deja 2 pendientes |
| TC-PUR-002-N | PUR-002 | Reenviar misma recepción o recibir veinte sin tolerancia aprobada. | Duplicado no suma; exceso requiere excepción y no se acepta silenciosamente. |
| TC-PUR-003-P | PUR-003 | Factura coincide con ocho recibidas y precio acordado. | Factura superior a lo recibido genera diferencia visible |
| TC-PUR-003-N | PUR-003 | Factura diez cuando sólo llegaron ocho. | Diferencia visible; no marcar conforme ni programar pago total automáticamente. |
| TC-PUR-004-P | PUR-004 | Deuda 100000 y pago 30000 conserva saldo 70000. | Pago parcial mantiene saldo al proveedor |
| TC-PUR-004-N | PUR-004 | Registrar dos veces mismo pago bancario a proveedor. | 409 DUPLICATE_PAYMENT; saldo permanece 70000. |
| TC-CAP-001-P | CAP-001 | Bidon 5L15000 y 1L4000 muestran3000/L y4000/L antes de otros costos. | Comparar bidones distintos muestra costo por litro; factura histórica no se llama cotización vigente. |
| TC-CAP-001-N | CAP-001 | Comparar sólo precio por envase sin contenido o calidad. | Comparación incompleta marcada, no recomendacion automática de compra. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
