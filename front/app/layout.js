import './globals.css'
import Lienzo from './lienzo.jsx'
import { NOMBRE_COMERCIAL } from '../lib/marca'

// Iconos PNG de la hoja del logo oficial (16/32/48 + ICO) y apple-touch 180
// con el wordmark completo sobre fondo blanco.
export const metadata = {
  title: NOMBRE_COMERCIAL,
  description: 'Plataforma de operación de Hotel Herencia (hotel, V1)',
  robots: { index: false, follow: false, nocache: true, noarchive: true },
  referrer: 'origin',
  icons: {
    icon: [
      { url: '/favicon-16.png', type: 'image/png', sizes: '16x16' },
      { url: '/favicon-32.png', type: 'image/png', sizes: '32x32' },
      { url: '/favicon-48.png', type: 'image/png', sizes: '48x48' },
      { url: '/favicon.ico', type: 'image/x-icon', sizes: 'any' },
    ],
    apple: [{ url: '/apple-icon.png', sizes: '180x180', type: 'image/png' }],
  },
}

export default function Layout({ children }) {
  return (
    <html lang="es">
      <body>
        <Lienzo>{children}</Lienzo>
      </body>
    </html>
  )
}
