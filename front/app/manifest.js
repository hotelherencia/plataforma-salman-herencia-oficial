import { NOMBRE_COMERCIAL } from '../lib/marca'

export default function manifest() {
  return {
    name: NOMBRE_COMERCIAL,
    short_name: NOMBRE_COMERCIAL,
    description: 'Plataforma de operación de Hotel Herencia, Chillán.',
    start_url: '/',
    display: 'standalone',
    background_color: '#f5efe4',
    theme_color: '#173326',
    lang: 'es-CL',
    icons: [
      { src: '/favicon-48.png', sizes: '48x48', type: 'image/png' },
      { src: '/logo-herencia-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/logo-herencia-192-maskable.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
      { src: '/logo-herencia-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
      { src: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
  }
}
