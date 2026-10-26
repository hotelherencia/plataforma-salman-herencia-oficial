# plataforma-salman

## Estado vigente de consolidación

Consultar el [informe vigente](docs/auditoria/consolidacion-final.md), la
[matriz de originales preservados](docs/auditoria/equivalencias-eliminados.json)
y el [inventario clasificado](docs/auditoria/inventario-consolidacion.json).
La raíz Git está en la carpeta padre. Las fuentes primarias se conservan únicamente
en `docs/originales/`; sus copias idénticas de la carpeta padre se eliminaron tras
verificar hashes y recuperabilidad. Catálogo activo: **77 FR y 31 SC**.

Desde esta carpeta ejecutar `python scripts/validar_todo.py` para las cinco suites
y `python scripts/auditar_consolidacion.py` para inventario y examen de secretos.
PostgreSQL y revisión visual actuales quedan sin ejecutar. Los apartados históricos
siguientes documentan fases previas; el informe vigente prevalece sobre estados
anteriores de Git y preservación de copias.

Base documental de ingeniería construida a partir de cuatro fuentes del 15-10-2026. Auditoría: 16-10-2026. **Sin implementación funcional**. Cinco features **BLOCKED para iniciar desarrollo**; no se presenta documentación incompleta como producto listo.

| Feature | Estado | Decisión principal pendiente |
|---|---|---|
| [000-core](specs/000-core/spec.md) | BLOCKED | Empresas/permisos, fiscalidad, privacidad y ratificación constitucional |
| [001-cafeteria-mesas-pos](specs/001-cafeteria-mesas-pos/spec.md) | BLOCKED | Momento de pago, convivencia Eleventa y continuidad offline |
| [002-hotel-reservas-concierge](specs/002-hotel-reservas-concierge/spec.md) | BLOCKED | PMS, acceso OTA/channel manager y políticas de reserva |
| [003-inmobiliaria-comercial](specs/003-inmobiliaria-comercial/spec.md) | BLOCKED | Reserva/reembolso, promesa, firma y portales |
| [004-constructora-obra](specs/004-constructora-obra/spec.md) | BLOCKED | Alcance V2, presupuesto, avance, inspección y aprobadores |

## Entregables y navegación

- [Árbol real de archivos](docs/auditorias/arbol.txt), [inventario](docs/auditorias/inventario.md), [hashes originales](docs/auditorias/originales-sha256.json).
- [Hallazgos](docs/auditorias/hallazgos.md), auditorías individuales [investigación](docs/auditorias/auditoria-inv.md), [cafetería](docs/auditorias/auditoria-caf.md), [hotel](docs/auditorias/auditoria-hot.md), [inmobiliaria/obra](docs/auditorias/auditoria-inm.md), [afirmaciones y evidencia literal](docs/auditorias/afirmaciones.md).
- [Constitución compartida propuesta](.specify/memory/constitution.md), [visión](docs/arquitectura/vision-general.md), [grafo y dependencias](docs/arquitectura/dependencias.md), ADR [001](docs/arquitectura/decisiones/ADR-001.md), [002](docs/arquitectura/decisiones/ADR-002.md), [003](docs/arquitectura/decisiones/ADR-003.md), [004](docs/arquitectura/decisiones/ADR-004.md).
- [Trazabilidad y equivalencias](docs/auditorias/trazabilidad.md), [investigación auditada](docs/investigacion/estado-del-arte.md), [matriz de evidencia externa](docs/investigacion/matriz-evidencia.md), [fuentes](docs/investigacion/fuentes.md).
- [Riesgos, seguridad y ocho políticas agénticas](docs/arquitectura/seguridad.md), [KPI y economía](docs/arquitectura/economia.md), [aclaraciones pendientes](docs/arquitectura/aclaraciones.md), [plan por fases](docs/arquitectura/fases.md).
- [Informe de validación y consistencia](docs/auditorias/validacion.md), [resultado automático local](docs/auditorias/validacion-local.json), [cambios y ciclos](docs/auditorias/registro-cambios.md), [estado de Spec Kit](docs/auditorias/spec-kit.md).

Cada feature incluye spec.md, research.md, plan.md, data-model.md, acceptance.md, quickstart.md, tasks.md, contracts/README.md y checklists/requirements.md. Los contratos son lógicos, con gate explícito antes de definir endpoints. Las tareas abiertas son de decisión/diseño; no se fabricó backlog productivo definitivo.

## Verificación reproducible

Desde esta carpeta:

```bash
python3 scripts/validar_documentacion.py
```

Valida hashes, estructura, enlaces locales, IDs, cobertura FR/SC y grafo propuesto; genera informe, árbol y diffs. No es un comando de Spec Kit ni prueba de producto. Originales preservados en carpeta padre y docs/originales; la extracción del DOCX es íntegra en texto, sin sustituir su binario.

Spec Kit v1.2.0 fue consultado oficialmente. No está instalado; la red del shell falla por DNS. Compatibilidad documental parcial, pendiente inicialización y validación operacional en entorno disponible. No se crearon comandos internos, feature activa ni configuración de integración ficticia. Git no es utilizable en la carpeta original y no se alteró su directorio protegido.

## Investigación competitiva posterior

Se enriquecieron las 13 historias heredadas sin cambiar sus IDs; se agregaron 10 FR y 26 criterios específicos. El estado de esa fase era **66 FR, 31 SC y cinco features BLOCKED**, pendientes de decisiones cliente y validación operativa. [Informe competitivo](docs/investigacion-competitiva/informe-final.md), [evidencias](docs/investigacion-competitiva/matriz-evidencias.md), [URLs efectivas](docs/investigacion-competitiva/urls-verificadas.md), [historias](docs/investigacion-competitiva/historias-propuestas.md) y [diff Git contra baseline](docs/investigacion-competitiva/cambios.patch).

REA no pudo clonarse/ejecutarse por conectividad; su versión y commit documental están registrados. No hubo instalación global ni código de producto. La URL principal de Fudo Chile es https://fu.do/es-cl/ según precisión del usuario.

Validación adicional: `python3 scripts/validar_investigacion.py`. Las copias de linea-base son evidencia archivada, no especificaciones activas ni una segunda constitución.

## Continuación vigente: hotel, inmobiliaria y constructora

Se profundizaron las otras verticales y el core con 26 fuentes adicionales, once FR y 39 criterios más, preservando historias y artefactos de cafetería. Catálogo vigente: **77 FR, 31 SC y 65 AC competitivos**. [Informe de continuación](docs/investigacion-competitiva/continuacion-01/informe.md), [revisión hotel](docs/investigacion-competitiva/hotel/revision-profunda.md), [revisión inmobiliaria](docs/investigacion-competitiva/inmobiliaria/revision-profunda.md), [revisión obra](docs/investigacion-competitiva/constructora/revision-profunda.md). Validar además con `python3 scripts/validar_continuacion.py`. Sin implementación y sin afirmar REA dinámico ejecutado.
