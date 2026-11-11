import './globals.css'
import Lienzo from './lienzo.jsx'

export const metadata = {
  title: 'Plataforma Herencia',
  description: 'Front mínimo de la plataforma (hotel, V1)',
  referrer: 'origin',
  icons: {
    icon: [{ url: '/favicon.ico', type: 'image/x-icon' }],
    shortcut: ['/favicon.ico'],
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
