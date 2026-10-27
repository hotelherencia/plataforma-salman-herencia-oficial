# F22 - Contratos para módulos futuros del grupo

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Definir interfaces de cafetería, inmobiliarias, inversiones, matriz y constructora sin inventar procesos no estudiados.

Actores: propietario;arquitectura;responsables de cada negocio. Entrega candidata: FUTURO. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Definir contratos comunes -> delimitar negocio -> incorporar hechos nuevos -> especificar nueva feature -> probar aislamiento -> integrar gerencial.

## Reglas que no se pueden violar
No construir contabilidad/nomina/obras desconocidas; misma propiedad no mezcla obligaciones ni permisos; cafe es mismo operador sin duplicación.

## Condiciones y configuración
Aprobación de alcance futuro y datos reales de cada unidad. Decisiones pendientes: D15, D21, D24, D34, D35, D38. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### CORE-007 - Contratos para futuras empresas y módulos
**Historia F22-US01.** Como propietario, necesito contratos para futuras empresas y módulos para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: CORE-001;CORE-003. Regla heredada preservada: Catálogos comunes, permisos y documentos; interfaces para cafetería, inmuebles, inversiones, matriz y constructora..

**Entradas y validación:** domain contracts, company/unit, common IDs, allowed scopes. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Futuros módulos intercambian referencias y hechos autorizados; no comparten datos personales por proveedor comun. Cafe completo y otras verticales son fase posterior.

**Escenario positivo TC-CORE-007-P:** Dado Inmobiliaria usa proveedor comun sin ver cobros del hotel. Cuando se completa la acción autorizada, entonces se cumple: Un identificador de proveedor compartido no comparte automáticamente pagos ni datos de huéspedes. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CORE-007-N:** Dado Futura aplicación pide acceso global por conocer party_id. Entonces 403; requiere contrato/permiso explícito por sociedad y finalidad.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F22-T01A` (pruebas), `F22-T01B` (implementación), `F22-T01C` (verificación). Evidencia prevista `evidence/F22/CORE-007/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: Artefactos de gobierno, contratos y pruebas, sin tablas de negocio nuevas.

Pantallas: UI-52; especificadas en `ux/pantallas.csv`. Operaciones propias: No API productiva en este paquete; contratos documentales y validaciones internas. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: group.report_ready, domain.onboard_requested. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
