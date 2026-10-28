'use client'

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
  async function salir() {
    try {
      await api('/sesion', { metodo: 'DELETE' })
    } finally {
      window.location.href = '/login'
    }
  }

  return (
    <nav style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem', fontSize: '0.95rem' }}>
      <strong>Herencia</strong>
      {ENLACES.map(([ruta, nombre]) => (
        <a key={ruta} href={ruta}>{nombre}</a>
      ))}
      <span style={{ color: '#999' }}>Cafetería · Inmobiliaria · Constructora (fuera de V1)</span>
      <button onClick={salir} style={{ marginLeft: 'auto' }}>Salir</button>
    </nav>
  )
}
