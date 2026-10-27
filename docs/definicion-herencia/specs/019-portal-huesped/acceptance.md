# Aceptacion F18

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-GEX-001-P | GEX-001 | Huésped consulta su cuenta y solicitud sin instalar app. | Conocer apellido y habitación no permite acceder; token revocado deja de funcionar. |
| TC-GEX-001-N | GEX-001 | Conocer apellido/habitacion o token de otro huésped. | 403 y sin revelacion de cuenta; registrar intento seguro. |
| TC-GEX-002-P | GEX-002 | Reclamo de ducha crea mantenimiento y seguimiento. | Reclamo de ducha genera tarea de mantenimiento vinculada sin revelar datos a marketing. |
| TC-GEX-002-N | GEX-002 | Marketing intenta acceder al relato sensible o ticket se cierra sin resolver. | Acceso denegado; cierre requiere criterio y conserva pendiente. |
| TC-GEX-003-P | GEX-003 | Cliente con beneficio aprobado lo usa sin resuscribirse a marketing. | Baja de promociones persiste en programas de fidelidad y no altera derechos de la reserva. |
| TC-GEX-003-N | GEX-003 | Agente pública reseña inventada o descuento no autorizado. | Bloqueo y alerta; contenido queda borrador/rechazado. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
