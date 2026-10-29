'use client'

import { usePathname } from 'next/navigation'
import BarraNav from './barra.jsx'

/** Estructura visual: chrome completo (sidebar + contenido), salvo en /login. */
export default function Lienzo({ children }) {
  const ruta = usePathname()

  if (ruta === '/login') return <>{children}</>

  return (
    <div className="aplicacion">
      <BarraNav />
      <div className="contenido">{children}</div>
    </div>
  )
}
