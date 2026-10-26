# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Conexión bancaria autorizada de lectura

  @INT-004 @TC-INT-004-P
  Escenario: TC-INT-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Movimientos nuevos se importan con cursor sin duplicar históricos.
    Entonces Revocar acceso impide nuevas lecturas y deja trazabilidad

  @INT-004 @TC-INT-004-N
  Escenario: TC-INT-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Revocar permiso mientras hay job programado.
    Entonces No nueva lectura; job bloqueado y auditoría de revocacion.
