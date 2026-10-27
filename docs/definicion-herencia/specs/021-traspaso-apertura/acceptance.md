# Aceptacion F20

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-MIG-001-P | MIG-001 | Fuente con encabezado ambiguo queda observada antes de migrar. | Fuente con fecha 31-6 se marca para revisión, no se inventa fecha |
| TC-MIG-001-N | MIG-001 | Inventar fecha válida para una fila 31-6. | Fila rechazada con motivo y sin escritura productiva. |
| TC-MIG-002-P | MIG-002 | Reserva enero pagada 100000 al saliente muestra crédito y fondo pendiente. | Reserva enero cobrada antes queda trazable sin doble venta |
| TC-MIG-002-N | MIG-002 | Cobrar nuevamente 100000 al huésped porque aún no se entrego dinero. | Bloqueo de cobro duplicado; diferencia se gestiona contra saliente segun acta. |
| TC-MIG-003-P | MIG-003 | Conteo y anticipos aprobados coinciden exactamente con lote cargado. | Suma de saldos aprobados coincide con importación y excepciones |
| TC-MIG-003-N | MIG-003 | Diferencia de cantidades o saldos no explicada. | No aprobar lote; conservar excepciones y volver a validar. |
| TC-MIG-004-P | MIG-004 | Recepción registra llegada, cobro, salida y turno en ejercicio ficticio. | Recepción completa ciclo sin depender de instrucciones del desarrollador |
| TC-MIG-004-N | MIG-004 | Sólo presentacion de pantallas sin operador realizando tareas. | Capacitación no aceptada; repetir prácticas y registrar resultado. |
| TC-MIG-005-P | MIG-005 | Reserva cruzada conserva cuenta y asignación aprobada por período. | Una reserva cobrada por operador saliente conserva pago histórico y monto por rendir sin cobrar de nuevo al cliente. |
| TC-MIG-005-N | MIG-005 | Abono enero por venta diciembre se registra automáticamente como nueva venta enero. | Clasificar en conciliacion/traspaso, no duplicar ingreso. |
| TC-MIG-006-P | MIG-006 | Colchón faltante queda observado con respaldo y responsable propuesto. | Un faltante queda abierto con responsable sin convertirse automáticamente en compra aprobada. |
| TC-MIG-006-N | MIG-006 | Sistema aprueba compra para cerrar artificialmente discrepancia. | Observacion permanece abierta; nueva compra necesita autorización independiente. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
