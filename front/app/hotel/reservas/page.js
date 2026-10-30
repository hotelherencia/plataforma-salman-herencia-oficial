'use client'

import { useState } from 'react'
import { api, MarcoHotel, Campo, CampoSelect } from '../../../lib/api'
import { ListaReservas, ReservasVacias } from '../_componentes/lista-reservas'

export default function Reservas() {
  const [filtros, setFiltros] = useState({ fecha: '', estado: '', texto: '' })
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState('')

  async function buscar(e) {
    e.preventDefault()
    setError('')
    setResultado(null)
    const params = new URLSearchParams()
    if (filtros.fecha) params.set('fecha', filtros.fecha)
    if (filtros.estado) params.set('estado', filtros.estado)
    if (filtros.texto) params.set('texto', filtros.texto)
    try {
      const r = await api(`/hotel/reservas?${params}`)
      if (r.estado >= 400) setError(JSON.stringify(r.datos))
      else setResultado(r.datos)
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Buscar reservas">
      <section className="tarjeta">
        <form className="formulario" onSubmit={buscar}>
          <Campo etiqueta="Fecha (la noche contiene ese día)" type="date" value={filtros.fecha} onChange={(e) => setFiltros({ ...filtros, fecha: e.target.value })} />
          <CampoSelect etiqueta="Estado" value={filtros.estado} onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}>
            <option value="">(cualquiera)</option>
            <option value="confirmada">confirmada</option>
            <option value="en_estadia">en_estadia</option>
            <option value="finalizada">finalizada</option>
            <option value="cancelada">cancelada</option>
          </CampoSelect>
          <Campo etiqueta="Texto (id, huésped, documento o habitación)" value={filtros.texto} onChange={(e) => setFiltros({ ...filtros, texto: e.target.value })} />
          <button type="submit" className="boton-primario">Buscar</button>
        </form>
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      {resultado &&
        (resultado.reservas.length === 0 ? (
          <ReservasVacias />
        ) : (
          <ListaReservas reservas={resultado.reservas} total={resultado.total} />
        ))}
    </MarcoHotel>
  )
}
