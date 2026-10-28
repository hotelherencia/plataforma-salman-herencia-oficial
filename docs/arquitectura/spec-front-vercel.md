# Especificación — Front en Vercel

**Sustituida el 2026-10-28 por [spec-front-v1.md](spec-front-v1.md).** Este archivo no gobierna.

**DECISIÓN del propietario, 2026-10-28.** Fuente: instrucción de construir el mínimo front / API / backend. Prevalece sobre ADR-001 en el punto en que ese ADR junta la web y la API en un solo Next.js. Los precios, temporadas y políticas fiscales siguen siendo decisión pendiente del Manual §9: esta spec no los fija.

## Artefacto

Un solo proyecto, `plataforma-salman-herencia-front`, Next.js, desplegado en Vercel. Una sesión y una empresa. El front no es un sitio por vertical.

## Esta versión

Rutas con pantalla: `/hotel` (habitaciones y tarifas, oferta, reserva, pago, estadía, salida, caja del día).

Rutas presentes y vacías: `/cafeteria`, `/inmobiliaria`, `/constructora`.

## Frontera

El front no calcula tarifa, no confirma cupo y no registra un pago. Cada acción es una llamada a la API de `docs/arquitectura/spec-api.md`. La única variable de entorno es `API_BASE_URL`, el origen del servicio en Railway.

La sesión viaja en cookie `HttpOnly`, `Secure`, `SameSite=None`, puesta por la API. El front no guarda un token en `localStorage` ni en el código fuente.

El front no llama a Webpay, Mercado Pago, Booking, Airbnb, SII ni WhatsApp.

## Criterio verificable

Con la API apagada, el front muestra error y no confirma una reserva. Con la API encendida, las pantallas del hotel leen y escriben solo contra `API_BASE_URL`.
