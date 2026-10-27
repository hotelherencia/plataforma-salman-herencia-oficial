# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: CRM, identidad y consentimiento

  @SOC-001 @TC-SOC-001-P
  Escenario: TC-SOC-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Mensajeria verificada funciona mientras publicación permanece desactivada.
    Entonces Sin permiso de publicación, mensajeria puede funcionar y publicación permanece deshabilitada.

  @SOC-001 @TC-SOC-001-N
  Escenario: TC-SOC-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Marcar toda cuenta META integrada al validar un sólo permiso.
    Entonces Rechazo de estado agregado; cada capacidad conserva gate propio.

  @SOC-004 @TC-SOC-004-P
  Escenario: TC-SOC-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Consulta se cotiza, cliente reserva y oportunidad queda GANADA.
    Entonces Una consulta sin pago ni condiciones cumplidas no figura como reserva confirmada.

  @SOC-004 @TC-SOC-004-N
  Escenario: TC-SOC-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Agente marca venta por un mensaje de interes sin reserva.
    Entonces Validación impide GANADA, conserva EN_ATENCION/COTIZADA.

  @SOC-005 @TC-SOC-005-P
  Escenario: TC-SOC-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Mismo contacto verifica correo y telefono y se vinculan dos canales.
    Entonces Dos personas con igual nombre no se fusionan; pasar a WhatsApp no revela otra conversación.

  @SOC-005 @TC-SOC-005-N
  Escenario: TC-SOC-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos personas se llaman Ana y el sistema mezcla conversaciones.
    Entonces No fusion; datos aislados hasta evidencia autorizada.

  @SOC-006 @TC-SOC-006-P
  Escenario: TC-SOC-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Recepción toma hilo y responde sin competencia del asistente.
    Entonces Recepción toma un caso y no recibe respuestas concurrentes contradictorias del bot.

  @SOC-006 @TC-SOC-006-N
  Escenario: TC-SOC-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Respuesta bot en cola intenta salir después de handoff.
    Entonces Bloqueo por versión de propietario; no mensaje contradictorio.

  @SOC-009 @TC-SOC-009-P
  Escenario: TC-SOC-009-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Hilo pendiente pasa al turno entrante con siguiente accion.
    Entonces Cambio de turno conserva los casos pendientes con historial y siguiente accion.

  @SOC-009 @TC-SOC-009-N
  Escenario: TC-SOC-009-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Turno saliente cierra sesion dejando reclamo urgente sin receptor.
    Entonces Asignar responsable de escalamiento y alerta, nunca cerrar caso automáticamente.

  @SOC-013 @TC-SOC-013-P
  Escenario: TC-SOC-013-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Baja cancela mensajes promocionales en cola y permite consultar cuenta.
    Entonces Solicitar baja impide nuevas promociones incluso si ya están en cola; no impide consultar la reserva.

  @SOC-013 @TC-SOC-013-N
  Escenario: TC-SOC-013-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Lista antigua vuelve a suscribir al cliente sin nueva evidencia.
    Entonces No cambia REVOKED; incidente de importacion/permiso.

  @SOC-017 @TC-SOC-017-P
  Escenario: TC-SOC-017-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Contacto con permiso recibe recordatorio aprobado y nueva validación.
    Entonces Un visitante anonimo no recibe un mensaje inventado; una oferta vencida requiere nueva cotización.

  @SOC-017 @TC-SOC-017-N
  Escenario: TC-SOC-017-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Visitante anonimo sin contacto se intenta contactar automáticamente.
    Entonces No mensaje; sólo estadistica agregada permitida.

  @SEC-007 @TC-SEC-007-P
  Escenario: TC-SEC-007-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Opt-out permite comprar sin eventos publicitarios personales.
    Entonces Rechazar seguimiento no impide reservar; payload de conversión no contiene datos prohibidos.

  @SEC-007 @TC-SEC-007-N
  Escenario: TC-SEC-007-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Payload conversion contiene documento del huésped.
    Entonces Validador de esquema rechaza y registra incidente sin copiar el dato en log.
