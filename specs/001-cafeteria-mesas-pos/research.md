# Investigación de diseño — Cafetería

Estado: propuesta fundamentada parcialmente; no es decisión de compra. Base: [investigación transversal](../../docs/investigacion/estado-del-arte.md), [matriz de evidencia](../../docs/investigacion/matriz-evidencia.md).

## Contexto y alternativas

Carta digital existente, exportaciones Eleventa, Webpay, SII y WhatsApp; muestras y credenciales no entregadas.

1. Adaptar un sistema de registro existente: reduce migración y exige API, exportación, licencias y garantías de servicio verificables.
2. Construir el dominio: mayor control, pero asume costo operativo, conciliación y mantenimiento. No aprobar sin inventario real y costo total.
3. Comenzar con apoyo de lectura y borradores: menor riesgo, permite línea base; no prometer automatización de escritura hasta demostrar autorización e idempotencia.

Recomendación provisional: inventariar operación y evaluar adaptadores antes de reemplazar sistemas. No se han probado credenciales, APIs de cliente ni proveedores. Precios, ROI y ausencia de competidores de INV son declaraciones no verificadas y no justifican decisiones.

## Evidencia faltante y experimento

Q-CAF-01: momento de pago y propina; Q-CAF-02: convivencia Eleventa y alcance offline; Q-CAF-03: carta, exportaciones, responsables de compras y sesión de cliente.

Solicitar muestra minimizada de datos y reglas aprobadas; documentar estructura, cobertura, duplicados y datos ausentes. Comparar dos alternativas con costo mensual completo, esfuerzo, recuperación y portabilidad; ejecutar luego una prueba de sandbox autorizada. Salida: ADR con evidencia, riesgos, responsable y criterios de reversión.

Las métricas y fórmulas están en `../../docs/arquitectura/economia.md`; no hay valores observados. Booking exige proceso de acceso; Airbnb publica partners pero eso no prueba acceso API; Meta no fue accesible en esta revisión. No inferir capacidad de escritura a partir de que un proveedor diga usar MCP.

## Investigación competitiva incorporada — 2026-10-16

Fuentes específicas: C02, C04, C05, C07, C08, C09, C10; [matriz verificable](../../docs/investigacion-competitiva/matriz-evidencias.md). Los flujos son reconstrucción documental; no hubo REA operativo ni prueba UI. Ver [metodología](../../docs/investigacion-competitiva/metodologia.md). La existencia de capacidad competidora no demuestra demanda propia.

Recomendaciones: adoptar estados, validaciones y casos borde como propuestas, sin replicar código, límites regionales ni reglas fiscales ajenas. En particular: No mover parte ya liquidada; para corrección usar flujo de ajuste aprobado. El total de cocina no cambia al dividir financieramente. Una reejecución de la misma regla/ventana/evento conserva identidad de detección.

Alternativas: adaptar sistema actual si el conector soporta la operación y el plan lo habilita; captura manual controlada si no hay integración; construir solo el límite propio justificado por el negocio. Se mantiene build/buy pendiente. No se infieren endpoints, arquitecturas o garantías externas.

## Identidad de plataforma y aplicabilidad territorial

Referencia principal Fudo Chile: https://fu.do/es-cl/ y producto https://fu.do/es-cl/tu-gestion/ (C11/C12), aportada por el usuario y abierta. El manual C02 es fuente auxiliar histórica; no habilita terminal ni reglas de país por sí mismo. WebPay, SII, API, cierre parcial y recetas son capacidades declaradas por el producto regional, pendientes de validar por plan, canal y cuenta. Evaluar adaptar Fudo/Toteat frente a reemplazar POS; no se selecciona proveedor ni se prometen contratos disponibles.
