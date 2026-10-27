# Plan técnico F08

Estado: PROPUESTA_TECNICA_PARA_REVISION. Baseline maestro 1.0; ADR-001 propone TypeScript/Next.js16/Node24/PostgreSQL17; versiones menores exactas y proveedor OIDC/hosting requieren D45. Este archivo no demuestra software existente.

## Componentes y frontera
Módulo `src/modules/alimentacion-espacios/` con `domain`, `application`, `infrastructure` y esquemas. Adaptadores no contienen reglas comerciales; UI consume servicios autorizados. Tests en `tests/F08/`. Las carpetas son destino propuesto, no archivos de aplicación incluidos.

## Secuencia de construcción
1. Validar requisitos FNB-001, FNB-002, FNB-003, FNB-004, FNB-005, SPA-001 y decisiones D10, D12, D23, D32; resolver sólo bloqueos del paquete y registrar los restantes.
2. Consumir contratos de F05, F06 y crear los tipos/modelos de `data-model.md`. No duplicar tablas globales de identidad, sociedad o dinero.
3. Escribir fixtures y pruebas negativas antes del handler; luego migraciones, dominio, permisos, adaptador y pantallas. Los datos reales no entran a repositorio.
4. Ejecutar los comandos/consultas definidos, verificar efectos atomicamente y producir eventos food.produced, breakfast.served, dinner.delivered, space.reserved.
5. Revisar contratos, vulnerabilidades, accesibilidad y regresión. Integrar sólo con evidencia y orden de trabajo autorizada.

## Transacciones, fechas e importes
Ingresar company_id desde sesion autorizada; comparar con recurso y aplicar RLS con rol no propietario. Dinero integer minor + moneda, cantidades decimal exacto, noches LocalDate, UTC para instantes. Para inventario bloquear filas tipo/noche ordenadas; registrar negocio y outbox en una transacción. Para dinero bloquear saldo y crear asignación sin exceder fuente. Claves externas únicas y reintentos con hash; nunca deduplicar por nombre/monto solamente. Una acción asincrona completa sólo al verificar su resultado.

## Permisos y superficie
Actores cocina;servicio desayuno;recepción;compras; ver `seguridad/permisos.csv`. Pantallas UI-23, UI-24, UI-25; no enviar campos ocultos al navegador. Cada mutacion necesita permiso de acción, revisión y aprobación cuando aplique. Tokens externos en gestor, no base ni logs planos.

## Interfaces y excepciones
Usar operaciones listadas en `contracts/interfaces.md`; respuestas 409 por conflicto, 412 por versión, 422 por regla, 503 si dependencia impide resolver. No reintentar cobro/compra externamente sin comprobar idempotencia/estado. Cada fallo termina con estado persistido, responsable, próximo intento o resolución manual.

## Dependencias de integración y salida
Prerequisitos de implementación: F05, F06. Capacidades necesarias para prueba integrada/activacion: F06; no son orden circular de escritura de código. F21 aporta controles desde F00 y verifica cada release, no se posterga seguridad al final.

## Pruebas, migración y recuperación
Ejecutar `acceptance.md`; carga de prueba objetivo por M22, alteraciones de permisos, repeticion de eventos, horas locales y archivos duplicados. Migraciones expandir -> backfill -> verificar -> endurecer, con plan de recuperación preservando hechos externos. No borrar cobros para revertir una versión. Evidencia por build y entorno, suite ejecutada/no ejecutada y limitaciones.

## Despliegue
Feature flag apagado por defecto para proveedores/opciones no validadas; entorno ensayo antes de producción. Métricas: fallos del módulo, latencia, eventos pendientes, conflictos y saldos no conciliados cuando aplique. Runbook asignado a responsable real antes de apertura. El agente no ejecuta despliegue ni gastos por recibir este plan.
