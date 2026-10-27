# Contrato lógico — cafetería (mesas, pedidos y operación)

Fecha: 2026-10-27. **PROPUESTA TÉCNICA** (no ratificada). Contrato del módulo
`cafeteria_mesas_pos/`; sirve a `001/H1/T-DIS`. Revisado contra el código y sus 19 pruebas.

## Permisos y tenant

- Empresa única `EMP-SINTETICA-001`; otra empresa → `AccesoDenegado`.
- Acceso por token QR de mesa; QR revocado o inexistente → `AccesoDenegado` con
  registro en el ledger.
- Aprobaciones (gastos, compras): solo rol `administrador`.

## Estados

- Mesa: `activa | revocada`.
- Pedido/comanda: `abierto → enviado`; una sola comanda por clave.
- Gasto: `pendiente → aprobado` (con correcciones del OCR conservadas).
- Propuesta de compra: `pendiente → aprobada | ejecutada | rechazada`; `expirada`
  a las 48 h (bloquea su uso y exige revisión).
- Ítem de cuenta: pagado o no; reparto con partes pagadas conservadas.

## Idempotencia y concurrencia

- Cerrojo global por servicio; `pagar_items` permite una sola imputación por ítem.
- `confirmar_pedido(clave)` y `vender(clave_venta)`: repetición devuelta el efecto
  existente (sin segunda comanda ni segundo movimiento de insumos).
- `alerta_anulacion(hecho_id)`: una sola alerta por hecho.
- Reparto: `divmod(total, partes)` con residuo a la última parte; partes pagadas
  no se recalculan ni se reinicia su cobro.

## Errores (excepciones)

`AccesoDenegado` · `FlujoAutorizadoRequerido` (ítem enviado a cocina) ·
`ValueError` (ítem ya pagado, parte ya pagada, propuesta expirada, sin ítems).

## Puertos (vacíos)

Pago y documento tributario responden «no configurado»; el servicio no los invoca.
