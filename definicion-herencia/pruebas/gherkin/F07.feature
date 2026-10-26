# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Aseo, inspección y lavandería

  @OPS-001 @TC-OPS-001-P
  Escenario: TC-OPS-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Una salida origina una tarea de aseo con mismo source_key.
    Entonces Checkout genera una tarea de salida sin duplicados

  @OPS-001 @TC-OPS-001-N
  Escenario: TC-OPS-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Recibir dos veces el mismo checkout.
    Entonces Una tarea, no dos ni doble incentivo.

  @OPS-002 @TC-OPS-002-P
  Escenario: TC-OPS-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Persona asignada completa checklist desde móvil y queda pendiente de inspección.
    Entonces Ejecutor registra la tarea desde móvil con su identidad

  @OPS-002 @TC-OPS-002-N
  Escenario: TC-OPS-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dispositivo offline envia tarea reasignada a otra persona.
    Entonces Conflicto visible, no sobrescritura; supervisor concilia ejecución real.

  @OPS-003 @TC-OPS-003-P
  Escenario: TC-OPS-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Inspección aprobada convierte habitación limpia a READY.
    Entonces Falla de inspección no declara habitación lista

  @OPS-003 @TC-OPS-003-N
  Escenario: TC-OPS-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Checklist incompleto o falla de higiene y solicitud de liberar.
    Entonces No entrega disponible; hallazgo y retrabajo asignados.

  @OPS-004 @TC-OPS-004-P
  Escenario: TC-OPS-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Dos jabones y dos toallas: baja dos jabones, mueve dos toallas.
    Entonces Repetir tarea no descuenta insumos dos veces

  @OPS-004 @TC-OPS-004-N
  Escenario: TC-OPS-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reenviar registro de consumo con mismo device event.
    Entonces Una sola afectacion y resultado previo; stock no disminuye otra vez.

  @OPS-005 @TC-OPS-005-P
  Escenario: TC-OPS-005-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Limpieza de sala se imputa a areas comunes.
    Entonces Limpieza comun no se imputa a una habitación arbitraria

  @OPS-005 @TC-OPS-005-N
  Escenario: TC-OPS-005-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Usuario intenta asignar todas las limpiezas comunes a cuarto vacío para mejorar otros margenes.
    Entonces Exigir destino válido o ajuste gerencial aprobado, auditar.

  @LIN-001 @TC-LIN-001-P
  Escenario: TC-LIN-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Toalla pasa limpia-asignada-usada y total patrimonial no cambia.
    Entonces Una toalla usada no desaparece del patrimonio textil

  @LIN-001 @TC-LIN-001-N
  Escenario: TC-LIN-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Restar una pieza del patrimonio cada noche ocupada.
    Entonces Validación rechaza movimiento de baja sin causa y autorización.

  @LIN-002 @TC-LIN-002-P
  Escenario: TC-LIN-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Enviar dos sábanas, recibir una buena: una pendiente.
    Entonces Dos piezas enviadas y una recibida dejan una pendiente

  @LIN-002 @TC-LIN-002-N
  Escenario: TC-LIN-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Intentar cerrar lote con una faltante sin resolución.
    Entonces 409 LOT_UNBALANCED; pendiente visible al proveedor.

  @LIN-003 @TC-LIN-003-P
  Escenario: TC-LIN-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Permanencia sin cambio de sábanas no genera envio ficticio.
    Entonces Una permanencia sin cambio no crea lavado ficticio

  @LIN-003 @TC-LIN-003-N
  Escenario: TC-LIN-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Tarea marcada no cambiada genera automáticamente dos sábanas usadas.
    Entonces Prueba detecta inconsistencia; movimiento bloqueado.

  @LIN-004 @TC-LIN-004-P
  Escenario: TC-LIN-004-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Lote 10000 repartido 6000/4000 mantiene total.
    Entonces Distribución del lote suma su costo total sin duplicar personal

  @LIN-004 @TC-LIN-004-N
  Escenario: TC-LIN-004-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Repartos suman 11000 o kilogramo se convierte a piezas sin base.
    Entonces No cerrar costeo; corregir regla o dejar costo no asignado.
