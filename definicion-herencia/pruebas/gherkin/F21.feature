# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Verificación transversal y continuidad

  @SEC-004 @TC-SEC-004-P
  Escenario: TC-SEC-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Ensayo recupera reservas/saldos y opera flujo de prueba.
    Entonces Restaurar ambiente de prueba recupera datos y permite operar

  @SEC-004 @TC-SEC-004-N
  Escenario: TC-SEC-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Backup existe pero nunca se ha restaurado o faltan documentos.
    Entonces No supera gate de continuidad; pendiente hasta ensayo verificable.

  @SEC-005 @TC-SEC-005-P
  Escenario: TC-SEC-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Recibo de emergencia E001 se carga una vez al volver.
    Entonces Reingreso de operaciones de emergencia no duplica pagos

  @SEC-005 @TC-SEC-005-N
  Escenario: TC-SEC-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reimportar E001 o activar venta offline desde navegador sin cupo fiable.
    Entonces Duplicado rechazado; venta bloqueada, excepción supervisada.

  @AI-006 @TC-AI-006-P
  Escenario: TC-AI-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Apagar proveedor IA permite reservar por web y cerrar caja.
    Entonces Desactivar modelo no impide registrar reserva ni cerrar caja

  @AI-006 @TC-AI-006-N
  Escenario: TC-AI-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Endpoint de reserva depende de una llamada a modelo para calcular cupo.
    Entonces Prueba falla; separar motor determinista antes de liberar.

  @SEC-009 @TC-SEC-009-P
  Escenario: TC-SEC-009-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Revisor reproduce controles de aislamiento y secretos con evidencia.
    Entonces Vulnerabilidad crítica sin corregir impide producción aunque todas las pantallas existan.

  @SEC-009 @TC-SEC-009-N
  Escenario: TC-SEC-009-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Interfaz completa pero vulnerabilidad crítica de acceso cruzado abierta.
    Entonces NO_GO para producción, aunque pruebas visuales pasen.

  @SEC-010 @TC-SEC-010-P
  Escenario: TC-SEC-010-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Build identificado con lock y pruebas de migracion/recuperacion.
    Entonces Dependencia insegura detectada detiene paquete; rollback no pierde cobros nuevos.

  @SEC-010 @TC-SEC-010-N
  Escenario: TC-SEC-010-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dependencia vulnerable o secreto detectado antes de release.
    Entonces Pipeline bloqueado y remediacion; no bypass por agente.

  @QA-001 @TC-QA-001-P
  Escenario: TC-QA-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Un ciclo sintético completo produce resultados esperados sin duplicados.
    Entonces La misma transacción es trazable sin duplicados y con fallos simulados; no confundir prueba sintética con integración real.

  @QA-001 @TC-QA-001-N
  Escenario: TC-QA-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Sólo se prueban pantallas o mocks y se declara integración real.
    Entonces Gate no superado; exigir adaptador/entorno autorizado y pruebas correspondientes.

  @QA-002 @TC-QA-002-P
  Escenario: TC-QA-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Veinte intentos y precio manipulado no crean sobreventa interna ni descuento falso.
    Entonces Dos solicitudes al último cupo interno no crean dos confirmaciones; cliente no puede fijar monto arbitrario.

  @QA-002 @TC-QA-002-N
  Escenario: TC-QA-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Desactivar constraint para hacer pasar prueba bajo carga.
    Entonces Rechazo de cambio y hallazgo crítico; mantener integridad.

  @QA-003 @TC-QA-003-P
  Escenario: TC-QA-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Auditoría enlaza requisito a artefactos y senala pendientes reales.
    Entonces No se cierra maestro con dependencias sin ID, reglas contradictorias o decisiones críticas ocultas.

  @QA-003 @TC-QA-003-N
  Escenario: TC-QA-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Declarar 100% terminado por número de archivos sin revisar contradicciones.
    Entonces Estado revisión pendiente; reporte honesto de alcance y evidencia.
