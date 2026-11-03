'use client'

import { useEffect, useRef, useState } from 'react'
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
 *
 * Navegación responsive (UX-01/UX-02, 2026-11-03): >860px barra lateral
 * actual; ≤860px cabecera compacta con botón «Menú» que abre un panel con
 * todas las opciones agrupadas — sin arrastre de descubrimiento, activo
 * único y visible, y «Cerrar sesión» siempre accesible.
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

function esActivo(ruta, href) {
  return ruta === href || ruta.startsWith(`${href}/`)
}

export default function BarraNav() {
  const ruta = usePathname()
  const sesion = useSesion()
  const enHotel = ruta.startsWith('/hotel')
  const hayOperacionActiva = OPERACION_HOTEL.some(([href]) => esActivo(ruta, href))
  const [abierto, setAbierto] = useState(false)
  const botonRef = useRef(null)
  const panelRef = useRef(null)

  async function salir() {
    try {
      await api('/sesion', { metodo: 'DELETE' })
    } finally {
      window.location.href = '/login'
    }
  }

  // El panel móvil es un diálogo: Escape lo cierra y devuelve el foco al botón.
  useEffect(() => {
    if (!abierto) return
    function tecla(e) {
      if (e.key === 'Escape') {
        setAbierto(false)
        botonRef.current?.focus()
      }
    }
    document.addEventListener('keydown', tecla)
    return () => document.removeEventListener('keydown', tecla)
  }, [abierto])

  useEffect(() => {
    if (abierto) panelRef.current?.querySelector('.activo')?.scrollIntoView({ block: 'nearest' })
  }, [abierto, ruta])

  const cerrar = () => setAbierto(false)

  return (
    <>
      {/* Escritorio (>860px): barra lateral */}
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

        <nav className="nav" aria-label="Navegación principal">
          <p className="nav-rotulo">Módulos</p>
          <Link href="/" className={ruta === '/' ? 'nav-enlace activo' : 'nav-enlace'}>
            Inicio
          </Link>
          <Link
            href="/hotel/panel"
            className={enHotel && !hayOperacionActiva ? 'nav-enlace activo' : 'nav-enlace'}
          >
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
                <Link key={href} href={href} className={esActivo(ruta, href) ? 'nav-enlace activo' : 'nav-enlace'}>
                  {nombre}
                </Link>
              ))}
            </>
          )}
        </nav>

        <Link href="/cuenta" className={ruta === '/cuenta' ? 'nav-enlace nav-cuenta activo' : 'nav-enlace nav-cuenta'}>
          Mi cuenta
        </Link>
        <div className="barra-pie">
          <button onClick={salir} className="boton-salir">Cerrar sesión</button>
        </div>
      </aside>

      {/* Móvil/tablet (≤860px): cabecera compacta + panel de menú */}
      <header className="barra-movil">
        <div className="marca">
          <span className="marca-punto" />
          <span>
            Herencia
            <span className="marca-sub">Grupo Salman · Plataforma</span>
          </span>
        </div>
        <button
          ref={botonRef}
          type="button"
          className="boton-menu"
          aria-expanded={abierto}
          aria-controls="menu-movil"
          onClick={() => setAbierto((v) => !v)}
        >
          Menú
        </button>
        {abierto && (
          <div className="menu-movil-fondo" onClick={() => { setAbierto(false); botonRef.current?.focus() }} />
        )}
        <div id="menu-movil" ref={panelRef} className={abierto ? 'menu-movil abierto' : 'menu-movil'} role="dialog" aria-modal="true" aria-label="Menú de navegación">
          <nav className="menu-movil-nav" aria-label="Navegación principal">
            <p className="nav-rotulo">Módulos</p>
            <Link href="/" onClick={cerrar} className={ruta === '/' ? 'nav-enlace activo' : 'nav-enlace'}>
              Inicio
            </Link>
            <Link href="/hotel/panel" onClick={cerrar} className={enHotel && !hayOperacionActiva ? 'nav-enlace activo' : 'nav-enlace'}>
              Hotel
            </Link>
            {MODULOS_CERRADOS.map((nombre) => (
              <span key={nombre} className="nav-cerrado" aria-disabled="true">
                {nombre}
              </span>
            ))}
            {enHotel && (
              <>
                <p className="nav-rotulo">Hotel · operación</p>
                {OPERACION_HOTEL.map(([href, nombre]) => (
                  <Link key={href} href={href} onClick={cerrar} className={esActivo(ruta, href) ? 'nav-enlace activo' : 'nav-enlace'}>
                    {nombre}
                  </Link>
                ))}
              </>
            )}
          </nav>
          <div className="menu-movil-pie">
            <Link href="/cuenta" onClick={cerrar} className={ruta === '/cuenta' ? 'nav-enlace nav-cuenta activo' : 'nav-enlace nav-cuenta'}>
              Mi cuenta
            </Link>
            <button onClick={salir} className="boton-salir">Cerrar sesión</button>
          </div>
        </div>
      </header>
    </>
  )
}
