'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { api, useSesion } from '../lib/api'
import { LOGO, NOMBRE_COMERCIAL } from '../lib/marca'
import { esAdminPlataforma, gestionaRecepcion } from '../lib/roles'
import { hayOperacionActiva, itemActivo, seccionesVisibles } from '../lib/menu-hotel'

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

const MODULOS_CERRADOS = ['Cafetería', 'Inmobiliaria', 'Constructora']

export default function BarraNav() {
  const ruta = usePathname()
  const sesion = useSesion()
  const enHotel = ruta.startsWith('/hotel')
  const visibilidad = {
    puedeVerAgente: sesion.fase === 'ok' && gestionaRecepcion(sesion.usuario.rol),
    puedeVerUsuarios: sesion.fase === 'ok' && esAdminPlataforma(sesion.usuario.rol),
  }
  const secciones = enHotel ? seccionesVisibles(visibilidad) : []
  const operacionActiva = hayOperacionActiva(ruta, visibilidad)
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
          <img className="marca-logo" src={LOGO.hoja40} srcSet={`${LOGO.hoja40} 1x, ${LOGO.hoja80} 2x`} alt={NOMBRE_COMERCIAL} width="50" height="40" />
          <span>
            {NOMBRE_COMERCIAL}
            <span className="marca-sub">Plataforma</span>
          </span>
        </div>

        {sesion.fase === 'ok' && (
          <p className="barra-empresa" title="Empresa de la sesión">
            {sesion.usuario.empresa_id}
          </p>
        )}

        <nav className="nav" aria-label="Navegación principal">
          <p className="nav-rotulo">Módulos</p>
          <Link href="/" aria-current={ruta === '/' ? 'page' : undefined} className={ruta === '/' ? 'nav-enlace activo' : 'nav-enlace'}>
            Inicio
          </Link>
          <Link
            href="/hotel/panel"
            className={enHotel && !operacionActiva ? 'nav-enlace activo' : 'nav-enlace'}
          >
            Hotel
          </Link>
          {MODULOS_CERRADOS.map((nombre) => (
            <span key={nombre} className="nav-cerrado" aria-disabled="true" title="Nombrada · no operable en esta versión">
              {nombre}
            </span>
          ))}

          {enHotel && secciones.map((seccion) => (
            <div key={seccion.id} className="nav-grupo">
              <p className="nav-rotulo">{seccion.rotulo}</p>
              {seccion.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={itemActivo(ruta, item) ? 'page' : undefined}
                  className={itemActivo(ruta, item) ? 'nav-enlace activo' : 'nav-enlace'}
                >
                  {item.nombre}
                </Link>
              ))}
            </div>
          ))}
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
          <img className="marca-logo" src={LOGO.hoja40} srcSet={`${LOGO.hoja40} 1x, ${LOGO.hoja80} 2x`} alt={NOMBRE_COMERCIAL} width="50" height="40" />
          <span>
            {NOMBRE_COMERCIAL}
            <span className="marca-sub">Plataforma</span>
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
            <Link href="/hotel/panel" onClick={cerrar} className={enHotel && !operacionActiva ? 'nav-enlace activo' : 'nav-enlace'}>
              Hotel
            </Link>
            {MODULOS_CERRADOS.map((nombre) => (
              <span key={nombre} className="nav-cerrado" aria-disabled="true">
                {nombre}
              </span>
            ))}
            {enHotel && secciones.map((seccion) => (
              <div key={seccion.id} className="nav-grupo">
                <p className="nav-rotulo">{seccion.rotulo}</p>
                {seccion.items.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={cerrar}
                    aria-current={itemActivo(ruta, item) ? 'page' : undefined}
                    className={itemActivo(ruta, item) ? 'nav-enlace activo' : 'nav-enlace'}
                  >
                    {item.nombre}
                  </Link>
                ))}
              </div>
            ))}
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
