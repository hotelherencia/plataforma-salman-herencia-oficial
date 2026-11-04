/**
 * Configuración desplegable de la landing. Son las únicas constantes que el
 * operador edita al publicar (ver README.md).
 *
 * PLATAFORMA_URL: origen del front público. Por defecto la instalación
 * productiva; el E2E la sobrescribe con `window.LANDING_PLATAFORMA_URL`
 * (addInitScript) para apuntar al front local sin tocar estos archivos.
 *
 * API_URL: origen del servicio para el formulario de contacto
 * (`POST {API_URL}/publico/leads`). D-PUB-01 resuelta (2026-11-04): el
 * formulario es propio y Formspree se retira. Por defecto es el front en
 * `/api/*` (reenvío al backend según `front/vercel.json`); el E2E y las
 * pruebas locales lo sobrescriben con `window.LANDING_API_URL`.
 */
export const PLATAFORMA_URL =
  (typeof window !== 'undefined' && window.LANDING_PLATAFORMA_URL) ||
  'https://plataforma-salman-herencia-oficial.vercel.app'

export const API_URL =
  (typeof window !== 'undefined' && window.LANDING_API_URL) || `${PLATAFORMA_URL}/api`
