# Compatibilidad y limitaciones de ejecución

El paquete usa directorios `specs/001-...` y archivos `spec.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `contracts/` y `quickstart.md`. La constitución propuesta se incluye también en `.specify/memory/constitution.md`; la copia legible `sdd/constitucion.md` debe permanecer identica. Es una estructura de intercambio compatible con el enfoque, no una instalación probada de una versión de SpecKit.

El equipo debe fijar release/commit y confirmar rutas/comandos/contexto en D37. Importar documentos conservando IDs y profundidad; herramientas que regeneren archivos necesitan diff y revisión. No se incluye `feature.json` activo porque ninguna feature fue seleccionada/ejecutada nativamente. No crear permisos/hooks/secrets automáticamente al descomprimir.

Las ordenes de trabajo JSON son contrato propio de gobierno, no schema oficial atribuido a GitHub. OpenAPI es contrato propio de aplicación. Las tasks apuntan a rutas futuras; no afirmar que source/tests/runtime existen en este paquete de especificaciones. El validador incluido válida este expediente documental solamente.
