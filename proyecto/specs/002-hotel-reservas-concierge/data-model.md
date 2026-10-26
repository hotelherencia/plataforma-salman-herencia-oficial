# Modelo conceptual — Hotel

Estado: **DRAFT** dentro de feature BLOCKED. No es esquema SQL ni migración.

## Entidades y relaciones

Propiedad → TipoHabitación → Habitación; Reserva → OcupaciónPorFecha; Tarifa → PolíticaCancelación; Huésped → CuentaEstadía → Cargo; TareaOperativa; ConexiónCanal y ConflictoSincronización.

Toda entidad privada incorpora identidad estable, tenant propietario, estado, versión, autor y fechas con zona UTC; presentación Chile según configuración. Relaciones internas exigen misma pertenencia. Las relaciones entre empresas requieren convenio, finalidad y permiso explícitos; pertenecer al mismo grupo no autoriza acceso. No compartir datos personales en catálogos públicos.

## Invariantes

Una habitación bloqueada por mantenimiento no admite asignación. No hay ocupaciones confirmadas incompatibles para la misma fecha/recurso. La cuenta no vuelve a tributar un anticipo ya documentado. Inventario y estado de limpieza son conceptos distintos.

## Ciclos de vida y concurrencia

Reserva: propuesta → retenida temporalmente → confirmada/cancelada/expirada; duraciones y compensaciones requieren política. Sincronización: pendiente → confirmada/conflicto; no vender inventario incierto sin cupo seguro aprobado.

Las transiciones críticas comprueban versión y autorización en el límite del servicio. Un resultado financiero desconocido mantiene la reserva de idempotencia mientras se consulta al proveedor. La integración debe tolerar mensajes duplicados y desordenados; verificar estado vigente antes de aplicar.

## Evidencia, privacidad y pendientes

Adjuntos separados del modelo conversacional, con tipo/tamaño permitido y acceso temporal autorizado. Bitácora con integridad verificable y datos personales minimizados; no prometer inmutabilidad absoluta ni conservación infinita. Retención y borrado legal se aplican a datos y evidencias sin destruir conciliación exigible. RPO/RTO y plazos: Q-CORE-03.

Q-HOT-01: PMS actual y fuente de inventario; Q-HOT-02: acceso OTA/channel manager; Q-HOT-03: habitaciones, cancelación, anticipos, datos de registro y autonomía.

## Refinamientos competitivos de entidades e invariantes

CupoPorFechaTipo separado de AsignaciónHabitación y Preparación (limpieza, inspección opcional, bloqueo técnico). OfertaVersionada → EvidenciaCanal (referencia externa, último estado confirmado, antigüedad). Atención → TransferenciaHumana.

Una habitación limpia puede seguir no asignable por mantenimiento; una habitación sucia hoy puede contribuir al inventario futuro según reglas aprobadas. Trasladar atención no confirma cancelación ni resuelve conversación. Fuente sin vigencia definida bloquea compromiso automático.

Toda nueva relación mantiene tenant, actor, versión y evidencia; no comparte datos del cliente entre empresas por aparecer en el mismo proveedor. Datos externos pueden estar incompletos: incertidumbre es atributo explícito, no valor cero o estado final. Los nombres son conceptuales; no hay esquema de proveedor observado ni persistencia seleccionada.

## Estados y relaciones de recuperación por dominio

PropuestaCambioReserva → versionBase/desglose/aceptación → ResultadoCambio. Cancelación referencia una SolicitudDevolucion independiente. CargoEstadia referencia reglaCantidad/período/cuenta y TareaCumplimiento. RecepcionEventoCanal conserva ID notificación, reserva externa, huella, origen, recepción durable, estado aplicación y cursor.

La identidad de reserva externa no basta para deduplicar sus cambios. Acusar receipt no equivale a aplicar ni aceptar comercialmente. No modificar precio aceptado sin nueva revisión. Reserva, devolución, cargo, pago y tarea tienen transiciones propias; el tenant y contribuyente son explícitos en referencias.

Los nombres describen conceptos propios propuestos; no son tablas o componentes internos observados. Las invariantes se revisan con los AC nuevos y deben ratificarse antes de esquema técnico.


Nota de protocolo: acuse de recepción y aceptación/aplicación se separan conceptualmente, pero el punto de acuse debe respetar el contrato real del canal. El ID de notificación externo se usa solo si el proveedor lo define; sin él, la clave/huella y recuperación requieren investigación, sin inventar campos ni deduplicar todos los cambios por ID de reserva.
