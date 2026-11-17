'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

/** Pestañas locales para no multiplicar entradas del menú (entrega 1A.3). */
export default function Subnav({ items }) {
  const ruta = usePathname()
  return (
    <nav className="subnav" aria-label="Secciones de esta pantalla">
      {items.map(([href, nombre]) => {
        const activo = ruta === href || (href !== '/hotel/reservas' && ruta.startsWith(`${href}/`)) || (href === '/hotel/reservas' && (ruta === '/hotel/reservas' || ruta.startsWith('/hotel/reservas/')))
        return (
          <Link key={href} href={href} aria-current={activo ? 'page' : undefined} className={activo ? 'subnav-enlace activo' : 'subnav-enlace'}>
            {nombre}
          </Link>
        )
      })}
    </nav>
  )
}
