# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Recepción, estadías y auditoría nocturna

  @REC-001 @TC-REC-001-P
  Escenario: TC-REC-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reserva de dos personas: llega una hoy, la segunda queda esperada.
    Entonces Reserva de dos pasajeros admite llegada parcial sin inventar el segundo

  @REC-001 @TC-REC-001-N
  Escenario: TC-REC-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Intentar ingresar a habitación sucia o fuera de servicio sin excepción permitida.
    Entonces 409 ROOM_NOT_READY; alternativa y escalamiento, sin check-in falso.

  @REC-002 @TC-REC-002-P
  Escenario: TC-REC-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cambiar 101 por 102 mantiene una estadía y una cuenta.
    Entonces Cambio conserva cuenta y genera aseo en habitación liberada

  @REC-002 @TC-REC-002-N
  Escenario: TC-REC-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Destino ocupado durante parte del intervalo solicitado.
    Entonces 409 y segmento original permanece activo; no movimiento a medias.

  @REC-003 @TC-REC-003-P
  Escenario: TC-REC-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Empresa con crédito aprobado sale con 80000 pendientes.
    Entonces Cuenta empresarial pendiente permanece por cobrar tras salida

  @REC-003 @TC-REC-003-N
  Escenario: TC-REC-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Particular con deuda intenta salida administrativa sin autorización requerida.
    Entonces Alerta a administrador; registrar realidad de salida sin marcar saldo pagado ni borrar deuda.

  @REC-004 @TC-REC-004-P
  Escenario: TC-REC-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Turno nocturno recibe llegada tardia y reclamo sin resolver.
    Entonces Incidencia pendiente pasa al siguiente turno con evidencia

  @REC-004 @TC-REC-004-N
  Escenario: TC-REC-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cerrar turno dejando incidente crítico sin receptor o responsable de escalamiento.
    Entonces Cierre exige responsable alterno y conserva pendiente visible.

  @REC-005 @TC-REC-005-P
  Escenario: TC-REC-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Objeto olvidado pasa a custodia y se entrega con respaldo al titular.
    Entonces Entrega registra receptor y responsable sin mostrarla publicamente

  @REC-005 @TC-REC-005-N
  Escenario: TC-REC-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Persona que conoce número de habitación solicita objeto sin verificación.
    Entonces Entrega bloqueada; caso reservado para responsable, sin revelar contenido.

  @OPS-006 @TC-OPS-006-P
  Escenario: TC-OPS-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Repetir cierre nocturno genera mismos cargos, no duplicados.
    Entonces Cruce de medianoche y horario de verano no duplica cargos ni fuerza cerrar una estadía activa.

  @OPS-006 @TC-OPS-006-N
  Escenario: TC-OPS-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cambio horario de verano provoca repetir hora del scheduler.
    Entonces Clave de noche/servicio evita duplicado; ejecución registrada una vez.
