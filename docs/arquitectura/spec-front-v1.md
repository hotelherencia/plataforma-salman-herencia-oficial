# Especificación front V1 — la aplicación en Vercel

**Estado:** REQUISITO PROPUESTO, fechado 2026-10-28. Un solo proyecto,
`plataforma-salman-herencia-front`, **Next.js**, desplegado en **Vercel**.
Consume y solo consume [spec-api-v1.md](spec-api-v1.md) en el origen
`API_BASE_URL` (el servicio de Railway). El hotel es el primer módulo;
`/cafeteria`, `/inmobiliaria` y `/constructora` existen como rutas vacías.

## Reglas duras

- **Una sesión, una empresa.** La sesión viaja en la cookie `sid`
  (HttpOnly, Secure, SameSite=None) que pone la API. El front **no guarda
  token en localStorage ni en el código**.
- El front **no calcula tarifa, no confirma cupo y no registra un pago**.
  Cada acción es una llamada a la API con `Idempotency-Key` en mutaciones.
- El front no llama a Webpay, Booking, Airbnb, SII ni WhatsApp. No existe
  otra URL que `API_BASE_URL`.
- Sin sesión: pantalla de login contra `POST /sesion`.

## Rutas de esta versión (hotel)

1. `/hotel/habitaciones` — alta y cambio de habitación y tarifa (admin).
2. `/hotel/oferta` — consulta de disponibilidad con tarifa y vencimiento.
3. `/hotel/reserva` — confirmación con clave de idempotencia visible en el
   flujo (reintento seguro).
4. `/hotel/pago` — registro de pago (modo manual de caja; pasarela muestra
   «no disponible» ante 503).
5. `/hotel/estadia` — check-in y operación de la estadía.
6. `/hotel/salida` — liquidación de la cuenta.
7. `/hotel/caja` — pagos del día ligados a reserva.

## Criterio de aceptación

1. **Con la API apagada, el front muestra error y no confirma una reserva.**
2. Con la API encendida, las siete pantallas leen y escriben solo por
   `API_BASE_URL`.
3. No hay secretos ni tokens en el repositorio del front; la única variable
   de entorno es `API_BASE_URL`.
4. Ninguna pantalla replica lógica del contrato (precios, cupos, efectos).
