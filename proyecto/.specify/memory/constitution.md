# Constitución compartida — plataforma-salman

Versión propuesta **1.1.0**, 2026-10-16. Base: CAF §1, versión declarada 1.0.0 del 2026-10-15. **Ratificación pendiente por Cristóbal Herrera** conforme a la gobernanza original. Única constitución del proyecto; los planes la referencian, no la duplican.

## I. Core primero, vertical después

Conservar la intención original de reutilización. Identidad, autorización, límites de tenant, adaptadores de pagos/documentos/comunicación y evidencia de auditoría son compartidos. Catálogo gastronómico, recetas, inventario, gastos del local, cuenta hotelera, CRM y presupuesto de obra pertenecen al dominio. Compartir una abstracción solo con al menos dos usos concretos o exigencia transversal de seguridad. No convertir transacciones de negocio heterogéneas en un motor universal.

## II. Chile como requisito operativo

Conservar pesos chilenos, presentación local y medios de pago/documentos aplicables. CLP se cobra en unidades enteras; cálculos internos de costo y conversiones desde UF requieren precisión y reglas de redondeo ratificadas. El documento tributario depende de la operación, contribuyente y modalidad declarada; no se emite automáticamente una segunda boleta si el comprobante ya cumple la función tributaria. Anticipos, reservas y liquidaciones necesitan política revisada por responsable tributario. Separar aprobación bancaria, emisión, aceptación y entrega documental.

## III. Agentes con autonomía explícitamente gobernada

Conservar la declaración de herramientas, acciones, aprobación y monto. Sin política autorizada el agente solo informa o prepara borradores. Denegación por defecto y límite autónomo monetario inicial **0 CLP** para compromisos; es control preventivo de diseño, no umbral comercial acordado. Modelo sin secretos ni credenciales de escritura. MCP no otorga permisos. Aprobaciones humanas verificadas, ligadas a operación y parámetros, con caducidad y uso único. Operaciones financieras, tributarias y contractuales pasan por servicio determinista, revisión y conciliación.

## IV. Seguridad y privacidad desde la especificación

Conservar modelo de amenazas y evaluación adversarial previa al cierre. Tenant derivado de identidad, mínimo privilegio en servicios, colas, búsquedas, adjuntos, analítica y backups. Empresas del mismo grupo permanecen separadas. Registrar finalidad, base de tratamiento, responsable/encargado, destinatarios, residencia, retención y derechos; no afirmar que C4A es siempre encargado. A fecha de esta auditoría, planificar régimen vigente Ley 19.628 y transición de Ley 21.719 al 01-12-2026, con validación jurídica contextual. Secretos fuera de prompts/repositorio, rotación y acceso auditado.

## V. Pruebas y criterios de aceptación verificables

Conservar Given/When/Then, pruebas antes de implementación y datos representativos para validar resultados. El original prohíbe dato sintético en demos a cliente; se conserva esa regla hasta que su responsable apruebe cambio. Demos con datos reales requieren autorización y minimización; si no existen, bloquear la demo. Pruebas automatizadas y adversariales sí pueden usar datos sintéticos identificados como tales, sin presentarlos como evidencia de rendimiento real. Definir denominadores, muestras, línea base y tolerancias. No declarar medido un objetivo ni verificada una integración sin prueba.

## VI. Simplicidad, observabilidad y medición de resultados

Conservar YAGNI, logs estructurados y métricas. Evaluar una aplicación por vertical como propuesta, no obligación de despliegues separados sin evidencia. Auditoría con actor, empresa, correlación, acción, parámetros minimizados, política, aprobación, evidencia y resultado, con integridad verificable y retención controlada. Evitar promesas de inmutabilidad absoluta. Idempotencia en efectos financieros y tributarios, contratos versionados y recuperación por conciliación. Definir RPO/RTO antes de producción; probar restauración y fallos parciales.

## Gobernanza y ampliaciones

El cambio se propone como MINOR por ampliaciones, pero modifica alcance del core y matiza emisión tributaria: el responsable puede exigir MAJOR al ratificar. No se afirma aprobación inexistente. Toda modificación incluye evidencia, versión, impacto, migración y aprobación de Cristóbal Herrera. Una violación crítica bloquea implementación; una decisión comercial pendiente no se resuelve con un supuesto técnico.

Registro de ampliaciones: aislamiento y mínimo privilegio (I/IV), fiscalidad idempotente (II/VI), secretos (III/IV), recuperación y contratos (VI), revisión humana y prevención de prompt injection (III/IV), evaluación de costo y precisión (V/VI). Los seis principios originales se conservan; el texto literal sigue en CAF §1 bajo docs/originales. Hallazgos F-001, F-002 y F-011 explican los matices propuestos.
