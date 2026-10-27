# F19 - Conexión bancaria autorizada de lectura

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Automatizar lectura bajo contrato sin retirar la importación segura ni iniciar transferencias.

Actores: tesorería;contador;soporte. Entrega candidata: E3. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Autorizar conexión -> leer cursor -> normalizar -> importar mismo pipeline -> reconciliar -> alertar vencimiento -> revocar -> usar CSV.

## Reglas que no se pueden violar
Sólo lectura; no credenciales bancarias en prompt; repetir página no duplica; cobertura del proveedor se prueba por cuenta.

## Condiciones y configuración
Banco/cuenta/proveedor/permiso lectura autorizados. Decisiones pendientes: D08, D16, D18. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### INT-004 - Conexión bancaria de lectura
**Historia F19-US01.** Como tesorería, necesito conexión bancaria de lectura para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** S13; P1; relación original: FIN-003. Regla heredada preservada: Cobertura, autorización, frecuencia y costo por cuenta.

**Entradas y validación:** bank account, consent, provider, read scope, cursor. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Sólo lectura consentida; importaciones por API usan mismo normalizador y deduplicacion que archivos. Revocacion detiene tareas y elimina credencial activa.

**Escenario positivo TC-INT-004-P:** Dado Movimientos nuevos se importan con cursor sin duplicar históricos. Cuando se completa la acción autorizada, entonces se cumple: Revocar acceso impide nuevas lecturas y deja trazabilidad Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INT-004-N:** Dado Revocar permiso mientras hay job programado. Entonces No nueva lectura; job bloqueado y auditoría de revocacion.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F19-T01A` (pruebas), `F19-T01B` (implementación), `F19-T01C` (verificación). Evidencia prevista `evidence/F19/INT-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: Artefactos de gobierno, contratos y pruebas, sin tablas de negocio nuevas.

Pantallas: UI-48; especificadas en `ux/pantallas.csv`. Operaciones propias: createBankConnection. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: bank.connection_expired, bank.page_received. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
