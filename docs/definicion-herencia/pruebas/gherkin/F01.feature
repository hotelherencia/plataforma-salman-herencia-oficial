# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Sociedades, identidad, permisos y auditoría

  @CORE-001 @TC-CORE-001-P
  Escenario: TC-CORE-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Usuario de Herencia registra una reserva del hotel y consulta su unidad, sin ver SB.
    Entonces Un usuario de Herencia no puede registrar un cobro en SB sin permiso

  @CORE-001 @TC-CORE-001-N
  Escenario: TC-CORE-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cambiar company_id de la solicitud por SB conservando sesion Herencia.
    Entonces 403 y ninguna escritura ni existencia revelada; evento seguro de denegacion.

  @CORE-002 @TC-CORE-002-P
  Escenario: TC-CORE-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Participación histórica del 2018 permanece consultable después de cargar una versión respaldada.
    Entonces Una modificacion futura conserva porcentajes históricos

  @CORE-002 @TC-CORE-002-N
  Escenario: TC-CORE-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Ingresar dos participaciones activas que sumen 110%.
    Entonces 422 con detalle de total, sin modificar versión previa.

  @CORE-003 @TC-CORE-003-P
  Escenario: TC-CORE-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Aseo recibe sus tareas y estados de habitaciones, no cuenta ni sueldo.
    Entonces Aseo no puede consultar salarios, identidades o cuentas ajenas

  @CORE-003 @TC-CORE-003-N
  Escenario: TC-CORE-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Acceso directo por URL a una remuneracion usando token de aseo.
    Entonces 403 sin payload sensible; exportación tampoco habilitada.

  @CORE-004 @TC-CORE-004-P
  Escenario: TC-CORE-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Revertir un pago registrado conserva original y referencia al ajuste autorizado.
    Entonces Corregir un pago conserva original y reverso

  @CORE-004 @TC-CORE-004-N
  Escenario: TC-CORE-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Recepción intenta DELETE sobre pago de turno cerrado.
    Entonces 405/409; solicitar ajuste con aprobación, sin cambiar saldo.

  @CORE-005 @TC-CORE-005-P
  Escenario: TC-CORE-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos noches en cambio de horario siguen siendo dos y el precio no varia por cambio de cotizacion posterior.
    Entonces Cruce horario y cambio posterior no alteran noches ni precio pactado

  @CORE-005 @TC-CORE-005-N
  Escenario: TC-CORE-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Envio de importe con decimales no admitidos para moneda configurada o salida anterior a llegada.
    Entonces 422, sin redondeo silencioso ni reserva creada.

  @CORE-006 @TC-CORE-006-P
  Escenario: TC-CORE-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos proveedores distintos pueden tener factura folio 100 sin conflicto.
    Entonces Factura duplicada se detecta sin bloquear otra de diferente emisor

  @CORE-006 @TC-CORE-006-N
  Escenario: TC-CORE-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Importar la misma factura del mismo emisor y sociedad dos veces.
    Entonces 409 DUPLICATE_DOCUMENT con referencia autorizada a original, sin otra deuda.

  @SEC-001 @TC-SEC-001-P
  Escenario: TC-SEC-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Usuario financiero con MFA accede a conciliación dentro de su sociedad.
    Entonces Usuario sin segundo factor no ejecuta acciones protegidas

  @SEC-001 @TC-SEC-001-N
  Escenario: TC-SEC-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Token vencido/revocado o sin MFA intenta devolución.
    Entonces 401/403 y ningun efecto; sesion puede reautenticarse.

  @SEC-002 @TC-SEC-002-P
  Escenario: TC-SEC-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Peticion válida muestra datos propios y proceso trazable.
    Entonces Solicitud de acceso/supresion usa flujo trazable y respeta retenciones legales

  @SEC-002 @TC-SEC-002-N
  Escenario: TC-SEC-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Solicitante no verificado pide exportación de otra persona.
    Entonces No entrega; verificar identidad por canal seguro sin revelar existencia.

  @SEC-003 @TC-SEC-003-P
  Escenario: TC-SEC-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Logs de pago contienen orden/correlacion y estado, no tarjeta.
    Entonces Escaneo y pruebas no encuentran secretos en repo/evidencia

  @SEC-003 @TC-SEC-003-N
  Escenario: TC-SEC-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Subir clave API a código o incluir pasaporte en payload publicitario.
    Entonces Bloqueo de pipeline/proceso, revocacion y evidencia saneada.

  @SEC-006 @TC-SEC-006-P
  Escenario: TC-SEC-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Mensaje malicioso se conserva como consulta y no cambia reglas.
    Entonces Resenia maliciosa no cambia beneficiario ni ejecuta herramientas

  @SEC-006 @TC-SEC-006-N
  Escenario: TC-SEC-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Huésped ordena ignorar instrucciones, marcar pagado y enviar bancos.
    Entonces Herramientas deniegan; bot deriva y no filtra datos.
