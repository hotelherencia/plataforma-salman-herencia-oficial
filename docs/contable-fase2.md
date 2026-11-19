# Módulo contable, fase 2: plan

Estado al 2026-11-19. Plan escrito antes de codificar; se ajusta por subapartado.

## 0. Punto de partida (lo que hay)

- **La fase 1 (caja) ya está en `main`** (migración `0050_caja_y_contabilidad.sql`, `servicio/contabilidad.py`,
  `servicio/rutas/caja.py`): turnos con arqueo y entrega entre turnos, medios de pago, retiros para depósito, reverso
  de pagos, cierre diario con conciliación por habitación, documento (boleta o factura con receptor) y voucher sin PAN,
  «Caja del día» en hora de Chile. Su diseño está en el informe de la fase 1; esta fase 2 **reutiliza** esas tablas y
  no las duplica: `pagos.documento_*` y `receptor` son el registro del documento, `caja_movimientos` (retiros) lo que
  cruza la conciliación bancaria y `cierres_diarios.resumen` lo que consolida el cierre mensual.
- Desde la épica ADP el dominio (`ServicioHotelInventario`) decide cuenta, pagos y liquidación; PostgreSQL proyecta.
  La fase 2 es contabilidad sobre esa proyección: **no recalcula reglas del hotel**, las lee. Lo que el dominio no
  modela (imputación por noche, cliente) vive en tablas nuevas, solo de agregar.
- Nombres: donde la fase 1 propuso otros nombres para la fase 2, manda este documento (`imputaciones_pago`, no
  `pago_imputaciones`). Módulos nuevos: `servicio/clientes.py` e `servicio/imputacion.py` (el `contabilidad.py` es de la
  fase 1). Migraciones de la fase 2: desde `0051`.
- Front sin librería de gráficos ni de planillas; backend sin librería `.xlsx` (se aprobó `openpyxl` y SVG propio).

## 1. Reglas que se mantienen en todo el módulo

Sin ítems de menú nuevos (pestañas dentro de Caja y Reportes); ninguna política ni monto en el código (todo en
`ajustes` o tablas editables por `admin_hotel`); CLP enteros; fechas y cortes de día en America/Santiago; todo
movimiento de dinero auditado (quién, cuándo, antes y después) e inmutable al cerrar (se corrige con ajustes); sin
número de tarjeta ni CVV (marca y 4 últimos); textos al huésped con «Llegada» y «Salida»; sin JSON a la vista, miles
con punto y fechas dd-mm-aaaa.

## 2. Decisiones tomadas

| Tema | Decisión |
|---|---|
| Fase 1 | Ya está en `main`; no se duplica. |
| `.xlsx` | `openpyxl` en `servicio/requirements.txt` y en los dos `pyproject.toml` (aprobado). |
| Gráficos | Componentes SVG propios en `front/lib`, sin dependencia nueva (aprobado). |
| Emisión al SII | Fuera de alcance: se **registran** boletas y facturas (folio, neto, IVA, total); no se envía nada. |
| Abono antes de la Llegada | Se mide contra el total de las noches, no contra la cuenta vacía del dominio: no es «exceso» y no pide confirmación. Pagar más que el total sí la pide. (Cambia un criterio de la fase 1.) |
| Cobrado con la caja cerrada | Lo cobrado sin turno entra en la cuadratura del turno que se abre después (desde que cerró el anterior). |

## 3. Subapartados

Migraciones: siguiente número libre al construir (hoy 0041 y más; 0035 la usa la cuenta vacía y 0040 las facturas de
proveedor). Cada subapartado trae migración, modelo, endpoints con rol, pestaña, tests de backend y un E2E corto.

### 2.1 Imputación de pagos y abonos (hecho)

- `clientes` (migración `0051`): RUT solo con números y dígito verificador (`CHECK`), único; el nombre se compara sin
  tildes ni mayúsculas. El mismo RUT con otro nombre responde 409, en el pago con factura y al crear una reserva.
- `imputaciones_pago`: pago → habitación, noche, cliente y monto (`anticipo`, `aplicacion_anticipo`, `consumo`,
  `ajuste`). Solo de agregar; el reverso de un pago agrega filas negativas con `revierte_id`.
- Antes de la Llegada el pago es anticipo; en la Llegada se aplica noche a noche; en la estadía va a las noches más
  antiguas, luego a consumos sueltos y el resto queda como abono.
- `GET /hotel/reservas/{id}/saldo` (total, abonado, pagado, pendiente y detalle por noche) y
  `GET /hotel/contabilidad/movimientos` (cargos, reversos y pagos con quién los hizo, sin depender de la caja).
- Front: bloque de saldo en Registrar pago, pestaña «Cargos y pagos» en Caja y validación del RUT.
- El documento (boleta o factura con receptor) y el folio siguen siendo los de la fase 1 en `pagos`.

### 2.2 Políticas de crédito por cliente

- `clientes_credito` (cliente_id, modalidad `credito|pago_al_registrarse|garantia_tarjeta`, limite_clp, plazo_dias,
  vigente_desde, actor). Las modalidades, topes y plazos permitidos salen del ajuste `politica_credito` (mantenedor).
- Cuentas por cobrar con antigüedad 0-30, 31-60, 61-90 y más de 90 días, calculada desde la fecha del documento.
- Alertas al superar el límite o vencer el plazo (reutiliza `avisos`).
- Front: pestaña «Cuentas por cobrar» en Caja; edición en Configuración.

### 2.3 Cuadratura diaria

- Vista calculada por día: habitaciones ocupadas, noches pagadas o con crédito y abonos aplicados. Diferencias:
  noche ocupada sin pago ni crédito, pago sin noche, abono sin aplicar, con enlace a la reserva.
- Se integra al cierre diario (fase 1): advierte si no calza y solo deja cerrar con justificación escrita y auditada.

### 2.4 Cierre mensual

- `cierres_mensuales` (mes, estado abierto|cerrado, totales congelados en JSON, actor, reabierto_por, motivo).
  Cierra consolidando los cierres diarios; con el mes cerrado, las escrituras con fecha de ese mes se rechazan (solo
  `admin_hotel` reabre y queda auditado).
- Exportación `.xlsx`: hoja matriz habitaciones × días (ocupada/libre y monto, totales por fila y columna) y hojas de
  ventas por medio de pago, por tipo de documento, abonos, retiros y depósitos.

### 2.5 Reportería y dashboard ejecutivo

- Ocupación % por habitación y por tipo, ADR, RevPAR, ventas por medio de pago y por canal, con rango de fechas y
  comparación con el período anterior. Informe mensual exportable a Excel (PDF si se aprueba una librería).
- Pestaña «Resumen» en Reportes con SVG propio.

### 2.6 Conciliación bancaria

- `cartolas` y `movimientos_banco` (importados de CSV o Excel; el mapeo de columnas por banco es un ajuste).
- Cruce con retiros de caja para depósito, transferencias recibidas y liquidaciones de tarjeta (comisión y fecha de
  abono como datos del mantenedor). Estados conciliado, parcial, pendiente; conciliación manual con justificación.

### 2.7 Conciliación tributaria

- Reporte diario y mensual por tipo de documento (neto, IVA con la tasa vigente al emitir, total). Una venta queda en
  el mes de su fecha aunque el abono llegue en el mes siguiente: aparece «en tránsito» en la conciliación bancaria.
  Las notas de crédito restan del mes que corresponde. Resumen de débito fiscal para el F29, sin enviar nada al SII.

## 4. Orden de trabajo y pruebas

1. Resolver la dependencia con la fase 1. 2. Subapartados 2.1 a 2.7 en orden, un commit por subapartado.
3. Antes de cada push: suite del servicio completa, build del front y E2E corto del subapartado (Node 24).
4. Script de seed local con habitaciones, reservas, abonos, pagos mixtos, un cliente con crédito y una cartola de
   ejemplo para cuadrar todo un mes de prueba. En producción solo registros con nombre «PRUEBA G».
