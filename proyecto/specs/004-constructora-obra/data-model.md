# Modelo conceptual — Constructora y control de obra

Estado: **DRAFT** dentro de feature BLOCKED. No es esquema SQL ni migración.

## Entidades y relaciones

ProyectoObra → PresupuestoVersionado → Partida → Programación; ReporteAvance → Evidencia → Inspección; Material → Movimiento; SolicitudCompra → Aprobación; Subcontrato es candidato pendiente de alcance.

Toda entidad privada incorpora identidad estable, tenant propietario, estado, versión, autor y fechas con zona UTC; presentación Chile según configuración. Relaciones internas exigen misma pertenencia. Las relaciones entre empresas requieren convenio, finalidad y permiso explícitos; pertenecer al mismo grupo no autoriza acceso. No compartir datos personales en catálogos públicos.

## Invariantes

Cada reporte conserva versión previa y autor; retrocesos se registran como rectificación aprobada. Porcentaje entre 0 y 100 con denominador definido. Avance físico, gasto y pago son distintos. Ninguna compra ni certificación técnica se ejecuta desde una transcripción sin revisión.

## Ciclos de vida y concurrencia

Reporte: recibido → extraído → revisión → aprobado/rechazado; solicitud: propuesta → aprobada/rechazada/expirada. Un cambio presupuestario no reescribe la línea base histórica.

Las transiciones críticas comprueban versión y autorización en el límite del servicio. Un resultado financiero desconocido mantiene la reserva de idempotencia mientras se consulta al proveedor. La integración debe tolerar mensajes duplicados y desordenados; verificar estado vigente antes de aplicar.

## Evidencia, privacidad y pendientes

Adjuntos separados del modelo conversacional, con tipo/tamaño permitido y acceso temporal autorizado. Bitácora con integridad verificable y datos personales minimizados; no prometer inmutabilidad absoluta ni conservación infinita. Retención y borrado legal se aplican a datos y evidencias sin destruir conciliación exigible. RPO/RTO y plazos: Q-CORE-03.

Q-OBR-01: obras propias o terceros, presupuesto y módulo previo no entregado; Q-OBR-02: unidad del avance, calendario y umbral; Q-OBR-03: aprobadores, compras, seguridad e inspecciones.

## Refinamientos competitivos de entidades e invariantes

ÍtemInspección → Observación (abierta/asignada/solución propuesta/cerrada/reabierta) → EvidenciaSolución y AprobaciónCierre. SolicitudCompraVersionada → LíneaOrdenAprobada → RecepciónParcial → Discrepancia. CampoExtraído enlaza evidencia original y revisión.

Cerrar exige rol; proponer solución no cierra. Cantidad recibida aceptada no excede pedido aprobado sin revisión de exceso. Convertir unidad requiere regla revisada; recibir no consume ni aumenta avance. Ubicación sugerida se diferencia de verificada.

Toda nueva relación mantiene tenant, actor, versión y evidencia; no comparte datos del cliente entre empresas por aparecer en el mismo proveedor. Datos externos pueden estar incompletos: incertidumbre es atributo explícito, no valor cero o estado final. Los nombres son conceptuales; no hay esquema de proveedor observado ni persistencia seleccionada.

## Estados y relaciones de recuperación por dominio

ParteTrabajo identifica autor, origen/turno/zona y fechas del hecho/recepción; ValorAvance distingue incremento/acumulado/rectificación y base versionada. Entrega/TramoOrden → RecepcionLinea con cantidades físicas aceptadas/rechazadas/devueltas y movimientos vinculados. ObligacionCosto referencia compromiso/devengo/pago, presupuesto y regla de cómputo. Observacion mantiene solución propuesta/revisión/rechazo/cierre y respuesta técnica autorizada.

Dos partes del mismo día no son duplicados por esa sola coincidencia. Los porcentajes acumulados no se suman. Rechazo/devolución no borra recepción ni crea abono financiero automático. El costo comprometido que contiene un devengo no se descuenta dos veces. Una respuesta técnica no autoriza un cambio de contrato/presupuesto ni certifica seguridad.

Los nombres describen conceptos propios propuestos; no son tablas o componentes internos observados. Las invariantes se revisan con los AC nuevos y deben ratificarse antes de esquema técnico.
