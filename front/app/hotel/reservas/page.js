'use client'

import { useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, Campo, CampoSelect, useSesion } from '../../../lib/api'
import { ListaReservas, ReservasVacias } from '../_componentes/lista-reservas'

export default function Reservas() {
  const sesion = useSesion()
  const [filtros, setFiltros] = useState({ desde: '', hasta: '', fecha: '', estado: '', texto: '', habitacion_id: '' })
  const [resultado, setResultado] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  async function buscar(e) {
    if (e) e.preventDefault()
    setError('')
    setCargando(true)
    const params = new URLSearchParams()
    for (const campo of ['desde', 'hasta', 'fecha', 'estado', 'texto', 'habitacion_id']) {
      if (filtros[campo]) params.set(campo, filtros[campo].trim())
    }
    try {
      const r = await api(`/hotel/reservas?${params}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setResultado(r.datos)
    } catch {
      setError('La API no está disponible')
    } finally {
      setCargando(false)
    }
  }

  // Al entrar se listan las reservas de la empresa (sin filtros): la página
  // nace con datos; el formulario solo acota lo que ya se ve.
  useEffect(() => {
    if (sesion.fase === 'ok') buscar(null)
  }, [sesion.fase])

  return (
    <MarcoHotel titulo="Buscar reservas">
      <section className="tarjeta">
        <form className="formulario" onSubmit={buscar}>
          <Campo etiqueta="Periodo desde" type="date" value={filtros.desde} onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })} />
          <Campo etiqueta="Periodo hasta (sin incluir)" type="date" value={filtros.hasta} onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })} />
          <Campo etiqueta="Fecha (la noche contiene ese día)" type="date" value={filtros.fecha} onChange={(e) => setFiltros({ ...filtros, fecha: e.target.value })} />
          <Campo etiqueta="Habitación (exacta)" value={filtros.habitacion_id} onChange={(e) => setFiltros({ ...filtros, habitacion_id: e.target.value })} />
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
        <p className="nota-clave">
          Periodo: lista las reservas que tienen al menos una noche entre «desde» y «hasta». Los filtros se combinan con Y.
          Abre una reserva para ver su cuenta (cargos, pagos y saldo).
        </p>
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      {cargando && <p className="estado">Buscando…</p>}
      {resultado &&
        (resultado.reservas.length === 0 ? (
          <ReservasVacias />
        ) : (
          <ListaReservas reservas={resultado.reservas} total={resultado.total} />
        ))}
    </MarcoHotel>
  )
}
