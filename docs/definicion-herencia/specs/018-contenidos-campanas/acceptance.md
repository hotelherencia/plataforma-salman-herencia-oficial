# Aceptacion F17

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-INT-006-P | INT-006 | Contenido aprobado se pública y guarda ID externo. | Sin aprobación no pública contenido ni activa gasto |
| TC-INT-006-N | INT-006 | Agente intenta publicar oferta o activar anuncio sin permiso. | Bloqueo y solicitud de aprobación; cero gasto externo. |
| TC-SOC-014-P | SOC-014 | Campaña aprobada opera dentro de límite y período. | Sin autorización no se activa gasto; aumentar presupuesto requiere nueva aprobación aplicable. |
| TC-SOC-014-N | SOC-014 | Modelo aumenta presupuesto para mejorar conversion por iniciativa. | 403 y solicitud pendiente; no gasto extra. |
| TC-SOC-015-P | SOC-015 | Pieza aprobada pública y guarda referencia externa. | Formato no admitido queda pendiente o se exporta para publicación manual, nunca figura publicado. |
| TC-SOC-015-N | SOC-015 | Proveedor rechaza formato pero interfaz muestra publicada. | Estado FAILED/MANUAL y alerta, sin evidencia ficticia. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
