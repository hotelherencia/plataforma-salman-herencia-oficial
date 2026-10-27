# Aceptacion F08

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-FNB-001-P | FNB-001 | Dos personas, dos noches generan cuatro derechos. | Dos personas por dos noches generan servicios segun días elegibles |
| TC-FNB-001-N | FNB-001 | Dos reservas duplicadas del mismo pasajero/dia causan doble derecho para misma estadía. | Constraint por stay_guest/dia evita duplicado; caso de identidad se revisa. |
| TC-FNB-002-P | FNB-002 | Diez porciones producidas, ocho servidas, dos merma quedan explicadas. | No-show no descuenta automáticamente un desayuno servido |
| TC-FNB-002-N | FNB-002 | No-show se marca servido automáticamente o merma se borra. | Bloqueo/alerta y corrección trazable; costo de producción no desaparece. |
| TC-FNB-003-P | FNB-003 | 100 gramos descuentan 0,1 kilogramo del lote. | Consumo en gramos descuenta correctamente una compra en kilos |
| TC-FNB-003-N | FNB-003 | Unidad incompatible como litros contra unidades sin factor aprobado. | 422 UNIT_CONVERSION_MISSING, sin consumo parcial. |
| TC-FNB-004-P | FNB-004 | Cena entregada crea cargo de venta y obligación de proveedor vinculados. | Cena no entregada no se registra como consumida sin resolución |
| TC-FNB-004-N | FNB-004 | Proveedor no entrega pero pedido figura confirmado. | INCIDENT sin consumo ficticio; resolver cargo/deuda con evidencia. |
| TC-FNB-005-P | FNB-005 | Costo cafetería 4000 asignado al hotel mantiene costo total 4000 en Herencia. | Desayuno incluido no crea una segunda venta del grupo |
| TC-FNB-005-N | FNB-005 | Registrar venta externa extra por 4000 sin cliente ni servicio adicional. | Rechazar clasificación automática; reporte detecta duplicación. |
| TC-SPA-001-P | SPA-001 | Evento 14-16 con 30 minutos antes/despues ocupa 13:30-16:30. | Dos eventos incompatibles no reservan el mismo espacio y horario |
| TC-SPA-001-N | SPA-001 | Segundo evento comienza 16:00 sin respetar limpieza. | 409 SPACE_CONFLICT con alternativa, sin reserva doble. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
