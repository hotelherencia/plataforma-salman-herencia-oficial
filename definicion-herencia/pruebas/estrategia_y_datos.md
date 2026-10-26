# Plan de verificación

Existen 306 casos por requisito (153positivos/153negativos), mas 48 escenarios de integración heredados desarrollados. Hay superposicion intencional entre niveles; no sumar casos como porcentaje de cobertura. Ninguno se ejecuto contra aplicación porque no hay software implementado en esta entrega. Las pruebas documentales de referencias son otra categoría.

## Niveles
Unitarias: precios,redondeos,capacidad,incentivos,reglas de estados y distribución. Integración: base real de ensayo y RLS,locks,outbox/inbox,importaciones,migraciones. Contratos: schemas,errores,compatibilidad de adaptadores y mocks rotulados. Extremo a extremo: red/enlace,reserva,pago,recepcion,servicios,caja,conciliacion. Seguridad: permisos de filas/columnas,CSRF,identidad,inyeccion,secretos. Continuidad:caida modelo/proveedor,cola,restauracion con hechos externos. UX: teclado/lector,dispositivo móvil,navegador interno.

## Fixture base
SociedadDEMO-HERENCIA y DEMO-OTRA con usuarios separados. Habitaciones de pruebaR01..R17, distribución ficticia 7 individuales,7 dobles,3 triples SÓLO para test; no afirma configuración real. Capacidad sintética calculada desde la configuración 7*1+7*2+3*3=30 plazas. Los identificadores,personas,email.example.invalid y tarifas son sintéticos. Nunca usar planillas de 2019 como fixture de PII.

Los casos relevantes modifican fixture: último cupo 1; cuota vencida; pago 100000; transferencia igual legitima; lote 2 sábanas retorna 1; compra 20 recibe 12; desayuno 10 sirve 8; derechos 2 personas 2 noches; traslado dehabitacion; código deusuariootra sociedad; creación de reserva en fecha de cambio horario.

## Evidencia requerida
IDcaso,versionmaestro,commit/build,entorno,dataset,versionadaptador,comando real,fecha,resultado PASS/FAIL/SKIPPED,motivo,evidencia y revisor. Resultado externo sólo real si cuenta y permiso comprobados; sandboxno producción. Un caso sin step implementado sigue NO_EJECUTADO. FallaP0 bloquea capacidad activa; opción apagada se declara no construida/no probada.

## Evaluaciones operativas
Validar guiones con recepción,aseo,cocina,contador y propietario. Todos los recorridos incluyen variante sin permisos y fallas; un formulario bonito no prueba cierres de banco. El revisor se designaD42 y no se inventa independencia. NativeSpecKit,tests de app,penetracion y recuperación real siguen pendientes de construcción.
