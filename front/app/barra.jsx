'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { api } from '../lib/api'

const ENLACES = [
  ['/hotel/habitaciones', 'Habitaciones y tarifas'],
  ['/hotel/oferta', 'Oferta'],
  ['/hotel/reserva', 'Reserva'],
  ['/hotel/pago', 'Pago'],
  ['/hotel/estadia', 'Estadía'],
  ['/hotel/salida', 'Salida'],
  ['/hotel/caja', 'Caja'],
]

export default function BarraNav() {
  const ruta = usePathname()

  async function salir() {
    try {
      await api('/sesion', { metodo: 'DELETE' })
    } finally {
      window.location.href = '/login'
    }
  }

  return (
    <aside className="barra">
      <div className="marca">
        <span className="marca-punto" />
        <span>
          Herencia
          <span className="marca-sub">Grupo Salman · Hotel</span>
        </span>
      </div>
      <nav className="nav">
        {ENLACES.map(([href, nombre]) => (
          <Link
            key={href}
            href={href}
            className={ruta === href ? 'nav-enlace activo' : 'nav-enlace'}
          >
            {nombre}
          </Link>
        ))}
      </nav>
      <Link
        href="/cuenta"
        className={ruta === '/cuenta' ? 'nav-enlace nav-cuenta activo' : 'nav-enlace nav-cuenta'}
      >
        Mi cuenta
      </Link>
      <div className="barra-pie">
        <p className="barra-modulos">
          Cafetería · Inmobiliaria · Constructora — fuera de V1
        </p>
        <button onClick={salir} className="boton-salir">Cerrar sesión</button>
      </div>
    </aside>
  )
}
