# Revisión documental — Inmobiliaria comercial

1. Leer spec.md y los bloqueos `Q-INM-01: proyectos, CRM y captura autorizada de leads; Q-INM-02: reserva, vigencia y reembolsos; Q-INM-03: revisión legal de promesa y firma; Q-INM-04: garantías y responsables.`.
2. Contrastar requisitos con la copia original indicada y trazabilidad global.
3. Revisar plan.md contra constitución; validar modelo e interfaces con responsables de negocio, seguridad y operación.
4. Revisar acceptance.md: completar datos, resultados esperados y ventanas antes del desarrollo.
5. Ejecutar desde la raíz `python3 scripts/validar_documentacion.py`; guardar informe. Esta comprobación es local y no es `/speckit.analyze`.
6. Cuando exista entorno Spec Kit inicializado, seguir `docs/auditorias/spec-kit.md`. No ejecutar implement ni converge en esta fase.

No hay aplicación, servidor, migraciones ni comandos de arranque de producto. Las pruebas futuras usan sandbox; producción requiere una fase posterior.

## Recorrido de validación competitivo (documental)

Revisar cada US-INM del spec con sus fuentes y ejecutar en mesa de revisión sus AC propuestos: preparar precondiciones y decisiones cliente → recorrer flujo normal → introducir excepción → verificar estado/evidencia/tenant y quién puede continuar. Usar los ejemplos de acceptance.md; no hay servidor para ejecutar el flujo. Registrar resultado revisado, pendiente o no aplicable, sin marcar una prueba como pasada por leerla.

Comparar con la línea base mediante `git diff --no-index docs/investigacion-competitiva/linea-base/specs/003-inmobiliaria-comercial/spec.md specs/003-inmobiliaria-comercial/spec.md`. Código de salida 1 indica diferencias, no un error de comparación. Para un paquete revisable completo usar cambios.patch y cambios.json en investigación competitiva.

## Recorridos de mesa de revisión: continuación

- RF-INM-01: preparar «ejecutivo/canal autorizado, zona horaria, duración y modalidad de agenda revisadas» y recorrer los tres AC de US-INM-001. Registrar quién aprueba y estados antes/después; no ejecutar operación real.
- RF-INM-02: preparar «plantilla y formalidades revisadas por abogado, proveedor/identificación de firmantes y política de conservación aprobados» y recorrer los tres AC de US-INM-001. Registrar quién aprueba y estados antes/después; no ejecutar operación real.
- RF-INM-03: preparar «identidad de personas revisada, vínculo actual y política de acceso/historial aprobados» y recorrer los tres AC de US-INM-002. Registrar quién aprueba y estados antes/después; no ejecutar operación real.
- RF-INM-04: preparar «cliente/unidad autorizados, catálogo de fallas y reglas de plazo/garantía ratificados» y recorrer los tres AC de US-INM-002. Registrar quién aprueba y estados antes/después; no ejecutar operación real.

Contrastar el resultado con la línea base de continuación en `docs/investigacion-competitiva/linea-base/continuacion-01/`. El patch incremental se entrega en continuacion-01/cambios.patch; Git diff --no-index es comparación documental, no commit ni análisis de Spec Kit.
