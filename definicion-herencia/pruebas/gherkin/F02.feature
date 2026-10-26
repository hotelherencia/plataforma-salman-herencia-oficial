# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Habitaciones, tarifas e inventario vendible

  @HOT-001 @TC-HOT-001-P
  Escenario: TC-HOT-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Activar 17 códigos únicos respaldados por ficha y ver sus estados.
    Entonces El catálogo aprobado suma 17 sin agregar la sala comun

  @HOT-001 @TC-HOT-001-N
  Escenario: TC-HOT-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Intentar activar dos habitaciones con mismo código o la sala como habitación adicional.
    Entonces 422/409 y catálogo sigue en revisión; no aumenta inventario.

  @HOT-002 @TC-HOT-002-P
  Escenario: TC-HOT-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos adultos en doble consumen una unidad y dos personas-noche por noche.
    Entonces Una doble con dos personas ocupa una habitación

  @HOT-002 @TC-HOT-002-N
  Escenario: TC-HOT-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Tres adultos intentan reservar una doble con max_total=2.
    Entonces 422 CAPACITY_EXCEEDED y ofrecer alternativa válida sin inventar camas.

  @HOT-003 @TC-HOT-003-P
  Escenario: TC-HOT-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Una reserva del 10 al 12 reduce una unidad en cada una de las dos noches.
    Entonces No se asigna dos veces el mismo intervalo

  @HOT-003 @TC-HOT-003-N
  Escenario: TC-HOT-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Asignar mismo cuarto a dos estadías con intervalos solapados.
    Entonces 409 ROOM_CONFLICT y conservar ambas reservas sin asignación doble.

  @HOT-004 @TC-HOT-004-P
  Escenario: TC-HOT-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Averia de ducha reduce disponibilidad y lista reservas que requieren reasignacion.
    Entonces Una averia no cancela silenciosamente una reserva

  @HOT-004 @TC-HOT-004-N
  Escenario: TC-HOT-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Crear bloqueo sobre reserva confirmada y pretender anular automáticamente esa reserva.
    Entonces Bloqueo e incidencia visibles; contrato de reserva no se cancela ni se reembolsa sólo.

  @HOT-005 @TC-HOT-005-P
  Escenario: TC-HOT-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Habitación desocupada y sucia con saldo empresarial pendiente se muestra correctamente.
    Entonces Checkout deja habitación sucia sin cambiar saldo contable

  @HOT-005 @TC-HOT-005-N
  Escenario: TC-HOT-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Marcar CLEAN para intentar ignorar bloqueo por equipo inseguro.
    Entonces No queda asignable mientras mantenimiento siga bloqueante; error explicativo.

  @RES-005 @TC-RES-005-P
  Escenario: TC-RES-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reserva pactada a 70000 conserva ese valor cuando tarifa cambia a 75000.
    Entonces Cambiar tarifa base no cambia una reserva confirmada

  @RES-005 @TC-RES-005-N
  Escenario: TC-RES-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Modificar precio publicado y reabrir detalle de reserva ya confirmada.
    Entonces El detalle conserva snapshot original; sólo nueva cotizacion usa nuevo precio.

  @RES-006 @TC-RES-006-P
  Escenario: TC-RES-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Precio 100000 con descuento 10% resulta 90000; comisión se registra aparte con su base.
    Entonces Aplicar descuento no duplica deduccion del canal

  @RES-006 @TC-RES-006-N
  Escenario: TC-RES-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Aplicar 17% histórico automáticamente como descuento y comisión de toda venta.
    Entonces Bloqueo de configuración sin política vigente; no deduccion duplicada.

  @REV-001 @TC-REV-001-P
  Escenario: TC-REV-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Plan mínimo dos noches rechaza una y ofrece dos disponibles.
    Entonces Reglas incompatibles explican bloqueo; aumentar tarifa no altera reservas confirmadas.

  @REV-001 @TC-REV-001-N
  Escenario: TC-REV-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cambiar tarifa base altera precio de reserva confirmada.
    Entonces Snapshot preservado; nueva política sólo afecta ofertas futuras.
