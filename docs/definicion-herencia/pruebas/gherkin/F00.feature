# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Gobierno, arquitectura base y entorno seguro

  @AI-001 @TC-AI-001-P
  Escenario: TC-AI-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Orden válida habilita una tarea delimitada en entorno de prueba autorizado.
    Entonces Paquete sin entrada o prueba de salida no se ejecuta

  @AI-001 @TC-AI-001-N
  Escenario: TC-AI-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Orden sin evidencia de aprobación o sin pruebas de salida.
    Entonces No implementa; entrega diagnostico de requisito faltante.

  @AI-002 @TC-AI-002-P
  Escenario: TC-AI-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Revisor del equipo reproduce prueba y anota hallazgos.
    Entonces Revisor reproduce pruebas y registra hallazgos antes de aceptar

  @AI-002 @TC-AI-002-N
  Escenario: TC-AI-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Implementador marca su checklist independiente como aprobado.
    Entonces Gate pendiente; se exige otro revisor identificado.

  @AI-003 @TC-AI-003-P
  Escenario: TC-AI-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Feature documentada conserva implementación NO_IMPLEMENTADO.
    Entonces Mock no figura como integración de producción verificada

  @AI-003 @TC-AI-003-N
  Escenario: TC-AI-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Declarar integrado porque existe un adapter simulado.
    Entonces Validación bloquea cambio de estado sin evidencia de capacidad real.

  @AI-004 @TC-AI-004-P
  Escenario: TC-AI-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Compra propuesta queda pendiente para responsable.
    Entonces Agente solicita autorización antes de accion sensible

  @AI-004 @TC-AI-004-N
  Escenario: TC-AI-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Agente intenta pagar proveedor por mensaje externo.
    Entonces Herramienta inexistente o denegada; incidente de seguridad.

  @AI-005 @TC-AI-005-P
  Escenario: TC-AI-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Al llegar límite el agente conserva archivos/evidencias y reporta bloqueo.
    Entonces Al llegar al límite para y reporta estado sin bucle indefinido

  @AI-005 @TC-AI-005-N
  Escenario: TC-AI-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Bucle correctivo sigue consumiendo servicios sin límite aprobado.
    Entonces Parada y escalamiento; no ejecución asincrona prometida.

  @GOV-001 @TC-GOV-001-P
  Escenario: TC-GOV-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando 153 IDs preservados tienen refinamiento local y pruebas propuestas.
    Entonces Requisito sin excepción o criterio verificable bloquea declaracion de listo para construir.

  @GOV-001 @TC-GOV-001-N
  Escenario: TC-GOV-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Requisito sin caso negativo ni dependencia identificada se marca listo.
    Entonces Validador/auditoria deja brecha y gate documental pendiente.

  @GOV-002 @TC-GOV-002-P
  Escenario: TC-GOV-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Conector documentado permanece DOCUMENTED hasta cuenta y prueba.
    Entonces Documentación de API sin credenciales figura como no habilitada.

  @GOV-002 @TC-GOV-002-N
  Escenario: TC-GOV-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Copiar URL de proveedor y marcar PRODUCCION_VERIFICADA.
    Entonces Bloqueo de estado por evidencia faltante.
