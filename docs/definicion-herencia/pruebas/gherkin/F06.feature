# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Compras, existencias y precios unitarios

  @INV-001 @TC-INV-001-P
  Escenario: TC-INV-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Bebida del archivo mal titulado se carga como producto de reventa con unidad correcta.
    Entonces Producto de bebidas no se clasifica por título erroneo del libro

  @INV-001 @TC-INV-001-N
  Escenario: TC-INV-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Producto duplicado por variacion ortografica genera dos stocks no revisados.
    Entonces Importación propone correspondencia y solicita validación antes de activar duplicado.

  @INV-002 @TC-INV-002-P
  Escenario: TC-INV-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Mover cinco unidades de bodega a piso conserva total y cambia ubicacion.
    Entonces Mover bodega a piso no modifica stock total del establecimiento

  @INV-002 @TC-INV-002-N
  Escenario: TC-INV-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Falla una pata de traslado o salida supera stock.
    Entonces Rollback completo/409 INSUFFICIENT_STOCK; sin unidades desaparecidas.

  @INV-003 @TC-INV-003-P
  Escenario: TC-INV-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Salida de leche usa lote vigente mas próximo a vencer.
    Entonces Producto vencido no se propone para servicio sin excepción permitida

  @INV-003 @TC-INV-003-N
  Escenario: TC-INV-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Lote vencido propuesto para desayuno.
    Entonces 422 LOT_NOT_USABLE y retiro/merma supervisada, no servicio.

  @INV-004 @TC-INV-004-P
  Escenario: TC-INV-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Conteo 20 al corte mas entrada posterior 5 termina 25 tras conciliación.
    Entonces Diferencia genera ajuste trazable y no altera original

  @INV-004 @TC-INV-004-N
  Escenario: TC-INV-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Aplicar conteo antiguo como saldo 20 perdiendo las cinco recibidas.
    Entonces Bloqueo por corte/version y recalculo con movimientos posteriores.

  @INV-005 @TC-INV-005-P
  Escenario: TC-INV-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Stock 3, mínimo 10 y pedido en transito 4 propone revisar tres unidades adicionales.
    Entonces Alerta identifica cantidad propuesta y bases, no compra sola

  @INV-005 @TC-INV-005-N
  Escenario: TC-INV-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Ejecutar compra automáticamente sin aprobación de presupuesto.
    Entonces Sólo alerta/borrador; ninguna orden enviada ni gasto.

  @PUR-001 @TC-PUR-001-P
  Escenario: TC-PUR-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Compra aprobada por responsable distinto pasa a ORDERED con evidencia.
    Entonces Compra fuera de umbral no se autoriza por el solicitante

  @PUR-001 @TC-PUR-001-N
  Escenario: TC-PUR-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Solicitante se autoaprueba compra superior a su límite.
    Entonces 403; estado REQUESTED sin orden externa.

  @PUR-002 @TC-PUR-002-P
  Escenario: TC-PUR-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Recibir ocho de diez incorpora ocho y deja dos abiertas.
    Entonces Recibir 8 de 10 aumenta stock en 8 y deja 2 pendientes

  @PUR-002 @TC-PUR-002-N
  Escenario: TC-PUR-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reenviar misma recepción o recibir veinte sin tolerancia aprobada.
    Entonces Duplicado no suma; exceso requiere excepción y no se acepta silenciosamente.

  @PUR-003 @TC-PUR-003-P
  Escenario: TC-PUR-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Factura coincide con ocho recibidas y precio acordado.
    Entonces Factura superior a lo recibido genera diferencia visible

  @PUR-003 @TC-PUR-003-N
  Escenario: TC-PUR-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Factura diez cuando sólo llegaron ocho.
    Entonces Diferencia visible; no marcar conforme ni programar pago total automáticamente.

  @PUR-004 @TC-PUR-004-P
  Escenario: TC-PUR-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Deuda 100000 y pago 30000 conserva saldo 70000.
    Entonces Pago parcial mantiene saldo al proveedor

  @PUR-004 @TC-PUR-004-N
  Escenario: TC-PUR-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Registrar dos veces mismo pago bancario a proveedor.
    Entonces 409 DUPLICATE_PAYMENT; saldo permanece 70000.

  @CAP-001 @TC-CAP-001-P
  Escenario: TC-CAP-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Bidon5L15000 y1L4000 muestran3000/L y4000/L antes de otros costos.
    Entonces Comparar bidones distintos muestra costo por litro; factura histórica no se llama cotización vigente.

  @CAP-001 @TC-CAP-001-N
  Escenario: TC-CAP-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Comparar sólo precio por envase sin contenido o calidad.
    Entonces Comparacion incompleta marcada, no recomendacion automática de compra.
