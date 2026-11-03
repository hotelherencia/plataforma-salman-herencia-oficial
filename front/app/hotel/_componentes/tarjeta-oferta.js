'use client'

import Link from 'next/link'

/**
 * Capa del módulo Hotel — oferta (pura, sin fetch): recibe solo props y
 * dibuja la respuesta de GET /hotel/oferta tal cual la envía la API — no
 * calcula tarifa, cupo ni totales.
 *
 * Presentación adaptada a mano desde «Project Detail View» de @kavikatiyar
 * (21st.dev, id 8248): ficha de registro con encabezado (título + insignia)
 * y campos etiquetados con icono. Sin fotos, estrellas ni llamados
 * comerciales — es una ficha operativa. Colores y tipografías en tokens de
 * globals.css.
 */

function IconoEscudo() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  )
}

function IconoReloj() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  )
}

function IconoEtiqueta() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z" />
      <circle cx="7.5" cy="7.5" r="0.5" fill="currentColor" />
    </svg>
  )
}

export function CabeceraOferta({ emitidaEn, vigenciaMinutos, cantidad }) {
  return (
    <div className="oferta-cabecera">
      <div className="oferta-estadistica">
        <span className="oferta-numero">{cantidad}</span>
        <span className="oferta-etiqueta">{cantidad === 1 ? 'habitación disponible' : 'habitaciones disponibles'}</span>
      </div>
      <div className="oferta-estadistica">
        <span className="oferta-etiqueta">oferta emitida</span>
        <span className="oferta-valor">{emitidaEn}</span>
      </div>
      <div className="oferta-estadistica">
        <span className="oferta-etiqueta">vigente</span>
        <span className="oferta-valor">{vigenciaMinutos} minutos</span>
      </div>
    </div>
  )
}

export function TarjetaOferta({ habitacionId, tipo, tarifaNocheClp, totalClp, politicaCancelacion, vigenteHasta, inicio, fin }) {
  return (
    <li className="ficha-oferta">
      <div className="ficha-oferta-cabecera">
        <span className="ficha-oferta-titulo">{habitacionId}</span>
        <span className="ficha-oferta-badge">{tipo}</span>
      </div>
      <div className="ficha-oferta-campos">
        <div className="ficha-campo">
          <span className="ficha-campo-etiqueta"><IconoEtiqueta /> total de la estadía</span>
          <span className="ficha-campo-valor ficha-precio">${totalClp}</span>
        </div>
        <div className="ficha-campo">
          <span className="ficha-campo-etiqueta">tarifa por noche</span>
          <span className="ficha-campo-valor">${tarifaNocheClp}</span>
        </div>
        <div className="ficha-campo ancho">
          <span className="ficha-campo-etiqueta"><IconoEscudo /> política de cancelación</span>
          <span className="ficha-campo-valor">{politicaCancelacion}</span>
        </div>
        <div className="ficha-campo ancho">
          <span className="ficha-campo-etiqueta"><IconoReloj /> vigencia de la oferta</span>
          <span className="ficha-campo-valor ficha-validez">vigente hasta {vigenteHasta}</span>
        </div>
      </div>
      <Link
        className="boton-primario ficha-oferta-accion"
        href={`/hotel/reserva?habitacion_id=${encodeURIComponent(habitacionId)}&inicio=${encodeURIComponent(inicio || '')}&fin=${encodeURIComponent(fin || '')}`}
      >
        Reservar estas noches
      </Link>
    </li>
  )
}

export function OfertaVacia() {
  return (
    <div className="oferta-vacia">
      <p className="oferta-vacia-titulo">Sin disponibilidad para esas fechas</p>
      <p className="oferta-vacia-texto">Probá con otro rango: la API responde solo lo vendible en ese período.</p>
    </div>
  )
}
