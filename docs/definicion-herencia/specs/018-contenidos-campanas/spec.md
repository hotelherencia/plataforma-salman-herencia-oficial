# F17 - Publicaciones y publicidad controlada

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Preparar contenido, publicar formatos verificados y activar gasto sólo dentro de autorizaciones.

Actores: marketing;propietario;aprobador presupuesto. Entrega candidata: E3. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Crear borrador -> revisar derechos/precio -> aprobar -> programar -> publicar con resultado -> activar gasto dentro de límite -> medir/corregir -> pausar.

## Reglas que no se pueden violar
No activar gasto sin aprobación independiente; fallo no se marca publicado; promoción válida contra cupos y condiciones; formato no soportado tiene salida manual.

## Condiciones y configuración
Derechos contenido, cuenta, capacidad y gasto aprobado. Decisiones pendientes: D19, D25, D26, D28, D30. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### INT-006 - Publicación y publicidad social
**Historia F17-US01.** Como marketing, necesito publicación y publicidad social para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P2; relación original: RES-002. Regla heredada preservada: Permisos y aprobación; no confundir con motor de reservas.

**Entradas y validación:** content/ads permissions, approval, budget. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Publicación y publicidad son capacidades separadas; sin aprobación sólo borrador o exportación manual. Gasto requiere límite ratificado.

**Escenario positivo TC-INT-006-P:** Dado Contenido aprobado se pública y guarda ID externo. Cuando se completa la acción autorizada, entonces se cumple: Sin aprobación no pública contenido ni activa gasto Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INT-006-N:** Dado Agente intenta publicar oferta o activar anuncio sin permiso. Entonces Bloqueo y solicitud de aprobación; cero gasto externo.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F17-T01A` (pruebas), `F17-T01B` (implementación), `F17-T01C` (verificación). Evidencia prevista `evidence/F17/INT-006/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-014 - Campañas y presupuesto publicitario
**Historia F17-US02.** Como marketing, necesito campañas y presupuesto publicitario para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P2; relación original: SOC-001;SOC-012. Regla heredada preservada: Borrador, aprobación, programación, gasto autorizado, cambios de precio y parada de emergencia..

**Entradas y validación:** campaign, approved budget, period, spend, stop control. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Aprobación cubre importe, fechas y objetivo; aumento o destino distinto requiere nueva aprobación. Parada de emergencia disponible; reportar gasto real y retraso proveedor.

**Escenario positivo TC-SOC-014-P:** Dado Campaña aprobada opera dentro de límite y período. Cuando se completa la acción autorizada, entonces se cumple: Sin autorización no se activa gasto; aumentar presupuesto requiere nueva aprobación aplicable. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-014-N:** Dado Modelo aumenta presupuesto para mejorar conversion por iniciativa. Entonces 403 y solicitud pendiente; no gasto extra.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F17-T02A` (pruebas), `F17-T02B` (implementación), `F17-T02C` (verificación). Evidencia prevista `evidence/F17/SOC-014/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-015 - Contenidos y publicación por formato
**Historia F17-US03.** Como marketing, necesito contenidos y publicación por formato para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P2; relación original: SOC-001. Regla heredada preservada: Calendario, fotos autorizadas, textos, formatos admitidos, aprobación y evidencia de publicación..

**Entradas y validación:** content, rights, format, approval, provider result. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Publicación requiere derechos de medios y texto veraz; precio/oferta revalidada. Estado PUBLISHED exige ID/evidencia del proveedor; formatos no soportados pasan a manual.

**Escenario positivo TC-SOC-015-P:** Dado Pieza aprobada pública y guarda referencia externa. Cuando se completa la acción autorizada, entonces se cumple: Formato no admitido queda pendiente o se exporta para publicación manual, nunca figura publicado. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-015-N:** Dado Proveedor rechaza formato pero interfaz muestra publicada. Entonces Estado FAILED/MANUAL y alerta, sin evidencia ficticia.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F17-T03A` (pruebas), `F17-T03B` (implementación), `F17-T03C` (verificación). Evidencia prevista `evidence/F17/SOC-015/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: campaign, content_piece.

Pantallas: UI-44, UI-45; especificadas en `ux/pantallas.csv`. Operaciones propias: createCampaign, activateCampaign, createContent, publishContent, listCampaigns. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: content.published, campaign.activated, campaign.paused. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
