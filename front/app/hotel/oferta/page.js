'use client'

import { useState } from 'react'
import { api, MarcoHotel, Campo } from '../../../lib/api'
import { CabeceraOferta, TarjetaOferta, OfertaVacia } from '../_componentes/tarjeta-oferta'

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
          <CabeceraOferta
            cantidad={salida.oferta.length}
            emitidaEn={salida.emitida_en}
            vigenciaMinutos={salida.vigencia_minutos}
          />
          {salida.oferta.length === 0 ? (
            <OfertaVacia />
          ) : (
            <ul className="oferta-rejilla">
              {salida.oferta.map((item) => (
                <TarjetaOferta
                  key={item.habitacion_id}
                  habitacionId={item.habitacion_id}
                  tipo={item.tipo}
                  tarifaNocheClp={item.tarifa_noche_clp}
                  totalClp={item.total_clp}
                  politicaCancelacion={item.politica_cancelacion}
                  vigenteHasta={item.vigente_hasta}
                />
              ))}
            </ul>
          )}
        </>
      )}
    </MarcoHotel>
  )
}
