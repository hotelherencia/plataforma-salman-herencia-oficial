'use client'

import { useState } from 'react'
import { api, MarcoHotel, SalidaJson, Campo } from '../../../lib/api'

export default function Oferta() {
  const [consulta, setConsulta] = useState({ inicio: '2026-11-10', fin: '2026-11-12', personas: '2' })
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')

  async function buscar(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    try {
      const params = new URLSearchParams({
        inicio: consulta.inicio,
        fin: consulta.fin,
        personas: consulta.personas,
      })
      const r = await api(`/hotel/oferta?${params}`)
      if (r.estado >= 400) setError(JSON.stringify(r.datos))
      else setSalida(r.datos)
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Oferta: disponibilidad y tarifa vigente">
      <form onSubmit={buscar}>
        <Campo etiqueta="Desde" type="date" value={consulta.inicio} onChange={(e) => setConsulta({ ...consulta, inicio: e.target.value })} />
        <Campo etiqueta="Hasta" type="date" value={consulta.fin} onChange={(e) => setConsulta({ ...consulta, fin: e.target.value })} />
        <Campo etiqueta="Personas" type="number" value={consulta.personas} onChange={(e) => setConsulta({ ...consulta, personas: e.target.value })} />
        <button type="submit">Consultar oferta</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {salida && (
        <>
          <p>
            Oferta emitida {salida.emitida_en} · vigente {salida.vigencia_minutos} minutos
          </p>
          <ul>
            {salida.oferta.map((item) => (
              <li key={item.habitacion_id}>
                {item.habitacion_id} ({item.tipo}) — ${item.tarifa_noche_clp}/noche · total ${item.total_clp} ·{' '}
                {item.politica_cancelacion}
              </li>
            ))}
          </ul>
          {salida.oferta.length === 0 && <p>Sin disponibilidad para esas fechas.</p>}
        </>
      )}
    </MarcoHotel>
  )
}
