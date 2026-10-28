'use client'

import { useState } from 'react'
import { api, MarcoHotel, SalidaJson, Campo } from '../../../lib/api'

export default function SalidaPage() {
  const [reservaId, setReservaId] = useState('')
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')

  async function checkOut(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    try {
      const r = await api(`/hotel/reservas/${reservaId}/salida`, {
        metodo: 'POST',
        claveIdempotencia: crypto.randomUUID(),
        cuerpo: {},
      })
      if (r.estado >= 400) setError(JSON.stringify(r.datos))
      else setSalida(r.datos)
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Check-out (salida y liquidación)">
      <form onSubmit={checkOut}>
        <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
        <button type="submit">Liquidar cuenta</button>
      </form>
      {error && <p role="alert">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
