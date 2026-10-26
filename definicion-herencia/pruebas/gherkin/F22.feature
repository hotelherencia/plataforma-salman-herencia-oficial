# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Contratos para módulos futuros del grupo

  @CORE-007 @TC-CORE-007-P
  Escenario: TC-CORE-007-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Inmobiliaria usa proveedor comun sin ver cobros del hotel.
    Entonces Un identificador de proveedor compartido no comparte automáticamente pagos ni datos de huéspedes.

  @CORE-007 @TC-CORE-007-N
  Escenario: TC-CORE-007-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Futura aplicación pide acceso global por conocer party_id.
    Entonces 403; requiere contrato/permiso explícito por sociedad y finalidad.
