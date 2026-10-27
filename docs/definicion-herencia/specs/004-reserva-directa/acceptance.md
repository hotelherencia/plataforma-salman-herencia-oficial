# Aceptacion F03

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-RES-001-P | RES-001 | Huésped completa reserva desde enlace y recepción ve mismo precio/fechas. | Reserva desde enlace social aparece en recepción con el mismo ID |
| TC-RES-001-N | RES-001 | Interrumpir correo después de confirmar reserva. | Reserva permanece confirmada; notificación fallida en cola y alerta. |
| TC-RES-002-P | RES-002 | Enlace Instagram produce canal DIRECT y origen instagram. | Reserva directa originada en Instagram no se atribuye a Booking |
| TC-RES-002-N | RES-002 | Parámetro URL contiene RUT, script o texto excesivo. | Se rechaza o descarta dato de atribución inseguro sin impedir compra legitima. |
| TC-RES-003-P | RES-003 | Retención de prueba de quince minutos expira y devuelve una unidad. | Cupo expirado no se confirma si ya fue vendido |
| TC-RES-003-N | RES-003 | Pago confirmado tras vencimiento y cupo vendido a otro cliente. | Estado PAGO_SIN_CUPO, incidencia y alternativa/devolucion autorizada; no sobreventa silenciosa. |
| TC-RES-004-P | RES-004 | Veinte solicitudes al último cupo producen un sólo compromiso interno. | Dos solicitudes simultaneas producen una sola confirmacion interna |
| TC-RES-004-N | RES-004 | Dos transacciones intentan confirmar el último cupo simultaneamente. | Una obtiene 201; restantes 409 NO_AVAILABILITY, sin contadores negativos. |
| TC-RES-007-P | RES-007 | Tres habitaciones con 50000,60000,70000 suman 180000. | Tres habitaciones suman sus lineas una sola vez |
| TC-RES-007-N | RES-007 | Consulta une pasajeros y multiplica total de cabecera por filas. | Prueba detecta total distinto; reporte debe agregar primero por nivel correcto. |
| TC-RES-008-P | RES-008 | Empresa paga dos estadías y documento mantiene pasajeros vinculados privadamente. | Factura a empresa sin perder pasajeros y estadías asociados |
| TC-RES-008-N | RES-008 | Recepción habilita crédito a empresa sin convenio vigente. | Reserva puede quedar pendiente, pero no salida a crédito sin aprobación. |
| TC-RES-009-P | RES-009 | Agregar una noche libre aumenta una unidad de inventario y su cargo, no noches previas. | Extension válida cupo y sólo agrega noches y cargos aplicables |
| TC-RES-009-N | RES-009 | Extender cuando última noche no esta disponible o versión ya cambio. | 409; reserva previa integra y cotización alternativa visible. |
| TC-RES-010-P | RES-010 | Cancelación permitida libera reserva y calcula devolución conforme a snapshot. | No-show no se convierte automáticamente en noche ocupada |
| TC-RES-010-N | RES-010 | Mensaje antiguo de confirmacion llega después de cancelación externa nueva. | No revierte cancelación; se ignora revisión obsoleta y registra motivo. |
| TC-RES-011-P | RES-011 | Pago de 180000 aplicado a tres cuentas por 50000,60000,70000. | Un pago colectivo puede aplicarse a varias cuentas sin exceso |
| TC-RES-011-N | RES-011 | Aplicar 200000 de un pago de 180000. | 422 ALLOCATION_EXCEEDS_AVAILABLE; ninguna aplicación parcial queda huérfana. |
| TC-INT-005-P | INT-005 | Una reserva confirmada genera una confirmacion operativa. | Reintento no envia confirmaciones duplicadas al mismo evento |
| TC-INT-005-N | INT-005 | Reintentar tras timeout de proveedor sin conocer entrega. | Consultar referencia cuando posible; estado incierto visible y evitar spam. |
| TC-SOC-002-P | SOC-002 | Click desde Instagram enlaza reserva directa con origen conocido. | Un clic de Instagram llega al motor y conserva fuente en la reserva; sin etiqueta queda desconocida, no inventada. |
| TC-SOC-002-N | SOC-002 | Eliminar etiquetas al volver del checkout o inventar campaña por ausencia. | Persistencia segura de origen disponible; ausencia queda UNKNOWN. |
| TC-SOC-003-P | SOC-003 | Checkout desde navegador interno vuelve a la misma reserva. | Volver del pago desde un navegador interno no pierde la reserva ni duplica el cobro. |
| TC-SOC-003-N | SOC-003 | Navegador pierde cookie después del pago. | Recuperación autenticada segura, no segundo cobro; si no hay acceso deriva. |
| TC-SOC-016-P | SOC-016 | Cliente abre oferta válida y completa pago segun política. | Un enlace vencido no mantiene cupo; compartirlo no permite ver otras reservas. |
| TC-SOC-016-N | SOC-016 | Token vencido o perteneciente a otra reserva usado para leer deuda. | 410/403 sin datos; ofrecer nueva cotización autorizada. |
| TC-UX-001-P | UX-001 | Completar reserva y cambiar habitación sólo con teclado. | Reserva y calendario tienen alternativa sin arrastrar; campos de error son anunciados y corregibles. |
| TC-UX-001-N | UX-001 | Campo con error sólo cambia color y no explica el problema. | Falla de aceptacion UX; agregar mensaje y foco sin perder datos. |
| TC-UX-002-P | UX-002 | Cambiar idioma conserva importe exacto y fechas de reserva. | Traducir no cambia monto, política aceptada ni cálculo de noches; fallo no se muestra como exito. |
| TC-UX-002-N | UX-002 | Traducir dia/mes invierte fechas o pantalla muestra datos previos de otra cuenta. | Rechazo del caso; limpiar estado y formatos inequívocos. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
