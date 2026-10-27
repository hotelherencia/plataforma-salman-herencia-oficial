# F08 - Desayunos, cenas y espacios compartidos

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Relacionar personas alojadas, servicios, consumos y costos, sin duplicar ventas entre hotel y cafetería.

Actores: cocina;servicio desayuno;recepción;compras. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Prever derechos -> producir porciones con ingredientes -> servir a derecho -> registrar ausente/merma; cena orden -> entrega -> cargo/deuda; sala con buffers -> uso -> limpieza.

## Reglas que no se pueden violar
Servicio desayuno no consume ingredientes otra vez; hotel-cafe mismo RUT no duplica venta externa; reserva sala no bloquea habitaciones por defecto.

## Condiciones y configuración
Recetas/unidades y proveedor cena validados; reglas de inclusiones. Decisiones pendientes: D10, D12, D23, D32. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### FNB-001 - Previsión de desayuno
**Historia F08-US01.** Como cocina, necesito previsión de desayuno para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: REC-001. Regla heredada preservada: Personas elegibles por fecha y reserva.

**Entradas y validación:** stay guests, eligible nights, service date, exceptions. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Propuesta: manana siguiente a noche prestada, incluida salida; excepciones aprobadas se versionan. Previsión no descuenta ingredientes ni marca servido.

**Escenario positivo TC-FNB-001-P:** Dado Dos personas, dos noches generan cuatro derechos. Cuando se completa la acción autorizada, entonces se cumple: Dos personas por dos noches generan servicios segun días elegibles Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FNB-001-N:** Dado Dos reservas duplicadas del mismo pasajero/dia causan doble derecho para misma estadía. Entonces Constraint por stay_guest/dia evita duplicado; caso de identidad se revisa.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F08-T01A` (pruebas), `F08-T01B` (implementación), `F08-T01C` (verificación). Evidencia prevista `evidence/F08/FNB-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FNB-002 - Desayuno servido y merma
**Historia F08-US02.** Como cocina, necesito desayuno servido y merma para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: FNB-001. Regla heredada preservada: Distinguir previsto, producido y servido.

**Entradas y validación:** production batch, portions, served, leftovers, waste. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Descontar ingredientes al producir confirmado; servir consume porción, no ingredientes otra vez. Distinguir previsto, producido, servido y merma.

**Escenario positivo TC-FNB-002-P:** Dado Diez porciones producidas, ocho servidas, dos merma quedan explicadas. Cuando se completa la acción autorizada, entonces se cumple: No-show no descuenta automáticamente un desayuno servido Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FNB-002-N:** Dado No-show se marca servido automáticamente o merma se borra. Entonces Bloqueo/alerta y corrección trazable; costo de producción no desaparece.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F08-T02A` (pruebas), `F08-T02B` (implementación), `F08-T02C` (verificación). Evidencia prevista `evidence/F08/FNB-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FNB-003 - Recetas y unidades
**Historia F08-US03.** Como cocina, necesito recetas y unidades para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Inventarios cocina; P0; relación original: INV-001. Regla heredada preservada: Versión de receta, porción y conversion de medidas.

**Entradas y validación:** recipe versión, ingredient, quantity, unit, yield. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Usar unidad base y conversion exacta; cambios conservan receta utilizada. Sustitución de ingrediente requiere equivalencia y alérgeno revisado.

**Escenario positivo TC-FNB-003-P:** Dado 100 gramos descuentan 0,1 kilogramo del lote. Cuando se completa la acción autorizada, entonces se cumple: Consumo en gramos descuenta correctamente una compra en kilos Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FNB-003-N:** Dado Unidad incompatible como litros contra unidades sin factor aprobado. Entonces 422 UNIT_CONVERSION_MISSING, sin consumo parcial.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F08-T03A` (pruebas), `F08-T03B` (implementación), `F08-T03C` (verificación). Evidencia prevista `evidence/F08/FNB-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FNB-004 - Cena subcontratada
**Historia F08-US04.** Como cocina, necesito cena subcontratada para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: PAY-002. Regla heredada preservada: Solicitud, proveedor, precio, costo, entrega y cargo.

**Entradas y validación:** meal order, guest, supplier, accepted price/cost, delivery. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Pedido y entrega separados; cargo y deuda se generan conforme a servicio aceptado. Cancelación coordina proveedor y cliente con reglas pactadas.

**Escenario positivo TC-FNB-004-P:** Dado Cena entregada crea cargo de venta y obligación de proveedor vinculados. Cuando se completa la acción autorizada, entonces se cumple: Cena no entregada no se registra como consumida sin resolución Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FNB-004-N:** Dado Proveedor no entrega pero pedido figura confirmado. Entonces INCIDENT sin consumo ficticio; resolver cargo/deuda con evidencia.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F08-T04A` (pruebas), `F08-T04B` (implementación), `F08-T04C` (verificación). Evidencia prevista `evidence/F08/FNB-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### FNB-005 - Hotel y cafetería mismo RUT
**Historia F08-US05.** Como cocina, necesito hotel y cafetería mismo rut para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: CORE-001;FNB-002. Regla heredada preservada: Transferencia/asignacion interna sin duplicar venta externa.

**Entradas y validación:** unit allocation, same company, service source. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Dentro de Herencia asignar costos internos con contrapartida gerencial eliminable; no nueva venta externa por desayuno incluido. Distinto RUT usa contrato intercompania real.

**Escenario positivo TC-FNB-005-P:** Dado Costo cafetería 4000 asignado al hotel mantiene costo total 4000 en Herencia. Cuando se completa la acción autorizada, entonces se cumple: Desayuno incluido no crea una segunda venta del grupo Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-FNB-005-N:** Dado Registrar venta externa extra por 4000 sin cliente ni servicio adicional. Entonces Rechazar clasificación automática; reporte detecta duplicación.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F08-T05A` (pruebas), `F08-T05B` (implementación), `F08-T05C` (verificación). Evidencia prevista `evidence/F08/FNB-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### SPA-001 - Sala por horas
**Historia F08-US06.** Como cocina, necesito sala por horas para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P1; relación original: CORE-001. Regla heredada preservada: Reserva, capacidad, montaje y limpieza.

**Entradas y validación:** space, capacity, start/end, setup/cleanup, price. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Intervalo incluye montaje y limpieza; bloquear solapes y aforo. Sala no aumenta inventario de habitaciones, ni se cobra sin política D23.

**Escenario positivo TC-SPA-001-P:** Dado Evento 14-16 con 30 minutos antes/despues ocupa 13:30-16:30. Cuando se completa la acción autorizada, entonces se cumple: Dos eventos incompatibles no reservan el mismo espacio y horario Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-SPA-001-N:** Dado Segundo evento comienza 16:00 sin respetar limpieza. Entonces 409 SPACE_CONFLICT con alternativa, sin reserva doble.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F08-T06A` (pruebas), `F08-T06B` (implementación), `F08-T06C` (verificación). Evidencia prevista `evidence/F08/SPA-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: recipe, recipe_line, food_batch, breakfast_service, meal_order, space, space_booking.

Pantallas: UI-23, UI-24, UI-25; especificadas en `ux/pantallas.csv`. Operaciones propias: produceFood, serveBreakfast, orderDinner, reserveSpace, listBreakfast. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: food.produced, breakfast.served, dinner.delivered, space.reserved. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
