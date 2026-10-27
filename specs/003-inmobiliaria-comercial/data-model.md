# Modelo conceptual — Inmobiliaria comercial

Estado: **DRAFT** dentro de feature BLOCKED. No es esquema SQL ni migración.

## Entidades y relaciones

ProyectoComercial → Unidad → PrecioVersionado; Lead → Contacto → Visita; Cotización → ReservaUnidad → Promesa; CalendarioPagos → Cuota; SolicitudPostventa. Unidad referencia opcionalmente un proyecto de obra mediante correspondencia autorizada.

Toda entidad privada incorpora identidad estable, tenant propietario, estado, versión, autor y fechas con zona UTC; presentación Chile según configuración. Relaciones internas exigen misma pertenencia. Las relaciones entre empresas requieren convenio, finalidad y permiso explícitos; pertenecer al mismo grupo no autoriza acceso. No compartir datos personales en catálogos públicos.

## Invariantes

Una unidad solo tiene una reserva vigente confirmada; cotizar no bloquea. Precio de cotización queda versionado. No fusionar personas solo por nombre o teléfono sin verificación. Una garantía no se deniega automáticamente. Promesa exige versión legal aprobada y evidencia de firma.

## Ciclos de vida y concurrencia

Unidad: disponible → reservada → promesada → escriturada; expiración y devolución solo mediante política pendiente. Postventa: recibida → clasificada provisionalmente → asignada → resuelta → validada por humano/cliente.

Las transiciones críticas comprueban versión y autorización en el límite del servicio. Un resultado financiero desconocido mantiene la reserva de idempotencia mientras se consulta al proveedor. La integración debe tolerar mensajes duplicados y desordenados; verificar estado vigente antes de aplicar.

## Evidencia, privacidad y pendientes

Adjuntos separados del modelo conversacional, con tipo/tamaño permitido y acceso temporal autorizado. Bitácora con integridad verificable y datos personales minimizados; no prometer inmutabilidad absoluta ni conservación infinita. Retención y borrado legal se aplican a datos y evidencias sin destruir conciliación exigible. RPO/RTO y plazos: Q-CORE-03.

Q-INM-01: proyectos, CRM y captura autorizada de leads; Q-INM-02: reserva, vigencia y reembolsos; Q-INM-03: revisión legal de promesa y firma; Q-INM-04: garantías y responsables.

## Refinamientos competitivos de entidades e invariantes

Contacto separado de ConsultaOrigen y de DeclaraciónCalificación (campo, fuente, fecha, confianza). Cita (propuesta/confirmada/cancelada) → CotizaciónVersionada → ReservaUnidad → EvidenciaFirma/Promesa. AtenciónPostventa con responsable, transferencia y reapertura.

No fusionar identidad por coincidencia única. Una promesa requiere firma y versión aprobada; un resultado del modelo no acredita financiamiento. Cambio de destinatario invalida permiso de envío privado hasta revalidación.

Toda nueva relación mantiene tenant, actor, versión y evidencia; no comparte datos del cliente entre empresas por aparecer en el mismo proveedor. Datos externos pueden estar incompletos: incertidumbre es atributo explícito, no valor cero o estado final. Los nombres son conceptuales; no hay esquema de proveedor observado ni persistencia seleccionada.

## Estados y relaciones de recuperación por dominio

Cita incorpora modoAgenda, zona/offset, duración, propuesta/confirmación y referencia externa; SolicitudCambio conserva ambas referencias. PromesaVersion referencia plantilla legal/huella/participantes y evidencias por firmante. Persona no es VinculoUnidad: este tiene vigencia, rol y permisos del portal. CasoPostventa vincula visitas, trabajos, aceptación y reapertura.

Firma parcial no es documento completado. Corrección de Persona no reasigna ninguna unidad y la reasignación de acceso no transfiere dominio legal. Permiso de lectura de documentos se revalida por vínculo vigente, incluso para enlace/sesión previos; el acceso histórico tiene política pendiente. El envío de información desde guardar contacto necesita intención autorizada.

Los nombres describen conceptos propios propuestos; no son tablas o componentes internos observados. Las invariantes se revisan con los AC nuevos y deben ratificarse antes de esquema técnico.
