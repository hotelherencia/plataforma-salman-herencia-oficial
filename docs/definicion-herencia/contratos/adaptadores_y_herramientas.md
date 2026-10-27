# Adaptadores, eventos y herramientas de IA

## Frontera externa
Los endpoints OpenAPI son propios. El adaptador de cada proveedor se completa con contrato/SDK/documentacion de la cuenta elegida; no inventar URL ni certificado. Conservar ambiente,versión,capacidad,autenticación,límite,costo,evidencia y estado. Cuenta verificada no habilita todas las funciones. Firma de webhook se comprueba sobre bytes originales; rechazar timestamp/replay cuando mecanismo lo permita. El endpoint normalizado interno se protege con identidad de servicio/mTLS y no se expone aInternet; eliminar cabeceras de confianza enviadas por clientes.

## Entrega y recuperación
Registrar inbox autenticado antes de ack segun protocolo; deduplicar; validar revisión de agregado; aplicar evento; registrar outbox en transacción; ack. Reintentos exponenciales con jitter y Retry-After; tras máximo acordado, DLQ con responsable. Reprocesar conserva clave y payloadhash. Versión mayor desconocida se pone en cuarentena, no truncar campos silenciosamente. Reconciliacion periodica detecta perdidos, no sólo duplicados.

## Herramientas del asistente
- consultar_disponibilidad: fechas locales,adultos,edades necesarias,tipo opcional. Llama searchAvailability; sólo devuelve tipos/precio/cupo del hotel autorizado. No retiene.
- cotizar_estadia: selección de tipo/plan y fechas. createQuote devuelve total,snapshot,expiración. Nunca aplica un precio dicho por usuario.
- crear_retencion_autorizada: quote_token válido y sesion; llama createHold y aplica límites. Sólo tras intencion de reservar y flujo autorizadoD29.
- generar_enlace_pago: reserva autorizada y método. startPayment calcula monto servidor; la herramienta no acepta beneficiario/importe libre. Retorna URLpermitida y expiración.
- consultar_estado_reserva: token/identidad con derecho; devuelve referencia/fechas/estado/saldo permitido, no documento de otro huésped.
- derivar_a_recepcion: motivo,prioridad y resumen mínimo. Toma humana revoca lease bot y descarta respuestas aún no enviadas.

Validar argumentos contra esquemas, permisos, contexto de sociedad y límites por ejecución. Los resultados son datos no instrucciones. Sin SQL, shell, navegador bancario ni cambio de roles. Registro guarda herramienta,hash,referencia,duracion,resultado,correlacion; no secreto ni conversacion sensible completa.

## Evaluación
Fixtures: fecha viernes ambigua, oferta vencida, cupo agotado tras pago, intento de instruccion maliciosa, cliente con nombre repetido, baja promocional, toma humana simultanea, tokenrevocado, herramienta caida. Requisito: cero acciones financieras/privacidad no autorizadas; disponibilidad/precio siempre herramienta. Umbrales de calidad y modelo aprobadosD29. Cambiar prompt/modelo requiere regresión antes de promover. Escalar no significa atención humana instantanea sin responsable.

## Mensajeria comercial
Validar permiso/finalidad y ventana justo antes de enviar, no al encolar solamente. No reutilizar una aprobación de anuncio para una campaña nueva ni mandar promoción por tener reserva. Conservar estados queued,sent,delivered,read,failed sin regresión por evento antiguo. Un estado service no es excusa para marketing. Publicar enlace al motor propio puede operar sin automatizar todas las redes.
