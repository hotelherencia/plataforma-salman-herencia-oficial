import BarraNav from './barra.jsx'

export const metadata = {
  title: 'Plataforma Herencia',
  description: 'Front mínimo de la plataforma (hotel, V1)',
}

export default function Layout({ children }) {
  return (
    <html lang="es">
      <body style={{ fontFamily: 'system-ui, sans-serif', margin: '1.5rem auto', maxWidth: '46rem', padding: '0 1rem' }}>
        <BarraNav />
        {children}
      </body>
    </html>
  )
}
