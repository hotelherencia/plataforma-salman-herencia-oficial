# Informe Forense: Reserva `RSV-374cbd57abf6`

## Resumen ejecutivo
La aritmética del saldo es exacta (`$205.500` cargos netos − `$605.000` pagados = `-$399.500` a favor del huésped): **no existe un bug de doble resta ni de suma en el cálculo del servidor**. El descuadre proviene de una combinación de **operación** (3 pagos en 9 minutos por `$100.000`, `$405.000` y `$100.000`, donde `$405.000` coincide exactamente con los 5 cargos vigentes antes de los reversos) y **fallas de diseño**: (1) `validar_datos_pago` (`servicio/contabilidad.py:145`) aceptaba pagos manuales sin `medio`, dejándolos como `no_informado` y sin movimiento de caja (`servicio/contabilidad.py:520`), y (2) `reversar_cargo` (`servicio/hotel_sql.py:617`) solo anula el cargo en `cargos` sin advertir ni ofrecer devolución de pagos ya cobrados. Los logs históricos de Railway del 18/11 rotaron (retención de 15 deploys) y la BD de producción (`postgres.railway.internal`) no expone proxy TCP público, por lo que las consultas de `consultas.sql` quedan listas para ejecutarse en entorno interno con `SET TRANSACTION READ ONLY`.

## Evidencia de código (archivo y línea)
- **Cálculo de cuenta y saldo:** `servicio/cobro.py:274` (`cargos_netos_clp = neto`, `pagado_clp = pagado`, `saldo_clp = neto - pagado`).
- **Reverso de cargo:** `servicio/rutas/hotel.py:769-793` y `servicio/hotel_sql.py:617-653`. Solo inserta un cargo `tipo='reverso'` en `cargos`; **no toca `pagos` ni `caja_movimientos`**.
- **Registro de pago manual:** `servicio/rutas/hotel.py:378-413` y `servicio/cobro.py:87-155`. Deduplica por `(reserva_id, clave)` e `Idempotency-Key`, pero el front (`front/app/hotel/pago/page.js:139-140`) regenera `claveCobro` tras cada éxito, permitiendo múltiples pagos seguidos si el operador reenvía o cobra de nuevo.
- **Pagos sin medio ni movimiento de caja:** `servicio/contabilidad.py:145` (`medio = datos.get("medio") or "no_informado"`) y `servicio/contabilidad.py:520` (`if medio == "no_informado" and preparado["turno_id"] is None: return`).
- **Devolución formal de saldo a favor:** `servicio/rutas/hotel.py:416-444` y `servicio/contabilidad.py:586-648` (`POST /hotel/reservas/{id}/devolucion`).

## Cronología reconstruida
1. **18/11 14:52:** Cargo automático de alojamiento: `Alojamiento 1 noches` por `$55.000`.
2. **18/11 14:53:** Se registran 4 cargos de minibar: `$100.000`, `$100.000`, `$100.000`, `$50.000`. Total acumulado de cargos: `$405.000`.
3. **18/11 15:00:** Pago #1 por `$100.000` (`no_informado` / `pendiente`). Pagado: `$100.000`, Saldo pendiente: `$305.000`.
4. **18/11 15:01:** Pago #2 por `$405.000` (`no_informado` / `pendiente`, calza con el total de cargos `$405.000`, confirmado con exceso). Pagado: `$505.000`, Saldo a favor: `$100.000`.
5. **18/11 15:09:** Pago #3 por `$100.000` (`no_informado` / `pendiente`). Pagado: `$605.000`, Saldo a favor: `$200.000`.
6. **19/11 19:58:** Se reversan 2 cargos de minibar de `$100.000` c/u con motivo `"Pago extra, no necesario se regresa al cliente."`. Cargos netos bajan a `$205.000`. Pagado sigue en `$605.000` → Saldo a favor sube a `$400.000`.
7. **19/11 20:25:** Cargo `Alfajores` por `$500`. Cargos netos: `$205.500`, Pagado: `$605.000`, Saldo a favor final: **`$399.500`**.

## Causa raíz
1. **Error de cálculo:** Inexistente. La fórmula `cargos_netos - pagado` es correcta.
2. **Error operativo:** Doble/triple cobro en 9 minutos (`$100k + $405k + $100k`) sobre cargos de minibar duplicados, y uso de «Reverso de cargo» en lugar de «Devolución de saldo a favor» o «Reverso de pago».
3. **Falla de diseño:**
   - El backend aceptaba pagos manuales sin `medio`, omitiendo el registro en `caja_movimientos` cuando no había turno abierto.
   - Al reversar un cargo cuando la reserva queda con saldo a favor (`saldo_clp < 0`), la UI no advertía que el dinero pagado no se devuelve automáticamente ni guiaba hacia `/hotel/reservas/{id}` → Devolución de saldo a favor.

## Impacto en caja y cuadratura
- Los 3 pagos suman `$605.000` en `pagos`, pero al tener `medio = 'no_informado'` quedaron fuera de los medios reales (`efectivo`, `debito`, `credito`, `transferencia`) y, si no había turno abierto, **no generaron filas en `caja_movimientos`**.
- Los 2 reversos de cargo (`-$200.000`) solo afectaron la cuenta de cargos del huésped, no la caja.

## Corrección aplicada en rama `fix/forense-rsv-374cbd57abf6`
- Aviso explícito en `front/app/hotel/reservas/[id]/page.js` cuando un reverso de cargo deja `saldo_clp < 0`, aclarando que el dinero pagado no se ha devuelto y debe registrarse una devolución de saldo a favor o reverso de pago.
- Test de reproducción `"PRUEBA G"` en `servicio/tests/test_forense_rsv_374cbd57abf6.py`.
- Scripts `ajuste.sql` y `reversa.sql` listos sin ejecutar para aprobación.
