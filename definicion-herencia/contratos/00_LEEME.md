# Contratos API propios

OpenAPI 3.1.1 contiene operaciones de comandos/consultas con payloads cerrados. Son contratos propuestos para nuestra aplicación, no una integración desplegada. Las listas ResourceSummary son proyecciones mínimas: las pantallas detalladas leen proyecciones autorizadas descritas en ux/pantallas.csv y modelos; no exponer entidades completas por serializacion automática.

## Consistencia y errores
Idempotency-Key se evalua por sociedad, actor, operación y hash del cuerpo. Repeticion identica devuelve el mismo recurso; payload distinto 409. La retención de claves debe cubrir reintentos y liquidaciones; propuesta 30 días para comandos, eventos financieros conservan referencia única durante retención aprobada. El header If-Match usa versión del recurso; 412 no reintenta escritura sin releer. Errores de negocio 422 incluyen código estable; inventario agotado 409 AVAILABLE_CAPACITY_EXCEEDED.

El usuario no proporciona company_id para flujos públicos: property_slug resuelve un establecimiento y sociedad activa en servidor. Los tokens públicos nunca habilitan APIs administrativas. Las operaciones que escriben montos validan origen, autorización y moneda. Limitar payload y uso antes de ejecutar consultas costosas.

## Lecturas y datos personales
Cada GET aplica permisos de columna y fila; la matriz de roles y ux define su proyección. Paginacion cursor estable con id/fecha y máximo 100; filtros permitidos: período, estado, unidad, tipo y canal segun recurso. Los exportadores requieren permiso adicional y evento de auditoría. Archivos grandes se entregan por URL firmada de vigencia corta y una finalidad, no por enlace público permanente.

## Catálogos y lectura detallada
`readAuthorizedRecord` entrega proyecciones tipadas por recurso, con permiso de entidad y política de columnas. La lista cerrada de campos esta en `proyecciones_lectura.csv`; los datos anidados tienen esquema en `modelos/esquemas_json.json`. Este endpoint es sólo lectura y no ofrece un CRUD que permita cambiar estados. Los comandos sensibles tienen rutas específicas. Los catálogos se crean mediante los comandos del dominio de su paquete, con campos y validaciones definidos en el diccionario y reglas del requisito; no convertir campos como status, approval o totals en escritura libre.

## Firma externa
El gateway verifica bytes originales con el esquema real del proveedor, limita replay y normaliza ExternalEnvelope. Este envelope se usa entre adaptador y dominio. Un proveedor con retorno/confirmacion como Webpay se confirma servidor a servidor; no convertirlo en un webhook ficticio. Secretos y tokens no se almacenan en documentos ni payload normalizado.
