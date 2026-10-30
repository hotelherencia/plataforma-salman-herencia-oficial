'use client'

import Link from 'next/link'
import { useSesion } from '../lib/api'

/**
 * Inicio de PLATAFORMA (capa Herencia): después del login se ve la
 * plataforma — marca, empresa de la sesión y selector de módulos — y desde
 * aquí se entra al módulo Hotel. No es un redirect oculto a la oferta.
 * Cafetería, inmobiliaria y constructora están nombradas y cerradas en esta
 * versión: tarjetas sin formularios ni fetch propio.
 * Presentación de las tarjetas adaptada de «Dashboard Overview»
 * de @uniquesonu (21st.dev, id 8371): cabecera con rótulo e insignia de
 * estado, nombre protagonista y pie de acción.
 */

function IconoHotel() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 4v16" /><path d="M2 8h18a2 2 0 0 1 2 2v10" /><path d="M2 17h20" /><path d="M6 8v9" />
    </svg>
  )
}

function IconoTaza() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17 8h1a4 4 0 1 1 0 8h-1" /><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" /><path d="M6 2v2" /><path d="M10 2v2" /><path d="M14 2v2" />
    </svg>
  )
}

function IconoEdificio() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="4" y="2" width="16" height="20" rx="2" /><path d="M9 22v-4h6v4" /><path d="M8 6h.01" /><path d="M16 6h.01" /><path d="M12 6h.01" /><path d="M8 10h.01" /><path d="M16 10h.01" /><path d="M12 10h.01" /><path d="M8 14h.01" /><path d="M16 14h.01" /><path d="M12 14h.01" />
    </svg>
  )
}

function IconoGrua() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 21h18" /><path d="M6 21V10l8-6v17" /><path d="M14 4h6v4" /><path d="M18 8v3" /><path d="M18 14h.01" />
    </svg>
  )
}

const MODULOS = [
  {
    nombre: 'Hotel',
    icono: IconoHotel,
    estado: 'operable',
    descripcion: 'Habitaciones, oferta, reservas, estadía, caja, limpieza y mantenimiento.',
    href: '/hotel/oferta',
  },
  {
    nombre: 'Cafetería',
    icono: IconoTaza,
    estado: 'cerrado',
    descripcion: 'Nombrada. No operable en esta versión.',
  },
  {
    nombre: 'Inmobiliaria',
    icono: IconoEdificio,
    estado: 'cerrado',
    descripcion: 'Nombrada. No operable en esta versión.',
  },
  {
    nombre: 'Constructora',
    icono: IconoGrua,
    estado: 'cerrado',
    descripcion: 'Nombrada. No operable en esta versión.',
  },
]

export default function Inicio() {
  const sesion = useSesion()

  if (sesion.fase === 'cargando')
    return (
      <main className="pagina">
        <p className="estado">Cargando…</p>
      </main>
    )
  if (sesion.fase === 'caida')
    return (
      <main className="pagina">
        <p role="alert" className="alerta">La API no está disponible: nada se puede leer ni confirmar.</p>
      </main>
    )
  if (sesion.fase === 'fuera')
    return (
      <main className="pagina">
        <p>Sesión cerrada. <a href="/login">Inicia sesión</a>.</p>
      </main>
    )

  return (
    <main className="pagina">
      <section className="plataforma-hero">
        <p className="plataforma-hero-rotulo">Grupo Salman · Plataforma</p>
        <h1 className="plataforma-hero-titulo">Herencia</h1>
        <p className="plataforma-hero-texto">
          Un núcleo con identidad, autorización, efecto del pago y auditoría.
          Cada módulo cubre solo su operación.
        </p>
        <p className="plataforma-hero-sesion">
          <span className="plataforma-chip">{sesion.usuario.empresa_id}</span>
          <span className="plataforma-chip suave">
            {sesion.usuario.usuario} · {sesion.usuario.rol}
          </span>
        </p>
      </section>

      <p className="nav-rotulo oscuro">Módulos</p>
      <section className="modulos-rejilla">
        {MODULOS.map((m) =>
          m.estado === 'operable' ? (
            <Link key={m.nombre} href={m.href} className="modulo-tarjeta operable">
              <div className="modulo-cabecera">
                <span className="modulo-rotulo">Módulo</span>
                <span className="modulo-insignia operable">Operable</span>
              </div>
              <div className="modulo-nombre-fila">
                <m.icono />
                <span className="modulo-nombre">{m.nombre}</span>
              </div>
              <span className="modulo-descripcion">{m.descripcion}</span>
              <span className="modulo-accion">Entrar al módulo →</span>
            </Link>
          ) : (
            <div key={m.nombre} className="modulo-tarjeta cerrado" aria-disabled="true">
              <div className="modulo-cabecera">
                <span className="modulo-rotulo">Módulo</span>
                <span className="modulo-insignia cerrado">Cerrada</span>
              </div>
              <div className="modulo-nombre-fila">
                <m.icono />
                <span className="modulo-nombre">{m.nombre}</span>
              </div>
              <span className="modulo-descripcion">{m.descripcion}</span>
              <span className="modulo-candado">En esta versión no se opera</span>
            </div>
          )
        )}
      </section>
    </main>
  )
}
