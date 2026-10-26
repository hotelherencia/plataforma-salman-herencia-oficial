# Plan propuesto — Hotel

Feature `002-hotel-reservas-concierge` · 2026-10-16 · **BLOCKED**. Entrada: [spec.md](spec.md).

## Resumen y contexto técnico

Comparar PMS existente con PMS nuevo; preferir evaluar channel manager autorizado antes de conectores directos. Servicio a habitación consume interfaz de pedidos opcional.

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

Propiedad → TipoHabitación → Habitación; Reserva → OcupaciónPorFecha; Tarifa → PolíticaCancelación; Huésped → CuentaEstadía → Cargo; TareaOperativa; ConexiónCanal y ConflictoSincronización.

Reserva: propuesta → retenida temporalmente → confirmada/cancelada/expirada; duraciones y compensaciones requieren política. Sincronización: pendiente → confirmada/conflicto; no vender inventario incierto sin cupo seguro aprobado.

Amenazas específicas: Sobreventa, datos de identidad, inventario obsoleto y modificación de reserva por suplantación. Controles: autorización fuera del LLM, evidencia no confiable como datos, claves por tenant, acceso mínimo, deduplicación y revisión humana. Recuperación: reconciliar fuente de verdad, conservar intentos fallidos y aplicar compensación aprobada; una devolución o rectificación no es un borrado.

Consultar `../../docs/arquitectura/dependencias.md`, `seguridad.md` y ADR-001 a ADR-004. No se necesitan bases de datos compartidas entre verticales.

## Fases y estructura

Fase 0: resolver `Q-HOT-01: PMS actual y fuente de inventario; Q-HOT-02: acceso OTA/channel manager; Q-HOT-03: habitaciones, cancelación, anticipos, datos de registro y autonomía.` y registrar decisiones. Fase 1: ratificar data-model.md y contratos lógicos con ejemplos válidos/erróneos. Fase 2: concretar tareas de desarrollo, pruebas previas e integración de sandbox. Esta entrega se detiene antes de implementar.

Código futuro en `verticales/hotel/`; hoy solo README de alcance. Artefactos presentes: spec, research, plan, data-model, quickstart, tasks, acceptance, contracts y checklists.

## Complexity Tracking

Se reduce el core original (catálogo, gastos y analítica quedan en dominios). Se elimina la dependencia obligatoria hotel→cafetería y obra→comercial mediante interfaces opcionales. No se justifica un proceso worker, Redis ni cuatro agentes separados como necesidad comprobada; evaluar aislamiento y costo antes de introducirlos.

## Consecuencias del refinamiento competitivo

Las historias US-HOT detallan estados y validaciones de negocio; los nuevos FR-016 y FR-017 no seleccionan proveedor o infraestructura. Una habitación limpia puede seguir no asignable por mantenimiento; una habitación sucia hoy puede contribuir al inventario futuro según reglas aprobadas. Trasladar atención no confirma cancelación ni resuelve conversación. Fuente sin vigencia definida bloquea compromiso automático.

Propiedad de datos: CupoPorFechaTipo separado de AsignaciónHabitación y Preparación (limpieza, inspección opcional, bloqueo técnico). OfertaVersionada → EvidenciaCanal (referencia externa, último estado confirmado, antigüedad). Atención → TransferenciaHumana. Mantener estos registros en el dominio; solo perfil de capacidad, correlación/auditoría y controles reutilizables residen en core. La transferencia humana de cada negocio no introduce un motor CRM global en 000. No hay nuevas dependencias obligatorias entre verticales ni ciclos. ADR-005 documenta impacto y alternativas; ADR-001/002/004 siguen propuestos.

Gate constitucional: principios I/III/IV/V/VI cubren límites, evidencia, mínimo privilegio, aceptación y recuperación; no se modifica constitución. Revisar políticas comerciales y validez de fuente antes de contratos ejecutables. Medir manual vs asistido con igual población; no prometer retorno por copiar un patrón de mercado.

## Impacto arquitectónico de la profundización

PropuestaCambioReserva → versionBase/desglose/aceptación → ResultadoCambio. Cancelación referencia una SolicitudDevolucion independiente. CargoEstadia referencia reglaCantidad/período/cuenta y TareaCumplimiento. RecepcionEventoCanal conserva ID notificación, reserva externa, huella, origen, recepción durable, estado aplicación y cursor.

La identidad de reserva externa no basta para deduplicar sus cambios. Acusar receipt no equivale a aplicar ni aceptar comercialmente. No modificar precio aceptado sin nueva revisión. Reserva, devolución, cargo, pago y tarea tienen transiciones propias; el tenant y contribuyente son explícitos en referencias.

Mantener propiedad de datos en el dominio; core solo valida capacidades/efectos, evidencia y referencias comunes. No elegir motor workflow, cola, aplicación móvil o ERP por aparecer en un proveedor. Recuperación exige registrar estado conocido/desconocido y reconciliar antes de repetir; no requiere prometer una tecnología de persistencia concreta en esta etapa. ADR-006 compara alternativas y preserva dependencias del ADR-005. Constitución revisada sin modificaciones; gates pendientes siguen bloqueando implementación.
