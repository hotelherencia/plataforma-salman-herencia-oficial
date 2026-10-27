# Contrato lógico — H1 (reserva y pago) y H2 (operación de estadía)

Fecha: 2026-10-27. **PROPUESTA TÉCNICA** (no ratificada). Contrato del módulo
`hotel_inventario/` revisado contra el código vigente; sirve a `002/H1/T-DIS` y
`002/H2/T-DIS`. Producer y consumidor son hoy el mismo módulo y sus pruebas.

## Permisos y tenant

- Empresa única `EMP-SINTETICA-001`; toda llamada con otra empresa → `AccesoDenegado`.
- El establecimiento pertenece a la empresa; la reserva guarda `self._empresa.id`.
- Documento del huésped: acceso solo con rol `recepcion`/`administrador` y queda registrado.

## Estados

- Unidad: `limpia | sucia | inspeccionada` (vendibles), `ocupada` (vendible solo
  fuera de su rango; el rango se protege por solape), `bloqueada | fuera_de_servicio`
  (fuera de todo el cupo), más banda `mantenimiento` (fuera de todo el cupo).
- Reserva: `confirmada → hospedada → salida`; `pendiente` (oferta sin vigencia, sin
  cupo); `cancelada`; `rechazada` (no entran a la estadía).
- Cargo: inmutable (`cargo | reverso`); corrección = reverso que referencia al original.
- Devolución: `pendiente → autorizada → efectuada` (aprobador registrado; efectuar
  exige operación financiera confirmada).
- Tarea: `pendiente → completada` (limpieza y mantención).
- Oferta: `emitida_en` + `vigente_hasta` (15 minutos); vencida no confirma cupo.

## Idempotencia (claves)

- Reserva concurrente sobre la última unidad: cerrojo; máximo una confirmación.
- `asentar_cargo`, `registrar_pago`, `pedir_a_habitacion`, `confirmar_pedido`:
  clave idempotente; repetición devuelve el efecto existente.
- `aplicar_cambio`: reintento de la misma propuesta = consulta de estado, sin
  segundo cargo; propuesta obsoleta o de otra reserva se rechaza.
- Cancelación: una sola por reserva (`ReservaNoCancelable` en segundo intento).

## Errores (excepciones)

`AccesoDenegado` · `CheckInNoPermitido` (hora, mantenimiento, unidad no preparada) ·
`CheckInIncompleto` (documento faltante; deriva a recepción) · `CheckOutNoPermitido` ·
`NocheNoAsentable` (fuera de rango o duplicada) · `ReservaNoCancelable` ·
`CargoNoReversible` · `ValueError` para recursos inexistentes y montos inválidos.

## Puertos (vacíos, sin simular éxito)

PMS, canal, pago, documento tributario y pedidos de cafetería responden
«no configurado»; el servicio no los invoca para fingir éxito (pedidos sí se
consulta la interfaz: sin ella el servicio se declara no disponible).
