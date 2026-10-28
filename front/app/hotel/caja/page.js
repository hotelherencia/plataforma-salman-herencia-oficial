'use client'

import { useState } from 'react'
import { api, MarcoHotel, Campo } from '../../../lib/api'

export default function Caja() {
  const hoy = new Date().toISOString().slice(0, 10)
  const [fecha, setFecha] = useState(hoy)
  const [caja, setCaja] = useState(null)
  const [error, setError] = useState('')

  async function consultar(e) {
    e.preventDefault()
    setError('')
    setCaja(null)
    try {
      const r = await api(`/hotel/caja?fecha=${fecha}`)
      if (r.estado >= 400) setError(JSON.stringify(r.datos))
      else setCaja(r.datos)
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Caja del día">
      <form onSubmit={consultar}>
        <Campo etiqueta="Fecha" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
        <button type="submit">Ver caja</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {caja && (
        <>
          <p>
            Total del día: <strong>${caja.total_clp}</strong>
          </p>
          <ul>
            {caja.pagos.map((p) => (
              <li key={p.pago_id}>
                {p.pago_id} · reserva {p.reserva_id} · habitación {p.habitacion_id} · ${p.monto_clp} · {p.modo} · {p.estado}
              </li>
            ))}
          </ul>
          {caja.pagos.length === 0 && <p>Sin pagos registrados en esta fecha.</p>}
        </>
      )}
    </MarcoHotel>
  )
}
