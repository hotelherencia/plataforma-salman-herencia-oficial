# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Traspaso, migración y apertura

  @MIG-001 @TC-MIG-001-P
  Escenario: TC-MIG-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Fuente con encabezado ambiguo queda observada antes de migrar.
    Entonces Fuente con fecha 31-6 se marca para revisión, no se inventa fecha

  @MIG-001 @TC-MIG-001-N
  Escenario: TC-MIG-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Inventar fecha válida para una fila 31-6.
    Entonces Fila rechazada con motivo y sin escritura productiva.

  @MIG-002 @TC-MIG-002-P
  Escenario: TC-MIG-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reserva enero pagada 100000 al saliente muestra crédito y fondo pendiente.
    Entonces Reserva enero cobrada antes queda trazable sin doble venta

  @MIG-002 @TC-MIG-002-N
  Escenario: TC-MIG-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cobrar nuevamente 100000 al huésped porque aún no se entrego dinero.
    Entonces Bloqueo de cobro duplicado; diferencia se gestiona contra saliente segun acta.

  @MIG-003 @TC-MIG-003-P
  Escenario: TC-MIG-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Conteo y anticipos aprobados coinciden exactamente con lote cargado.
    Entonces Suma de saldos aprobados coincide con importación y excepciones

  @MIG-003 @TC-MIG-003-N
  Escenario: TC-MIG-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Diferencia de cantidades o saldos no explicada.
    Entonces No aprobar lote; conservar excepciones y volver a validar.

  @MIG-004 @TC-MIG-004-P
  Escenario: TC-MIG-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Recepción registra llegada, cobro, salida y turno en ejercicio ficticio.
    Entonces Recepción completa ciclo sin depender de instrucciones del desarrollador

  @MIG-004 @TC-MIG-004-N
  Escenario: TC-MIG-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Sólo presentacion de pantallas sin operador realizando tareas.
    Entonces Capacitación no aceptada; repetir prácticas y registrar resultado.

  @MIG-005 @TC-MIG-005-P
  Escenario: TC-MIG-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reserva cruzada conserva cuenta y asignación aprobada por período.
    Entonces Una reserva cobrada por operador saliente conserva pago histórico y monto por rendir sin cobrar de nuevo al cliente.

  @MIG-005 @TC-MIG-005-N
  Escenario: TC-MIG-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Abono enero por venta diciembre se registra automáticamente como nueva venta enero.
    Entonces Clasificar en conciliacion/traspaso, no duplicar ingreso.

  @MIG-006 @TC-MIG-006-P
  Escenario: TC-MIG-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Colchon faltante queda observado con respaldo y responsable propuesto.
    Entonces Un faltante queda abierto con responsable sin convertirse automáticamente en compra aprobada.

  @MIG-006 @TC-MIG-006-N
  Escenario: TC-MIG-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Sistema aprueba compra para cerrar artificialmente discrepancia.
    Entonces Observacion permanece abierta; nueva compra necesita autorización independiente.
