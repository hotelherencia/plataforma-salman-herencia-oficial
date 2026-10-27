# Revisión documental — Constructora y control de obra

1. Leer spec.md y los bloqueos `Q-OBR-01: obras propias o terceros, presupuesto y módulo previo no entregado; Q-OBR-02: unidad del avance, calendario y umbral; Q-OBR-03: aprobadores, compras, seguridad e inspecciones.`.
2. Contrastar requisitos con la copia original indicada y trazabilidad global.
3. Revisar plan.md contra constitución; validar modelo e interfaces con responsables de negocio, seguridad y operación.
4. Revisar acceptance.md: completar datos, resultados esperados y ventanas antes del desarrollo.
5. Ejecutar desde la raíz `python3 scripts/validar_documentacion.py`; guardar informe. Esta comprobación es local y no es `/speckit.analyze`.
6. Cuando exista entorno Spec Kit inicializado, seguir `docs/auditorias/spec-kit.md`. No ejecutar implement ni converge en esta fase.

No hay aplicación, servidor, migraciones ni comandos de arranque de producto. Las pruebas futuras usan sandbox; producción requiere una fase posterior.

## Recorrido de validación competitivo (documental)

Revisar cada US-OBR del spec con sus fuentes y ejecutar en mesa de revisión sus AC propuestos: preparar precondiciones y decisiones cliente → recorrer flujo normal → introducir excepción → verificar estado/evidencia/tenant y quién puede continuar. Usar los ejemplos de acceptance.md; no hay servidor para ejecutar el flujo. Registrar resultado revisado, pendiente o no aplicable, sin marcar una prueba como pasada por leerla.

Comparar con la línea base mediante `git diff --no-index docs/investigacion-competitiva/linea-base/specs/004-constructora-obra/spec.md specs/004-constructora-obra/spec.md`. Código de salida 1 indica diferencias, no un error de comparación. Para un paquete revisable completo usar cambios.patch y cambios.json en investigación competitiva.

## Recorridos de mesa de revisión: continuación

- RF-OBR-01: preparar «obra/partida/versión y unidades identificadas; permisos de reporte/revisión y canal soportado» y recorrer los tres AC de US-OBR-003. Registrar quién aprueba y estados antes/después; no ejecutar operación real.
- RF-OBR-02: preparar «orden/líneas/versiones autorizadas, unidades revisadas, documento de entrega y responsables» y recorrer los tres AC de US-OBR-004. Registrar quién aprueba y estados antes/después; no ejecutar operación real.
- RF-OBR-03: preparar «presupuesto vigente por partida, reglas de compromiso/devengo/pago y aprobación definidos» y recorrer los tres AC de US-OBR-004. Registrar quién aprueba y estados antes/después; no ejecutar operación real.
- RF-OBR-04: preparar «observación vinculada a evidencia/partida, responsables y permisos de solución/cierre definidos» y recorrer los tres AC de US-OBR-004. Registrar quién aprueba y estados antes/después; no ejecutar operación real.

Contrastar el resultado con la línea base de continuación en `docs/investigacion-competitiva/linea-base/continuacion-01/`. El patch incremental se entrega en continuacion-01/cambios.patch; Git diff --no-index es comparación documental, no commit ni análisis de Spec Kit.
