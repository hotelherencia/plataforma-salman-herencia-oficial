# Modelo conceptual — Cafetería

Estado: **DRAFT** dentro de feature BLOCKED. No es esquema SQL ni migración.

## Entidades y relaciones

Mesa → Pedido → Ítem; Producto → Receta → Insumo; Compra → MovimientoStock; Gasto → Evidencia. Pedido referencia pagos del core, no replica el estado bancario.

Toda entidad privada incorpora identidad estable, tenant propietario, estado, versión, autor y fechas con zona UTC; presentación Chile según configuración. Relaciones internas exigen misma pertenencia. Las relaciones entre empresas requieren convenio, finalidad y permiso explícitos; pertenecer al mismo grupo no autoriza acceso. No compartir datos personales en catálogos públicos.

## Invariantes

El total asignado a pagos no supera el saldo exigible; un ítem no se liquida dos veces. El movimiento de stock se deduplica por venta y versión de receta. Sin receta el margen es desconocido, no cero. El momento de consumo de stock queda pendiente de Q-CAF-01.

## Ciclos de vida y concurrencia

Pedido: borrador → enviado → preparado → servido; anulación exige rol y evidencia. Compra: pendiente → aprobada/rechazada. El cierre de mesa exige saldo cero y conciliación; la emisión tributaria tiene estado independiente.

Las transiciones críticas comprueban versión y autorización en el límite del servicio. Un resultado financiero desconocido mantiene la reserva de idempotencia mientras se consulta al proveedor. La integración debe tolerar mensajes duplicados y desordenados; verificar estado vigente antes de aplicar.

## Evidencia, privacidad y pendientes

Adjuntos separados del modelo conversacional, con tipo/tamaño permitido y acceso temporal autorizado. Bitácora con integridad verificable y datos personales minimizados; no prometer inmutabilidad absoluta ni conservación infinita. Retención y borrado legal se aplican a datos y evidencias sin destruir conciliación exigible. RPO/RTO y plazos: Q-CORE-03.

Q-CAF-01: momento de pago y propina; Q-CAF-02: convivencia Eleventa y alcance offline; Q-CAF-03: carta, exportaciones, responsables de compras y sesión de cliente.

## Refinamientos competitivos de entidades e invariantes

AsignaciónCuenta → ParteSaldo (ítems/importes, redondeo, descuento y propina separada) → IntentoPago. EjecuciónRegla → Detección → Propuesta/Alerta → Revisión.

No mover parte ya liquidada; para corrección usar flujo de ajuste aprobado. El total de cocina no cambia al dividir financieramente. Una reejecución de la misma regla/ventana/evento conserva identidad de detección.

Toda nueva relación mantiene tenant, actor, versión y evidencia; no comparte datos del cliente entre empresas por aparecer en el mismo proveedor. Datos externos pueden estar incompletos: incertidumbre es atributo explícito, no valor cero o estado final. Los nombres son conceptuales; no hay esquema de proveedor observado ni persistencia seleccionada.
