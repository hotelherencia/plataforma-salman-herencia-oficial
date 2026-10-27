# Catálogo de aceptación — Cafetería

Escenarios propuestos; ninguno ejecutado sobre producto. Cada ID tiene namespace de feature. Para cada FR se prueba resultado autorizado, denegación, duplicación y recuperación; los datos deben ser autorizados y minimizados.

| Prueba | Requisito | Dado / Cuando / Entonces |
|---|---|---|
| AT-001 | FR-001 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Con QR activo se abre la carta de su mesa sin instalar app; QR revocado o modificado no permite acceder a cuentas ajenas. |
| AT-002 | FR-002 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Dos clientes agregan ítems separados y compartidos; editar tras enviar a cocina exige flujo autorizado, sin alterar silenciosamente lo enviado. |
| AT-003 | FR-003 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Al confirmar pedido aparece una sola comanda con mesa/hora/estado; medir <5 segundos y registrar fallos en la muestra definida. |
| AT-004 | FR-004 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Con cuenta de dos personas se pagan ítems o reparto igual según regla ratificada; dos cobros concurrentes no consumen dos veces el mismo saldo. |
| AT-005 | FR-005 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Pago validado deriva al documento aplicable; repetir confirmación no duplica; indisponibilidad SII conserva pendiente, evidencia y alerta. |
| AT-006 | FR-006 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Internet cae y reinicia caja: procedimiento aprobado conserva pedidos pendientes y concilia al reconectar sin fingir pago electrónico ni duplicar ventas. |
| AT-007 | FR-007 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Factura fotografiada con líneas erróneas crea borrador pendiente; solo aprobador autorizado valida proveedor/monto/fecha y conserva corrección del OCR. |
| AT-008 | FR-008 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Venta con receta versionada de cuatro insumos genera un movimiento por insumo una sola vez; sin receta señala costo desconocido. |
| AT-009 | FR-009 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Con ventas y costos conocidos, dashboard calcula margen por producto/día/franja y lista cinco peores; costo ausente no se interpreta como cero. |
| AT-010 | FR-010 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Archivo real de la versión Eleventa del cliente se importa con conteos/totales reconciliados; filas faltantes o duplicadas se reportan, no se inventan. |
| AT-011 | FR-011 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Stock bajo mínimo proyectado produce propuesta de cantidades/costo; sin aprobación humana autenticada no se envía compra y a 48 h expira. |
| AT-012 | FR-012 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Anulación superior al umbral definido produce alerta en <1 minuto; la base temporal y el umbral se registran y no se sanciona automáticamente. |
| AT-013 | FR-013 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Cada propuesta, rechazo, expiración y ejecución deja registro con identidad/evidencia/aprobación; una ausencia se detecta en conciliación de eventos. |
| AT-014 | FR-014 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Una venta usa identidad, pagos, documentos y auditoría del core sin replicar estado bancario; probar con adaptador de core y mismo tenant. |
| ADV-001 | NFR-001/002/003 | Dos personas pagan el mismo ítem concurrentemente: solo una imputación; la otra recibe saldo actualizado. |
| ADV-002 | NFR-001/002/003 | Repetir retorno bancario y reintentar pedido no duplica cocina, stock, pago ni documento. |
| ADV-003 | NFR-001/002/003 | Sin red, mostrar pendiente y no aceptar pago electrónico como aprobado; reconciliar al volver sin doble venta. |

## Criterios de éxito y evidencia

| Criterio | Verificación pendiente |
|---|---|
| SC-001 | Medir «El 90 % de los pedidos por QR llegan a cocina en menos de 5 segundos». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-002 | Medir «El tiempo de cierre de cuenta por mesa baja al menos 30 % frente a la medición previa con eleventa». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-003 | Medir «El 100 % de los pagos aprobados queda conciliado con su obligación documental aplicable; objetivo de entrega <30 s cuando proceda y haya disponibilidad externa, sujeto a ratificación; fallos quedan pendientes y alertados». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-004 | Medir «El margen por producto calculado difiere menos del 2 % del cálculo manual mensual». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-005 | Medir «El inventario proyectado difiere menos del 5 % del conteo físico semanal». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-006 | Medir «Las órdenes sugeridas por el agente evitan quiebres de stock en al menos el 95 % de los insumos críticos». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-007 | Medir «Cero acciones de agente sin registro en el ledger (auditoría mensual)». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-008 | Medir «El administrador obtiene el dashboard diario sin planilla manual en menos de 1 minuto». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |

## Escenarios competitivos por historia

Propuestos; no ejecutados sobre producto. Los números de ejemplo prueban aritmética y control, no fijan política comercial.

### US-CAF-001 / H1

- AC-US-CAF-001-01: Dada regla de ejemplo que asigna residuo a última parte y total 10000 CLP, cuando se divide en tres, entonces se muestran 3333,3333,3334 y una sola comanda original.
- AC-US-CAF-001-02: Dada una parte pagada, cuando se modifica el reparto pendiente, entonces aquella conserva monto y evidencia; no se reinicia su cobro.

### US-CAF-002 / H2

- AC-US-CAF-002-01: Dada receta sin costo de un insumo, cuando se calcula margen, entonces se marca no calculable y no integra un promedio como cero.
- AC-US-CAF-002-02: Dado mismo archivo importado dos veces, cuando se reconcilia, entonces totales y movimientos no se duplican y filas descartadas tienen motivo.

### US-CAF-003 / H3

- AC-US-CAF-003-01: Dada alerta ya emitida por una anulación, cuando se reejecuta misma ventana, entonces se identifica la misma alerta y no una nueva compra.
- AC-US-CAF-003-02: Dada propuesta no aprobada y datos vencidos, cuando se intenta usarla, entonces se bloquea y exige revisión.

| Prueba | Requisito | Escenario de resultado |
|---|---|---|
| AT-015 | FR-015 | Dada regla ratificada para residuo y cuenta de 10000 CLP dividida en tres, cuando se confirma reparto, entonces suma 10000, muestra residuo y conserva descuentos/propina diferenciados; no modifica partes pagadas ni crea comanda nueva. Denegar recurso de otro tenant y conservar evidencia. |
| AT-016 | FR-016 | Dadas dos ejecuciones de la misma regla/ventana/evento, cuando se evalúa la detección, entonces conserva su identidad y evidencia sin alertas duplicadas; propuesta caducada no permite compra. Denegar recurso de otro tenant y conservar evidencia. |

NFR-006 se verifica por los mismos AC: fuente sin vigencia, extracción ambigua o transición sin evidencia no permite compromiso; la ruta manual mantiene las validaciones.
