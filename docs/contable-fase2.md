# Módulo contable, fase 2: plan

Estado al 2026-11-19. Plan escrito antes de codificar; se ajusta por subapartado.

## 0. Punto de partida (lo que hay y lo que no)

- **La fase 1 no está en `main` ni en ninguna rama remota.** No existen apertura ni cierre de caja, turnos, retiros de
  efectivo, medios de pago, cierre diario ni la corrección horaria de «Caja del día» (`cobro.caja_del_dia` sigue usando
  `p.creado_en::date`, es decir UTC). Las subpartes 2.3 y 2.4 consolidan el cierre diario y 2.6 cruza los retiros, así
  que dependen de ella. Ver «Dependencias» abajo.
- Existen: `pagos` (monto, clave, `modo` manual/pasarela, estado), `cargos` append-only, `liquidaciones`,
  `reserva_noches` (precio congelado por noche), IVA editable (`ajustes_plataforma.iva_porcentaje`, `servicio/iva.py`),
  `ajustes` (JSON editable en Configuración, `servicio/ajustes.py`), `auditoria`, roles `admin_hotel`
  (`roles.con_admin_hotel`), y las facturas **de proveedor** (0040, recibidas). **No** existe registro de boletas ni
  facturas **emitidas** al huésped ni maestro de clientes.
- Desde la épica ADP el dominio (`ServicioHotelInventario`) decide cuenta, pagos y liquidación; PostgreSQL proyecta.
  La fase 2 es contabilidad sobre esa proyección: **no recalcula reglas del hotel**, las lee. Lo que el dominio no
  modela (imputación por noche, documento tributario, cliente) vive en tablas nuevas, append-only.
- Front sin librería de gráficos ni de planillas (`next`, `react`, `react-dom` y nada más). Backend sin librería `.xlsx`.

## 1. Reglas que se mantienen en todo el módulo

Sin ítems de menú nuevos (pestañas dentro de Caja y Reportes); ninguna política ni monto en el código (todo en
`ajustes` o tablas editables por `admin_hotel`); CLP enteros; fechas y cortes de día en America/Santiago; todo
movimiento de dinero auditado (quién, cuándo, antes y después) e inmutable al cerrar (se corrige con ajustes); sin
número de tarjeta ni CVV (marca y 4 últimos); textos al huésped con «Llegada» y «Salida»; sin JSON a la vista, miles
con punto y fechas dd-mm-aaaa.

## 2. Dependencias y decisiones abiertas

| Tema | Decisión propuesta | Falta |
|---|---|---|
| Fase 1 | Construirla primero **solo** si no existe en otro lugar (otro agente trabaja en paralelo) | Confirmar dónde está |
| `.xlsx` | Agregar `openpyxl` a `servicio/requirements.txt` y a los dos `pyproject.toml` | Aprobar la dependencia |
| Gráficos | Componentes SVG propios en `front/lib` (sin dependencia nueva) | Aprobar |
| Emisión al SII | Fuera de alcance: se **registran** boletas y facturas (folio, neto, IVA, total); no se envía nada al SII | Confirmar |
| Folios | Los carga y valida el mantenedor (rango por tipo de documento); no se generan en código | Definir origen del folio |

## 3. Subapartados

Migraciones: siguiente número libre al construir (hoy 0041 y más; 0035 la usa la cuenta vacía y 0040 las facturas de
proveedor). Cada subapartado trae migración, modelo, endpoints con rol, pestaña, tests de backend y un E2E corto.

### 2.1 Imputación de pagos y abonos

- `clientes` (id, tipo persona|empresa, rut único normalizado, razón social, giro, correo, activo).
- `documentos_venta` (id, tipo boleta|factura|nota_credito, folio, fecha, cliente_id, reserva_id, neto, iva, total,
  referencia a otro documento, estado, actor). Append-only; la corrección es una nota de crédito.
- `imputaciones_pago` (id, pago_id, reserva_id, habitacion_id, noche NULL, cliente_id, monto_clp, tipo
  anticipo|consumo|ajuste, documento_id, actor, creado_en). Un pago se reparte en una o varias noches; un anticipo
  sin noche se aplica al consumo de cada noche (noche a noche, al asentarse en la Llegada).
- `GET /hotel/reservas/{id}/saldo`: total, abonado (anticipos), pagado (consumo imputado) y pendiente.
- `POST /hotel/reservas/{id}/pagos` acepta `documento: {tipo, rut?, razon_social?, giro?}`; factura exige los tres.
- Front: pestaña «Imputación» en Caja y bloque de saldo siempre visible en el detalle de la reserva.

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
