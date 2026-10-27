# Contrato lógico — H3 (concierge y atención)

Fecha: 2026-10-27. **PROPUESTA TÉCNICA** (no ratificada). Contrato del concierge
local y las capacidades de H3 en `hotel_inventario/`; sirve a `002/H3/T-DIS`.

## Límites

- El concierge **no envía mensajes**: WhatsApp y cualquier envío son puertos
  externos. El concierge decide, deriva, deduplica y registra; sus respuestas son
  registros locales (`RespuestaConcierge`).
- Límite autónomo: 0 CLP como control propuesto (constitución 1.1.0 sin
  ratificar); `ejecutar_sin_aprobacion` con monto > 0 → `AccesoDenegado`.

## Consulta del huésped (FR-010)

- `datos_reserva(empresa_id, reserva_id, solicitante)`: el solicitante debe ser
  `huesped:<reserva_id>`; otro → `AccesoDenegado` con evidencia.
- `pedir_cambio(...)`: sin permiso de mutación queda **borrador** y escala
  (`ResultadoBorrador(aplicado=False, escalado=True)`); registrado en el ledger.

## Política y aprobaciones (FR-011)

- `autorizar_accion(descripcion, parametros, monto, ahora, vigencia_minutos)` →
  aprobación ligada a parámetros exactos, vigencia y uso único.
- `ejecutar_accion_aprobada(...)`: parametros/monto/vigencia/uso distintos →
  `AccesoDenegado` con evidencia ("aprobacion invalidada").

## Upsells (FR-012)

- `ofrecer_upsell(reserva HOSPEDADA, extra)` → `PropuestaUpsell` con link a
  flujo de pago controlado y tarifa comprobada del catálogo; no asienta cargo.
- `contabilizar_conversion`: solo cuenta si existe pago con clave
  `upsell:<id>`; una respuesta con link jamás figura como reserva pagada.

## Registro (FR-013)

- `registrar_accion(fuente, regla, actor, resultado, cuando, datos)`: entrada
  inmutable; rechaza payloads con documento completo del huésped.

## Proyección (FR-014)

- `proyeccion_publica(...)` → solo `unidad_id` + `capacidad`, sin datos de
  huésped; `modificar_desde_proyeccion` → siempre `AccesoDenegado`.

## Concierge (FR-010 a FR-013)

- `atender(conversacion_id, mensaje)`: cancelar/devolver → `derivar_a_recepcion`
  (transferencia con receptor y `resuelto=False`); no cancela, no devuelve, no
  marca resuelto. En atención humana: mensaje adicional → `accion="ninguna"`.
- `notificar_hecho(hecho_id, link)`: una sola notificación por hecho.
