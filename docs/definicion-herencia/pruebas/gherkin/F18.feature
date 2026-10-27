# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Portal, solicitudes y experiencia del huésped

  @GEX-001 @TC-GEX-001-P
  Escenario: TC-GEX-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Huésped consulta su cuenta y solicitud sin instalar app.
    Entonces Conocer apellido y habitación no permite acceder; token revocado deja de funcionar.

  @GEX-001 @TC-GEX-001-N
  Escenario: TC-GEX-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Conocer apellido/habitacion o token de otro huésped.
    Entonces 403 y sin revelacion de cuenta; registrar intento seguro.

  @GEX-002 @TC-GEX-002-P
  Escenario: TC-GEX-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reclamo de ducha crea mantenimiento y seguimiento.
    Entonces Reclamo de ducha genera tarea de mantenimiento vinculada sin revelar datos a marketing.

  @GEX-002 @TC-GEX-002-N
  Escenario: TC-GEX-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Marketing intenta acceder al relato sensible o ticket se cierra sin resolver.
    Entonces Acceso denegado; cierre requiere criterio y conserva pendiente.

  @GEX-003 @TC-GEX-003-P
  Escenario: TC-GEX-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cliente con beneficio aprobado lo usa sin resuscribirse a marketing.
    Entonces Baja de promociones persiste en programas de fidelidad y no altera derechos de la reserva.

  @GEX-003 @TC-GEX-003-N
  Escenario: TC-GEX-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Agente pública reseña inventada o descuento no autorizado.
    Entonces Bloqueo y alerta; contenido queda borrador/rechazado.
