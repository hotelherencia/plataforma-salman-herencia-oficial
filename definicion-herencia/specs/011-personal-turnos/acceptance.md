# Aceptacion F10

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-HR-001-P | HR-001 | Nómina actual autorizada crea trabajadores; planilla 2019 sólo antecedente. | Los seis cargos históricos no crean empleados activos automáticos |
| TC-HR-001-N | HR-001 | Importar seis recepcionistas históricos como activos por defecto. | Staging exige validación y no crea cuentas operativas. |
| TC-HR-002-P | HR-002 | Ausencia nocturna muestra franja descubierta y permite reemplazo habilitado. | Franja descubierta o turno incompatible aparece como alerta |
| TC-HR-002-N | HR-002 | Asignar mismo trabajador en dos puestos solapados. | 409 SHIFT_CONFLICT; cobertura no se presenta completa. |
| TC-HR-003-P | HR-003 | Tiempo real difiere de plan y supervisor revisa antes de exportar. | Horas de tarea no se convierten automáticamente en horas extra pagables |
| TC-HR-003-N | HR-003 | Convertir automáticamente minutos de aseo en horas extra pagadas. | No generar concepto pagable; queda propuesta pendiente de revisión. |
| TC-HR-004-P | HR-004 | Tarea compartida 60/40 reparte puntos sin multiplicarlos. | Retrabajo no genera automáticamente un segundo incentivo |
| TC-HR-004-N | HR-004 | Dos personas se asignan cada una el 100% de la misma tarea. | Validación rechaza suma mayor que uno antes de preliquidar. |
| TC-HR-005-P | HR-005 | Regla nueva aplica al siguiente período sin alterar premio aprobado anterior. | Cambio de regla no altera incentivos ya aprobados |
| TC-HR-005-N | HR-005 | Cambiar peso de tareas después de aprobar liquidación previa. | Nueva versión no reescribe anterior; corrección excepcional con evidencia. |
| TC-HR-006-P | HR-006 | Exportación validada de incentivos recibe acuse y queda EXPORTED. | No usa tasas de 2019 ni ejecuta pago por orden del modelo |
| TC-HR-006-N | HR-006 | Reenviar mismo lote como conceptos nuevos o usar tasas de 2019. | Detectar reenvio y bloquear regla sin validación vigente. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
