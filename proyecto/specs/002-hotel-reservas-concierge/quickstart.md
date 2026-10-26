# Revisión documental — Hotel

1. Leer spec.md y los bloqueos `Q-HOT-01: PMS actual y fuente de inventario; Q-HOT-02: acceso OTA/channel manager; Q-HOT-03: habitaciones, cancelación, anticipos, datos de registro y autonomía.`.
2. Contrastar requisitos con la copia original indicada y trazabilidad global.
3. Revisar plan.md contra constitución; validar modelo e interfaces con responsables de negocio, seguridad y operación.
4. Revisar acceptance.md: completar datos, resultados esperados y ventanas antes del desarrollo.
5. Ejecutar desde la raíz `python3 scripts/validar_documentacion.py`; guardar informe. Esta comprobación es local y no es `/speckit.analyze`.
6. Cuando exista entorno Spec Kit inicializado, seguir `docs/auditorias/spec-kit.md`. No ejecutar implement ni converge en esta fase.

No hay aplicación, servidor, migraciones ni comandos de arranque de producto. Las pruebas futuras usan sandbox; producción requiere una fase posterior.

## Recorrido de validación competitivo (documental)

Revisar cada US-HOT del spec con sus fuentes y ejecutar en mesa de revisión sus AC propuestos: preparar precondiciones y decisiones cliente → recorrer flujo normal → introducir excepción → verificar estado/evidencia/tenant y quién puede continuar. Usar los ejemplos de acceptance.md; no hay servidor para ejecutar el flujo. Registrar resultado revisado, pendiente o no aplicable, sin marcar una prueba como pasada por leerla.

Comparar con la línea base mediante `git diff --no-index docs/investigacion-competitiva/linea-base/specs/002-hotel-reservas-concierge/spec.md specs/002-hotel-reservas-concierge/spec.md`. Código de salida 1 indica diferencias, no un error de comparación. Para un paquete revisable completo usar cambios.patch y cambios.json en investigación competitiva.

## Recorridos de mesa de revisión: continuación

- RF-HOT-01: preparar «reserva vigente versionada, identidad validada, política de cambios/cancelación y aprobador definidos» y recorrer los tres AC de US-HOT-001. Registrar quién aprueba y estados antes/después; no ejecutar operación real.
- RF-HOT-02: preparar «reserva/cuenta válidas, producto/servicio mapeado, periodicidad y responsable aprobados» y recorrer los tres AC de US-HOT-002. Registrar quién aprueba y estados antes/después; no ejecutar operación real.
- RF-HOT-03: preparar «conector autorizado, correspondencia de propiedad/recurso y mecanismo de autenticación/revisión definidos» y recorrer los tres AC de US-HOT-001. Registrar quién aprueba y estados antes/después; no ejecutar operación real.
- RF-HOT-04: preparar «identidad para datos privados, datos vigentes, política de acción y receptor humano definidos» y recorrer los tres AC de US-HOT-003. Registrar quién aprueba y estados antes/después; no ejecutar operación real.

Contrastar el resultado con la línea base de continuación en `docs/investigacion-competitiva/linea-base/continuacion-01/`. El patch incremental se entrega en continuacion-01/cambios.patch; Git diff --no-index es comparación documental, no commit ni análisis de Spec Kit.
