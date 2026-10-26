# Aceptacion F19

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-INT-004-P | INT-004 | Movimientos nuevos se importan con cursor sin duplicar históricos. | Revocar acceso impide nuevas lecturas y deja trazabilidad |
| TC-INT-004-N | INT-004 | Revocar permiso mientras hay job programado. | No nueva lectura; job bloqueado y auditoría de revocacion. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
