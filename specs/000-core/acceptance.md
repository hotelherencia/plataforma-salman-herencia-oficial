# Catálogo de aceptación — Core transversal

Escenarios propuestos; ninguno ejecutado sobre producto. Cada ID tiene namespace de feature. Para cada FR se prueba resultado autorizado, denegación, duplicación y recuperación; los datos deben ser autorizados y minimizados.

| Prueba | Requisito | Dado / Cuando / Entonces |
|---|---|---|
| AT-001 | FR-001 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Una identidad con membresía vencida solicita datos: se deniega; la membresía vigente solo habilita su empresa. |
| AT-002 | FR-002 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Usuario, worker y agente de A usan identificador de B: se deniega sin revelar existencia y se registra el intento. |
| AT-003 | FR-003 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Diez retornos repetidos y desordenados de una orden producen una única imputación; monto u orden incoherentes pasan a revisión sin saldo acreditado. |
| AT-004 | FR-004 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Una operación cubierta por voucher o anticipo ya documentado no genera duplicado; una observación documental conserva pago y alerta para regularización según política. |
| AT-005 | FR-005 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Una acción crítica produce evidencia con actor, tenant, política, aprobación y resultado; alteración del registro es detectable por el mecanismo seleccionado. |
| AT-006 | FR-006 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Un operador sin permiso intenta leer certificado o adjunto ajeno: se deniega; vence el plazo de retención aprobado y se aplica disposición registrada. |
| AT-007 | FR-007 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Un agente cambia el monto después de la aprobación: autorización inválida, operación denegada y nueva aprobación requerida. |
| AT-008 | FR-008 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: El proveedor cae tras enviar confirmación: el estado queda desconocido/pendiente; al consultar y reconciliar se aplica un solo resultado. |
| AT-009 | FR-009 | Dadas precondiciones del requisito y actor/tenant autorizados, cuando se ejecuta el flujo: Un consumidor de versión anterior recibe cambio incompatible: se mantiene versión compatible o se impide publicación hasta completar prueba y migración. |
| ADV-001 | NFR-001/002/003 | Un usuario, worker y agente del tenant A intentan leer/escribir un recurso de B: todos reciben denegación sin revelar existencia. |
| ADV-002 | NFR-001/002/003 | Repetir confirmación bancaria diez veces mantiene un único efecto y permite auditoría. |
| ADV-003 | NFR-001/002/003 | Cambiar monto tras aprobación invalida autorización; proveedor desconectado queda pendiente y bloquea ejecución. |

## Criterios de éxito y evidencia

| Criterio | Verificación pendiente |
|---|---|
| SC-001 | Medir «Cero accesos entre tenants en la batería adversarial aprobada». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-002 | Medir «Un único efecto financiero ante diez repeticiones del mismo resultado». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |
| SC-003 | Medir «Toda acción crítica tiene actor, tenant, evidencia y resultado auditables». Registrar muestra, ventana temporal, denominador, errores y línea base; conservar conteos y evidencia. No hay medición actual. |

## Escenarios competitivos por historia

Propuestos; no ejecutados sobre producto. Los números de ejemplo prueban aritmética y control, no fijan política comercial.

### US-CORE-001 / H1

- AC-US-CORE-001-01: Dado conector habilitado para A, cuando B intenta usar su referencia, entonces se deniega sin revelar secretos.
- AC-US-CORE-001-02: Dado plan sin permiso de leads, cuando se solicita captura, entonces se informa capacidad no habilitada y se registra motivo.

### US-CORE-002 / H2

- AC-US-CORE-002-01: Dado pago desconocido, cuando llega confirmación repetida diez veces, entonces se aplica un solo efecto y el caso se cierra con evidencia.
- AC-US-CORE-002-02: Dado pago rechazado posterior a operación offline registrada, cuando se concilia, entonces no figura autorizado ni se borra la deuda.

### US-CORE-003 / H3

- AC-US-CORE-003-01: Dada aprobación por 10000 CLP, cuando la propuesta cambia a 11000, entonces no se ejecuta con el permiso anterior.
- AC-US-CORE-003-02: Dado conector de lectura, cuando una respuesta solicita escritura, entonces la capa de autorización deniega y registra.

| Prueba | Requisito | Escenario de resultado |
|---|---|---|
| AT-010 | FR-010 | Dado conector sin permiso por plan o perteneciente a otra empresa, cuando se solicita operación, entonces se deniega; habilitar exige evidencia, versión y tenant verificado. Denegar recurso de otro tenant y conservar evidencia. |
| AT-011 | FR-011 | Dado intento pendiente con evento autorizado vigente, cuando llegan diez duplicados y un evento antiguo de inicio, entonces conserva una única imputación y no retrocede; una devolución posterior requiere transición y autorización propias. Denegar recurso de otro tenant y conservar evidencia. |

NFR-006 se verifica por los mismos AC: fuente sin vigencia, extracción ambigua o transición sin evidencia no permite compromiso; la ruta manual mantiene las validaciones.

## Aceptación de profundización funcional

Casos adicionales propuestos; ninguna prueba de producto fue ejecutada.

### RF-CORE-01 / US-CORE-003

- AC-US-CORE-003-03: Dada herramienta de contacto con flag de envío, cuando solo se autorizó guardar datos, entonces el adaptador no envía correo y registra los efectos excluidos.
- AC-US-CORE-003-04: Dada página de contrato con placeholder o efectos desconocidos, cuando se intenta habilitar la herramienta, entonces queda bloqueada sin llamar al destino.
- AC-US-CORE-003-05: Dada notificación de cuenta A repetida con referencia de B, cuando se procesa, entonces no accede a B ni repite comunicación; registra discrepancia para revisar.

| Prueba | Requisito | Escenario propuesto |
|---|---|---|
| AT-012 | FR-012 | Dada herramienta de contacto con flag de envío, cuando solo se autorizó guardar datos, entonces el adaptador no envía correo y registra los efectos excluidos. Probar también permiso insuficiente y referencia de otro tenant. |
