# Aceptacion F01

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-CORE-001-P | CORE-001 | Usuario de Herencia registra una reserva del hotel y consulta su unidad, sin ver SB. | Un usuario de Herencia no puede registrar un cobro en SB sin permiso |
| TC-CORE-001-N | CORE-001 | Cambiar company_id de la solicitud por SB conservando sesion Herencia. | 403 y ninguna escritura ni existencia revelada; evento seguro de denegacion. |
| TC-CORE-002-P | CORE-002 | Participación histórica del 2018 permanece consultable después de cargar una versión respaldada. | Una modificación futura conserva porcentajes históricos |
| TC-CORE-002-N | CORE-002 | Ingresar dos participaciones activas que sumen 110%. | 422 con detalle de total, sin modificar versión previa. |
| TC-CORE-003-P | CORE-003 | Aseo recibe sus tareas y estados de habitaciones, no cuenta ni sueldo. | Aseo no puede consultar salarios, identidades o cuentas ajenas |
| TC-CORE-003-N | CORE-003 | Acceso directo por URL a una remuneracion usando token de aseo. | 403 sin payload sensible; exportación tampoco habilitada. |
| TC-CORE-004-P | CORE-004 | Revertir un pago registrado conserva original y referencia al ajuste autorizado. | Corregir un pago conserva original y reverso |
| TC-CORE-004-N | CORE-004 | Recepción intenta DELETE sobre pago de turno cerrado. | 405/409; solicitar ajuste con aprobación, sin cambiar saldo. |
| TC-CORE-005-P | CORE-005 | Dos noches en cambio de horario siguen siendo dos y el precio no varia por cambio de cotización posterior. | Cruce horario y cambio posterior no alteran noches ni precio pactado |
| TC-CORE-005-N | CORE-005 | Envio de importe con decimales no admitidos para moneda configurada o salida anterior a llegada. | 422, sin redondeo silencioso ni reserva creada. |
| TC-CORE-006-P | CORE-006 | Dos proveedores distintos pueden tener factura folio 100 sin conflicto. | Factura duplicada se detecta sin bloquear otra de diferente emisor |
| TC-CORE-006-N | CORE-006 | Importar la misma factura del mismo emisor y sociedad dos veces. | 409 DUPLICATE_DOCUMENT con referencia autorizada a original, sin otra deuda. |
| TC-SEC-001-P | SEC-001 | Usuario financiero con MFA accede a conciliación dentro de su sociedad. | Usuario sin segundo factor no ejecuta acciones protegidas |
| TC-SEC-001-N | SEC-001 | Token vencido/revocado o sin MFA intenta devolución. | 401/403 y ningun efecto; sesion puede reautenticarse. |
| TC-SEC-002-P | SEC-002 | Peticion válida muestra datos propios y proceso trazable. | Solicitud de acceso/supresion usa flujo trazable y respeta retenciones legales |
| TC-SEC-002-N | SEC-002 | Solicitante no verificado pide exportación de otra persona. | No entrega; verificar identidad por canal seguro sin revelar existencia. |
| TC-SEC-003-P | SEC-003 | Logs de pago contienen orden/correlacion y estado, no tarjeta. | Escaneo y pruebas no encuentran secretos en repo/evidencia |
| TC-SEC-003-N | SEC-003 | Subir clave API a código o incluir pasaporte en payload publicitario. | Bloqueo de pipeline/proceso, revocacion y evidencia saneada. |
| TC-SEC-006-P | SEC-006 | Mensaje malicioso se conserva como consulta y no cambia reglas. | Resenia maliciosa no cambia beneficiario ni ejecuta herramientas |
| TC-SEC-006-N | SEC-006 | Huésped ordena ignorar instrucciones, marcar pagado y enviar bancos. | Herramientas deniegan; bot deriva y no filtra datos. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
