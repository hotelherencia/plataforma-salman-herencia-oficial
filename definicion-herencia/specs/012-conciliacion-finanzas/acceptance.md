# Aceptacion F11

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-FIN-001-P | FIN-001 | Alojamiento 140000 con anticipo 70000 refleja ingreso total una vez. | Mismo servicio no se suma cuatro veces al resultado |
| TC-FIN-001-N | FIN-001 | Sumar cargo, factura, cobro y depósito en una sola columna ingresos. | Validador financiero detecta duplicación; reporte no aceptable. |
| TC-FIN-002-P | FIN-002 | Pago parcial reduce sólo cuentas seleccionadas y recalcula bandas de vencimiento. | Pago grupal reduce las cuentas correctas sin saldos ocultos |
| TC-FIN-002-N | FIN-002 | Aplicar pago a otra empresa con nombre similar. | Rechazo por ID/pagador/alcance; no saldos ocultos. |
| TC-FIN-003-P | FIN-003 | Misma cartola cargada dos veces no agrega movimientos. | Reimportar archivo identico no duplica movimientos |
| TC-FIN-003-N | FIN-003 | Dos transferencias legitimas de 50000 mismo día tienen IDs diferentes. | Ambas se conservan; deduplicacion no usa sólo monto/fecha. |
| TC-FIN-004-P | FIN-004 | Abono 135000 concilia tres cobros de 50000 menos comisión total 15000. | Abono agrupado se aplica a tres cobros y cuadra |
| TC-FIN-004-N | FIN-004 | Asignar un abono completo a dos grupos simultaneamente. | 409 OVERALLOCATED; sólo un grupo consume saldo disponible. |
| TC-FIN-005-P | FIN-005 | Canal liquida bruto 200000 menos fee 20000, neto 180000. | No descontar dos veces comisión ya facturada fuera del abono |
| TC-FIN-005-N | FIN-005 | Hotel cobra 200000 directo y sistema reduce además abono por comisión ya pagada aparte. | Diferencia identificada; modelo impide doble fee mediante fuente/documento. |
| TC-FIN-006-P | FIN-006 | Dos candidatos del mismo importe quedan en cola de revisión. | Dos transferencias iguales permanecen distinguibles por evidencia |
| TC-FIN-006-N | FIN-006 | Conciliar automáticamente sólo por monto coincidente. | No publicar match; exigir referencia o aprobación documentada. |
| TC-FIN-009-P | FIN-009 | Desayuno interno cambia costo de unidad, no costo total del grupo. | Consolidado elimina sólo duplicaciones definidas con evidencia |
| TC-FIN-009-N | FIN-009 | Eliminar factura a tercero por parecer transacción interna sin referencia pareada. | Eliminación bloqueada; saldo y evidencia permanecen. |
| TC-FIN-011-P | FIN-011 | Segundo envio del mismo lote se reconoce como reintento. | Exportar dos veces el mismo período no genera asientos duplicados en destino sin detectar el reenvio. |
| TC-FIN-011-N | FIN-011 | Destino no soporta idempotencia y usuario reenvia como nuevo. | Bloquear automatismo y requerir verificación manual de importación previa. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
