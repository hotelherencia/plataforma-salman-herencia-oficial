# F12 - Costos, presupuestos e indicadores

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Mostrar resultados sin duplicados, separar datos medidos/estimados y explicar cada fórmula.

Actores: propietario;administración;contador;marketing limitado. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Registrar costo fuente -> atribuir directo -> distribuir bolsa no directa -> generar KPI -> mostrar cobertura -> contrastar caja/banco -> analizar variacion -> proponer precio.

## Reglas que no se pueden violar
No sumar devengo/factura/cobro/banco; mismo costo no directo y comun; estimaciones etiquetadas; desconocido no cero; atribución no causalidad.

## Condiciones y configuración
Fuentes disponibles y reglas de distribución aprobadas. Decisiones pendientes: D18, D24, D30, D32, D34, D35. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### FIN-007 - Costo directo de estadía
**Historia F12-US01.** Como propietario, necesito costo directo de estadía para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: OPS-004;FNB-002;FIN-001. Regla heredada preservada: Consumos reales y estimados etiquetados.

**Entradas y validación:** cost source, stay/room, measured flag, allocation. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Todo costo apunta a compra, tarea, lote o servicio; separar estimado, medido y pendiente. Un costo faltante no vale cero ni acredita margen completo.

**Escenario positivo TC-FIN-007-P:** Dado Costo de lavado llega a lote y documento proveedor desde cuenta de estadía. Cuando se completa la acción autorizada, entonces se cumple: Detalle llega a tarea, lote, compra o servicio fuente Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FIN-007-N:** Dado Cargar mismo costo como linea directa y otra copia por reporte. Entonces Unicidad de fuente y base de distribución impiden duplicado.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F12-T01A` (pruebas), `F12-T01B` (implementación), `F12-T01C` (verificación). Evidencia prevista `evidence/F12/FIN-007/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FIN-008 - Distribución de costos comunes
**Historia F12-US02.** Como propietario, necesito distribución de costos comunes para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P1; relación original: FIN-007. Regla heredada preservada: Base, período y versión; conservar total distribuido.

**Entradas y validación:** pool total, already_direct, basis weights, period. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Bolsa neta excluye lo ya directo; asignaciones calculadas con decimal y residuo controlado. Base cero deja no asignado, no division por cero.

**Escenario positivo TC-FIN-008-P:** Dado Bolsa 100000 distribuye 60000/40000 y conserva total. Cuando se completa la acción autorizada, entonces se cumple: Suma de asignaciones coincide con bolsa y no duplica salarios Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FIN-008-N:** Dado Sumar sueldos completos y además horas directas ya incluidas sin descontar. Entonces Control de reconciliacion falla; corregir bolsa antes de cierre.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F12-T02A` (pruebas), `F12-T02B` (implementación), `F12-T02C` (verificación). Evidencia prevista `evidence/F12/FIN-008/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### KPI-001 - Ocupación y calidad de dato
**Historia F12-US03.** Como propietario, necesito ocupación y calidad de dato para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Planillas ocupación; P0; relación original: HOT-003;REC-001. Regla heredada preservada: Denominador fisico/comercial y días completos visibles.

**Entradas y validación:** room nights, capacity, blocks, data coverage. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Definir denominador físico y disponible por separado; excluir noches no informadas del cálculo parcial y mostrar cobertura. No-show no es ocupado.

**Escenario positivo TC-KPI-001-P:** Dado 193/510 produce 37,84% como ejemplo histórico fechado, no pronostico. Cuando se completa la acción autorizada, entonces se cumple: Marzo parcial no se muestra como un mes completo Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-KPI-001-N:** Dado Mes parcialmente informado presentado como ocupación mensual completa. Entonces Indicador etiqueta parcial y no compara sin advertencia.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F12-T03A` (pruebas), `F12-T03B` (implementación), `F12-T03C` (verificación). Evidencia prevista `evidence/F12/KPI-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### KPI-002 - ADR, RevPAR y margen
**Historia F12-US04.** Como propietario, necesito adr, revpar y margen para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: FIN-001;FIN-007. Regla heredada preservada: Definición de impuestos, ingresos y servicios incluidos.

**Entradas y validación:** lodging revenue net, sold nights, available nights, cost. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** ADR y RevPAR usan conceptos/version aprobados; desayuno de paquete requiere asignación declarada. Permitir reconstruir cada sumatoria.

**Escenario positivo TC-KPI-002-P:** Dado Ingreso alojamiento 200000, 4 noches vendidas,10 disponibles: ADR50000 y RevPAR20000. Cuando se completa la acción autorizada, entonces se cumple: Cada indicador permite reconstruir el cálculo desde cargos Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-KPI-002-N:** Dado Denominador cero o ingreso incluye garantía e impuesto no configurado. Entonces NO_APLICA o validación de definición; nunca infinito o margen falso.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F12-T04A` (pruebas), `F12-T04B` (implementación), `F12-T04C` (verificación). Evidencia prevista `evidence/F12/KPI-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### KPI-003 - Operación diaria accionable
**Historia F12-US05.** Como propietario, necesito operación diaria accionable para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: OPS-001;FNB-001;PAY-006. Regla heredada preservada: Llegadas, salidas, aseo, desayunos, caja y alertas.

**Entradas y validación:** operational date, arrivals, tasks, service, cash, alerts. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Tablero accionable por rol y unidad; cada tarjeta abre registros y responsable. Alerta con estado de cierre, no número sin origen.

**Escenario positivo TC-KPI-003-P:** Dado Click en tres habitaciones pendientes muestra tres tareas reales. Cuando se completa la acción autorizada, entonces se cumple: Cada alerta abre registro fuente y responsable Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-KPI-003-N:** Dado Aseo intenta abrir desde tablero una cuenta de huésped. Entonces 403 y sin datos financieros aunque conozca URL.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F12-T05A` (pruebas), `F12-T05B` (implementación), `F12-T05C` (verificación). Evidencia prevista `evidence/F12/KPI-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-012 - Medición de conversión sin duplicados
**Historia F12-US06.** Como propietario, necesito medición de conversión sin duplicados para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: SOC-002;RES-001;PAY-003. Regla heredada preservada: Definir evento y valor: consulta, reserva, anticipo, estadía; deduplicar pixel/servidor donde se autorice..

**Entradas y validación:** business event, consent, event_id, amount mapping. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Definir conversion canónica reservation.confirmed y valor total pactado; payment.received es financiero, no segunda compra publicitaria. Doble canal browser/server usa mismo ID cuando habilitado.

**Escenario positivo TC-SOC-012-P:** Dado Reserva 140000 con anticipo 70000 se reporta una conversion de 140000, no 210000. Cuando se completa la acción autorizada, entonces se cumple: Una reserva enviada por navegador y servidor cuenta una vez; devolución se registra internamente sin inventar API externa de borrado. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-012-N:** Dado Pixel y servidor usan IDs diferentes para el mismo hecho. Entonces Prueba bloquea configuración; dedup requerida antes de activar.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F12-T06A` (pruebas), `F12-T06B` (implementación), `F12-T06C` (verificación). Evidencia prevista `evidence/F12/SOC-012/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SOC-018 - Costo comercial y rentabilidad de canal
**Historia F12-US07.** Como propietario, necesito costo comercial y rentabilidad de canal para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: SOC-012;FIN-007. Regla heredada preservada: Gasto, fuente, atribución, período, cancelaciones, venta realizada y contribución, sin duplicar comisiones..

**Entradas y validación:** campaign spend, booking/stay IDs, refunds, net margin. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Separar captacion de estadía prestada y costo comercial; comision/fee fuente única. Origen desconocido y cobertura visibles; atribución no prueba causalidad.

**Escenario positivo TC-SOC-018-P:** Dado Diez reservas y seis canceladas muestran cuatro estadías, no diez ventas realizadas. Cuando se completa la acción autorizada, entonces se cumple: Reporte distingue reserva captada, cobro y margen de estadía; trafico desconocido permanece visible. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SOC-018-N:** Dado Sumar comisión de canal y deducirla otra vez del neto recibido. Entonces Reconciliacion detecta duplicación y reporte queda observado.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F12-T07A` (pruebas), `F12-T07B` (implementación), `F12-T07C` (verificación). Evidencia prevista `evidence/F12/SOC-018/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### REV-002 - Pronósticos y recomendaciones evaluables
**Historia F12-US08.** Como propietario, necesito pronósticos y recomendaciones evaluables para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P2; relación original: KPI-001;KPI-002. Regla heredada preservada: Separar dato real y estimado, validar fuera de muestra, mostrar incertidumbre, aprobación de cambios..

**Entradas y validación:** history coverage, training split, baseline, uncertainty. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Pronostico temporal sin fuga de futuro, comparación con método simple y cobertura suficiente. Recomendacion no modifica tarifa sin permiso.

**Escenario positivo TC-REV-002-P:** Dado Modelo validado reporta error frente a baseline y rango. Cuando se completa la acción autorizada, entonces se cumple: Con datos insuficientes no se pública recomendacion como precision demostrada. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-REV-002-N:** Dado Datos escasos y cifra precisa presentada como certeza o actualizacion automática. Entonces Etiqueta EXPERIMENTAL/NO_APLICA y sin cambio de precio.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F12-T08A` (pruebas), `F12-T08B` (implementación), `F12-T08C` (verificación). Evidencia prevista `evidence/F12/REV-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FIN-010 - Presupuesto operativo, inversión y caja
**Historia F12-US09.** Como propietario, necesito presupuesto operativo, inversión y caja para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P1; relación original: FIN-001;CAP-003. Regla heredada preservada: Separar gastos recurrentes, activos, tecnología y publicidad; compromisos, pagos y variaciones..

**Entradas y validación:** budget nature, approved/committed/received/paid, forecast. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Mostrar etapas sin sumarlas como costos acumulados; inversion/tecnologia/anuncios separados de gasto operativo. Nulo significa sin presupuesto, no cero aprobado.

**Escenario positivo TC-FIN-010-P:** Dado Compra equipo 100000: compromiso 100000 luego pago 100000, flujo sólo 100000. Cuando se completa la acción autorizada, entonces se cumple: Una compra de equipo no se suma dos veces a costos operativos y flujo por falta de clasificación. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FIN-010-N:** Dado Reporte suma compromiso+pago y muestra 200000 gastados. Entonces Reconciliacion de estados falla; no publicar ese resultado.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F12-T09A` (pruebas), `F12-T09B` (implementación), `F12-T09C` (verificación). Evidencia prevista `evidence/F12/FIN-010/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: cost_entry, cost_pool, budget_line, conversion_event.

Pantallas: UI-35, UI-36, UI-37; especificadas en `ux/pantallas.csv`. Operaciones propias: distributeCost, calculateReport. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: cost.distributed, report.generated, conversion.recorded. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
