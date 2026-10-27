# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Personal, turnos e incentivos

  @HR-001 @TC-HR-001-P
  Escenario: TC-HR-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Nómina actual autorizada crea trabajadores; planilla 2019 sólo antecedente.
    Entonces Los seis cargos históricos no crean empleados activos automáticos

  @HR-001 @TC-HR-001-N
  Escenario: TC-HR-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Importar seis recepcionistas históricos como activos por defecto.
    Entonces Staging exige validación y no crea cuentas operativas.

  @HR-002 @TC-HR-002-P
  Escenario: TC-HR-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Ausencia nocturna muestra franja descubierta y permite reemplazo habilitado.
    Entonces Franja descubierta o turno incompatible aparece como alerta

  @HR-002 @TC-HR-002-N
  Escenario: TC-HR-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Asignar mismo trabajador en dos puestos solapados.
    Entonces 409 SHIFT_CONFLICT; cobertura no se presenta completa.

  @HR-003 @TC-HR-003-P
  Escenario: TC-HR-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Tiempo real difiere de plan y supervisor revisa antes de exportar.
    Entonces Horas de tarea no se convierten automáticamente en horas extra pagables

  @HR-003 @TC-HR-003-N
  Escenario: TC-HR-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Convertir automáticamente minutos de aseo en horas extra pagadas.
    Entonces No generar concepto pagable; queda propuesta pendiente de revisión.

  @HR-004 @TC-HR-004-P
  Escenario: TC-HR-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Tarea compartida 60/40 reparte puntos sin multiplicarlos.
    Entonces Retrabajo no genera automáticamente un segundo incentivo

  @HR-004 @TC-HR-004-N
  Escenario: TC-HR-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos personas se asignan cada una el 100% de la misma tarea.
    Entonces Validación rechaza suma mayor que uno antes de preliquidar.

  @HR-005 @TC-HR-005-P
  Escenario: TC-HR-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Regla nueva aplica al siguiente período sin alterar premio aprobado anterior.
    Entonces Cambio de regla no altera incentivos ya aprobados

  @HR-005 @TC-HR-005-N
  Escenario: TC-HR-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cambiar peso de tareas después de aprobar liquidacion previa.
    Entonces Nueva versión no reescribe anterior; corrección excepcional con evidencia.

  @HR-006 @TC-HR-006-P
  Escenario: TC-HR-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Exportación validada de incentivos recibe acuse y queda EXPORTED.
    Entonces No usa tasas de 2019 ni ejecuta pago por orden del modelo

  @HR-006 @TC-HR-006-N
  Escenario: TC-HR-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reenviar mismo lote como conceptos nuevos o usar tasas de 2019.
    Entonces Detectar reenvio y bloquear regla sin validación vigente.
