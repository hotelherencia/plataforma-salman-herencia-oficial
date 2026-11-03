'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { api, useSesion } from '../lib/api'

/**
 * Marco de PLATAFORMA (capa Herencia): marca, empresa de la sesión y
 * selector de módulos. El módulo Hotel es el único operable; cafetería,
 * inmobiliaria y constructora están nombradas y cerradas en esta versión —
 * sin formularios ni fetch propio.
 * Presentación adaptada de «Dashboard Sidebar» de @arunjdass (21st.dev,
 * id 14941): navegación por grupos con rótulo, estado activo por borde y
 * sesión/cierre abajo. Vocabulario de esta capa: plataforma, módulo, sesión.
 */

const OPERACION_HOTEL = [
  ['/hotel/panel', 'Panel'],
  ['/hotel/ocupacion', 'Ocupación'],
  ['/hotel/habitaciones', 'Habitaciones y tarifas'],
  ['/hotel/oferta', 'Oferta'],
  ['/hotel/reserva', 'Reserva'],
  ['/hotel/reservas', 'Reservas'],
  ['/hotel/pago', 'Pago'],
  ['/hotel/estadia', 'Estadía'],
  ['/hotel/salida', 'Salida'],
  ['/hotel/caja', 'Caja'],
  ['/hotel/usuarios', 'Usuarios'],
]

const MODULOS_CERRADOS = ['Cafetería', 'Inmobiliaria', 'Constructora']

export default function BarraNav() {
  const ruta = usePathname()
  const sesion = useSesion()
  const enHotel = ruta.startsWith('/hotel')

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
          <span className="marca-sub">Grupo Salman · Plataforma</span>
        </span>
      </div>

      {sesion.fase === 'ok' && (
        <p className="barra-empresa" title="Empresa de la sesión">
          {sesion.usuario.empresa_id}
        </p>
      )}

      <nav className="nav">
        <p className="nav-rotulo">Módulos</p>
        <Link href="/" className={ruta === '/' ? 'nav-enlace activo' : 'nav-enlace'}>
          Inicio
        </Link>
        <Link href="/hotel/panel" className={enHotel ? 'nav-enlace activo' : 'nav-enlace'}>
          Hotel
        </Link>
        {MODULOS_CERRADOS.map((nombre) => (
          <span key={nombre} className="nav-cerrado" aria-disabled="true" title="Nombrada · no operable en esta versión">
            {nombre}
          </span>
        ))}

        {enHotel && (
          <>
            <p className="nav-rotulo">Hotel · operación</p>
            {OPERACION_HOTEL.map(([href, nombre]) => (
              <Link
                key={href}
                href={href}
                className={ruta === href || ruta.startsWith(`${href}/`) ? 'nav-enlace activo' : 'nav-enlace'}
              >
                {nombre}
              </Link>
            ))}
          </>
        )}
      </nav>

      <Link
        href="/cuenta"
        className={ruta === '/cuenta' ? 'nav-enlace nav-cuenta activo' : 'nav-enlace nav-cuenta'}
      >
        Mi cuenta
      </Link>
      <div className="barra-pie">
        <button onClick={salir} className="boton-salir">Cerrar sesión</button>
      </div>
    </aside>
  )
}
