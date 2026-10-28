# Especificación API V1 — contrato entre el front y el backend

**Estado:** REQUISITO PROPUESTO, fechado 2026-10-28. Es el contrato que el
front (Vercel) y el backend (Railway) cumplen juntos; sustituye como contrato
vigente al catálogo heredado `docs/definicion-herencia/contratos/openapi.yaml`
(que queda como referencia histórica, no como contrato). Lo sirve el backend;
una operación que no está en la tabla no se publica.

## Identidad y sesión

- La empresa sale **solo** de la sesión. Un `company_id` enviado por el
  cliente no autoriza nada.
- `POST /sesion` abre la sesión con **usuario y clave** (DECISIÓN, 2026-10-28:
  tabla `usuarios` en PostgreSQL; la clave se guarda solo como hash argon2id;
  el usuario pertenece a una empresa; V1 crea el administrador inicial al
  arrancar, leyendo usuario y clave de variables de entorno, nunca de un SQL
  commiteado ni del repositorio).
- La sesión vive en el servidor (tabla `sesiones`, revocable). El front solo
  recibe la cookie.
- Cookie de sesión: nombre `sid`, **HttpOnly**, **Secure** en producción,
  **SameSite=None** (front y API son orígenes distintos: Vercel ↔ Railway).
  En local, sobre `http://127.0.0.1`, la cookie usa **SameSite=Lax** y no
  pide `Secure`: el navegador rechaza `SameSite=None` sin `Secure`, y los
  dos puertos de `127.0.0.1` son el mismo sitio.
- Sin sesión válida → **401**. Sesión de otra empresa sobre un recurso →
  **403**, sin revelar si el recurso existe.

## Idempotencia

- Toda mutación (POST/PUT) lleva cabecera `Idempotency-Key`.
- Misma clave + mismo cuerpo → mismo resultado (la respuesta original se
  repite).
- Misma clave + otro cuerpo → **409**.
- La clave es por empresa y por operación; se guarda en PostgreSQL
  (`claves_idempotencia`: clave, hash del cuerpo, respuesta, código).

## Errores y puertos

- Puerto externo sin adaptador (pasarela, DTE, PMS, canal, mensajería) →
  **503** y el estado queda **pendiente**; nada se marca como cobrado,
  emitido ni enviado. El cuerpo declara qué puerto falta.

## Operaciones de esta versión (10)

| Operación | Efecto |
|---|---|
| `POST /sesion` | Abre sesión de la empresa Herencia y fija la cookie `sid`. |
| `DELETE /sesion` | Cierra la sesión (la fila de `sesiones` queda revocada). |
| `PUT /hotel/habitaciones/{id}` | Alta o cambio de habitación: tipo, capacidad. Solo administrador. |
| `PUT /hotel/tarifas` | Tarifa por fecha y unidad. No cambia el precio de una reserva ya aceptada. |
| `GET /hotel/oferta?inicio&fin&personas` | Solo lo disponible, con tarifa vigente y vencimiento de la oferta. |
| `POST /hotel/reservas` | Confirma una sola vez. La última unidad en carrera queda en una sola reserva: la confirmación es transaccional y la base rechaza el solape en (unidad, fechas). |
| `POST /hotel/reservas/{id}/pagos` | El núcleo registra el efecto. Si el núcleo rechaza, no hay pago. Cuerpo: `{monto_clp, clave, modo}`. `modo="manual"` (DECISIÓN, 2026-10-28): caja en efectivo o transferencia que recepción registra; solo roles recepción, caja o administrador; no consulta el banco y no queda conciliado. `modo="pasarela"` sin adaptador → 503 y nada marcado como cobrado. |
| `POST /hotel/reservas/{id}/entrada` | Check-in si la habitación está lista (mantenimiento abierto bloquea). |
| `POST /hotel/reservas/{id}/salida` | Liquida la cuenta y devuelve la liquidación. |
| `GET /hotel/caja?fecha=YYYY-MM-DD` | Pagos del día ligados a reserva. Sin movimiento bancario en esta versión. |

## Criterio de aceptación

El front de Vercel puede implementarse leyendo solo este contrato. Las diez
operaciones pasan contra PostgreSQL con las reglas de sesión, idempotencia y
errores de arriba; nada fuera de la tabla existe.
