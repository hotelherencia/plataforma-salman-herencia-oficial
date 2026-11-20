# Propuesta de operación de dominio: cambio de fechas de una reserva

- **Fecha:** 2026-11-20
- **Clase de evidencia:** **REQUISITO PROPUESTO** (apoyado en el **HECHO DOCUMENTADO** de `docs/decisiones/decisiones-2026-11-20.md` §2 sobre `Q-HOT-04` / `#91`).
- **Estado:** Propuesta técnica para siguiente iteración; **no implementada** en este lote.

## Por qué NO se puede editar `inicio` / `fin` con un `UPDATE` directo

En el modelo vigente (`verticales/hotel/incremento1/hotel_inventario/servicio.py` y `servicio/hotel_sql.py`), las únicas operaciones de dominio sobre la estadía de una reserva son:

- `reasignar` (`POST /hotel/reservas/{id}/habitacion`, `#360`/`#361`): mueve la unidad conservando fechas y tarifa.
- `cancelar` (`POST /hotel/reservas/{id}/cancelacion`): cancela desde `confirmada` aplicando política de 48 h y revirtiendo cargos previos.
- `previsualizar_cambio` / `aplicar_cambio`: solo recalcula ajuste por cambio de tarifa unitaria, no cambia fechas ni cupo.

Un `UPDATE reservas SET inicio = ..., fin = ...` directo violaría invariantes críticas:

1. **Cupo y concurrencia:** la restricción de exclusión `reservas_sin_solapamiento` y la verificación de mantenimiento por noche (`#349`) deben evaluarse dentro del candado exclusivo (`hotel_sql.EXCLUSIVO` + `hotel_sql.bloquear`).
2. **Tarifa congelada noche a noche (`#305`):** `reserva_noches` congela el precio de cada noche; mover el rango exige recalcular las noches nuevas con el resolvedor único `servicio/precios.py`.
3. **Contabilidad append-only (`cargos` e `imputaciones_pago`):** si la reserva ya está `en_estadia`, las noches ya asentadas como cargos no se editan ni borran; noches removidas requieren `reversar_cargo` y noches agregadas requieren `asentar_cargo`. Si el nuevo total queda menor que lo pagado, el saldo pasa a favor del huésped y se resuelve mediante devolución formal (`POST /hotel/reservas/{id}/devolucion`, `#91`).

## Operación propuesta

### 1. Dominio (`ServicioHotelInventario`)

```python
def previsualizar_cambio_fechas(
    self, empresa_id: str, reserva_id: str, nuevo_inicio: date, nuevo_fin: date,
    tarifas_nuevas: dict[date, int], ahora: datetime
) -> PropuestaCambioFechas

def cambiar_fechas(
    self, empresa_id: str, reserva_id: str, nuevo_inicio: date, nuevo_fin: date,
    tarifas_nuevas: dict[date, int], motivo: str, ahora: datetime
) -> ResultadoCambioFechas
```

**Invariantes:**
- Solo permitido en `confirmada` (cualquier cambio de `inicio` y `fin` con `nuevo_fin > nuevo_inicio`) o `en_estadia` (solo cambiar `fin` >= `hoy`, nunca mover `inicio` al pasado ya cursado).
- Verifica disponibilidad de la unidad (o permite combinar con destino si se extiende) excluyendo la propia `reserva_id`, y sin mantenimiento solapado (`#349`).
- Recalcula el total de noches con `servicio/precios.py` (si alguna noche no tiene tarifa → `409 sin tarifa vigente`).
- En `confirmada`: actualiza `reserva_noches` (la cuenta sigue vacía hasta la Llegada, ENMIENDA ADP-4).
- En `en_estadia`: asienta cargos `Noche` para las noches añadidas (`clave=noche:YYYY-MM-DD`) y revierte con `reversar_cargo` las noches eliminadas; re-aplica anticipos pendientes si corresponde.
- Registra traza en `auditoria` (`accion='reserva_cambio_fechas'`, `resultado='inicio,fin'` sin datos personales) y opcionalmente tabla `reserva_cambios_fechas` (análogo a `reasignaciones`).

### 2. Contrato HTTP propuesto

- `POST /hotel/reservas/{id}/fechas`
  - Roles: `recepcion`, `admin_hotel`, `administrador`.
  - Cabecera obligatoria: `Idempotency-Key`.
  - Cuerpo: `{ "inicio": "YYYY-MM-DD", "fin": "YYYY-MM-DD", "motivo": "...", "simular": false }` (`simular: true` devuelve diferencia de noches/monto sin mutar).
  - Respuestas: `200` con fechas nuevas, `reserva_noches`, diferencia CLP y saldo actualizado; `409` si no hay cupo, falta tarifa o estado no permite el cambio; `422` si rango inválido o motivo < 3 caracteres; `403` si ajena/inexistente o rol sin permiso.

## Alternativa operativa vigente mientras no se implemente

En V1 actual, la ficha de la reserva (`/hotel/reservas/{id}`) ofrece:
- **Cambiar habitación** (`POST /hotel/reservas/{id}/habitacion`).
- **Cancelar reserva** (`POST /hotel/reservas/{id}/cancelacion`, solo desde `confirmada`) + enlace a crear nueva reserva con las fechas deseadas.
