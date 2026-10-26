# Modelo conceptual — Core transversal

Estado: **DRAFT** dentro de feature BLOCKED. No es esquema SQL ni migración.

## Entidades y relaciones

Tenant → Membresía ← Identidad; Rol → Permiso; IntentoPago → ResultadoProveedor; ObligaciónDocumental → DocumentoTributario; AcciónAuditada → Evidencia; PolíticaAgente → Aprobación; ReferenciaNegocio opaca, sin copiar entidades verticales.

Toda entidad privada incorpora identidad estable, tenant propietario, estado, versión, autor y fechas con zona UTC; presentación Chile según configuración. Relaciones internas exigen misma pertenencia. Las relaciones entre empresas requieren convenio, finalidad y permiso explícitos; pertenecer al mismo grupo no autoriza acceso. No compartir datos personales en catálogos públicos.

## Invariantes

Toda referencia de negocio y relación interna pertenece al mismo tenant salvo vínculo explícito autorizado. El tenant se deriva de identidad verificada, no de una instrucción del modelo. Una clave de idempotencia se vincula a tenant, operación y huella de solicitud; distinto contenido se rechaza. Montos en moneda explícita; CLP entero no obliga a redondear cálculos internos de costo o UF.

## Ciclos de vida y concurrencia

Pago: iniciado → pendiente → autorizado/rechazado/desconocido; desconocido requiere consulta y conciliación. Documento: pendiente → emitido/observado → regularizado; nunca borrar el rastro de rechazo. Aprobación: solicitada → aprobada/rechazada/expirada, vinculada a parámetros exactos.

Las transiciones críticas comprueban versión y autorización en el límite del servicio. Un resultado financiero desconocido mantiene la reserva de idempotencia mientras se consulta al proveedor. La integración debe tolerar mensajes duplicados y desordenados; verificar estado vigente antes de aplicar.

## Evidencia, privacidad y pendientes

Adjuntos separados del modelo conversacional, con tipo/tamaño permitido y acceso temporal autorizado. Bitácora con integridad verificable y datos personales minimizados; no prometer inmutabilidad absoluta ni conservación infinita. Retención y borrado legal se aplican a datos y evidencias sin destruir conciliación exigible. RPO/RTO y plazos: Q-CORE-03.

Q-CORE-01: empresas, roles y autorización entre empresas; Q-CORE-02: tratamiento fiscal y proveedor DTE por contribuyente; Q-CORE-03: responsables de datos, retención, recuperación, presupuesto y autonomía.

## Refinamientos competitivos de entidades e invariantes

PerfilConector (tenant, referenciaCuenta opaca, proveedor, país/plan opcionales, capacidades, permisos, revisión/versionado) → EvidenciaRevisión. EventoExterno (identidad proveedor, operación, recibido/ocurrido, correlación, estado) → Intento → CasoConciliación (motivo, responsable, resolución).

No retroceder resultado conciliado por un mensaje antiguo. Una devolución posterior es transición de negocio autorizada, no un evento antiguo ignorado. Si no hay secuencia confiable, consultar autoridad y marcar incertidumbre, sin deducir orden por timestamp.

Toda nueva relación mantiene tenant, actor, versión y evidencia; no comparte datos del cliente entre empresas por aparecer en el mismo proveedor. Datos externos pueden estar incompletos: incertidumbre es atributo explícito, no valor cero o estado final. Los nombres son conceptuales; no hay esquema de proveedor observado ni persistencia seleccionada.

## Estados y relaciones de recuperación por dominio

PerfilOperacion añade efectos explícitos por campo/flag, destinatarios permitidos, condiciones y versión revisada. IntencionEfecto separa solicitud/permiso/ejecución/resultado; no se almacena secreto ni aprobación en texto del modelo. EventoExterno referencia cuenta/propiedad autorizada sin permitir que el payload cambie tenant.

Una herramienta denominada guardar/consultar puede producir comunicación; denegar si el perfil no acredita todos sus efectos. Una revisión de perfil no transfiere aprobaciones antiguas a nuevos flags.

Los nombres describen conceptos propios propuestos; no son tablas o componentes internos observados. Las invariantes se revisan con los AC nuevos y deben ratificarse antes de esquema técnico.
