'use client'

import { useState } from 'react'
import { api, MarcoHotel, SalidaJson, Campo } from '../../../lib/api'

export default function Estadia() {
  const [reservaId, setReservaId] = useState('')
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')

  async function checkIn(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    try {
      const r = await api(`/hotel/reservas/${reservaId}/entrada`, {
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
    <MarcoHotel titulo="Check-in (entrada a la estadía)">
      <section className="tarjeta">
        <form className="formulario" onSubmit={checkIn}>
          <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
          <button type="submit" className="boton-primario">Registrar entrada</button>
        </form>
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
