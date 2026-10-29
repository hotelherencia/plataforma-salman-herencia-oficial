'use client'

import { useState } from 'react'
import { api, MarcoHotel, Campo } from '../../../lib/api'

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
      <section className="tarjeta">
        <form className="formulario" onSubmit={buscar}>
          <Campo etiqueta="Desde" type="date" value={consulta.inicio} onChange={(e) => setConsulta({ ...consulta, inicio: e.target.value })} />
          <Campo etiqueta="Hasta" type="date" value={consulta.fin} onChange={(e) => setConsulta({ ...consulta, fin: e.target.value })} />
          <Campo etiqueta="Personas" type="number" value={consulta.personas} onChange={(e) => setConsulta({ ...consulta, personas: e.target.value })} />
          <button type="submit" className="boton-primario">Consultar oferta</button>
        </form>
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      {salida && (
        <>
          <p className="nota-clave">
            Oferta emitida {salida.emitida_en} · vigente {salida.vigencia_minutos} minutos
          </p>
          <ul className="resultados">
            {salida.oferta.map((item) => (
              <li key={item.habitacion_id} className="resultado-item">
                <span className="resultado-id">{item.habitacion_id}</span>
                <span className="resultado-dato">{item.tipo}</span>
                <span className="resultado-dato">${item.tarifa_noche_clp}/noche</span>
                <span className="resultado-precio">total ${item.total_clp}</span>
                <span className="resultado-dato">{item.politica_cancelacion}</span>
              </li>
            ))}
          </ul>
          {salida.oferta.length === 0 && <p className="estado">Sin disponibilidad para esas fechas.</p>}
        </>
      )}
    </MarcoHotel>
  )
}
