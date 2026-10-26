# Aceptacion F21

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-SEC-004-P | SEC-004 | Ensayo recupera reservas/saldos y opera flujo de prueba. | Restaurar ambiente de prueba recupera datos y permite operar |
| TC-SEC-004-N | SEC-004 | Backup existe pero nunca se ha restaurado o faltan documentos. | No supera gate de continuidad; pendiente hasta ensayo verificable. |
| TC-SEC-005-P | SEC-005 | Recibo de emergencia E001 se carga una vez al volver. | Reingreso de operaciones de emergencia no duplica pagos |
| TC-SEC-005-N | SEC-005 | Reimportar E001 o activar venta offline desde navegador sin cupo fiable. | Duplicado rechazado; venta bloqueada, excepción supervisada. |
| TC-AI-006-P | AI-006 | Apagar proveedor IA permite reservar por web y cerrar caja. | Desactivar modelo no impide registrar reserva ni cerrar caja |
| TC-AI-006-N | AI-006 | Endpoint de reserva depende de una llamada a modelo para calcular cupo. | Prueba falla; separar motor determinista antes de liberar. |
| TC-SEC-009-P | SEC-009 | Revisor reproduce controles de aislamiento y secretos con evidencia. | Vulnerabilidad crítica sin corregir impide producción aunque todas las pantallas existan. |
| TC-SEC-009-N | SEC-009 | Interfaz completa pero vulnerabilidad crítica de acceso cruzado abierta. | NO_GO para producción, aunque pruebas visuales pasen. |
| TC-SEC-010-P | SEC-010 | Build identificado con lock y pruebas de migracion/recuperacion. | Dependencia insegura detectada detiene paquete; rollback no pierde cobros nuevos. |
| TC-SEC-010-N | SEC-010 | Dependencia vulnerable o secreto detectado antes de release. | Pipeline bloqueado y remediación; no bypass por agente. |
| TC-QA-001-P | QA-001 | Un ciclo sintético completo produce resultados esperados sin duplicados. | La misma transacción es trazable sin duplicados y con fallos simulados; no confundir prueba sintética con integración real. |
| TC-QA-001-N | QA-001 | Sólo se prueban pantallas o mocks y se declara integración real. | Gate no superado; exigir adaptador/entorno autorizado y pruebas correspondientes. |
| TC-QA-002-P | QA-002 | Veinte intentos y precio manipulado no crean sobreventa interna ni descuento falso. | Dos solicitudes al último cupo interno no crean dos confirmaciones; cliente no puede fijar monto arbitrario. |
| TC-QA-002-N | QA-002 | Desactivar constraint para hacer pasar prueba bajo carga. | Rechazo de cambio y hallazgo crítico; mantener integridad. |
| TC-QA-003-P | QA-003 | Auditoría enlaza requisito a artefactos y senala pendientes reales. | No se cierra maestro con dependencias sin ID, reglas contradictorias o decisiones críticas ocultas. |
| TC-QA-003-N | QA-003 | Declarar 100% terminado por número de archivos sin revisar contradicciones. | Estado revisión pendiente; reporte honesto de alcance y evidencia. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
