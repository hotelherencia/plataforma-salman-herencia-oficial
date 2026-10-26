# Plan propuesto — Core transversal

Feature `000-core` · 2026-10-16 · **BLOCKED**. Entrada: [spec.md](spec.md).

## Resumen y contexto técnico

Webpay/Transbank, SII/proveedor documental y canal de comunicación mediante adaptadores, sin herramientas financieras directas al modelo.

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

Tenant → Membresía ← Identidad; Rol → Permiso; IntentoPago → ResultadoProveedor; ObligaciónDocumental → DocumentoTributario; AcciónAuditada → Evidencia; PolíticaAgente → Aprobación; ReferenciaNegocio opaca, sin copiar entidades verticales.

Pago: iniciado → pendiente → autorizado/rechazado/desconocido; desconocido requiere consulta y conciliación. Documento: pendiente → emitido/observado → regularizado; nunca borrar el rastro de rechazo. Aprobación: solicitada → aprobada/rechazada/expirada, vinculada a parámetros exactos.

Amenazas específicas: Escape entre tenants, privilegios de soporte, repetición de pago, pérdida de evidencia y extracción de secretos. Controles: autorización fuera del LLM, evidencia no confiable como datos, claves por tenant, acceso mínimo, deduplicación y revisión humana. Recuperación: reconciliar fuente de verdad, conservar intentos fallidos y aplicar compensación aprobada; una devolución o rectificación no es un borrado.

Consultar `../../docs/arquitectura/dependencias.md`, `seguridad.md` y ADR-001 a ADR-004. No se necesitan bases de datos compartidas entre verticales.

## Fases y estructura

Fase 0: resolver `Q-CORE-01: empresas, roles y autorización entre empresas; Q-CORE-02: tratamiento fiscal y proveedor DTE por contribuyente; Q-CORE-03: responsables de datos, retención, recuperación, presupuesto y autonomía.` y registrar decisiones. Fase 1: ratificar data-model.md y contratos lógicos con ejemplos válidos/erróneos. Fase 2: concretar tareas de desarrollo, pruebas previas e integración de sandbox. Esta entrega se detiene antes de implementar.

Código futuro en `core/`; hoy solo README de alcance. Artefactos presentes: spec, research, plan, data-model, quickstart, tasks, acceptance, contracts y checklists.

## Complexity Tracking

Se reduce el core original (catálogo, gastos y analítica quedan en dominios). Se elimina la dependencia obligatoria hotel→cafetería y obra→comercial mediante interfaces opcionales. No se justifica un proceso worker, Redis ni cuatro agentes separados como necesidad comprobada; evaluar aislamiento y costo antes de introducirlos.

## Consecuencias del refinamiento competitivo

Las historias US-CORE detallan estados y validaciones de negocio; los nuevos FR-010 y FR-011 no seleccionan proveedor o infraestructura. No retroceder resultado conciliado por un mensaje antiguo. Una devolución posterior es transición de negocio autorizada, no un evento antiguo ignorado. Si no hay secuencia confiable, consultar autoridad y marcar incertidumbre, sin deducir orden por timestamp.

Propiedad de datos: PerfilConector (tenant, referenciaCuenta opaca, proveedor, país/plan opcionales, capacidades, permisos, revisión/versionado) → EvidenciaRevisión. EventoExterno (identidad proveedor, operación, recibido/ocurrido, correlación, estado) → Intento → CasoConciliación (motivo, responsable, resolución). Mantener estos registros en el dominio; solo perfil de capacidad, correlación/auditoría y controles reutilizables residen en core. La transferencia humana de cada negocio no introduce un motor CRM global en 000. No hay nuevas dependencias obligatorias entre verticales ni ciclos. ADR-005 documenta impacto y alternativas; ADR-001/002/004 siguen propuestos.

Gate constitucional: principios I/III/IV/V/VI cubren límites, evidencia, mínimo privilegio, aceptación y recuperación; no se modifica constitución. Revisar políticas comerciales y validez de fuente antes de contratos ejecutables. Medir manual vs asistido con igual población; no prometer retorno por copiar un patrón de mercado.

## Impacto arquitectónico de la profundización

PerfilOperacion añade efectos explícitos por campo/flag, destinatarios permitidos, condiciones y versión revisada. IntencionEfecto separa solicitud/permiso/ejecución/resultado; no se almacena secreto ni aprobación en texto del modelo. EventoExterno referencia cuenta/propiedad autorizada sin permitir que el payload cambie tenant.

Una herramienta denominada guardar/consultar puede producir comunicación; denegar si el perfil no acredita todos sus efectos. Una revisión de perfil no transfiere aprobaciones antiguas a nuevos flags.

Mantener propiedad de datos en el dominio; core solo valida capacidades/efectos, evidencia y referencias comunes. No elegir motor workflow, cola, aplicación móvil o ERP por aparecer en un proveedor. Recuperación exige registrar estado conocido/desconocido y reconciliar antes de repetir; no requiere prometer una tecnología de persistencia concreta en esta etapa. ADR-006 compara alternativas y preserva dependencias del ADR-005. Constitución revisada sin modificaciones; gates pendientes siguen bloqueando implementación.
