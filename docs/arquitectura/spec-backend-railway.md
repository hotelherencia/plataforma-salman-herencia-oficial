# Especificación — Backend en Railway

**Sustituida el 2026-10-28 por [spec-backend-v1.md](spec-backend-v1.md).** Este archivo no gobierna.

**DECISIÓN del propietario, 2026-10-28.** Un solo servicio implementa `docs/arquitectura/spec-api.md`. El front no vive en este servicio.

## Artefacto

Un servicio, `plataforma-salman-herencia-api`, en Railway. Python, FastAPI, PostgreSQL 17. Al arrancar carga el núcleo y el módulo hotel en el mismo proceso. El hotel usa la empresa del núcleo. El proceso no arranca si el hotel trae otra empresa.

Cafetería, inmobiliaria y constructora no se cargan en esta versión.

## Persistencia

PostgreSQL guarda habitación, tarifa, reserva, pago y efecto del núcleo. Al reiniciar el servicio, una reserva confirmada sigue ahí. `DATABASE_URL` y los secretos viven en variables de Railway. El repositorio no lleva `.env`.

## Puertos

Webpay, Mercado Pago, SII, Booking, Airbnb y WhatsApp son puertos del núcleo. En esta versión responden «no configurado» y la API traduce eso a 503. No hay adaptador real y no se simula éxito.

`plataforma/servidor.py` no es este servicio. No usa FastAPI, no usa PostgreSQL y no es el artefacto de Railway.

## Criterio verificable

`GET /salud` responde en el origen de Railway. Las diez operaciones de `spec-api.md` pasan contra PostgreSQL. Una segunda llamada con la misma clave de pago no crea un segundo efecto. El front en Vercel usa ese origen y ningún otro.
