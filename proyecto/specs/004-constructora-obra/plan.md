# Plan propuesto — Constructora y control de obra

Feature `004-constructora-obra` · 2026-10-16 · **BLOCKED**. Entrada: [spec.md](spec.md).

## Resumen y contexto técnico

WhatsApp, fotos y voz no confiables; presupuesto digital pendiente. Relación con 003 opcional por ID de correspondencia, sin acceso compartido a bases de datos.

La base Python 3.12/FastAPI, Next.js, PostgreSQL 16 y Redis figura como propuesta en CAF §6, HOT §6 e INM §6; no hay benchmark, repositorio previo, presupuesto ni decisión aprobada. No fijar versiones ni desplegar antes de ADR-003. Claude Agent SDK también es candidato, no dependencia seleccionada. Se propone web responsive y adaptadores por proveedor; hosting, residencia, modelo LLM, colas y almacenamiento quedan pendientes. Las escalas de las fuentes son supuestos, no dimensionamiento validado.

## Constitution Check

| Principio | Resultado documental | Gate de implementación |
|---|---|---|
| Core primero | Responsabilidades separadas, ADR-001 | Validar contratos y límites |
| Chile operativo | Política tributaria y vigencia legal identificadas | Q-CORE-02 pendiente |
| Autonomía gobernada | Política de denegación y aprobación definida | Límites comerciales pendientes |
| Seguridad y privacidad | Amenazas y pruebas propuestas | Retención, roles y revisión legal pendientes |
| Pruebas verificables | acceptance.md trazable a cada FR | No se ejecutaron pruebas de producto |
| Simplicidad y medición | Sin microservicios ni stack impuestos | Costos y línea base pendientes |

No se declara cumplido un gate por haber escrito una tabla. Las ampliaciones de constitución esperan ratificación según su gobernanza.

## Diseño, dependencias y amenazas

ProyectoObra → PresupuestoVersionado → Partida → Programación; ReporteAvance → Evidencia → Inspección; Material → Movimiento; SolicitudCompra → Aprobación; Subcontrato es candidato pendiente de alcance.

Reporte: recibido → extraído → revisión → aprobado/rechazado; solicitud: propuesta → aprobada/rechazada/expirada. Un cambio presupuestario no reescribe la línea base histórica.

Amenazas específicas: Evidencia manipulada, avance no comparable, órdenes indebidas y publicación de ubicación de trabajadores. Controles: autorización fuera del LLM, evidencia no confiable como datos, claves por tenant, acceso mínimo, deduplicación y revisión humana. Recuperación: reconciliar fuente de verdad, conservar intentos fallidos y aplicar compensación aprobada; una devolución o rectificación no es un borrado.

Consultar `../../docs/arquitectura/dependencias.md`, `seguridad.md` y ADR-001 a ADR-004. No se necesitan bases de datos compartidas entre verticales.

## Fases y estructura

Fase 0: resolver `Q-OBR-01: obras propias o terceros, presupuesto y módulo previo no entregado; Q-OBR-02: unidad del avance, calendario y umbral; Q-OBR-03: aprobadores, compras, seguridad e inspecciones.` y registrar decisiones. Fase 1: ratificar data-model.md y contratos lógicos con ejemplos válidos/erróneos. Fase 2: concretar tareas de desarrollo, pruebas previas e integración de sandbox. Esta entrega se detiene antes de implementar.

Código futuro en `verticales/constructora/`; hoy solo README de alcance. Artefactos presentes: spec, research, plan, data-model, quickstart, tasks, acceptance, contracts y checklists.

## Complexity Tracking

Se reduce el core original (catálogo, gastos y analítica quedan en dominios). Se elimina la dependencia obligatoria hotel→cafetería y obra→comercial mediante interfaces opcionales. No se justifica un proceso worker, Redis ni cuatro agentes separados como necesidad comprobada; evaluar aislamiento y costo antes de introducirlos.

## Consecuencias del refinamiento competitivo

Las historias US-OBR detallan estados y validaciones de negocio; los nuevos FR-019 y FR-020 no seleccionan proveedor o infraestructura. Cerrar exige rol; proponer solución no cierra. Cantidad recibida aceptada no excede pedido aprobado sin revisión de exceso. Convertir unidad requiere regla revisada; recibir no consume ni aumenta avance. Ubicación sugerida se diferencia de verificada.

Propiedad de datos: ÍtemInspección → Observación (abierta/asignada/solución propuesta/cerrada/reabierta) → EvidenciaSolución y AprobaciónCierre. SolicitudCompraVersionada → LíneaOrdenAprobada → RecepciónParcial → Discrepancia. CampoExtraído enlaza evidencia original y revisión. Mantener estos registros en el dominio; solo perfil de capacidad, correlación/auditoría y controles reutilizables residen en core. La transferencia humana de cada negocio no introduce un motor CRM global en 000. No hay nuevas dependencias obligatorias entre verticales ni ciclos. ADR-005 documenta impacto y alternativas; ADR-001/002/004 siguen propuestos.

Gate constitucional: principios I/III/IV/V/VI cubren límites, evidencia, mínimo privilegio, aceptación y recuperación; no se modifica constitución. Revisar políticas comerciales y validez de fuente antes de contratos ejecutables. Medir manual vs asistido con igual población; no prometer retorno por copiar un patrón de mercado.

## Impacto arquitectónico de la profundización

ParteTrabajo identifica autor, origen/turno/zona y fechas del hecho/recepción; ValorAvance distingue incremento/acumulado/rectificación y base versionada. Entrega/TramoOrden → RecepcionLinea con cantidades físicas aceptadas/rechazadas/devueltas y movimientos vinculados. ObligacionCosto referencia compromiso/devengo/pago, presupuesto y regla de cómputo. Observacion mantiene solución propuesta/revisión/rechazo/cierre y respuesta técnica autorizada.

Dos partes del mismo día no son duplicados por esa sola coincidencia. Los porcentajes acumulados no se suman. Rechazo/devolución no borra recepción ni crea abono financiero automático. El costo comprometido que contiene un devengo no se descuenta dos veces. Una respuesta técnica no autoriza un cambio de contrato/presupuesto ni certifica seguridad.

Mantener propiedad de datos en el dominio; core solo valida capacidades/efectos, evidencia y referencias comunes. No elegir motor workflow, cola, aplicación móvil o ERP por aparecer en un proveedor. Recuperación exige registrar estado conocido/desconocido y reconciliar antes de repetir; no requiere prometer una tecnología de persistencia concreta en esta etapa. ADR-006 compara alternativas y preserva dependencias del ADR-005. Constitución revisada sin modificaciones; gates pendientes siguen bloqueando implementación.
