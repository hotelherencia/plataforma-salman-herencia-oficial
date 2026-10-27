# Investigación de diseño — Core transversal

Estado: propuesta fundamentada parcialmente; no es decisión de compra. Base: [investigación transversal](../../docs/investigacion/estado-del-arte.md), [matriz de evidencia](../../docs/investigacion/matriz-evidencia.md).

## Contexto y alternativas

Webpay/Transbank, SII/proveedor documental y canal de comunicación mediante adaptadores, sin herramientas financieras directas al modelo.

1. Adaptar un sistema de registro existente: reduce migración y exige API, exportación, licencias y garantías de servicio verificables.
2. Construir el dominio: mayor control, pero asume costo operativo, conciliación y mantenimiento. No aprobar sin inventario real y costo total.
3. Comenzar con apoyo de lectura y borradores: menor riesgo, permite línea base; no prometer automatización de escritura hasta demostrar autorización e idempotencia.

Recomendación provisional: inventariar operación y evaluar adaptadores antes de reemplazar sistemas. No se han probado credenciales, APIs de cliente ni proveedores. Precios, ROI y ausencia de competidores de INV son declaraciones no verificadas y no justifican decisiones.

## Evidencia faltante y experimento

Q-CORE-01: empresas, roles y autorización entre empresas; Q-CORE-02: tratamiento fiscal y proveedor DTE por contribuyente; Q-CORE-03: responsables de datos, retención, recuperación, presupuesto y autonomía.

Solicitar muestra minimizada de datos y reglas aprobadas; documentar estructura, cobertura, duplicados y datos ausentes. Comparar dos alternativas con costo mensual completo, esfuerzo, recuperación y portabilidad; ejecutar luego una prueba de sandbox autorizada. Salida: ADR con evidencia, riesgos, responsable y criterios de reversión.

Las métricas y fórmulas están en `../../docs/arquitectura/economia.md`; no hay valores observados. Booking exige proceso de acceso; Airbnb publica partners pero eso no prueba acceso API; Meta no fue accesible en esta revisión. No inferir capacidad de escritura a partir de que un proveedor diga usar MCP.

## Investigación competitiva incorporada — 2026-10-16

Fuentes específicas: C04, C06, H01, H10, I06, I07, I10; [matriz verificable](../../docs/investigacion-competitiva/matriz-evidencias.md). Los flujos son reconstrucción documental; no hubo REA operativo ni prueba UI. Ver [metodología](../../docs/investigacion-competitiva/metodologia.md). La existencia de capacidad competidora no demuestra demanda propia.

Recomendaciones: adoptar estados, validaciones y casos borde como propuestas, sin replicar código, límites regionales ni reglas fiscales ajenas. En particular: No retroceder resultado conciliado por un mensaje antiguo. Una devolución posterior es transición de negocio autorizada, no un evento antiguo ignorado. Si no hay secuencia confiable, consultar autoridad y marcar incertidumbre, sin deducir orden por timestamp.

Alternativas: adaptar sistema actual si el conector soporta la operación y el plan lo habilita; captura manual controlada si no hay integración; construir solo el límite propio justificado por el negocio. Se mantiene build/buy pendiente. No se infieren endpoints, arquitecturas o garantías externas.

## Profundización: reglas, excepciones y fuentes efectivas

Fuentes nuevas y previas pertinentes: H13, H15, I11, I17. Análisis funcional detallado en [continuación](../../docs/investigacion-competitiva/continuacion-01/alcance-y-evidencia.md) y fichas verticales. No se validan integraciones por encontrar una URL: I17 muestra un placeholder, I18/I19 y O15 tienen acceso incompleto, H17 corresponde a Channels Plus y no prueba el conector PMS requerido. Mantener estas diferencias al comparar construir/adaptar/contratar.

Los casos RF-CORE-01 separan estados que antes podían confundirse. Recomendación: revisar contratos y reglas con operador real; exigir origen, límites por versión y muestra de error/recuperación. Ningún nuevo FR implica contratar un proveedor, implementar un optimizador o adoptar su arquitectura.
