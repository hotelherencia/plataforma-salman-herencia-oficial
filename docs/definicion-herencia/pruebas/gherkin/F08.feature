# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Desayunos, cenas y espacios compartidos

  @FNB-001 @TC-FNB-001-P
  Escenario: TC-FNB-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos personas, dos noches generan cuatro derechos.
    Entonces Dos personas por dos noches generan servicios segun días elegibles

  @FNB-001 @TC-FNB-001-N
  Escenario: TC-FNB-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos reservas duplicadas del mismo pasajero/dia causan doble derecho para misma estadía.
    Entonces Constraint por stay_guest/dia evita duplicado; caso de identidad se revisa.

  @FNB-002 @TC-FNB-002-P
  Escenario: TC-FNB-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Diez porciones producidas, ocho servidas, dos merma quedan explicadas.
    Entonces No-show no descuenta automáticamente un desayuno servido

  @FNB-002 @TC-FNB-002-N
  Escenario: TC-FNB-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando No-show se marca servido automáticamente o merma se borra.
    Entonces Bloqueo/alerta y corrección trazable; costo de producción no desaparece.

  @FNB-003 @TC-FNB-003-P
  Escenario: TC-FNB-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando 100 gramos descuentan 0,1 kilogramo del lote.
    Entonces Consumo en gramos descuenta correctamente una compra en kilos

  @FNB-003 @TC-FNB-003-N
  Escenario: TC-FNB-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Unidad incompatible como litros contra unidades sin factor aprobado.
    Entonces 422 UNIT_CONVERSION_MISSING, sin consumo parcial.

  @FNB-004 @TC-FNB-004-P
  Escenario: TC-FNB-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cena entregada crea cargo de venta y obligación de proveedor vinculados.
    Entonces Cena no entregada no se registra como consumida sin resolución

  @FNB-004 @TC-FNB-004-N
  Escenario: TC-FNB-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Proveedor no entrega pero pedido figura confirmado.
    Entonces INCIDENT sin consumo ficticio; resolver cargo/deuda con evidencia.

  @FNB-005 @TC-FNB-005-P
  Escenario: TC-FNB-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Costo cafetería 4000 asignado al hotel mantiene costo total 4000 en Herencia.
    Entonces Desayuno incluido no crea una segunda venta del grupo

  @FNB-005 @TC-FNB-005-N
  Escenario: TC-FNB-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Registrar venta externa extra por 4000 sin cliente ni servicio adicional.
    Entonces Rechazar clasificación automática; reporte detecta duplicación.

  @SPA-001 @TC-SPA-001-P
  Escenario: TC-SPA-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Evento 14-16 con 30 minutos antes/despues ocupa 13:30-16:30.
    Entonces Dos eventos incompatibles no reservan el mismo espacio y horario

  @SPA-001 @TC-SPA-001-N
  Escenario: TC-SPA-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Segundo evento comienza 16:00 sin respetar limpieza.
    Entonces 409 SPACE_CONFLICT con alternativa, sin reserva doble.
