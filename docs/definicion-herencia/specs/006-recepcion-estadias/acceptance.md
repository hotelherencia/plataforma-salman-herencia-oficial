# Aceptacion F05

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-REC-001-P | REC-001 | Reserva de dos personas: llega una hoy, la segunda queda esperada. | Reserva de dos pasajeros admite llegada parcial sin inventar el segundo |
| TC-REC-001-N | REC-001 | Intentar ingresar a habitación sucia o fuera de servicio sin excepción permitida. | 409 ROOM_NOT_READY; alternativa y escalamiento, sin check-in falso. |
| TC-REC-002-P | REC-002 | Cambiar 101 por 102 mantiene una estadía y una cuenta. | Cambio conserva cuenta y genera aseo en habitación liberada |
| TC-REC-002-N | REC-002 | Destino ocupado durante parte del intervalo solicitado. | 409 y segmento original permanece activo; no movimiento a medias. |
| TC-REC-003-P | REC-003 | Empresa con crédito aprobado sale con 80000 pendientes. | Cuenta empresarial pendiente permanece por cobrar tras salida |
| TC-REC-003-N | REC-003 | Particular con deuda intenta salida administrativa sin autorización requerida. | Alerta a administrador; registrar realidad de salida sin marcar saldo pagado ni borrar deuda. |
| TC-REC-004-P | REC-004 | Turno nocturno recibe llegada tardia y reclamo sin resolver. | Incidencia pendiente pasa al siguiente turno con evidencia |
| TC-REC-004-N | REC-004 | Cerrar turno dejando incidente crítico sin receptor o responsable de escalamiento. | Cierre exige responsable alterno y conserva pendiente visible. |
| TC-REC-005-P | REC-005 | Objeto olvidado pasa a custodia y se entrega con respaldo al titular. | Entrega registra receptor y responsable sin mostrarla publicamente |
| TC-REC-005-N | REC-005 | Persona que conoce número de habitación solicita objeto sin verificación. | Entrega bloqueada; caso reservado para responsable, sin revelar contenido. |
| TC-OPS-006-P | OPS-006 | Repetir cierre nocturno genera mismos cargos, no duplicados. | Cruce de medianoche y horario de verano no duplica cargos ni fuerza cerrar una estadía activa. |
| TC-OPS-006-N | OPS-006 | Cambio horario de verano provoca repetir hora del scheduler. | Clave de noche/servicio evita duplicado; ejecución registrada una vez. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
