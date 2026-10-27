# Plan propuesto — Inmobiliaria comercial

Feature `003-inmobiliaria-comercial` · 2026-10-16 · **BLOCKED**. Entrada: [spec.md](spec.md).

## Resumen y contexto técnico

Webpay y documentos del core; proveedor de firma pendiente; portales solo con autorización, API o correo permitido; no asumir acceso a portales ni validez jurídica universal de firma.

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

ProyectoComercial → Unidad → PrecioVersionado; Lead → Contacto → Visita; Cotización → ReservaUnidad → Promesa; CalendarioPagos → Cuota; SolicitudPostventa. Unidad referencia opcionalmente un proyecto de obra mediante correspondencia autorizada.

Unidad: disponible → reservada → promesada → escriturada; expiración y devolución solo mediante política pendiente. Postventa: recibida → clasificada provisionalmente → asignada → resuelta → validada por humano/cliente.

Amenazas específicas: Doble reserva, discriminación en calificación, exposición financiera, promesas no válidas y rechazo indebido de garantía. Controles: autorización fuera del LLM, evidencia no confiable como datos, claves por tenant, acceso mínimo, deduplicación y revisión humana. Recuperación: reconciliar fuente de verdad, conservar intentos fallidos y aplicar compensación aprobada; una devolución o rectificación no es un borrado.

Consultar `../../docs/arquitectura/dependencias.md`, `seguridad.md` y ADR-001 a ADR-004. No se necesitan bases de datos compartidas entre verticales.

## Fases y estructura

Fase 0: resolver `Q-INM-01: proyectos, CRM y captura autorizada de leads; Q-INM-02: reserva, vigencia y reembolsos; Q-INM-03: revisión legal de promesa y firma; Q-INM-04: garantías y responsables.` y registrar decisiones. Fase 1: ratificar data-model.md y contratos lógicos con ejemplos válidos/erróneos. Fase 2: concretar tareas de desarrollo, pruebas previas e integración de sandbox. Esta entrega se detiene antes de implementar.

Código futuro en `verticales/inmobiliaria/`; hoy solo README de alcance. Artefactos presentes: spec, research, plan, data-model, quickstart, tasks, acceptance, contracts y checklists.

## Complexity Tracking

Se reduce el core original (catálogo, gastos y analítica quedan en dominios). Se elimina la dependencia obligatoria hotel→cafetería y obra→comercial mediante interfaces opcionales. No se justifica un proceso worker, Redis ni cuatro agentes separados como necesidad comprobada; evaluar aislamiento y costo antes de introducirlos.

## Consecuencias del refinamiento competitivo

Las historias US-INM detallan estados y validaciones de negocio; los nuevos FR-015 y FR-016 no seleccionan proveedor o infraestructura. No fusionar identidad por coincidencia única. Una promesa requiere firma y versión aprobada; un resultado del modelo no acredita financiamiento. Cambio de destinatario invalida permiso de envío privado hasta revalidación.

Propiedad de datos: Contacto separado de ConsultaOrigen y de DeclaraciónCalificación (campo, fuente, fecha, confianza). Cita (propuesta/confirmada/cancelada) → CotizaciónVersionada → ReservaUnidad → EvidenciaFirma/Promesa. AtenciónPostventa con responsable, transferencia y reapertura. Mantener estos registros en el dominio; solo perfil de capacidad, correlación/auditoría y controles reutilizables residen en core. La transferencia humana de cada negocio no introduce un motor CRM global en 000. No hay nuevas dependencias obligatorias entre verticales ni ciclos. ADR-005 documenta impacto y alternativas; ADR-001/002/004 siguen propuestos.

Gate constitucional: principios I/III/IV/V/VI cubren límites, evidencia, mínimo privilegio, aceptación y recuperación; no se modifica constitución. Revisar políticas comerciales y validez de fuente antes de contratos ejecutables. Medir manual vs asistido con igual población; no prometer retorno por copiar un patrón de mercado.

## Impacto arquitectónico de la profundización

Cita incorpora modoAgenda, zona/offset, duración, propuesta/confirmación y referencia externa; SolicitudCambio conserva ambas referencias. PromesaVersion referencia plantilla legal/huella/participantes y evidencias por firmante. Persona no es VinculoUnidad: este tiene vigencia, rol y permisos del portal. CasoPostventa vincula visitas, trabajos, aceptación y reapertura.

Firma parcial no es documento completado. Corrección de Persona no reasigna ninguna unidad y la reasignación de acceso no transfiere dominio legal. Permiso de lectura de documentos se revalida por vínculo vigente, incluso para enlace/sesión previos; el acceso histórico tiene política pendiente. El envío de información desde guardar contacto necesita intención autorizada.

Mantener propiedad de datos en el dominio; core solo valida capacidades/efectos, evidencia y referencias comunes. No elegir motor workflow, cola, aplicación móvil o ERP por aparecer en un proveedor. Recuperación exige registrar estado conocido/desconocido y reconciliar antes de repetir; no requiere prometer una tecnología de persistencia concreta en esta etapa. ADR-006 compara alternativas y preserva dependencias del ADR-005. Constitución revisada sin modificaciones; gates pendientes siguen bloqueando implementación.
