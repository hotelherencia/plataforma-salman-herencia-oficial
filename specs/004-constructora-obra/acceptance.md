# Catálogo de aceptación — Constructora y control de obra

Escenarios propuestos; ninguno ejecutado sobre producto. Cada ID tiene namespace de feature. Para cada FR se prueba resultado autorizado, denegación, duplicación y recuperación; los datos deben ser autorizados y minimizados.

| Prueba | Requisito | Dado / Cuando / Entonces |
|---|---|---|
| AT-001 | FR-010 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Reporte por voz/foto queda como extracción con partida, fecha y evidencia; ubicación solo cuando proceda; retroceso no sobrescribe dato aprobado. |
| AT-002 | FR-011 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Con presupuesto y programación aprobados, cálculo del desvío usa denominador y umbral ratificados; programado cero no produce división por cero ni alerta inventada. |
| AT-003 | FR-012 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Necesidad de material genera solicitud con cantidad/proveedor/precio de referencia y versión; sin aprobación válida no hay envío ni compra. |
| AT-004 | FR-015 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Cambiar presupuesto crea nueva versión y conserva línea base, unidades y aprobador; gasto ejecutado no se interpreta como avance físico. |
| AT-005 | FR-016 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Inspección con observación registra evidencia, responsable y decisión humana; asistente no certifica seguridad ni cierra observación sin inspector autorizado. |
| AT-006 | FR-017 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Recepción y consumo de material aprobados generan movimientos únicos por obra; repetir reporte no duplica stock y diferencia con conteo físico se concilia. |
| AT-007 | FR-018 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Usuario de empresa comercial no consulta fotos, trabajadores ni presupuesto de constructora sin convenio/permiso; toda decisión de obra conserva actor y evidencia. |
| ADV-001 | NFR-001/002/003 | Reporte contradice avance anterior: conservar ambos y requerir aprobación de rectificación. |
| ADV-002 | NFR-001/002/003 | Voz solicita comprar material e incluye instrucciones: solo crear borrador, sin orden a proveedor. |
| ADV-003 | NFR-001/002/003 | Empresa constructora no consulta clientes ni documentos comerciales de inmobiliaria sin autorización explícita. |

## Criterios de éxito y evidencia

| Criterio | Verificación pendiente |
|---|---|
| SC-008 | Medir «Avance por partida disponible el día del reporte; objetivo heredado, condicionado a revisión». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-010 | Medir «Cero compras ejecutadas sin aprobación válida en pruebas adversariales». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-011 | Medir «100 % de rectificaciones conserva evidencia y autor en la batería de aceptación». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |

## Escenarios competitivos por historia

Propuestos; no ejecutados sobre producto. Los números de ejemplo prueban aritmética y control, no fijan política comercial.

### US-OBR-003 / H3

- AC-US-OBR-003-01: Dada nota que dice comprar e incluye instrucciones, cuando se procesa, entonces solo crea borrador con campos pendientes y no envía orden.
- AC-US-OBR-003-02: Dada IA desactivada, cuando se informa avance manualmente, entonces el reporte sigue disponible y conserva autor/evidencia con mismas validaciones.

### US-OBR-004 / H4

- AC-US-OBR-004-01: Dado ítem de inspección fallido, cuando se crea observación, entonces conserva vínculo, responsable y estado; el reportante sin permiso no puede cerrarla.
- AC-US-OBR-004-02: Dada orden de 10 unidades y recepción de 6, cuando se confirma, entonces quedan 4 pendientes; repetir mismo evento no recibe 12.

| Prueba | Requisito | Escenario de resultado |
|---|---|---|
| AT-008 | FR-019 | Dado ítem fallido de inspección, cuando se crea observación, entonces conserva vínculo/responsable/plazo; reportante sin permiso no cierra y propuesta de solución exige validación del inspector para cierre o reapertura. Denegar recurso de otro tenant y conservar evidencia. |
| AT-009 | FR-020 | Dada orden aprobada de 10 unidades y recepción parcial de 6, cuando se confirma dos veces el mismo evento, entonces se reciben 6 y quedan 4; unidad/precio/versión discrepantes requieren revisión sin compra automática. Denegar recurso de otro tenant y conservar evidencia. |

NFR-006 se verifica por los mismos AC: fuente sin vigencia, extracción ambigua o transición sin evidencia no permite compromiso; la ruta manual mantiene las validaciones.

## Aceptación de profundización funcional

Casos adicionales propuestos; ninguna prueba de producto fue ejecutada.

### RF-OBR-01 / US-OBR-003

- AC-US-OBR-003-03: Dados dos partes legítimos de turnos distintos en una obra/día y un reenvío del primero, cuando se reciben, entonces conserva ambos aportes y no duplica el reenvío.
- AC-US-OBR-003-04: Dado porcentaje 40 % acumulado y nuevo reporte 45 % acumulado de la misma partida, cuando se revisa, entonces no produce 85 % por sumarlos y requiere la base/unidad definida.
- AC-US-OBR-003-05: Dada falta de conexión para transcribir, cuando se carga evidencia, entonces no se marca transcrita/aprobada; la vía manual soportada conserva mismos permisos y revisión.

### RF-OBR-02 / US-OBR-004

- AC-US-OBR-004-03: Dada orden de diez unidades y entrega física de seis con cinco aceptadas y una rechazada a reponer por política configurada, cuando se valida, entonces stock aumenta cinco y pendientes de suministro son cinco, con rechazo documentado.
- AC-US-OBR-004-04: Dada misma entrega recibida dos veces por reintento, cuando se registra, entonces no duplica stock; una segunda entrega con identidad distinta sí se evalúa como nueva.
- AC-US-OBR-004-05: Dada devolución de una unidad previamente aceptada, cuando se aprueba, entonces conserva recepción y registra movimiento de devolución; no se infiere abono financiero ni cambio de contrato.

### RF-OBR-03 / US-OBR-004

- AC-US-OBR-004-06: Dado presupuesto de ejemplo 100 y compromiso total 50 que ya incluye devengo 20 y pago 10, cuando se calcula disponible sin otras obligaciones, entonces es 50 y no 20 al descontar los tres estados otra vez.
- AC-US-OBR-004-07: Dada modificación aprobada de presupuesto, cuando se compara avance/costo histórico, entonces conserva línea base, versión vigente y motivo/aprobador; no reescribe el pasado.
- AC-US-OBR-004-08: Dada partida sin fórmula o clasificación válida, cuando se evalúa compra, entonces indica control no evaluable y requiere revisión, sin aprobar automáticamente.

### RF-OBR-04 / US-OBR-004

- AC-US-OBR-004-09: Dado solucionador sin permiso de aceptar, cuando informa reparación lista, entonces queda por revisar y no cerrada; el inspector puede no aceptar con motivo.
- AC-US-OBR-004-10: Dado comentario generado por IA que cambia una especificación técnica, cuando se adjunta al caso, entonces no se convierte en respuesta oficial ni modifica presupuesto o programa.
- AC-US-OBR-004-11: Dada observación reabierta por nueva evidencia, cuando se inspecciona historial, entonces conserva cierre previo, responsable, evidencia y motivo de reapertura.

| Prueba | Requisito | Escenario propuesto |
|---|---|---|
| AT-010 | FR-021 | Dados dos partes legítimos de turnos distintos en una obra/día y un reenvío del primero, cuando se reciben, entonces conserva ambos aportes y no duplica el reenvío. Probar también permiso insuficiente y referencia de otro tenant. |
| AT-011 | FR-022 | Dada orden de diez unidades y entrega física de seis con cinco aceptadas y una rechazada a reponer por política configurada, cuando se valida, entonces stock aumenta cinco y pendientes de suministro son cinco, con rechazo documentado. Probar también permiso insuficiente y referencia de otro tenant. |
| AT-012 | FR-023 | Dado presupuesto de ejemplo 100 y compromiso total 50 que ya incluye devengo 20 y pago 10, cuando se calcula disponible sin otras obligaciones, entonces es 50 y no 20 al descontar los tres estados otra vez. Probar también permiso insuficiente y referencia de otro tenant. |
