# Aceptacion F02

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-HOT-001-P | HOT-001 | Activar 17 códigos únicos respaldados por ficha y ver sus estados. | El catálogo aprobado suma 17 sin agregar la sala comun |
| TC-HOT-001-N | HOT-001 | Intentar activar dos habitaciones con mismo código o la sala como habitación adicional. | 422/409 y catálogo sigue en revisión; no aumenta inventario. |
| TC-HOT-002-P | HOT-002 | Dos adultos en doble consumen una unidad y dos personas-noche por noche. | Una doble con dos personas ocupa una habitación |
| TC-HOT-002-N | HOT-002 | Tres adultos intentan reservar una doble con max_total=2. | 422 CAPACITY_EXCEEDED y ofrecer alternativa válida sin inventar camas. |
| TC-HOT-003-P | HOT-003 | Una reserva del 10 al 12 reduce una unidad en cada una de las dos noches. | No se asigna dos veces el mismo intervalo |
| TC-HOT-003-N | HOT-003 | Asignar mismo cuarto a dos estadías con intervalos solapados. | 409 ROOM_CONFLICT y conservar ambas reservas sin asignación doble. |
| TC-HOT-004-P | HOT-004 | Averia de ducha reduce disponibilidad y lista reservas que requieren reasignacion. | Una averia no cancela silenciosamente una reserva |
| TC-HOT-004-N | HOT-004 | Crear bloqueo sobre reserva confirmada y pretender anular automáticamente esa reserva. | Bloqueo e incidencia visibles; contrato de reserva no se cancela ni se reembolsa sólo. |
| TC-HOT-005-P | HOT-005 | Habitación desocupada y sucia con saldo empresarial pendiente se muestra correctamente. | Checkout deja habitación sucia sin cambiar saldo contable |
| TC-HOT-005-N | HOT-005 | Marcar CLEAN para intentar ignorar bloqueo por equipo inseguro. | No queda asignable mientras mantenimiento siga bloqueante; error explicativo. |
| TC-RES-005-P | RES-005 | Reserva pactada a 70000 conserva ese valor cuando tarifa cambia a 75000. | Cambiar tarifa base no cambia una reserva confirmada |
| TC-RES-005-N | RES-005 | Modificar precio publicado y reabrir detalle de reserva ya confirmada. | El detalle conserva snapshot original; sólo nueva cotización usa nuevo precio. |
| TC-RES-006-P | RES-006 | Precio 100000 con descuento 10% resulta 90000; comisión se registra aparte con su base. | Aplicar descuento no duplica deduccion del canal |
| TC-RES-006-N | RES-006 | Aplicar 17% histórico automáticamente como descuento y comisión de toda venta. | Bloqueo de configuración sin política vigente; no deduccion duplicada. |
| TC-REV-001-P | REV-001 | Plan mínimo dos noches rechaza una y ofrece dos disponibles. | Reglas incompatibles explican bloqueo; aumentar tarifa no altera reservas confirmadas. |
| TC-REV-001-N | REV-001 | Cambiar tarifa base altera precio de reserva confirmada. | Snapshot preservado; nueva política sólo afecta ofertas futuras. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
