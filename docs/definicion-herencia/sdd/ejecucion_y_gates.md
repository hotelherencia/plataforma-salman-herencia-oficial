# Marco de ejecución SDD

## Incorporacion
El responsable del equipo recibe ZIP, verifica manifiesto y crea copia de trabajo autorizada. Revisar ADR-001 y D37-D45. Fijar version/commit de Spec Kit, agente, sistema operativo, herramientas y plantillas. Esta entrega no incluye instalación nativa ni comandos ya ejecutados.

El maestro mantiene reglas globales; spec por feature es contrato de comportamiento; plan propone solución; tasks descompone. Integrar con plantillas oficiales de la versión instalada sin sustituir ni perder IDs. Los comandos se invocan en el agente compatible, no en cualquier chat ni se presumen shell.

## Flujo
Constitution -> specify -> clarify -> plan -> checklist -> tasks -> analyze -> implement -> converge. En nuestro paquete spec/plan/tasks ya estan desarrollados; el equipo debe revisarlos y adaptarlos al entorno instalado, no regenerarlos ignorando el maestro. Una aclaracion modifica fuente/impacto; no reabre políticas sin propietario.

## GateG0: autorizar paquete
Alcance claro, decisiones bloqueantes cerradas, contrato de datos/API estable, tests y fixture, permisos, presupuesto, archivos permitidos, implementador y revisor. D45 bloquea arquitectura de código hasta resolver, no lectura funcional. Aprobación explícita necesaria.

## GateG1: módulo compatible
Tareas T00..T99 producen código y pruebas locales/contrato. T99 certifica sólo candidata de integración, no capacidad productiva. Dependencia de implementación consume ese contrato estable; pruebas con simulador deben estar rotuladas. Así F03 se construye contra PaymentStatus y F04 implementa después el proveedor sin ciclo.

## GateG2: integración completa
Ejecutar los tests de los paquetes involucrados con sus dependencias reales habilitadas en entorno controlado. F03+F04 prueban reserva/pago; F05+F07 disponibilidad física; F07+F10 calidad/incentivos; F12 con sus fuentes; F20 con reconciliacion/recuperacion. Estas relaciones son gates de evidencia, no ciclos del grafo de tareas. Todos sus requisitos siguen NO_ACEPTADOS hasta pasarG2.

## GateG3: producción
Build, migraciones, permisos, rendimiento, seguridad, recuperación, contratos de proveedor, personal capacitado y saldos de corte validados. Aprobación humana y contingencia. No resolver vulnerabilidad crítica con frase de aceptacion del agente. Delimitar funcionalidades apagadas; sus controles pasan antes de activarlas.

## Paralelismo y eficiencia
Un coordinador asigna features con contratos estables; ramas/worktrees separados y un propietario del esquema compartido. No dos agentes editando misma migración simultaneamente. Máximo de concurrencia/costo D40; propuesta tres ciclos correctivos antes de escalar. Detener ante secreto, duda financiera, conflicto de requerimiento o presupuesto.

## Cambios y seguimiento
Reporte por IDs aceptados con denominador versionado, no por lineas de código. Mantener propuesto/especificado/implementado/probado/aceptado separados. No aprobar deuda técnica silenciosa. Cada cambio incluye pruebas de regresión y contratos consumidores. La salida del modelo no sustituye resultados de herramientas.
