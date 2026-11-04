# Landing de Hotel Herencia (estática)

Sitio marketing de una sola página, servido tal cual (Apache) sin build.
Es la versión del repositorio de https://hotelherencia.cl/ con el CTA
«Consultar reserva» ya integrado a la plataforma (V1-ISSUE-25, CA-PUB-12):
el visitante elige llegada, salida y huéspedes, y el CTA abre
`/reservar?inicio=…&fin=…&personas=…` del front público con esos parámetros.
El front los valida de nuevo, muestra la disponibilidad real que decide el
servidor y deja la solicitud idempotente; recepción la convierte en reserva
con trazabilidad (`servicio/canal_publico.py`).

## Estructura

- `index.html` — contenido del sitio (hero, ubicación, servicios,
  habitaciones, galería, preguntas frecuentes, contacto). Semántico y con
  nombres accesibles estables (los usa la E2E).
- `css/landing.css` — hoja propia, independiente del front de la plataforma.
- `js/reserva.js` — utilidades **puras** del CTA (validación del rango y
  constructor del deep link). Espejan `validar()` de
  `front/app/reservar/page.js`: la landing y el front rechazan los mismos
  rangos. Sin DOM: también las importan los tests de Node.
- `js/config.js` — lo único que se edita al publicar (constantes de abajo).
- `js/widget.js` — cableado del formulario del hero al deep link.
- `js/galeria.js` — carruseles de habitaciones y galería (mejora progresiva:
  sin JS queda visible la primera imagen de cada grupo).
- `js/formulario.js` — cableado del formulario de contacto de #contacto a
  `POST {API_URL}/publico/leads`.
- `js/leads.js` — utilidades **puras** del formulario de contacto (mapeo del
  cuerpo a snake_case y mensajes según el código HTTP). Sin DOM: también las
  importan los tests de Node.
- `test/leads.test.mjs` — tests del mapeo y los mensajes.
- `test/reserva.test.mjs` — tests del constructor: `node --test 'landing/test/*.test.mjs'`.

## Configuración al publicar

En `js/config.js`:

- `PLATAFORMA_URL`: origen del front público. Por defecto la instalación en
  Vercel. El E2E la sobrescribe en el navegador con
  `window.LANDING_PLATAFORMA_URL` (addInitScript), sin tocar estos archivos.
- `API_URL`: origen del servicio que recibe el formulario de contacto
  (`POST {API_URL}/publico/leads`, especificación en
  `docs/arquitectura/spec-api-v1.md` «Contacto y leads de la landing»).
  D-PUB-01 resuelta (2026-11-04, orden del propietario): el formulario es
  **propio** y Formspree se retira — las consultas quedan en la plataforma
  como leads gestionables por recepción. Por defecto es el front en `/api/*`
  (reenvío al backend según `front/vercel.json`); el E2E y las pruebas
  locales lo sobrescriben con `window.LANDING_API_URL`.

## Fotografías

Los `.foto-marcador` son marcadores de posición (gradiente). Al publicar,
reemplazarlos por las fotografías reales del sitio (mismos `aria-label`
descriptivos ya escritos).

## Verificación

- `node --test landing/test/reserva.test.mjs` — validación y constructor del enlace.
- `cd e2e && FRONT_URL=http://127.0.0.1:3000 node e2e-landing.mjs` — E2E
  PUB-07/08/09 con navegador real contra esta carpeta servida estáticamente
  y el front en build de producción (mismos requisitos que `e2e/README.md`).

## Alcance y límites

- La URL lleva solo fechas y personas; **nada de datos personales** (Ley
  21.719): nombre y contacto los pide el front dentro de la solicitud.
- El origen «landing» queda trazado en `solicitudes.origen` al persistir;
  la métrica completa «ingresos por canal» sigue propuesta en el issue #324
  (requiere decisión del propietario).
- Este código se publica en el hosting del sitio marketing; el issue #313 se
  cierra cuando el CTA real está publicado y verificado en producción.
