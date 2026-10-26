# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Booking y distribución externa

  @INT-001 @TC-INT-001-P
  Escenario: TC-INT-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Crear/modificar/cancelar reserva de prueba autorizada verifica cada capacidad.
    Entonces Se crea, modifica y cancela reserva real de prueba autorizada

  @INT-001 @TC-INT-001-N
  Escenario: TC-INT-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Sólo existe documentación pública sin cuenta ni permisos.
    Entonces Estado DOCUMENTED/BLOCKED; no marcar integrado ni activar inventario comun.

  @INT-002 @TC-INT-002-P
  Escenario: TC-INT-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cancelación revision3 permanece frente a confirmacion revision2.
    Entonces Cancelación no se revierte por una confirmacion antigua

  @INT-002 @TC-INT-002-N
  Escenario: TC-INT-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Evento mismo ID con contenido diferente.
    Entonces Incidencia de integridad y cuarentena; no sobrescritura silenciosa.

  @INT-003 @TC-INT-003-P
  Escenario: TC-INT-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Caida suspende ventas o aplica cupos segregados autorizados.
    Entonces Caida no figura como sincronizado ni vende cupos sin control

  @INT-003 @TC-INT-003-N
  Escenario: TC-INT-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Conector falla pero interfaz sigue mostrando sincronizado/verde.
    Entonces Prueba falla; estado DEGRADED y alerta a responsable.

  @SOC-019 @TC-SOC-019-P
  Escenario: TC-SOC-019-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Perfil enlaza web aún sin feed tarifario habilitado.
    Entonces Sin proveedor habilitado no se anuncia tarifa sincronizada; enlace normal sigue operativo.

  @SOC-019 @TC-SOC-019-N
  Escenario: TC-SOC-019-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Anunciar sincronización de tarifas sin contrato/feed funcional.
    Entonces Capacidad UNAVAILABLE/BLOCKED, no logo de integrado falso.

  @INT-007 @TC-INT-007-P
  Escenario: TC-INT-007-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Token vence: alerta y DEGRADED del conector afectado.
    Entonces Token vencido genera alerta y estado degradado; no se muestra conectado en verde.

  @INT-007 @TC-INT-007-N
  Escenario: TC-INT-007-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Conector sigue verde porque servidor HTTP responde.
    Entonces Prueba falla; separar liveness de sincronización funcional.
