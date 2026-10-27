# Aceptacion F15

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-SOC-007-P | SOC-007 | Respuesta libre dentro de ventana o plantilla válida fuera de ella. | Un mensaje fuera de ventana sin plantilla permitida se bloquea y queda explicacion; no se reintenta como spam. |
| TC-SOC-007-N | SOC-007 | Fuera de ventana se intenta enviar texto libre promocional. | BLOCKED con motivo, sin reintentos para evadir restricción. |
| TC-SOC-008-P | SOC-008 | Mensaje entrante inicia hilo y respuesta permitida se entrega. | Una revocacion de acceso suspende sólo el conector afectado y alerta; no simula mensajes enviados. |
| TC-SOC-008-N | SOC-008 | API rechaza permiso y app afirma mensaje enviado. | Estado FAILED/DEGRADED, alerta y alternativa humana. |
| TC-SOC-011-P | SOC-011 | Diez reenvios del mismo mensaje crean un mensaje y una oportunidad. | Repetir mensaje diez veces crea un mensaje y una oportunidad; firma inválida no crea nada. |
| TC-SOC-011-N | SOC-011 | Firma inválida o misma ID con contenido alterado. | 401 o cuarentena de integridad; sin creación de objetos comerciales. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
