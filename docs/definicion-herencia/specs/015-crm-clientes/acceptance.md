# Aceptacion F14

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-SOC-001-P | SOC-001 | Mensajeria verificada funciona mientras publicación permanece desactivada. | Sin permiso de publicación, mensajeria puede funcionar y publicación permanece deshabilitada. |
| TC-SOC-001-N | SOC-001 | Marcar toda cuenta META integrada al validar un sólo permiso. | Rechazo de estado agregado; cada capacidad conserva gate propio. |
| TC-SOC-004-P | SOC-004 | Consulta se cotiza, cliente reserva y oportunidad queda GANADA. | Una consulta sin pago ni condiciones cumplidas no figura como reserva confirmada. |
| TC-SOC-004-N | SOC-004 | Agente marca venta por un mensaje de interes sin reserva. | Validación impide GANADA, conserva EN_ATENCION/COTIZADA. |
| TC-SOC-005-P | SOC-005 | Mismo contacto verifica correo y telefono y se vinculan dos canales. | Dos personas con igual nombre no se fusionan; pasar a WhatsApp no revela otra conversación. |
| TC-SOC-005-N | SOC-005 | Dos personas se llaman Ana y el sistema mezcla conversaciones. | No fusion; datos aislados hasta evidencia autorizada. |
| TC-SOC-006-P | SOC-006 | Recepción toma hilo y responde sin competencia del asistente. | Recepción toma un caso y no recibe respuestas concurrentes contradictorias del bot. |
| TC-SOC-006-N | SOC-006 | Respuesta bot en cola intenta salir después de handoff. | Bloqueo por versión de propietario; no mensaje contradictorio. |
| TC-SOC-009-P | SOC-009 | Hilo pendiente pasa al turno entrante con siguiente acción. | Cambio de turno conserva los casos pendientes con historial y siguiente acción. |
| TC-SOC-009-N | SOC-009 | Turno saliente cierra sesion dejando reclamo urgente sin receptor. | Asignar responsable de escalamiento y alerta, nunca cerrar caso automáticamente. |
| TC-SOC-013-P | SOC-013 | Baja cancela mensajes promocionales en cola y permite consultar cuenta. | Solicitar baja impide nuevas promociones incluso si ya están en cola; no impide consultar la reserva. |
| TC-SOC-013-N | SOC-013 | Lista antigua vuelve a suscribir al cliente sin nueva evidencia. | No cambia REVOKED; incidente de importacion/permiso. |
| TC-SOC-017-P | SOC-017 | Contacto con permiso recibe recordatorio aprobado y nueva validación. | Un visitante anonimo no recibe un mensaje inventado; una oferta vencida requiere nueva cotización. |
| TC-SOC-017-N | SOC-017 | Visitante anonimo sin contacto se intenta contactar automáticamente. | No mensaje; sólo estadistica agregada permitida. |
| TC-SEC-007-P | SEC-007 | Opt-out permite comprar sin eventos publicitarios personales. | Rechazar seguimiento no impide reservar; payload de conversión no contiene datos prohibidos. |
| TC-SEC-007-N | SEC-007 | Payload conversion contiene documento del huésped. | Validador de esquema rechaza y registra incidente sin copiar el dato en log. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
