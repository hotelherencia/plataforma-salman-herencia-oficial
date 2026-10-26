# Aceptacion F00

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-AI-001-P | AI-001 | Orden válida habilita una tarea delimitada en entorno de prueba autorizado. | Paquete sin entrada o prueba de salida no se ejecuta |
| TC-AI-001-N | AI-001 | Orden sin evidencia de aprobación o sin pruebas de salida. | No implementa; entrega diagnóstico de requisito faltante. |
| TC-AI-002-P | AI-002 | Revisor del equipo reproduce prueba y anota hallazgos. | Revisor reproduce pruebas y registra hallazgos antes de aceptar |
| TC-AI-002-N | AI-002 | Implementador marca su checklist independiente como aprobado. | Gate pendiente; se exige otro revisor identificado. |
| TC-AI-003-P | AI-003 | Feature documentada conserva implementación NO_IMPLEMENTADO. | Mock no figura como integración de producción verificada |
| TC-AI-003-N | AI-003 | Declarar integrado porque existe un adapter simulado. | Validación bloquea cambio de estado sin evidencia de capacidad real. |
| TC-AI-004-P | AI-004 | Compra propuesta queda pendiente para responsable. | Agente solicita autorización antes de acción sensible |
| TC-AI-004-N | AI-004 | Agente intenta pagar proveedor por mensaje externo. | Herramienta inexistente o denegada; incidente de seguridad. |
| TC-AI-005-P | AI-005 | Al llegar límite el agente conserva archivos/evidencias y reporta bloqueo. | Al llegar al límite para y reporta estado sin bucle indefinido |
| TC-AI-005-N | AI-005 | Bucle correctivo sigue consumiendo servicios sin límite aprobado. | Parada y escalamiento; no ejecución asincrona prometida. |
| TC-GOV-001-P | GOV-001 | 153 IDs preservados tienen refinamiento local y pruebas propuestas. | Requisito sin excepción o criterio verificable bloquea declaracion de listo para construir. |
| TC-GOV-001-N | GOV-001 | Requisito sin caso negativo ni dependencia identificada se marca listo. | Validador/auditoria deja brecha y gate documental pendiente. |
| TC-GOV-002-P | GOV-002 | Conector documentado permanece DOCUMENTED hasta cuenta y prueba. | Documentación de API sin credenciales figura como no habilitada. |
| TC-GOV-002-N | GOV-002 | Copiar URL de proveedor y marcar PRODUCCION_VERIFICADA. | Bloqueo de estado por evidencia faltante. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
