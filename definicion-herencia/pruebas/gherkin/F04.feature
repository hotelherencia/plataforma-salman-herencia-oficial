# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Pagos, caja y documentos tributarios

  @PAY-001 @TC-PAY-001-P
  Escenario: TC-PAY-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando 100000 recibidos en diciembre para enero figuran como anticipo y obligación futura.
    Entonces Anticipo diciembre para enero no se suma a venta enero dos veces

  @PAY-001 @TC-PAY-001-N
  Escenario: TC-PAY-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Clasificar garantía por daños como venta del día automáticamente.
    Entonces Rechazo de regla contable y registro pendiente de clasificación.

  @PAY-002 @TC-PAY-002-P
  Escenario: TC-PAY-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cuenta 140000 se cubre con 70000 transferencia y 70000 tarjeta.
    Entonces Dos medios cancelan una cuenta sin duplicar ingresos

  @PAY-002 @TC-PAY-002-N
  Escenario: TC-PAY-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos operadores aplican simultaneamente el mismo saldo de pago.
    Entonces Sólo aplicaciones permitidas; segundo recibe conflicto, nunca saldo negativo.

  @PAY-003 @TC-PAY-003-P
  Escenario: TC-PAY-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Respuesta autorizada de proveedor coincide con orden y monto esperado.
    Entonces Retorno del navegador sin autorización no marca pagado

  @PAY-003 @TC-PAY-003-N
  Escenario: TC-PAY-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cliente envia success=true o token de otra orden.
    Entonces No se marca pagado; evento de fraude y error sin revelar otra cuenta.

  @PAY-004 @TC-PAY-004-P
  Escenario: TC-PAY-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Diez repeticiones identicas generan un pago y una aplicación.
    Entonces Repetir callback diez veces registra un cobro

  @PAY-004 @TC-PAY-004-N
  Escenario: TC-PAY-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reintentar tras timeout sin conocer si proveedor cargo.
    Entonces Consultar estado por orden antes de otro intento; estado UNKNOWN visible.

  @PAY-005 @TC-PAY-005-P
  Escenario: TC-PAY-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Devolución parcial de 20000 sobre 70000 deja 50000 netos y evidencia.
    Entonces Devolución parcial deja saldo y trazabilidad correctos

  @PAY-005 @TC-PAY-005-N
  Escenario: TC-PAY-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos devoluciones concurrentes que superan saldo disponible.
    Entonces 409 REFUND_LIMIT; ninguna doble salida, escalamiento de incertidumbre.

  @PAY-006 @TC-PAY-006-P
  Escenario: TC-PAY-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando 10000 inicial +50000 cobros -20000 retiro =40000 esperado.
    Entonces Arqueo concilia efectivo esperado y contado; diferencia no se borra

  @PAY-006 @TC-PAY-006-N
  Escenario: TC-PAY-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Conteo 39000 y operador intenta cambiar una venta para cuadrar.
    Entonces Diferencia -1000 permanece; requerir motivo y revisión.

  @PAY-007 @TC-PAY-007-P
  Escenario: TC-PAY-007-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Retiro 20000 y abono 20000 cancelan transito sin afectar resultado.
    Entonces Retiro para depositar no reduce resultado como gasto

  @PAY-007 @TC-PAY-007-N
  Escenario: TC-PAY-007-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Depósito por 19000 para retiro de 20000.
    Entonces 1000 pendiente y alerta; no ajuste automático de ingresos.

  @PAY-008 @TC-PAY-008-P
  Escenario: TC-PAY-008-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Supervisor reabre con motivo y deja auditoría antes/despues.
    Entonces Recepcionista no reabre un cierre aprobado

  @PAY-008 @TC-PAY-008-N
  Escenario: TC-PAY-008-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Recepcionista intenta reabrir turno ya aprobado.
    Entonces 403; original inmutable y solicitud de revisión opcional.

  @TAX-001 @TC-TAX-001-P
  Escenario: TC-TAX-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Proveedor acepta emisión y se registra folio/respuesta verificables.
    Entonces Rechazo de emisión queda pendiente, no como documento aceptado

  @TAX-001 @TC-TAX-001-N
  Escenario: TC-TAX-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Proveedor rechaza documento por dato tributario inválido.
    Entonces Estado REJECTED y tarea de corrección, no mostrarlo como emitido aceptado.

  @TAX-002 @TC-TAX-002-P
  Escenario: TC-TAX-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Caso ficticio cumple política aprobada y conserva respaldo de tratamiento.
    Entonces Extranjero sin requisitos no obtiene exención automática

  @TAX-002 @TC-TAX-002-N
  Escenario: TC-TAX-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Huésped extranjero sin evidencia suficiente pide tarifa exenta.
    Entonces Derivar validación y aplicar regla aprobada correspondiente, no exención automática.

  @TAX-003 @TC-TAX-003-P
  Escenario: TC-TAX-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Nota parcial enlazada ajusta referencia sin borrar factura original.
    Entonces Anulación preserva documento original y saldo correcto

  @TAX-003 @TC-TAX-003-N
  Escenario: TC-TAX-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Eliminar factura para ocultar error o emitir dos notas iguales por reintento.
    Entonces Operación bloqueada/deduplicada, historial integro.

  @SEC-008 @TC-SEC-008-P
  Escenario: TC-SEC-008-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Enlace de una reserva cobra sólo monto calculado por servidor.
    Entonces Probar enlace de otra reserva no revela cuenta; un enlace a pago no autoriza devolución.

  @SEC-008 @TC-SEC-008-N
  Escenario: TC-SEC-008-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Manipular ID o amount en URL para pagar menos o leer otra cuenta.
    Entonces 403/422, sin cambiar oferta ni estado financiero.
