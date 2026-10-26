# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Activos, mantenimiento y renovación

  @MNT-001 @TC-MNT-001-P
  Escenario: TC-MNT-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Vencimiento de revisión genera una tarea del equipo concreto.
    Entonces Vencimiento genera tarea sin bloquear habitaciones no afectadas

  @MNT-001 @TC-MNT-001-N
  Escenario: TC-MNT-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reejecutar scheduler del mismo día.
    Entonces No duplica orden; muestra ID existente.

  @MNT-002 @TC-MNT-002-P
  Escenario: TC-MNT-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reparacion verificada libera cuarto previamente bloqueado.
    Entonces Habitación fuera de servicio sólo se libera con cierre autorizado

  @MNT-002 @TC-MNT-002-N
  Escenario: TC-MNT-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Proveedor factura pero equipo sigue fallando.
    Entonces Habitación permanece bloqueada y orden en verificacion/incidencia.

  @CAP-002 @TC-CAP-002-P
  Escenario: TC-CAP-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Equipo del arrendatario figura como tercero, no patrimonio propio.
    Entonces Un equipo del arrendatario no pasa automáticamente a ser activo del grupo.

  @CAP-002 @TC-CAP-002-N
  Escenario: TC-CAP-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Importar inventario y asignar todos los bienes a Herencia automáticamente.
    Entonces Staging bloquea propiedad desconocida para activación contable.

  @CAP-003 @TC-CAP-003-P
  Escenario: TC-CAP-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Diez colchones tienen partida, especificación y costo total con instalación.
    Entonces Diez colchones tienen presupuesto, propuesta, aprobación y estado separados del stock de jabon.

  @CAP-003 @TC-CAP-003-N
  Escenario: TC-CAP-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Necesidad de mejora se interpreta como obligación del arrendatario sin contrato.
    Entonces Mantener propuesta y asunto discutido separados; no deuda automática.

  @CAP-004 @TC-CAP-004-P
  Escenario: TC-CAP-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Equipo recibido e instalado pasa inspección antes de READY.
    Entonces Equipo pagado pero no instalado no libera una habitación bloqueada.

  @CAP-004 @TC-CAP-004-N
  Escenario: TC-CAP-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Equipo pagado aún en transporte libera habitación.
    Entonces Validación bloquea liberacion y conserva estado ORDERED.

  @CAP-005 @TC-CAP-005-P
  Escenario: TC-CAP-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reemplazo mantiene vinculo y evidencia del activo retirado.
    Entonces Reemplazo conserva historial del activo retirado; ajuste no borra faltante de traspaso.

  @CAP-005 @TC-CAP-005-N
  Escenario: TC-CAP-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Contabilizar compra dos veces como gasto y activo, o eliminar faltante histórico.
    Entonces Control contable/trace bloquea lote y requiere corrección autorizada.

  @CAP-006 @TC-CAP-006-P
  Escenario: TC-CAP-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Renovación prevista detecta reserva que requiere reasignar.
    Entonces Una obra bloquea inventario aprobado y alerta reservas afectadas antes de la intervención.

  @CAP-006 @TC-CAP-006-N
  Escenario: TC-CAP-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Intervencion inicia sin bloquear y canal vende la habitación.
    Entonces Incidente crítico y stop-sell controlado; no aceptar como flujo conforme.
