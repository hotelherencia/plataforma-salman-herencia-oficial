/**
 * Configuración desplegable de la landing. Son las únicas constantes que el
 * operador edita al publicar (ver README.md).
 *
 * PLATAFORMA_URL: origen del front público. Por defecto la instalación
 * productiva; el E2E la sobrescribe con `window.LANDING_PLATAFORMA_URL`
 * (addInitScript) para apuntar al front local sin tocar estos archivos.
 *
 * FORMSPREE_URL: endpoint del formulario de contacto. D-PUB-01 (qué pasa con
 * Formspree) sigue DECISIÓN PENDIENTE del propietario: mientras no haya
 * endpoint configurado, el formulario orienta al visitante hacia teléfono y
 * WhatsApp en vez de enviar a un servicio externo.
 */
export const PLATAFORMA_URL =
  (typeof window !== 'undefined' && window.LANDING_PLATAFORMA_URL) ||
  'https://plataforma-salman-herencia-oficial.vercel.app'

export const FORMSPREE_URL = null
