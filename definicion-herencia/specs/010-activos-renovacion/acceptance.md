# Aceptacion F09

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-MNT-001-P | MNT-001 | Vencimiento de revisión genera una tarea del equipo concreto. | Vencimiento genera tarea sin bloquear habitaciones no afectadas |
| TC-MNT-001-N | MNT-001 | Reejecutar scheduler del mismo día. | No duplica orden; muestra ID existente. |
| TC-MNT-002-P | MNT-002 | Reparacion verificada libera cuarto previamente bloqueado. | Habitación fuera de servicio sólo se libera con cierre autorizado |
| TC-MNT-002-N | MNT-002 | Proveedor factura pero equipo sigue fallando. | Habitación permanece bloqueada y orden en verificacion/incidencia. |
| TC-CAP-002-P | CAP-002 | Equipo del arrendatario figura como tercero, no patrimonio propio. | Un equipo del arrendatario no pasa automáticamente a ser activo del grupo. |
| TC-CAP-002-N | CAP-002 | Importar inventario y asignar todos los bienes a Herencia automáticamente. | Staging bloquea propiedad desconocida para activación contable. |
| TC-CAP-003-P | CAP-003 | Diez colchones tienen partida, especificación y costo total con instalación. | Diez colchones tienen presupuesto, propuesta, aprobación y estado separados del stock de jabon. |
| TC-CAP-003-N | CAP-003 | Necesidad de mejora se interpreta como obligación del arrendatario sin contrato. | Mantener propuesta y asunto discutido separados; no deuda automática. |
| TC-CAP-004-P | CAP-004 | Equipo recibido e instalado pasa inspección antes de READY. | Equipo pagado pero no instalado no libera una habitación bloqueada. |
| TC-CAP-004-N | CAP-004 | Equipo pagado aún en transporte libera habitación. | Validación bloquea liberacion y conserva estado ORDERED. |
| TC-CAP-005-P | CAP-005 | Reemplazo mantiene vinculo y evidencia del activo retirado. | Reemplazo conserva historial del activo retirado; ajuste no borra faltante de traspaso. |
| TC-CAP-005-N | CAP-005 | Contabilizar compra dos veces como gasto y activo, o eliminar faltante histórico. | Control contable/trace bloquea lote y requiere corrección autorizada. |
| TC-CAP-006-P | CAP-006 | Renovación prevista detecta reserva que requiere reasignar. | Una obra bloquea inventario aprobado y alerta reservas afectadas antes de la intervención. |
| TC-CAP-006-N | CAP-006 | Intervencion inicia sin bloquear y canal vende la habitación. | Incidente crítico y stop-sell controlado; no aceptar como flujo conforme. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
