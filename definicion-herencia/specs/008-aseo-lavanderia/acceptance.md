# Aceptacion F07

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-OPS-001-P | OPS-001 | Una salida origina una tarea de aseo con mismo source_key. | Checkout genera una tarea de salida sin duplicados |
| TC-OPS-001-N | OPS-001 | Recibir dos veces el mismo checkout. | Una tarea, no dos ni doble incentivo. |
| TC-OPS-002-P | OPS-002 | Persona asignada completa checklist desde móvil y queda pendiente de inspección. | Ejecutor registra la tarea desde móvil con su identidad |
| TC-OPS-002-N | OPS-002 | Dispositivo offline envia tarea reasignada a otra persona. | Conflicto visible, no sobrescritura; supervisor concilia ejecución real. |
| TC-OPS-003-P | OPS-003 | Inspección aprobada convierte habitación limpia a READY. | Falla de inspección no declara habitación lista |
| TC-OPS-003-N | OPS-003 | Checklist incompleto o falla de higiene y solicitud de liberar. | No entrega disponible; hallazgo y retrabajo asignados. |
| TC-OPS-004-P | OPS-004 | Dos jabones y dos toallas: baja dos jabones, mueve dos toallas. | Repetir tarea no descuenta insumos dos veces |
| TC-OPS-004-N | OPS-004 | Reenviar registro de consumo con mismo device event. | Una sola afectacion y resultado previo; stock no disminuye otra vez. |
| TC-OPS-005-P | OPS-005 | Limpieza de sala se imputa a areas comunes. | Limpieza comun no se imputa a una habitación arbitraria |
| TC-OPS-005-N | OPS-005 | Usuario intenta asignar todas las limpiezas comunes a cuarto vacío para mejorar otros margenes. | Exigir destino válido o ajuste gerencial aprobado, auditar. |
| TC-LIN-001-P | LIN-001 | Toalla pasa limpia-asignada-usada y total patrimonial no cambia. | Una toalla usada no desaparece del patrimonio textil |
| TC-LIN-001-N | LIN-001 | Restar una pieza del patrimonio cada noche ocupada. | Validación rechaza movimiento de baja sin causa y autorización. |
| TC-LIN-002-P | LIN-002 | Enviar dos sábanas, recibir una buena: una pendiente. | Dos piezas enviadas y una recibida dejan una pendiente |
| TC-LIN-002-N | LIN-002 | Intentar cerrar lote con una faltante sin resolución. | 409 LOT_UNBALANCED; pendiente visible al proveedor. |
| TC-LIN-003-P | LIN-003 | Permanencia sin cambio de sábanas no genera envio ficticio. | Una permanencia sin cambio no crea lavado ficticio |
| TC-LIN-003-N | LIN-003 | Tarea marcada no cambiada genera automáticamente dos sábanas usadas. | Prueba detecta inconsistencia; movimiento bloqueado. |
| TC-LIN-004-P | LIN-004 | Lote 10000 repartido 6000/4000 mantiene total. | Distribución del lote suma su costo total sin duplicar personal |
| TC-LIN-004-N | LIN-004 | Repartos suman 11000 o kilogramo se convierte a piezas sin base. | No cerrar costeo; corregir regla o dejar costo no asignado. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
