# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Reserva directa desde enlace social

  @RES-001 @TC-RES-001-P
  Escenario: TC-RES-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Huésped completa reserva desde enlace y recepción ve mismo precio/fechas.
    Entonces Reserva desde enlace social aparece en recepción con el mismo ID

  @RES-001 @TC-RES-001-N
  Escenario: TC-RES-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Interrumpir correo después de confirmar reserva.
    Entonces Reserva permanece confirmada; notificación fallida en cola y alerta.

  @RES-002 @TC-RES-002-P
  Escenario: TC-RES-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Enlace Instagram produce canal DIRECT y origen instagram.
    Entonces Reserva directa originada en Instagram no se atribuye a Booking

  @RES-002 @TC-RES-002-N
  Escenario: TC-RES-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Parámetro URL contiene RUT, script o texto excesivo.
    Entonces Se rechaza o descarta dato de atribución inseguro sin impedir compra legitima.

  @RES-003 @TC-RES-003-P
  Escenario: TC-RES-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Retención de prueba de quince minutos expira y devuelve una unidad.
    Entonces Cupo expirado no se confirma si ya fue vendido

  @RES-003 @TC-RES-003-N
  Escenario: TC-RES-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Pago confirmado tras vencimiento y cupo vendido a otro cliente.
    Entonces Estado PAGO_SIN_CUPO, incidencia y alternativa/devolucion autorizada; no sobreventa silenciosa.

  @RES-004 @TC-RES-004-P
  Escenario: TC-RES-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Veinte solicitudes al último cupo producen un sólo compromiso interno.
    Entonces Dos solicitudes simultaneas producen una sola confirmacion interna

  @RES-004 @TC-RES-004-N
  Escenario: TC-RES-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos transacciones intentan confirmar el último cupo simultaneamente.
    Entonces Una obtiene 201; restantes 409 NO_AVAILABILITY, sin contadores negativos.

  @RES-007 @TC-RES-007-P
  Escenario: TC-RES-007-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Tres habitaciones con 50000,60000,70000 suman 180000.
    Entonces Tres habitaciones suman sus lineas una sola vez

  @RES-007 @TC-RES-007-N
  Escenario: TC-RES-007-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Consulta une pasajeros y multiplica total de cabecera por filas.
    Entonces Prueba detecta total distinto; reporte debe agregar primero por nivel correcto.

  @RES-008 @TC-RES-008-P
  Escenario: TC-RES-008-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Empresa paga dos estadías y documento mantiene pasajeros vinculados privadamente.
    Entonces Factura a empresa sin perder pasajeros y estadías asociados

  @RES-008 @TC-RES-008-N
  Escenario: TC-RES-008-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Recepción habilita crédito a empresa sin convenio vigente.
    Entonces Reserva puede quedar pendiente, pero no salida a crédito sin aprobación.

  @RES-009 @TC-RES-009-P
  Escenario: TC-RES-009-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Agregar una noche libre aumenta una unidad de inventario y su cargo, no noches previas.
    Entonces Extension válida cupo y sólo agrega noches y cargos aplicables

  @RES-009 @TC-RES-009-N
  Escenario: TC-RES-009-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Extender cuando última noche no esta disponible o versión ya cambio.
    Entonces 409; reserva previa integra y cotizacion alternativa visible.

  @RES-010 @TC-RES-010-P
  Escenario: TC-RES-010-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cancelación permitida libera reserva y calcula devolución conforme a snapshot.
    Entonces No-show no se convierte automáticamente en noche ocupada

  @RES-010 @TC-RES-010-N
  Escenario: TC-RES-010-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Mensaje antiguo de confirmacion llega después de cancelación externa nueva.
    Entonces No revierte cancelación; se ignora revisión obsoleta y registra motivo.

  @RES-011 @TC-RES-011-P
  Escenario: TC-RES-011-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Pago de 180000 aplicado a tres cuentas por 50000,60000,70000.
    Entonces Un pago colectivo puede aplicarse a varias cuentas sin exceso

  @RES-011 @TC-RES-011-N
  Escenario: TC-RES-011-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Aplicar 200000 de un pago de 180000.
    Entonces 422 ALLOCATION_EXCEEDS_AVAILABLE; ninguna aplicación parcial queda huérfana.

  @INT-005 @TC-INT-005-P
  Escenario: TC-INT-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Una reserva confirmada genera una confirmacion operativa.
    Entonces Reintento no envia confirmaciones duplicadas al mismo evento

  @INT-005 @TC-INT-005-N
  Escenario: TC-INT-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reintentar tras timeout de proveedor sin conocer entrega.
    Entonces Consultar referencia cuando posible; estado incierto visible y evitar spam.

  @SOC-002 @TC-SOC-002-P
  Escenario: TC-SOC-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Click desde Instagram enlaza reserva directa con origen conocido.
    Entonces Un clic de Instagram llega al motor y conserva fuente en la reserva; sin etiqueta queda desconocida, no inventada.

  @SOC-002 @TC-SOC-002-N
  Escenario: TC-SOC-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Eliminar etiquetas al volver del checkout o inventar campaña por ausencia.
    Entonces Persistencia segura de origen disponible; ausencia queda UNKNOWN.

  @SOC-003 @TC-SOC-003-P
  Escenario: TC-SOC-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Checkout desde navegador interno vuelve a la misma reserva.
    Entonces Volver del pago desde un navegador interno no pierde la reserva ni duplica el cobro.

  @SOC-003 @TC-SOC-003-N
  Escenario: TC-SOC-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Navegador pierde cookie después del pago.
    Entonces Recuperación autenticada segura, no segundo cobro; si no hay acceso deriva.

  @SOC-016 @TC-SOC-016-P
  Escenario: TC-SOC-016-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cliente abre oferta válida y completa pago segun política.
    Entonces Un enlace vencido no mantiene cupo; compartirlo no permite ver otras reservas.

  @SOC-016 @TC-SOC-016-N
  Escenario: TC-SOC-016-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Token vencido o perteneciente a otra reserva usado para leer deuda.
    Entonces 410/403 sin datos; ofrecer nueva cotizacion autorizada.

  @UX-001 @TC-UX-001-P
  Escenario: TC-UX-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Completar reserva y cambiar habitación sólo con teclado.
    Entonces Reserva y calendario tienen alternativa sin arrastrar; campos de error son anunciados y corregibles.

  @UX-001 @TC-UX-001-N
  Escenario: TC-UX-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Campo con error sólo cambia color y no explica el problema.
    Entonces Falla de aceptacion UX; agregar mensaje y foco sin perder datos.

  @UX-002 @TC-UX-002-P
  Escenario: TC-UX-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cambiar idioma conserva importe exacto y fechas de reserva.
    Entonces Traducir no cambia monto, política aceptada ni calculo de noches; fallo no se muestra como exito.

  @UX-002 @TC-UX-002-N
  Escenario: TC-UX-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Traducir dia/mes invierte fechas o pantalla muestra datos previos de otra cuenta.
    Entonces Rechazo del caso; limpiar estado y formatos inequívocos.
