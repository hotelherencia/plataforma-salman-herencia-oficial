# Incremento 1 — cafetería: mesas con QR, pedidos y operación

Fecha: 2026-10-27. **PROPUESTA TÉCNICA** (no ratificada; el acta sigue sin firma y
corrige después). Módulo en memoria y sin red: `cafeteria_mesas_pos/`. Misma empresa
fija que el hotel (`EMP-SINTETICA-001`, una sola empresa, varias verticales). Puertos
de pago y documento tributario vacíos («no configurado»); el servicio no los invoca
para simular éxito. Datos sintéticos. La interfaz de pedidos de este módulo es el
adaptador real candidato para el puerto `PuertoPedidosCafeteria` del hotel (AT-007).

## Cola local drenada (ids de `specs/001-cafeteria-mesas-pos/acceptance.md`)

```
abrir_mesa → QR activo abre la carta de su mesa; QR revocado o modificado
   no accede a cuentas ajenas                                  [AT-001]
ítems separados y compartidos por cliente; editar lo enviado a
   cocina exige flujo autorizado (denegado con evidencia)      [AT-002]
confirmar pedido → una sola comanda con mesa, hora y estado;
   la misma clave no duplica                                    [AT-003]
dos cobros del mismo ítem: una sola imputación, el segundo falla
                                                               [AT-004, ADV-001]
factura con líneas erróneas → borrador pendiente; solo el rol
   aprobador valida y conserva la corrección del OCR           [AT-007]
venta con receta versionada → un movimiento por insumo una sola
   vez; sin receta el costo queda desconocido                  [AT-008]
margen por producto con costos conocidos; costo ausente →
   «no calculable», nunca cero                                 [AT-009, AC-US-CAF-002-01]
stock bajo mínimo → propuesta de compra (cantidades y costo);
   sin aprobación humana no se ejecuta; expira a 48 h; vencida
   se bloquea y exige revisión                                 [AT-011, AC-US-CAF-003-02]
anulación sobre umbral → una sola alerta con umbral registrado,
   sin sanción automática; repetir el hecho no duplica         [AT-012, AT-016,
                                                               AC-US-CAF-003-01]
reparto igual con residuo a la última parte: 10000/3 →
   3333, 3333, 3334; descuento y propina diferenciados; no crea
   comanda nueva; la parte pagada conserva monto y evidencia   [AT-015,
                                                               AC-US-CAF-001-01/02]
ledger: cada propuesta, rechazo, expiración y ejecución queda
   registrada con identidad y regla                            [AT-013 parcial local]
```

## Ejecutar las pruebas

Desde esta carpeta:

```bash
python -m unittest discover -s tests -t .
```

Resultado real del 2026-10-27: `Ran 19 tests`, `OK`, exit 0.

## Puerto vacío (no construido aquí)

AT-005 (SII), AT-006/ADV-003 (red y reconciliación bancaria real), AT-010
(archivo Eleventa real), AT-014 (adaptador del core), ADV-002 (retorno bancario).
