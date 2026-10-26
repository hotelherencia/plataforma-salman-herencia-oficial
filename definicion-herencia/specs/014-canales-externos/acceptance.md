# Aceptacion F13

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-INT-001-P | INT-001 | Crear/modificar/cancelar reserva de prueba autorizada verifica cada capacidad. | Se crea, modifica y cancela reserva real de prueba autorizada |
| TC-INT-001-N | INT-001 | Sólo existe documentación pública sin cuenta ni permisos. | Estado DOCUMENTED/BLOCKED; no marcar integrado ni activar inventario comun. |
| TC-INT-002-P | INT-002 | Cancelación revisión 3 permanece frente a confirmacion revisión 2. | Cancelación no se revierte por una confirmacion antigua |
| TC-INT-002-N | INT-002 | Evento mismo ID con contenido diferente. | Incidencia de integridad y cuarentena; no sobrescritura silenciosa. |
| TC-INT-003-P | INT-003 | Caida suspende ventas o aplica cupos segregados autorizados. | Caida no figura como sincronizado ni vende cupos sin control |
| TC-INT-003-N | INT-003 | Conector falla pero interfaz sigue mostrando sincronizado/verde. | Prueba falla; estado DEGRADED y alerta a responsable. |
| TC-SOC-019-P | SOC-019 | Perfil enlaza web aún sin feed tarifario habilitado. | Sin proveedor habilitado no se anuncia tarifa sincronizada; enlace normal sigue operativo. |
| TC-SOC-019-N | SOC-019 | Anunciar sincronización de tarifas sin contrato/feed funcional. | Capacidad UNAVAILABLE/BLOCKED, no logo de integrado falso. |
| TC-INT-007-P | INT-007 | Token vence: alerta y DEGRADED del conector afectado. | Token vencido genera alerta y estado degradado; no se muestra conectado en verde. |
| TC-INT-007-N | INT-007 | Conector sigue verde porque servidor HTTP responde. | Prueba falla; separar liveness de sincronización funcional. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
