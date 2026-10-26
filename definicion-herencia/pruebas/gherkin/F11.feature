# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Conciliación y auxiliares financieros

  @FIN-001 @TC-FIN-001-P
  Escenario: TC-FIN-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Alojamiento 140000 con anticipo 70000 refleja ingreso total una vez.
    Entonces Mismo servicio no se suma cuatro veces al resultado

  @FIN-001 @TC-FIN-001-N
  Escenario: TC-FIN-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Sumar cargo, factura, cobro y depósito en una sola columna ingresos.
    Entonces Validador financiero detecta duplicación; reporte no aceptable.

  @FIN-002 @TC-FIN-002-P
  Escenario: TC-FIN-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Pago parcial reduce sólo cuentas seleccionadas y recalcula bandas de vencimiento.
    Entonces Pago grupal reduce las cuentas correctas sin saldos ocultos

  @FIN-002 @TC-FIN-002-N
  Escenario: TC-FIN-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Aplicar pago a otra empresa con nombre similar.
    Entonces Rechazo por ID/pagador/alcance; no saldos ocultos.

  @FIN-003 @TC-FIN-003-P
  Escenario: TC-FIN-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Misma cartola cargada dos veces no agrega movimientos.
    Entonces Reimportar archivo identico no duplica movimientos

  @FIN-003 @TC-FIN-003-N
  Escenario: TC-FIN-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos transferencias legitimas de 50000 mismo día tienen IDs diferentes.
    Entonces Ambas se conservan; deduplicacion no usa sólo monto/fecha.

  @FIN-004 @TC-FIN-004-P
  Escenario: TC-FIN-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Abono 135000 concilia tres cobros de 50000 menos comisión total 15000.
    Entonces Abono agrupado se aplica a tres cobros y cuadra

  @FIN-004 @TC-FIN-004-N
  Escenario: TC-FIN-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Asignar un abono completo a dos grupos simultaneamente.
    Entonces 409 OVERALLOCATED; sólo un grupo consume saldo disponible.

  @FIN-005 @TC-FIN-005-P
  Escenario: TC-FIN-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Canal liquida bruto 200000 menos fee 20000, neto 180000.
    Entonces No descontar dos veces comisión ya facturada fuera del abono

  @FIN-005 @TC-FIN-005-N
  Escenario: TC-FIN-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Hotel cobra 200000 directo y sistema reduce además abono por comisión ya pagada aparte.
    Entonces Diferencia identificada; modelo impide doble fee mediante fuente/documento.

  @FIN-006 @TC-FIN-006-P
  Escenario: TC-FIN-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos candidatos del mismo importe quedan en cola de revisión.
    Entonces Dos transferencias iguales permanecen distinguibles por evidencia

  @FIN-006 @TC-FIN-006-N
  Escenario: TC-FIN-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Conciliar automáticamente sólo por monto coincidente.
    Entonces No publicar match; exigir referencia o aprobación documentada.

  @FIN-009 @TC-FIN-009-P
  Escenario: TC-FIN-009-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Desayuno interno cambia costo de unidad, no costo total del grupo.
    Entonces Consolidado elimina sólo duplicaciones definidas con evidencia

  @FIN-009 @TC-FIN-009-N
  Escenario: TC-FIN-009-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Eliminar factura a tercero por parecer transacción interna sin referencia pareada.
    Entonces Eliminación bloqueada; saldo y evidencia permanecen.

  @FIN-011 @TC-FIN-011-P
  Escenario: TC-FIN-011-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Segundo envio del mismo lote se reconoce como reintento.
    Entonces Exportar dos veces el mismo período no genera asientos duplicados en destino sin detectar el reenvio.

  @FIN-011 @TC-FIN-011-N
  Escenario: TC-FIN-011-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Destino no soporta idempotencia y usuario reenvia como nuevo.
    Entonces Bloquear automatismo y requerir verificación manual de importación previa.
