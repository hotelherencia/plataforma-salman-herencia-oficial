# F06 - Compras, existencias y precios unitarios

Versión 1.0, 25/10/2026. **DESARROLLADO PARA REVISIÓN; NO APROBADO; NO IMPLEMENTADO.**

## Objetivo y frontera
Comparar compras, recibir cantidades reales, registrar deuda y mantener inventario por ubicacion/lote.

Actores: bodega;compras;administración;contador. Entrega candidata: E1. La fecha de apertura no sustituye pruebas o acceso real a proveedores. Este paquete no autoriza gastos ni cambios en producción.

## Recorrido funcional
Solicitar -> comparar -> aprobar orden -> recibir real -> controlar factura -> registrar cuenta por pagar -> pagar aprobado -> contar y ajustar con evidencia.

## Reglas que no se pueden violar
Pagar no significa recibir; compras/recepciones parciales preservan pendiente; devolución es contramovimiento; stock no negativo salvo excepción aprobada que no oculta falta.

## Condiciones y configuración
Catalogo/unidades/ubicaciones validados; reglas de aprobación y costos. Decisiones pendientes: D13, D14, D24, D31, D32. Datos de demostracion se etiquetan y no se publican como reales.

## Escenarios detallados y requisitos

### INV-001 - Catálogo y unidades
**Historia F06-US01.** Como bodega, necesito catálogo y unidades para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Inventarios generales; P0; relación original: CORE-006. Regla heredada preservada: Producto, categoría, compra, consumo y conversion.

**Entradas y validación:** product kind, base/purchase unit, conversion, quality. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Catálogo separa naturaleza del articulo y no hereda errores de títulos históricos. Conversion positiva y exacta; activos no se tratan como jabon consumible.

**Escenario positivo TC-INV-001-P:** Dado Bebida del archivo mal titulado se carga como producto de reventa con unidad correcta. Cuando se completa la acción autorizada, entonces se cumple: Producto de bebidas no se clasifica por título erroneo del libro Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INV-001-N:** Dado Producto duplicado por variacion ortografica genera dos stocks no revisados. Entonces Importación propone correspondencia y solicita validación antes de activar duplicado.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F06-T01A` (pruebas), `F06-T01B` (implementación), `F06-T01C` (verificación). Evidencia prevista `evidence/F06/INV-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### INV-002 - Movimientos y ubicaciones
**Historia F06-US02.** Como bodega, necesito movimientos y ubicaciones para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Inventarios generales; P0; relación original: INV-001. Regla heredada preservada: Entrada, salida, transferencia, merma y ajuste.

**Entradas y validación:** stock movement, source, warehouse, quantity, transfer. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Movimientos inmutables; dos patas de transferencia atomicas. Saldo derivado por articulo/lote/ubicacion y sociedad, sin permitir stock negativo por edicion directa.

**Escenario positivo TC-INV-002-P:** Dado Mover cinco unidades de bodega a piso conserva total y cambia ubicacion. Cuando se completa la acción autorizada, entonces se cumple: Mover bodega a piso no modifica stock total del establecimiento Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INV-002-N:** Dado Falla una pata de traslado o salida supera stock. Entonces Rollback completo/409 INSUFFICIENT_STOCK; sin unidades desaparecidas.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F06-T02A` (pruebas), `F06-T02B` (implementación), `F06-T02C` (verificación). Evidencia prevista `evidence/F06/INV-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### INV-003 - Lotes y vencimientos
**Historia F06-US03.** Como bodega, necesito lotes y vencimientos para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta operativa; P0; relación original: INV-001. Regla heredada preservada: Caducidad y rotación para productos aplicables.

**Entradas y validación:** lot, expiry, quarantine, product policy. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Seleccionar lote utilizable de vencimiento mas próximo; vencido o cuarentena no se sirve. Excepción comercial no anula control sanitario.

**Escenario positivo TC-INV-003-P:** Dado Salida de leche usa lote vigente mas próximo a vencer. Cuando se completa la acción autorizada, entonces se cumple: Producto vencido no se propone para servicio sin excepción permitida Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INV-003-N:** Dado Lote vencido propuesto para desayuno. Entonces 422 LOT_NOT_USABLE y retiro/merma supervisada, no servicio.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F06-T03A` (pruebas), `F06-T03B` (implementación), `F06-T03C` (verificación). Evidencia prevista `evidence/F06/INV-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### INV-004 - Inventario físico y ajustes
**Historia F06-US04.** Como bodega, necesito inventario físico y ajustes para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: INV-002. Regla heredada preservada: Conteo, diferencia, motivo y aprobador.

**Entradas y validación:** count snapshot, physical count, movements after cutoff. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Conteo ciego y reconteo de diferencias; ajuste aprobado conserva referencia al corte y movimientos posteriores. No sobrescribir saldo actual con conteo antiguo.

**Escenario positivo TC-INV-004-P:** Dado Conteo 20 al corte mas entrada posterior 5 termina 25 tras conciliación. Cuando se completa la acción autorizada, entonces se cumple: Diferencia genera ajuste trazable y no altera original Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INV-004-N:** Dado Aplicar conteo antiguo como saldo 20 perdiendo las cinco recibidas. Entonces Bloqueo por corte/version y recalculo con movimientos posteriores.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F06-T04A` (pruebas), `F06-T04B` (implementación), `F06-T04C` (verificación). Evidencia prevista `evidence/F06/INV-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### INV-005 - Reposicion y alertas
**Historia F06-US05.** Como bodega, necesito reposicion y alertas para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P1; relación original: INV-002. Regla heredada preservada: Mínimos, consumo, plazo proveedor y ocupación futura.

**Entradas y validación:** minimum, usable stock, transit, demand, lead time. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Sugerencia muestra demanda y regla; no compra por si sola. Cantidad propuesta considera compromisos pendientes y unidades normalizadas.

**Escenario positivo TC-INV-005-P:** Dado Stock 3, mínimo 10 y pedido en transito 4 propone revisar tres unidades adicionales. Cuando se completa la acción autorizada, entonces se cumple: Alerta identifica cantidad propuesta y bases, no compra sola Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-INV-005-N:** Dado Ejecutar compra automáticamente sin aprobación de presupuesto. Entonces Sólo alerta/borrador; ninguna orden enviada ni gasto.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F06-T05A` (pruebas), `F06-T05B` (implementación), `F06-T05C` (verificación). Evidencia prevista `evidence/F06/INV-005/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### PUR-001 - Solicitud y aprobación
**Historia F06-US06.** Como bodega, necesito solicitud y aprobación para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; inventarios; P0; relación original: CORE-003. Regla heredada preservada: Solicitante, aprobador, presupuesto y proveedor.

**Entradas y validación:** requester, supplier, amount, budget, approval. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Solicitud se válida contra presupuesto/umbral; fuera de límite exige otro aprobador. Cambios materiales invalidan autorización anterior.

**Escenario positivo TC-PUR-001-P:** Dado Compra aprobada por responsable distinto pasa a ORDERED con evidencia. Cuando se completa la acción autorizada, entonces se cumple: Compra fuera de umbral no se autoriza por el solicitante Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PUR-001-N:** Dado Solicitante se autoaprueba compra superior a su límite. Entonces 403; estado REQUESTED sin orden externa.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F06-T06A` (pruebas), `F06-T06B` (implementación), `F06-T06C` (verificación). Evidencia prevista `evidence/F06/PUR-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### PUR-002 - Recepción parcial
**Historia F06-US07.** Como bodega, necesito recepción parcial para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Inventarios proveedor/factura; P0; relación original: PUR-001;INV-002. Regla heredada preservada: Cantidad recibida distinta de ordenada/pagada.

**Entradas y validación:** order line, receipt, accepted/rejected quantity. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Aumentar inventario sólo por cantidad aceptada en ubicacion/lote; pendiente calculado contra orden. Reversion requiere verificar consumo posterior.

**Escenario positivo TC-PUR-002-P:** Dado Recibir ocho de diez incorpora ocho y deja dos abiertas. Cuando se completa la acción autorizada, entonces se cumple: Recibir 8 de 10 aumenta stock en 8 y deja 2 pendientes Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PUR-002-N:** Dado Reenviar misma recepción o recibir veinte sin tolerancia aprobada. Entonces Duplicado no suma; exceso requiere excepción y no se acepta silenciosamente.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F06-T07A` (pruebas), `F06-T07B` (implementación), `F06-T07C` (verificación). Evidencia prevista `evidence/F06/PUR-002/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### PUR-003 - Control orden-recepción-documento
**Historia F06-US08.** Como bodega, necesito control orden-recepción-documento para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Propuesta de control; P0; relación original: PUR-002. Regla heredada preservada: Tolerancias y excepciones aprobadas.

**Entradas y validación:** order, receipt, invoice quantity/price, tolerances. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Comparación de tres fuentes conserva diferencias; factura puede registrarse para control pero pago queda bloqueado hasta aceptacion de excepción.

**Escenario positivo TC-PUR-003-P:** Dado Factura coincide con ocho recibidas y precio acordado. Cuando se completa la acción autorizada, entonces se cumple: Factura superior a lo recibido genera diferencia visible Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PUR-003-N:** Dado Factura diez cuando sólo llegaron ocho. Entonces Diferencia visible; no marcar conforme ni programar pago total automáticamente.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F06-T08A` (pruebas), `F06-T08B` (implementación), `F06-T08C` (verificación). Evidencia prevista `evidence/F06/PUR-003/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### PUR-004 - Cuenta por pagar y programación
**Historia F06-US09.** Como bodega, necesito cuenta por pagar y programación para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Usuario; P0; relación original: PUR-003. Regla heredada preservada: Vencimiento, abonos y pagos sin duplicados.

**Entradas y validación:** payable, due date, approved payment, bank evidence. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Saldo = deuda aprobada menos pagos aplicados y notas válidas; programación no es pago ejecutado. Reintento de registro no duplica salida.

**Escenario positivo TC-PUR-004-P:** Dado Deuda 100000 y pago 30000 conserva saldo 70000. Cuando se completa la acción autorizada, entonces se cumple: Pago parcial mantiene saldo al proveedor Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-PUR-004-N:** Dado Registrar dos veces mismo pago bancario a proveedor. Entonces 409 DUPLICATE_PAYMENT; saldo permanece 70000.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F06-T09A` (pruebas), `F06-T09B` (implementación), `F06-T09C` (verificación). Evidencia prevista `evidence/F06/PUR-004/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

### CAP-001 - Precios unitarios comparables
**Historia F06-US10.** Como bodega, necesito precios unitarios comparables para cumplir la regla de negocio y su evidencia, dentro de mi sociedad/unidad autorizada.

**Fuente y prioridad:** Auditoría v 0.2; solicitud del propietario; fuentes R01-R15 segun tema; P0; relación original: INV-001;PUR-001. Regla heredada preservada: Unidad, presentacion, calidad, fecha, neto, impuestos, transporte, descuento y costo utilizable..

**Entradas y validación:** pack size, unit, quality, net/tax/freight, price date. Usar tipos y restricciones del diccionario. Ausencia de datos obligatorios produce rechazo explícito; no rellenar con información inventada.

**Ejecución y resultado:** Normalizar por unidad utilizable y calidad equivalente; separar cotización vigente de compra histórica. Costo total considera traslado y condiciones de impuesto aprobadas.

**Escenario positivo TC-CAP-001-P:** Dado Bidon 5L15000 y 1L4000 muestran3000/L y4000/L antes de otros costos. Cuando se completa la acción autorizada, entonces se cumple: Comparar bidones distintos muestra costo por litro; factura histórica no se llama cotización vigente. Verificar estado persistido, efecto y evidencia del requisito, no sólo mensaje visual.

**Escenario negativo TC-CAP-001-N:** Dado Comparar sólo precio por envase sin contenido o calidad. Entonces Comparación incompleta marcada, no recomendacion automática de compra.

**Autorización y trazabilidad:** aplicar el permiso, perfil candidato, alcance y control de aprobación de `seguridad/permisos.csv` para la operación invocada; denegar lo no concedido. Las operaciones públicas usan exclusivamente el alcance público definido, no un perfil interno. Los controles de gobierno sin API requieren la orden de trabajo y el aprobador de `sdd/ejecucion_y_gates.md`. D14 ratifica las asignaciones personales y umbrales, no permite ignorar controles mientras está pendiente. Registrar actor, fecha, versión, motivo y correlación, sin secretos. Correcciones financieras por reverso y compensación, no borrado de historia.

**Entregables verificables:** tareas `F06-T10A` (pruebas), `F06-T10B` (implementación), `F06-T10C` (verificación). Evidencia prevista `evidence/F06/CAP-001/`; estado actual **NO_EJECUTADA**. Dependencias externas se simulan sólo en pruebas identificadas; validación de producción sigue pendiente.

## Datos, pantallas, interfaces y fallas
Entidades propias: supplier, product, warehouse, stock_lot, stock_movement, supplier_price, purchase_order, purchase_line, receipt, receipt_line, stock_count.

Pantallas: UI-17, UI-18, UI-19; especificadas en `ux/pantallas.csv`. Operaciones propias: createProduct, createPurchase, approvePurchase, receivePurchase, adjustStock, transferStock, readStock, listPurchases. Estados/transiciones completos en `reglas/transiciones.csv` y contratos en `contratos/openapi.yaml`.

Eventos: purchase.approved, goods.received, stock.moved, stock.adjusted. Se publican en outbox dentro de la transacción; consumidores idempotentes. Si una dependencia falla, conservar PENDING/CONFLICT/DEGRADED y motivo; nunca informar confirmacion externa sin evidencia. Seguridad y correcciones financieras son transversales obligatorias.

## Alcance excluido
No habilita otros negocios ni todas las capacidades del proveedor por tener una cuenta conectada. No cambia políticas o porcentajes sin decisión documentada. Funciones opcionales permanecen NO_ACTIVADAS hasta sus pruebas y aprobación.

## Criterio de aceptacion
Todos los requisitos anteriores cubiertos por resultados positivos/negativos; contratos consistentes; pruebas de permisos y efectos financieros/inventario donde correspondan; migración ensayada; decisiones bloqueantes resueltas; revisor distinto al implementador. Un prototipo visual o checkbox no satisface el criterio.
