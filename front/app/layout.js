import './globals.css'
import Lienzo from './lienzo.jsx'

// icon.svg + icon.png (RGBA) + favicon.ico regenerado: evita 404/ORB por
// HTML de error cacheado y el fallo Turbopack del ICO no-RGBA.
export const metadata = {
  title: 'Plataforma Herencia',
  description: 'Front mínimo de la plataforma (hotel, V1)',
  referrer: 'origin',
  icons: {
    icon: [
      { url: '/icon.svg', type: 'image/svg+xml' },
      { url: '/icon.png', type: 'image/png', sizes: '32x32' },
      { url: '/favicon.ico', type: 'image/x-icon', sizes: 'any' },
    ],
    shortcut: ['/icon.svg'],
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
